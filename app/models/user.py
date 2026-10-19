import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Boolean, Integer, DateTime, func, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class UserRole(str, enum.Enum):
    student = "student"
    president = "president"
    superadmin = "superadmin"

class AcademicLevel(str, enum.Enum):
    nd1 = "ND I"
    nd2 = "ND II"
    hnd1 = "HND I"
    hnd2 = "HND II"

class AcademicPathway(str, enum.Enum):
    hardware_embedded = "Computer Hardware & Embedded Systems"
    software_systems = "Software Systems & Networking"
    telecommunications = "Telecommunications & Signal Processing"
    general = "Computer Engineering"

class AccountType(str, enum.Enum):
    free = "free"
    pro = "pro"
    department_scholar = "scholar"

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    matric_number: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    
    # String reference links this directly to your chat.py model without importing it
    chat_sessions: Mapped[list["ChatSession"]] = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")

    # Academic & Level Tracking
    level: Mapped[AcademicLevel] = mapped_column(Enum(AcademicLevel), default=AcademicLevel.nd1)
    pathway: Mapped[AcademicPathway] = mapped_column(
        Enum(AcademicPathway), default=AcademicPathway.hardware_embedded
    )

    # Roles, Billing, Quotas & Token Meters
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.student)
    account_type: Mapped[AccountType] = mapped_column(Enum(AccountType), default=AccountType.free)
    tokens_remaining: Mapped[int] = mapped_column(Integer, default=50000)  # Token bucket
    pdf_quota_remaining: Mapped[int] = mapped_column(Integer, default=3)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships (Commented out until their respective models are built and imported)
    # documents = relationship("Document", back_populates="uploader", cascade="all, delete-orphan")
    # transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    # chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    # user_media = relationship("MediaAsset", back_populates="user", cascade="all, delete-orphan")
    # mock_attempts = relationship("MockExamAttempt", back_populates="user", cascade="all, delete-orphan")