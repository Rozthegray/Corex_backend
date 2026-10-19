import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Numeric, DateTime, ForeignKey, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class PaymentStatus(str, enum.Enum):
    pending = "pending"
    successful = "successful"
    failed = "failed"

class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # If a user is deleted, their transactions are cascade deleted (financial audit requires only aggregate sums or external Paystack logs)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    reference: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    
    amount_naira: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    reserve_amount_naira: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    president_amount_naira: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.pending)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    user = relationship("User", back_populates="transactions")