from pathlib import Path
from typing import List
from uuid import uuid4
import hashlib
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.material import Material
from app.schemas.material import MaterialOut, MaterialTextOut
from app.services.pdf_service import extract_pdf_text
from app.core.security import get_current_user
from app.models.teacher import Teacher

router = APIRouter()
logger = logging.getLogger("reading_assessment")

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
MATERIALS_DIR = DATA_DIR / "materials"


@router.post("/upload", response_model=MaterialOut)
def upload_material(
    title: str = Form(...),
    language: str = Form(...),
    class_level: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Teacher = Depends(get_current_user),
):
    logger.info("materials.upload start title=%s", title)
    MATERIALS_DIR.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename).suffix or ".pdf"
    filename = f"{uuid4().hex}{suffix}"
    save_path = MATERIALS_DIR / filename

    file_hash = hashlib.sha256()
    with save_path.open("wb") as buffer:
        while True:
            chunk = file.file.read(8192)
            if not chunk:
                break
            file_hash.update(chunk)
            buffer.write(chunk)

    sha256 = file_hash.hexdigest()
    duplicate = db.query(Material).filter(Material.sha256 == sha256).first()
    if duplicate:
        save_path.unlink(missing_ok=True)
        logger.info("materials.upload duplicate sha256=%s", sha256)
        raise HTTPException(status_code=409, detail="Duplicate PDF detected")

    try:
        text_content = extract_pdf_text(str(save_path))
    except Exception:
        logger.warning("materials.upload text_extract_failed path=%s", save_path)
        text_content = ""

    material = Material(
        title=title,
        filepath=str(save_path),
        text_content=text_content,
        sha256=sha256,
        language=language,
        class_level=class_level,
        teacher_id=current_user.id if not current_user.is_admin else None,
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    logger.info("materials.upload done id=%s", material.id)
    return material


@router.get("", response_model=List[MaterialOut])
def list_materials(db: Session = Depends(get_db), current_user: Teacher = Depends(get_current_user)):
    logger.info("materials.list")
    query = db.query(Material)
    if not current_user.is_admin:
        query = query.filter((Material.teacher_id == current_user.id) | (Material.teacher_id.is_(None)))
    return query.order_by(Material.uploaded_at.desc()).all()


@router.get("/{material_id}/text", response_model=MaterialTextOut)
def get_material_text(material_id: int, db: Session = Depends(get_db), current_user: Teacher = Depends(get_current_user)):
    query = db.query(Material).filter(Material.id == material_id)
    if not current_user.is_admin:
        query = query.filter((Material.teacher_id == current_user.id) | (Material.teacher_id.is_(None)))
        
    material = query.first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found or not authorized")
    return material


@router.delete("/{material_id}")
def delete_material(material_id: int, db: Session = Depends(get_db), current_user: Teacher = Depends(get_current_user)):
    logger.info("materials.delete start id=%s", material_id)
    query = db.query(Material).filter(Material.id == material_id)
    if not current_user.is_admin:
        query = query.filter(Material.teacher_id == current_user.id)
        
    material = query.first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found or not authorized to delete")
    
    # Optionally delete the associated PDF file
    if material.filepath:
        Path(material.filepath).unlink(missing_ok=True)
        
    db.delete(material)
    db.commit()
    logger.info("materials.delete done id=%s", material_id)
    return {"deleted": True}
