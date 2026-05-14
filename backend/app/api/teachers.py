from typing import List
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.teacher import Teacher
from app.schemas.teacher import TeacherCreate, TeacherOut
from app.core.security import get_current_user

router = APIRouter()
logger = logging.getLogger("reading_assessment")


@router.post("", response_model=TeacherOut)
def create_teacher(payload: TeacherCreate, db: Session = Depends(get_db), current_user: Teacher = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can create teachers")
        
    from app.core.security import get_password_hash
    logger.info("teachers.create start name=%s", payload.name)
    teacher = Teacher(
        name=payload.name,
        email=payload.email,
        subject=payload.subject,
        hashed_password=get_password_hash(payload.password),
        is_admin=False
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    logger.info("teachers.create done id=%s", teacher.id)
    return teacher


@router.get("", response_model=List[TeacherOut])
def list_teachers(db: Session = Depends(get_db), current_user: Teacher = Depends(get_current_user)):
    logger.info("teachers.list")
    if current_user.is_admin:
        return db.query(Teacher).order_by(Teacher.created_at.desc()).all()
    else:
        return [current_user]


@router.delete("/{teacher_id}")
def delete_teacher(teacher_id: int, db: Session = Depends(get_db), current_user: Teacher = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Only admins can delete teachers")
        
    logger.info("teachers.delete start id=%s", teacher_id)
    teacher = db.query(Teacher).filter(Teacher.id == teacher_id).first()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    db.delete(teacher)
    db.commit()
    logger.info("teachers.delete done id=%s", teacher_id)
    return {"deleted": True}
