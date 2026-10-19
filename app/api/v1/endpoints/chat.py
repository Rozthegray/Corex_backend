import json
import uuid
from fastapi import APIRouter, HTTPException, Depends, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.core.pinecone import pinecone_index
from app.api.deps import get_current_user 
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage
from openai import AsyncOpenAI

# Import the PDF library we just installed
try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    HAS_FPDF = False

router = APIRouter()
openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

# --- SCHEMAS ---
class ChatRequest(BaseModel):
    message: str
    course_code: Optional[str] = None
    session_id: Optional[str] = None  # Added so we can continue existing chats!

class ImageRequest(BaseModel):
    prompt: str

class PDFRequest(BaseModel):
    title: str = "Research_Report"
    content: str


# --- 1. CHAT HISTORY ROUTES (For the Sidebar) ---
@router.get("/sessions")
async def get_chat_sessions(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Fetch all chat sessions for the sidebar history."""
    stmt = select(ChatSession).where(ChatSession.user_id == current_user.id).order_by(ChatSession.updated_at.desc())
    result = await db.execute(stmt)
    return {"sessions": result.scalars().all()}

@router.get("/sessions/{session_id}")
async def get_session_messages(session_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Fetch all messages inside a specific session."""
    stmt = select(ChatSession).where(ChatSession.id == uuid.UUID(session_id), ChatSession.user_id == current_user.id)
    session = (await db.execute(stmt)).scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    msg_stmt = select(ChatMessage).where(ChatMessage.session_id == session.id).order_by(ChatMessage.created_at.asc())
    messages = (await db.execute(msg_stmt)).scalars().all()
    return {"session": session, "messages": messages}


# --- 2. OPENAI IMAGE GENERATION ROUTE ---
# --- 2. OPENAI IMAGE GENERATION ROUTE ---
@router.post("/image")
async def generate_image(request: ImageRequest, current_user: User = Depends(get_current_user)):
    try:
        response = await openai_client.images.generate(
            model="gpt-image-2.5-flare", # Replaces the deprecated DALL-E models
            prompt=request.prompt,
            size="1024x1024",
            n=1,
        )
        return {"image_url": response.data[0].url}
    except Exception as e:
        error_msg = str(e).lower()
        if "billing" in error_msg or "tier" in error_msg or "quota" in error_msg:
            raise HTTPException(status_code=402, detail="OpenAI Billing Error: Verify your $5 credit is active.")
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")
# --- 3. PDF GENERATION ROUTE ---
@router.post("/pdf")
async def generate_pdf(request: PDFRequest, current_user: User = Depends(get_current_user)):
    """Converts the AI's markdown report into a downloadable PDF."""
    if not HAS_FPDF:
        raise HTTPException(status_code=500, detail="FPDF is missing. Run: pip install fpdf2")
    
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("helvetica", size=12)
        
        # Add Title
        pdf.set_font("helvetica", style="B", size=16)
        pdf.cell(0, 10, request.title, new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(10)
        
        # Add Body Content
        pdf.set_font("helvetica", size=11)
        # Encode and decode to handle potential special characters gracefully
        safe_content = request.content.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 8, safe_content)
        
        pdf_bytes = pdf.output()
        
        return Response(
            content=bytes(pdf_bytes), 
            media_type="application/pdf", 
            headers={"Content-Disposition": f"attachment; filename={request.title}.pdf"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF conversion failed: {str(e)}")


# --- 4. MAIN STREAMING ROUTE ---
@router.post("/stream")
async def chat_stream(request: ChatRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    
    # 1. Handle Chat Session Logic
    if request.session_id:
        chat_session_id = uuid.UUID(request.session_id)
    else:
        chat_session = ChatSession(
            user_id=current_user.id,
            course_code=request.course_code,
            title=request.message[:40] + "..." 
        )
        db.add(chat_session)
        await db.flush() 
        chat_session_id = chat_session.id

    # 2. Save the User's Message
    user_msg = ChatMessage(session_id=chat_session_id, role="user", content=request.message)
    db.add(user_msg)
    await db.commit()

    # 3. Pinecone Context 
    try:
        embed_res = await openai_client.embeddings.create(
            input=request.message,
            model="text-embedding-3-small",
            dimensions=1536 
        )
        query_vector = embed_res.data[0].embedding
        
        filter_dict = {"course_code": {"$eq": request.course_code}} if request.course_code else None
        search_res = pinecone_index.query(vector=query_vector, top_k=5, include_metadata=True, filter=filter_dict)
        joined_context = "\n\n---\n\n".join([m.metadata.get("text", "") for m in search_res.matches if "text" in m.metadata])
    except Exception:
        joined_context = "No archive context found."

    # 4. System Prompt
    system_prompt = f"""You are Corex AI, the official academic archive assistant for {current_user.full_name}.

    INTENT DETECTION RULES:
    1. IMAGE GENERATION: To draw an image, reply with a vivid description and output EXACTLY: [TRIGGER_IMAGE_GENERATION: <prompt>]
    2. PDF GENERATION: To generate a PDF report, output EXACTLY: [TRIGGER_PDF_GENERATION]
    3. RESEARCH REPORTS: Ask for Title, Course Code, Student Name, Matric Number, Department, and Lecturer Name. Once provided, write a deeply analytical academic report.

    CONTEXT:
    {joined_context}
    """

    # 5. Stream the Response
    async def event_generator():
        full_response = ""
        try:
            stream = await openai_client.chat.completions.create(
                model="gpt-4o-mini", 
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": request.message}
                ],
                stream=True
            )
            async for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_response += content
                    yield f"data: {json.dumps({'text': content, 'session_id': str(chat_session_id)})}\n\n"
            
            yield "data: [DONE]\n\n"

            # Save Assistant response
            assistant_msg = ChatMessage(session_id=chat_session_id, role="assistant", content=full_response)
            db.add(assistant_msg)
            await db.commit()
            
        except Exception as e:
            yield f"data: {json.dumps({'text': f'\\n\\n[Error: {str(e)}]'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")