from typing import List
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.student import Student
from app.schemas.student import StudentCreate, StudentOut
from app.core.security import get_current_user
from app.models.teacher import Teacher

router = APIRouter()
logger = logging.getLogger("reading_assessment")


@router.post("", response_model=StudentOut)
def create_student(payload: StudentCreate, db: Session = Depends(get_db), current_user: Teacher = Depends(get_current_user)):
    logger.info("students.create start name=%s", payload.name)
    # If not admin, force the teacher_id to be the current_user's id
    teacher_id = payload.teacher_id if current_user.is_admin else current_user.id
    
    student = Student(
        name=payload.name,
        class_name=payload.class_name,
        roll_no=payload.roll_no,
        teacher_id=teacher_id,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    logger.info("students.create done id=%s", student.id)
    return student


@router.get("", response_model=List[StudentOut])
def list_students(db: Session = Depends(get_db), current_user: Teacher = Depends(get_current_user)):
    logger.info("students.list")
    query = db.query(Student)
    if not current_user.is_admin:
        query = query.filter(Student.teacher_id == current_user.id)
    return query.order_by(Student.created_at.desc()).all()


@router.delete("/{student_id}")
def delete_student(student_id: int, db: Session = Depends(get_db), current_user: Teacher = Depends(get_current_user)):
    logger.info("students.delete start id=%s", student_id)
    query = db.query(Student).filter(Student.id == student_id)
    if not current_user.is_admin:
        query = query.filter(Student.teacher_id == current_user.id)
        
    student = query.first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found or not authorized")
    
    db.delete(student)
    db.commit()
    logger.info("students.delete done id=%s", student_id)
    return {"deleted": True}
