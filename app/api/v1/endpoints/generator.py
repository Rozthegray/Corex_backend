import time
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.redis import redis_client
from app.api.deps import get_current_user
from app.models.user import User
from app.services.pdf.engine import compile_academic_pdf

router = APIRouter()

class DocumentGenerationRequest(BaseModel):
    markdown_content: str
    include_cover: bool = False
    title: str | None = None
    course_code: str | None = None
    lecturer_name: str | None = None

@router.post("/render-pdf")
async def render_pdf_document(
    payload: DocumentGenerationRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Rate Limiting via Redis (Max 2 PDF generations per minute per user)
    rl_key = f"rl:pdf:{current_user.id}"
    current_requests = await redis_client.incr(rl_key)
    if current_requests == 1:
        await redis_client.expire(rl_key, 60) # 60-second sliding window
        
    if current_requests > 2:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Please wait a minute.")

    # 2. Database Quota Enforcement
    if current_user.pdf_quota_remaining <= 0:
        raise HTTPException(
            status_code=403, 
            detail="PDF generation quota exhausted. Upgrade to Pro for 10 more exports."
        )

    # 3. Compile Document
    metadata = {
        "title": payload.title or "Untitled Document",
        "course_code": payload.course_code or "",
        "lecturer_name": payload.lecturer_name or "",
        "student_name": current_user.full_name,
        "matric_number": current_user.matric_number or "N/A"
    }

    try:
        # Offload to WeasyPrint (can be moved to ARQ/Celery for extremely large documents)
        pdf_bytes = compile_academic_pdf(
            markdown_content=payload.markdown_content,
            include_cover=payload.include_cover,
            metadata=metadata
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF Compilation failed: {str(e)}")

    # 4. Deduct Quota (only deduct if compilation succeeds)
    current_user.pdf_quota_remaining -= 1
    await db.commit()

    # 5. Return Binary Stream
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{metadata["course_code"]}_Report.pdf"'
        }
    )