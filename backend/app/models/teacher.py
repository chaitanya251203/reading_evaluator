from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.db.database import Base


class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    students = relationship("Student", back_populates="teacher")
