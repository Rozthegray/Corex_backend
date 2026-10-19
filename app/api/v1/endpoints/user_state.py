from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, AcademicLevel, AcademicPathway
from app.models.chat import ChatSession
from app.models.mock_exam import MockExamAttempt

router = APIRouter()

class ProfileUpdateRequest(BaseModel):
    level: AcademicLevel | None = None
    pathway: AcademicPathway | None = None

@router.get("/profile")
async def get_user_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Calculate stats
    sessions_count = await db.scalar(
        select(func.count(ChatSession.id)).where(ChatSession.user_id == current_user.id)
    )
    exams_count = await db.scalar(
        select(func.count(MockExamAttempt.id)).where(MockExamAttempt.user_id == current_user.id)
    )

    return {
        "id": str(current_user.id),
        "full_name": current_user.full_name,
        "email": current_user.email,
        "matric_number": current_user.matric_number,
        "level": current_user.level.value,
        "pathway": current_user.pathway.value,
        "account_type": current_user.account_type.value,
        "role": current_user.role.value,
        "tokens_remaining": current_user.tokens_remaining,
        "pdf_quota_remaining": current_user.pdf_quota_remaining,
        "history_summary": {
            "total_chat_sessions": sessions_count or 0,
            "mock_exams_attempted": exams_count or 0
        }
    }

@router.patch("/profile")
async def update_user_academics(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if payload.level:
        current_user.level = payload.level
    if payload.pathway:
        current_user.pathway = payload.pathway
        
    await db.commit()
    return {"status": "success", "level": current_user.level.value, "pathway": current_user.pathway.value}