from sqlalchemy import Column, String, Text, ForeignKey, DateTime
from sqlalchemy.sql import func
import uuid
from app.core.database import Base # Adjust if your Base import differs

class Question(Base):
    __tablename__ = "questions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    course_code = Column(String, index=True, nullable=False)
    content = Column(Text, nullable=False)
    
    # The new column to store the local path of the uploaded diagram/image
    image_url = Column(String, nullable=True) 
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())