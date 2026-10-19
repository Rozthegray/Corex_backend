import uuid
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.core.database import Base

class LibraryDocument(Base):
    __tablename__ = "library_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    file_url = Column(String(255), nullable=False) # URL to AWS S3/Cloudinary/Neon
    course_code = Column(String(20), nullable=False)
    
    # Gating parameters
    level = Column(String(50), nullable=False)     # e.g., "HND I"
    pathway = Column(String(100), nullable=False)  # e.g., "Computer Engineering"
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class MockExam(Base):
    __tablename__ = "mock_exams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    course_code = Column(String(20), nullable=False)
    duration_minutes = Column(Integer, default=60)
    
    # Storing exam questions as a JSON array for easy frontend parsing
    questions = Column(JSONB, nullable=False) 
    
    # Gating parameters
    level = Column(String(50), nullable=False)
    pathway = Column(String(100), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())