from pathlib import Path
from typing import List
from uuid import uuid4
import asyncio
import base64
import json
import logging
import shutil
import time
import wave

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.db.database import SessionLocal, get_db
from app.models import Material, ReadingSession, Student, Teacher  # noqa: F401 — loads all models
from app.schemas.reading import (
    ReadingSessionEvaluate,
    ReadingSessionOut,
    ReadingSessionSummary,
)
from app.services.eval_service import evaluate_reading
from app.services.pdf_service import extract_pdf_text
from app.services.alignment_service import align_words
from app.services.highlight_service import build_highlight_state
from app.services.text_processing_service import tokenize
from app.services.stt_service import transcribe_audio
from app.services.ai_service import generate_session_overview

import os
import websockets as _ws_lib

logger = logging.getLogger(__name__)
router = APIRouter()

AUDIO_DIR = Path("data/audio")
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# Limit concurrent Groq/Whisper evaluations
STT_SEMAPHORE = asyncio.Semaphore(4)

# Deepgram logic removed as requested

@router.post("/transcribe", response_model=ReadingSessionOut)
def transcribe_reading(
    student_id: int = Form(...),
    material_id: int = Form(...),
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    logger.info("reading.transcribe start student_id=%s material_id=%s", student_id, material_id)
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    suffix = Path(audio.filename).suffix or ".wav"
    filename = f"{uuid4().hex}{suffix}"
    audio_path = AUDIO_DIR / filename

    with audio_path.open("wb") as buffer:
        shutil.copyfileobj(audio.file, buffer)

    stt_result = transcribe_audio(str(audio_path), language=material.language)
    transcript = stt_result["text"]
    segments = stt_result["segments"]
    duration_seconds = stt_result["duration_seconds"]

    try:
        passage_text = extract_pdf_text(material.filepath)
    except Exception:
        logger.warning("reading.transcribe pdf_text_failed material_id=%s", material.id)
        passage_text = ""
    metrics = evaluate_reading(passage_text, transcript, segments, duration_seconds)

    wrong_words = metrics.get("wrong_words", [])
    ai_overview = generate_session_overview(passage_text, transcript, metrics, wrong_words)

    session = ReadingSession(
        student_id=student.id,
        material_id=material.id,
        audio_path=str(audio_path),
        transcript=transcript or "",
        accuracy=metrics["accuracy"],
        fluency=metrics["fluency"],
        completion=metrics["completion"],
        pace_wpm=metrics["pace_wpm"],
        pace_score=metrics["pace_score"],
        pronunciation=metrics["pronunciation"],
        final_score=metrics["final_score"],
        grade=metrics["grade"],
        wrong_words=json.dumps(wrong_words),
        ai_overview=ai_overview,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    logger.info("reading.transcribe done session_id=%s", session.id)
    return session


@router.get("/sessions/{student_id}", response_model=List[ReadingSessionSummary])
def get_student_sessions(student_id: int, db: Session = Depends(get_db)):
    """Return all evaluated sessions for a student, newest first."""
    sessions = (
        db.query(ReadingSession)
        .filter(ReadingSession.student_id == student_id, ReadingSession.evaluated == True)  # noqa: E712
        .order_by(ReadingSession.created_at.desc())
        .all()
    )
    result = []
    for s in sessions:
        mat = db.query(Material).filter(Material.id == s.material_id).first()
        result.append(ReadingSessionSummary(
            id=s.id, student_id=s.student_id, material_id=s.material_id,
            material_title=mat.title if mat else "Unknown",
            material_language=mat.language if mat else "english",
            transcript=s.transcript or "", accuracy=s.accuracy, fluency=s.fluency,
            completion=s.completion, pace_wpm=s.pace_wpm, pace_score=s.pace_score,
            pronunciation=s.pronunciation, final_score=s.final_score, grade=s.grade,
            evaluated=s.evaluated, wrong_words=s.wrong_words or "[]",
            session_type=s.session_type or "normal", ai_overview=s.ai_overview or "",
            teacher_notes=s.teacher_notes or "",
            created_at=s.created_at,
        ))
    return result

from pydantic import BaseModel
class NotesUpdate(BaseModel):
    notes: str

@router.put("/sessions/{session_id}/notes")
def update_teacher_notes(session_id: int, update: NotesUpdate, db: Session = Depends(get_db)):
    """Update teacher notes for a reading session."""
    session = db.query(ReadingSession).filter(ReadingSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.teacher_notes = update.notes
    db.commit()
    return {"status": "success", "notes": session.teacher_notes}

@router.post("/evaluate/{session_id}", response_model=ReadingSessionOut)
async def evaluate_session_audio(session_id: int, db: Session = Depends(get_db)):
    """Run Whisper transcription + evaluation on a saved session's audio."""
    import asyncio
    logger.info("reading.evaluate_audio start session_id=%s", session_id)

    # Read from DB before running Whisper (don't hold session open during inference)
    session = db.query(ReadingSession).filter(ReadingSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    material = db.query(Material).filter(Material.id == session.material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    audio_path = session.audio_path
    if not audio_path or not Path(audio_path).exists():
        raise HTTPException(status_code=404, detail="Audio file not found for this session")

    language = material.language
    passage_text = material.text_content or ""

    # Run transcription in a thread pool (works for both Groq API and local whisper)
    async with STT_SEMAPHORE:
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None, lambda: transcribe_audio(audio_path, language=language)
            )
        except Exception as e:
            logger.exception("reading.evaluate_audio transcription failed session_id=%s", session_id)
            raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

    transcript = result["text"]
    segments = result["segments"]
    duration_seconds = result["duration_seconds"]

    metrics = evaluate_reading(passage_text, transcript, segments, duration_seconds)
    wrong_words = metrics.get("wrong_words", [])
    ai_overview = generate_session_overview(passage_text, transcript, metrics, wrong_words)

    # Write results back to DB
    session.transcript = transcript or ""
    session.accuracy = metrics["accuracy"]
    session.fluency = metrics["fluency"]
    session.completion = metrics["completion"]
    session.pace_wpm = metrics["pace_wpm"]
    session.pace_score = metrics["pace_score"]
    session.pronunciation = metrics["pronunciation"]
    session.final_score = metrics["final_score"]
    session.grade = metrics["grade"]
    session.wrong_words = json.dumps(wrong_words)
    session.ai_overview = ai_overview
    session.evaluated = True
    db.commit()
    db.refresh(session)

    logger.info("reading.evaluate_audio done session_id=%s score=%s", session.id, session.final_score)
    return session



@router.post("/evaluate", response_model=ReadingSessionOut)
def evaluate_session(payload: ReadingSessionEvaluate, db: Session = Depends(get_db)):
    logger.info("reading.evaluate start session_id=%s", payload.session_id)
    session = db.query(ReadingSession).filter(ReadingSession.id == payload.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.evaluated = True
    db.commit()
    db.refresh(session)
    logger.info("reading.evaluate done session_id=%s", session.id)
    return session


@router.get("/sessions", response_model=List[ReadingSessionSummary])
def list_sessions(
    student_id: int = Query(...),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(ReadingSession, Material)
        .join(Material, ReadingSession.material_id == Material.id)
        .filter(ReadingSession.student_id == student_id)
        .order_by(ReadingSession.created_at.desc())
        .all()
    )

    results = []
    for session, material in rows:
        results.append(
            ReadingSessionSummary(
                id=session.id,
                student_id=session.student_id,
                material_id=session.material_id,
                material_title=material.title,
                transcript=session.transcript,
                accuracy=session.accuracy,
                fluency=session.fluency,
                completion=session.completion,
                pace_wpm=session.pace_wpm,
                pace_score=session.pace_score,
                pronunciation=session.pronunciation,
                final_score=session.final_score,
                grade=session.grade,
                evaluated=session.evaluated,
                created_at=session.created_at,
            )
        )
    return results


@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db)):
    logger.info("reading.delete start session_id=%s", session_id)
    session = db.query(ReadingSession).filter(ReadingSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.audio_path:
        Path(session.audio_path).unlink(missing_ok=True)

    db.delete(session)
    db.commit()
    logger.info("reading.delete done session_id=%s", session_id)
    return {"deleted": True}


def _write_audio_file(path: Path, data: bytes, audio_format: str, channels: int, sample_width: int, sample_rate: int):
    """Write raw PCM or other audio bytes to a file."""
    if audio_format == "pcm":
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(data)
    else:
        path.write_bytes(data)


@router.websocket("/ws/transcribe")
async def ws_transcribe(websocket: WebSocket):
    await websocket.accept()
    db = SessionLocal()

    buffer = bytearray()
    material = None
    student = None
    language = None
    extension = ".wav"
    audio_format = "wav"
    sample_rate = 16000
    channels = 1
    sample_width = 2
    session_id = None
    try:
        while True:
            message = await websocket.receive_text()
            payload = json.loads(message)
            msg_type = payload.get("type")

            if msg_type == "start":
                # Reset state for a new session
                buffer = bytearray()
                session_id = None

                student_id = payload.get("student_id")
                material_id = payload.get("material_id")
                language = payload.get("language")
                extension = payload.get("extension", ".wav")
                audio_format = payload.get("format", "wav")
                sample_rate = payload.get("sample_rate", 16000)
                channels = payload.get("channels", 1)
                sample_width = payload.get("sample_width", 2)
                session_type = payload.get("session_type", "normal")

                student = db.query(Student).filter(Student.id == student_id).first()
                material = db.query(Material).filter(Material.id == material_id).first()

                if not student or not material:
                    await websocket.send_json({"type": "error", "message": "Invalid student/material"})
                    continue

                if not material.text_content:
                    try:
                        material.text_content = extract_pdf_text(material.filepath)
                        db.commit()
                    except Exception:
                        logger.warning("reading.ws text_extract_failed material_id=%s", material.id)
                        material.text_content = ""

                expected_words = tokenize(material.text_content)
                await websocket.send_json({"type": "ready", "word_count": len(expected_words)})

                continue

            if msg_type == "audio":
                chunk_b64 = payload.get("data")
                if not chunk_b64:
                    continue
                raw_pcm = base64.b64decode(chunk_b64)
                buffer.extend(raw_pcm)
                continue

            if msg_type == "stop":
                # Save audio and create an unevaluated session
                if material and student and buffer:
                    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
                    filename = f"{uuid4().hex}{extension}"
                    audio_path = AUDIO_DIR / filename
                    _write_audio_file(audio_path, buffer, audio_format, channels, sample_width, sample_rate)

                    session_obj = ReadingSession(
                        student_id=student.id,
                        material_id=material.id,
                        audio_path=str(audio_path),
                        transcript="",
                        evaluated=False,
                        session_type=session_type,
                    )
                    db.add(session_obj)
                    db.commit()
                    db.refresh(session_obj)
                    session_id = session_obj.id
                    logger.info("reading.ws saved session_id=%s", session_id)

                    try:
                        await websocket.send_json({
                            "type": "stopped",
                            "session_id": session_id,
                        })
                    except Exception:
                        pass

                break

    except WebSocketDisconnect:
        logger.info("reading.ws disconnected")
        # Still save audio if we have it
        if material and student and buffer and not session_id:
            try:
                AUDIO_DIR.mkdir(parents=True, exist_ok=True)
                filename = f"{uuid4().hex}{extension}"
                audio_path = AUDIO_DIR / filename
                _write_audio_file(audio_path, buffer, audio_format, channels, sample_width, sample_rate)

                session_obj = ReadingSession(
                    student_id=student.id,
                    material_id=material.id,
                    audio_path=str(audio_path),
                    transcript="",
                    evaluated=False,
                )
                db.add(session_obj)
                db.commit()
                logger.info("reading.ws saved on disconnect session_id=%s", session_obj.id)
            except Exception:
                logger.exception("reading.ws failed to save on disconnect")
    except Exception:
        logger.exception("reading.ws unexpected error")
    finally:
        db.close()
