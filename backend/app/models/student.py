from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.database import Base


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    class_name = Column(String, nullable=False)
    roll_no = Column(String, nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    teacher = relationship("Teacher", back_populates="students")
    sessions = relationship("ReadingSession", back_populates="student")
