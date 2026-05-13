from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship

from app.db.database import Base


class ReadingSession(Base):
    __tablename__ = "reading_sessions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    audio_path = Column(String, nullable=False)
    transcript = Column(Text, nullable=False)
    accuracy = Column(Float, default=0.0)
    fluency = Column(Float, default=0.0)
    completion = Column(Float, default=0.0)
    pace_wpm = Column(Float, default=0.0)
    pace_score = Column(Float, default=0.0)
    pronunciation = Column(Float, default=0.0)
    final_score = Column(Float, default=0.0)
    grade = Column(String, default="E")
    evaluated = Column(Boolean, default=False)
    wrong_words = Column(Text, default="[]")          # JSON list of mispronounced/missed words
    session_type = Column(String, default="normal")   # "normal" | "improvement"
    ai_overview = Column(Text, default="")            # AI-generated improvement summary
    teacher_notes = Column(Text, default="")          # Notes added by the teacher
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="sessions")
    material = relationship("Material", back_populates="sessions")
