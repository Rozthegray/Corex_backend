import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class LeadershipTenure(Base):
    __tablename__ = "leadership_tenures"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # RESTRICT ensures a user record cannot be deleted if they were a President, preserving financial audit trails
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    
    academic_session: Mapped[str] = mapped_column(String(32), nullable=False)
    paystack_subaccount_code: Mapped[str] = mapped_column(String(128), nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
    
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    concluded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationship back to the User model
    user = relationship("User", back_populates="tenures")