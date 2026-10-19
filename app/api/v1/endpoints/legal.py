from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()

@router.delete("/user")
async def delete_user_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Permanently purges the user. PostgreSQL foreign keys (ON DELETE CASCADE) 
    automatically drop their associated Paystack transaction logs. Their uploaded 
    documents remain (ON DELETE SET NULL) to preserve the public knowledge base.
    """
    if current_user.role == "president":
        raise HTTPException(
            status_code=400, 
            detail="Active President cannot delete account. Complete tenure handoff first."
        )
        
    await db.delete(current_user)
    await db.commit()
    
    return {"detail": "Account and associated data permanently purged."}