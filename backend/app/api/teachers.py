from typing import List
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.teacher import Teacher
from app.schemas.teacher import TeacherCreate, TeacherOut

router = APIRouter()
logger = logging.getLogger("reading_assessment")


@router.post("", response_model=TeacherOut)
def create_teacher(payload: TeacherCreate, db: Session = Depends(get_db)):
    logger.info("teachers.create start name=%s", payload.name)
    teacher = Teacher(
        name=payload.name,
        subject=payload.subject,
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    logger.info("teachers.create done id=%s", teacher.id)
    return teacher


@router.get("", response_model=List[TeacherOut])
def list_teachers(db: Session = Depends(get_db)):
    logger.info("teachers.list")
    return db.query(Teacher).order_by(Teacher.created_at.desc()).all()


@router.delete("/{teacher_id}")
def delete_teacher(teacher_id: int, db: Session = Depends(get_db)):
    logger.info("teachers.delete start id=%s", teacher_id)
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    db.delete(teacher)
    db.commit()
    logger.info("teachers.delete done id=%s", teacher_id)
    return {"deleted": True}
