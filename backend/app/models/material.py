from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.db.database import Base


class Material(Base):
    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    text_content = Column(Text, nullable=False, default="")
    sha256 = Column(String, nullable=False, unique=True)
    language = Column(String, nullable=False)
    class_level = Column(String, nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    teacher = relationship("Teacher")

    sessions = relationship("ReadingSession", back_populates="material")
