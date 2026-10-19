from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, UserRole
from app.models.chat import ChatSession
# If you haven't created the Document model yet, this gracefully handles it
try:
    from app.models.document import Document
    HAS_LIBRARY = True
except ImportError:
    HAS_LIBRARY = False

router = APIRouter()

# Strict Admin Verification
def verify_admin(current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.president, UserRole.superadmin]:
        raise HTTPException(status_code=403, detail="Requires Department President privileges.")
    return current_user

@router.get("/stats")
async def get_system_stats(
    admin: User = Depends(verify_admin), 
    db: AsyncSession = Depends(get_db)
):
    """
    Aggregates comprehensive system telemetry: user counts, RAG indices, 
    financial routing, and recent system logs.
    """
    # 1. Core KPIs
    total_users = await db.scalar(select(func.count(User.id)))
    
    total_docs = 0
    if HAS_LIBRARY:
        total_docs = await db.scalar(select(func.count(Document.id)))
        
    # Assume roughly 25 vectors per document for the Pinecone estimate
    estimated_vectors = total_docs * 25 

    # 2. Financial Split Mock (In production, query your Transactions table or Paystack API)
    # Let's assume you have 10 Pro users paying ₦2,000 each for this example
    pro_users = await db.scalar(select(func.count(User.id)).where(User.account_type == "pro"))
    total_revenue = pro_users * 2000 if pro_users else 50000 # Default to 50k for UI testing if no pro users exist
    
    reserve_80 = total_revenue * 0.80
    stipend_20 = total_revenue * 0.20

    # 3. System Log (Recent User Registrations)
    log_stmt = select(User).order_by(desc(User.created_at)).limit(5)
    log_res = await db.execute(log_stmt)
    recent_users = log_res.scalars().all()
    
    system_log = []
    for u in recent_users:
        system_log.append({
            "id": str(u.id),
            "action": "NEW_STUDENT_REGISTERED",
            "details": f"{u.full_name} ({u.level} - {u.pathway}) joined the platform.",
            "timestamp": u.created_at.isoformat()
        })

    return {
        "users": total_users or 0,
        "documents": total_docs or 0,
        "pinecone_vectors": estimated_vectors or 0,
        "finances": {
            "total_revenue": total_revenue,
            "reserve_wallet_80": reserve_80,
            "president_stipend_20": stipend_20
        },
        "system_log": system_log
    }