from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class ReadingSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    material_id: int
    audio_path: str
    transcript: str
    accuracy: float
    fluency: float
    completion: float
    pace_wpm: float
    pace_score: float
    pronunciation: float
    final_score: float
    grade: str
    evaluated: bool
    wrong_words: Optional[str] = "[]"   # JSON string — parsed by frontend
    session_type: Optional[str] = "normal"
    ai_overview: Optional[str] = ""
    created_at: datetime
    statuses: Optional[List[str]] = None


class ReadingSessionEvaluate(BaseModel):
    session_id: int


class ReadingSessionSummary(BaseModel):
    id: int
    student_id: int
    material_id: int
    material_title: str
    material_language: str = "english"
    transcript: str
    accuracy: float
    fluency: float
    completion: float
    pace_wpm: float
    pace_score: float
    pronunciation: float
    final_score: float
    grade: str
    evaluated: bool
    wrong_words: Optional[str] = "[]"
    session_type: Optional[str] = "normal"
    ai_overview: Optional[str] = ""
    teacher_notes: Optional[str] = ""
    created_at: datetime


class WrongWordItem(BaseModel):
    word: str
    count: int
    lang: Optional[str] = "english"


class ImprovementsOut(BaseModel):
    student_id: int
    words: List[WrongWordItem]


class PracticeStoryOut(BaseModel):
    student_id: int
    story_text: str
    wrong_words: List[str]
    material_id: int   # temporary DB material created for the story
