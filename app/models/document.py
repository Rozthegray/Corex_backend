import uuid
import enum
from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Enum, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.core.database import Base

class DocCategory(str, enum.Enum):
    syllabus = "syllabus"
    project_manual = "project_manual"
    lecturer_guide = "lecturer_guide"
    past_question = "past_question"

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    course_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    lecturer_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    category: Mapped[DocCategory] = mapped_column(Enum(DocCategory), nullable=False)
    file_url: Mapped[str] = mapped_column(Text, nullable=False)
    
    # If a user is deleted, their uploaded documents remain in the archive, but uploader becomes NULL
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    # Restored as a unidirectional relationship to prevent mapper crashes
    uploader = relationship("User")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # If a document is deleted, all its vector chunks are purged automatically
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # 1536 dimensions matches Anthropic/OpenAI embedding standards
    # Note: mapped_column(Vector(1536)) handles the pgvector type mapping
    embedding = mapped_column(Vector(1536))
    
    # Map to 'metadata' in DB, but 'chunk_metadata' in Python to avoid SQLAlchemy conflicts
    chunk_metadata: Mapped[dict] = mapped_column("metadata", JSONB, server_default='{}')

    # Relationships
    document = relationship("Document", back_populates="chunks")

    # Table-level configurations (Indices)
    __table_args__ = (
        Index(
            "idx_document_chunks_embedding",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )