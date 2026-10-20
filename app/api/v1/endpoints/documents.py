import os
import shutil
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, UserRole
from app.models.document import Document, DocCategory
from app.services.rag.extractor import extract_multimodal_content
from app.services.rag.chunker import chunk_text
from app.services.rag.embedder import generate_and_upsert_vectors

router = APIRouter()

# Create a local storage directory for uploaded PDFs and Images
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# STRICTLY NO TRAILING SLASH: "/upload" prevents the 307 Redirect CORS crash
# STRICTLY NO TRAILING SLASH: "/upload" prevents the 307 Redirect CORS crash
@router.post("/upload")
async def upload_academic_document(
    title: str = Form(...),
    course_code: str = Form(...),
    lecturer_name: str = Form(""),
    category: DocCategory = Form(...),
    file: UploadFile = File(...),
    # 1. TEMPORARILY DISABLE AUTH DEPENDENCY
    # current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 2. TEMPORARILY DISABLE ROLE CHECK
    # if current_user.role not in [UserRole.president, UserRole.superadmin]:
    #     raise HTTPException(status_code=403, detail="Not authorized to ingest documents.")

    valid_extensions = ('.pdf', '.png', '.jpg', '.jpeg')
    if not file.filename.lower().endswith(valid_extensions):
        raise HTTPException(status_code=400, detail="Only PDF and Image files are supported.")

    # 1. Save the file locally to the `uploads/` folder
    safe_filename = f"{uuid.uuid4().hex[:8]}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 2. Read back into memory for AI Extraction (OCR + PyMuPDF)
    with open(file_path, "rb") as f:
        file_bytes = f.read()
        
    raw_text = extract_multimodal_content(file_bytes, file.filename)
    if not raw_text.strip():
        os.remove(file_path)
        raise HTTPException(status_code=400, detail="Could not extract text or OCR content.")

    # 3. AI Vector Ingestion Pipeline
    chunks = chunk_text(raw_text)
    total_vectors = await generate_and_upsert_vectors(
        chunks=chunks,
        course_code=course_code,
        lecturer_name=lecturer_name,
        title=title,
        category=category.value
    )

    # 4. RE-ENABLED DB SAVE: This ensures the file appears in the Student Library
    document = Document(
        title=title,
        course_code=course_code,
        lecturer_name=lecturer_name,
        category=category,
        file_url=safe_filename, 
        # Hardcode a fallback ID or UUID if current_user is still disabled for testing
        uploaded_by="00000000-0000-0000-0000-000000000000" 
    )
    db.add(document)
    await db.commit()

    return {
        "detail": "Document ingested, OCR processed, and vectorized.", 
        "pinecone_vectors_created": total_vectors
    }

@router.get("/library")
async def get_student_library(
    category: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Allows students to browse available documents."""
    stmt = select(Document).order_by(desc(Document.created_at))
    if category:
        stmt = stmt.where(Document.category == category)
        
    result = await db.execute(stmt)
    docs = result.scalars().all()
    
    return [
        {
            "id": str(d.id),
            "title": d.title,
            "course_code": d.course_code,
            "lecturer_name": d.lecturer_name,
            "category": d.category.value,
            "date": d.created_at.isoformat()
        } for d in docs
    ]

@router.get("/{document_id}/download")
async def download_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Securely streams the raw PDF/Image file to the student."""
    stmt = select(Document).where(Document.id == document_id)
    document = (await db.execute(stmt)).scalar_one_or_none()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found in archive.")
        
    file_path = os.path.join(UPLOAD_DIR, document.file_url)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Physical file missing from storage.")
        
    # Return as a downloadable attachment
    return FileResponse(
        path=file_path, 
        filename=f"{document.course_code}_{document.title}{os.path.splitext(document.file_url)[1]}",
        media_type="application/octet-stream"
    )