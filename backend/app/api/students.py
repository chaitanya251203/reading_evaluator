from typing import List
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.student import Student
from app.schemas.student import StudentCreate, StudentOut

router = APIRouter()
logger = logging.getLogger("reading_assessment")


@router.post("", response_model=StudentOut)
def create_student(payload: StudentCreate, db: Session = Depends(get_db)):
    logger.info("students.create start name=%s", payload.name)
    student = Student(
        name=payload.name,
        class_name=payload.class_name,
        roll_no=payload.roll_no,
        teacher_id=payload.teacher_id,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    logger.info("students.create done id=%s", student.id)
    return student


@router.get("", response_model=List[StudentOut])
def list_students(db: Session = Depends(get_db)):
    logger.info("students.list")
    return db.query(Student).order_by(Student.created_at.desc()).all()


@router.delete("/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db)):
    logger.info("students.delete start id=%s", student_id)
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    db.delete(student)
    db.commit()
    logger.info("students.delete done id=%s", student_id)
    return {"deleted": True}
