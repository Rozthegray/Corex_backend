import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Text, Integer, Numeric, DateTime, ForeignKey, Enum, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class ExamType(str, enum.Enum):
    continuous_assessment = "test"  # CA Test (typically 30-40 marks)
    semester_exam = "exam"          # Final Semester Examination (60-70 marks)

class MockExam(Base):
    __tablename__ = "mock_exams"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    exam_type: Mapped[ExamType] = mapped_column(Enum(ExamType), default=ExamType.continuous_assessment)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    total_marks: Mapped[int] = mapped_column(Integer, default=100)
    
    # Stores generated questions, options/marking rubrics, and source past questions
    questions_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    attempts = relationship("MockExamAttempt", back_populates="mock_exam", cascade="all, delete-orphan")

class MockExamAttempt(Base):
    __tablename__ = "mock_exam_attempts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    mock_exam_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("mock_exams.id", ondelete="CASCADE"), nullable=False)
    
    student_submissions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    ai_evaluation: Mapped[dict] = mapped_column(JSONB, default=dict)
    score_achieved: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="mock_attempts")
    mock_exam = relationship("MockExam", back_populates="attempts")