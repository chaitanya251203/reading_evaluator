"""
Improvements API — aggregates wrong words across all sessions for a student
and generates practice stories via the AI service.
"""
from __future__ import annotations

import json
import logging
from collections import Counter
from typing import List
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.material import Material
from app.models.session import ReadingSession
from app.models.student import Student
from app.schemas.reading import ImprovementsOut, PracticeStoryOut, WrongWordItem
from app.services.ai_service import generate_practice_story

router = APIRouter()
logger = logging.getLogger("reading_assessment")


def _aggregate_wrong_words(sessions_with_lang: list) -> dict:
    """Flatten + count wrong words per language, skipping single-char tokens."""
    # counter maps word -> {count, lang}
    word_data: dict = {}
    for session, lang in sessions_with_lang:
        raw = session.wrong_words or "[]"
        try:
            words = json.loads(raw)
        except Exception:
            words = []
        for w in words:
            w_clean = w.strip().lower()
            # Skip blank or single-character tokens (akshar)
            if not w_clean or len(w_clean) <= 1:
                continue
            if w_clean not in word_data:
                word_data[w_clean] = {"count": 0, "lang": lang or "english"}
            word_data[w_clean]["count"] += 1
    return word_data


@router.get("/{student_id}", response_model=ImprovementsOut)
def get_improvements(student_id: int, db: Session = Depends(get_db)):
    """Return aggregated wrong-word frequencies for a student, tagged with language."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    sessions = (
        db.query(ReadingSession)
        .filter(ReadingSession.student_id == student_id, ReadingSession.evaluated == True)  # noqa: E712
        .all()
    )

    # Join each session with its material language (normalize short codes)
    sessions_with_lang = []
    _lang_map = {"en": "english", "hi": "hindi", "english": "english", "hindi": "hindi"}
    for s in sessions:
        mat = db.query(Material).filter(Material.id == s.material_id).first()
        raw_lang = (mat.language or "english").strip().lower() if mat else "english"
        lang = _lang_map.get(raw_lang, "english")
        sessions_with_lang.append((s, lang))

    word_data = _aggregate_wrong_words(sessions_with_lang)

    # Sort by count desc, take top 60
    sorted_words = sorted(word_data.items(), key=lambda x: x[1]["count"], reverse=True)[:60]
    words = [
        WrongWordItem(word=w, count=d["count"], lang=d["lang"])
        for w, d in sorted_words
    ]

    logger.info("improvements.get student_id=%s total_unique_words=%s", student_id, len(words))
    return ImprovementsOut(student_id=student_id, words=words)


@router.post("/{student_id}/story", response_model=PracticeStoryOut)
def create_practice_story(student_id: int, language: str = Query("english"), db: Session = Depends(get_db)):
    """Generate a practice story from the student's worst words, filtered by language."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Get all evaluated sessions
    all_sessions = (
        db.query(ReadingSession)
        .filter(ReadingSession.student_id == student_id, ReadingSession.evaluated == True)  # noqa: E712
        .all()
    )

    # Filter sessions by material language
    filtered_sessions = []
    for s in all_sessions:
        mat = db.query(Material).filter(Material.id == s.material_id).first()
        if mat and mat.language.lower() == language.lower():
            filtered_sessions.append((s, mat.language.lower()))

    # Fallback to all sessions if no sessions match the language
    if filtered_sessions:
        sessions_to_use = filtered_sessions
    else:
        sessions_to_use = []
        for s in all_sessions:
            mat = db.query(Material).filter(Material.id == s.material_id).first()
            mat_lang = mat.language.lower() if mat else "english"
            sessions_to_use.append((s, mat_lang))

    counter = _aggregate_wrong_words(sessions_to_use)
    sorted_words = sorted(counter.items(), key=lambda x: x[1]["count"], reverse=True)[:20]
    top_words = [w for w, _ in sorted_words]

    if not top_words:
        raise HTTPException(status_code=400, detail=f"No wrong words recorded yet for {language}. Complete at least one evaluated reading session first.")

    story_text = generate_practice_story(top_words, language)

    if not story_text:
        raise HTTPException(status_code=503, detail="AI story generation failed. Check your OPENAI_API_KEY.")

    # Save story as a temporary Material so the WS reading session can reference it
    practice_material = Material(
        title=f"[Practice] {student.name}",
        filepath="inline",           # no PDF — text_content is the source
        text_content=story_text,
        sha256=f"practice_{uuid.uuid4().hex[:12]}",
        language=language,
        class_level="practice",
    )
    db.add(practice_material)
    db.commit()
    db.refresh(practice_material)

    logger.info(
        "improvements.story student_id=%s material_id=%s words=%s",
        student_id, practice_material.id, len(top_words),
    )
    return PracticeStoryOut(
        student_id=student_id,
        story_text=story_text,
        wrong_words=top_words,
        material_id=practice_material.id,
    )

from pydantic import BaseModel
class ReportRequest(BaseModel):
    session_ids: List[int] = []

@router.post("/{student_id}/report")
def generate_student_report(student_id: int, req: ReportRequest, db: Session = Depends(get_db)):
    """Generate a comprehensive LLM report for a student based on selected sessions."""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    query = db.query(ReadingSession).filter(ReadingSession.student_id == student_id, ReadingSession.evaluated == True)
    if req.session_ids:
        query = query.filter(ReadingSession.id.in_(req.session_ids))
    sessions = query.all()

    if not sessions:
        raise HTTPException(status_code=400, detail="No sessions found for report generation.")

    # Build context string
    context_lines = [f"Student: {student.name} (Class {student.class_name})"]
    context_lines.append(f"Total Sessions Analyzed: {len(sessions)}\n")
    for s in sessions:
        mat = db.query(Material).filter(Material.id == s.material_id).first()
        mat_title = mat.title if mat else "Unknown Material"
        context_lines.append(f"--- Session on {s.created_at.strftime('%Y-%m-%d')} ---")
        context_lines.append(f"Material: {mat_title} (Score: {s.final_score}, Grade: {s.grade})")
        context_lines.append(f"Metrics: Accuracy {s.accuracy}%, Fluency {s.fluency}%, WPM {s.pace_wpm}")
        context_lines.append(f"Wrong Words: {s.wrong_words}")
        if s.teacher_notes:
            context_lines.append(f"Teacher Notes: {s.teacher_notes}")
        if s.ai_overview:
            context_lines.append(f"Previous AI Feedback: {s.ai_overview}")
        context_lines.append("")

    context_str = "\n".join(context_lines)

    prompt = f"""
You are an expert reading teacher and curriculum advisor. Write a comprehensive progress report for the student based on their reading sessions.
Focus on their improvement areas, recurring mistakes, fluency trends, and provide actionable advice for the teacher and parents.
Format the report in clean markdown with headers and bullet points.

Reading History Context:
{context_str}
"""
    from app.services.ai_service import _chat
    report_md = _chat(prompt, max_tokens=1500)
    if not report_md:
        raise HTTPException(status_code=500, detail="Failed to generate report")

    return {"report": report_md}
