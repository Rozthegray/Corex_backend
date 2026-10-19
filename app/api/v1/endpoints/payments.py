import uuid
import hmac
import hashlib
import json
from fastapi import APIRouter, Depends, Request, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User, SubscriptionTier
from app.models.payment import Transaction, PaymentStatus
from app.models.tenure import LeadershipTenure
from app.services.paystack import initialize_split_payment

router = APIRouter()

@router.post("/initiate")
async def initiate_checkout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Generates a checkout link for the Pro tier (₦500).
    Protected by the Idempotency Middleware.
    """
    idempotency_key = request.headers.get("x-idempotency-key")
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="X-Idempotency-Key header is required")

    # 1. Fetch the active Department President's subaccount
    stmt = select(LeadershipTenure).where(LeadershipTenure.is_current == True)
    result = await db.execute(stmt)
    active_tenure = result.scalar_one_or_none()
    
    if not active_tenure:
        raise HTTPException(status_code=500, detail="System configuration error: No active leadership tenure found.")

    # 2. Define amounts (₦500 total)
    total_amount_naira = 500.00
    reserve_amount_naira = 400.00
    president_amount_naira = 100.00
    amount_kobo = int(total_amount_naira * 100)
    
    reference = f"tx-{uuid.uuid4().hex[:16]}"

    # 3. Create pending transaction in DB
    transaction = Transaction(
        user_id=current_user.id,
        reference=reference,
        idempotency_key=idempotency_key,
        amount_naira=total_amount_naira,
        reserve_amount_naira=reserve_amount_naira,
        president_amount_naira=president_amount_naira,
        status=PaymentStatus.pending
    )
    db.add(transaction)
    await db.commit()

    # 4. Initialize with Paystack
    auth_url = await initialize_split_payment(
        email=current_user.email,
        amount_kobo=amount_kobo,
        reference=reference,
        subaccount_code=active_tenure.paystack_subaccount_code
    )

    return {"authorization_url": auth_url, "reference": reference}


@router.post("/webhook")
async def paystack_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Receives events from Paystack. Must verify the HMAC SHA512 signature.
    """
    payload = await request.body()
    signature = request.headers.get("x-paystack-signature")
    
    if not signature:
        raise HTTPException(status_code=400, detail="Missing signature")

    # 1. Verify the payload cryptographically
    expected_hash = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode('utf-8'),
        payload,
        hashlib.sha512
    ).hexdigest()

    if expected_hash != signature:
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_data = json.loads(payload)
    event_type = event_data.get("event")

    # 2. Process successful charge
    if event_type == "charge.success":
        reference = event_data["data"]["reference"]
        
        # Find the transaction
        stmt = select(Transaction).where(Transaction.reference == reference)
        result = await db.execute(stmt)
        transaction = result.scalar_one_or_none()
        
        if transaction and transaction.status == PaymentStatus.pending:
            # Mark as successful
            transaction.status = PaymentStatus.successful
            
            # Upgrade user to Pro and allocate monthly PDF quota
            user_stmt = select(User).where(User.id == transaction.user_id)
            user_res = await db.execute(user_stmt)
            user = user_res.scalar_one()
            
            user.tier = SubscriptionTier.pro
            user.pdf_quota_remaining += 10 # Add 10 pro PDF compilations
            
            await db.commit()

    return {"status": "success"}

    # Add to backend/app/api/v1/endpoints/payments.py

class TokenPurchaseRequest(BaseModel):
    package: str # e.g., "10k", "50k"

@router.post("/top-up-tokens")
async def purchase_tokens(
    payload: TokenPurchaseRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    idempotency_key = request.headers.get("x-idempotency-key")
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="X-Idempotency-Key required")

    # Pricing Engine
    packages = {
        "10k": {"tokens": 10000, "price_naira": 200.00},
        "50k": {"tokens": 50000, "price_naira": 800.00}
    }
    
    if payload.package not in packages:
        raise HTTPException(status_code=400, detail="Invalid token package")

    selected = packages[payload.package]
    amount_kobo = int(selected["price_naira"] * 100)
    reference = f"tk-{uuid.uuid4().hex[:16]}" # 'tk-' prefix identifies token purchases

    # Fetch President's subaccount for the 20% split
    tenure_stmt = select(LeadershipTenure).where(LeadershipTenure.is_current == True)
    active_tenure = (await db.execute(tenure_stmt)).scalar_one_or_none()
    
    # 80/20 split calculations
    reserve_naira = selected["price_naira"] * 0.8
    president_naira = selected["price_naira"] * 0.2

    transaction = Transaction(
        user_id=current_user.id,
        reference=reference,
        idempotency_key=idempotency_key,
        amount_naira=selected["price_naira"],
        reserve_amount_naira=reserve_naira,
        president_amount_naira=president_naira,
        status=PaymentStatus.pending
    )
    db.add(transaction)
    await db.commit()

    # Pass token metadata to Paystack so it returns in the webhook
    metadata = {"transaction_type": "token_top_up", "token_amount": selected["tokens"]}

    auth_url = await initialize_split_payment(
        email=current_user.email,
        amount_kobo=amount_kobo,
        reference=reference,
        subaccount_code=active_tenure.paystack_subaccount_code,
        metadata=metadata
    )
    return {"authorization_url": auth_url, "reference": reference}


@router.post("/webhook")
async def paystack_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    # ... (Keep existing signature verification logic) ...
    
    if event_type == "charge.success":
        reference = event_data["data"]["reference"]
        metadata = event_data["data"].get("metadata", {})
        
        stmt = select(Transaction).where(Transaction.reference == reference)
        transaction = (await db.execute(stmt)).scalar_one_or_none()
        
        if transaction and transaction.status == PaymentStatus.pending:
            transaction.status = PaymentStatus.successful
            
            user_stmt = select(User).where(User.id == transaction.user_id)
            user = (await db.execute(user_stmt)).scalar_one()
            
            # Route logic based on transaction type
            if metadata.get("transaction_type") == "token_top_up":
                user.tokens_remaining += int(metadata.get("token_amount", 0))
            else:
                # Default to Pro subscription logic
                user.tier = SubscriptionTier.pro
                user.pdf_quota_remaining += 10 
            
            await db.commit()

    return {"status": "success"}