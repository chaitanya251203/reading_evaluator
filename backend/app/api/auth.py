import os
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.db.database import get_db
from app.models.teacher import Teacher
from app.core.security import create_access_token

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "placeholder")

class LoginRequest(BaseModel):
    email: str
    password: str

class SignupRequest(BaseModel):
    name: str
    email: str
    password: str
    subject: str

class GoogleLoginRequest(BaseModel):
    token: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict

@router.post("/login")
def login_standard(req: LoginRequest, db: Session = Depends(get_db)):
    if req.email == "admin@vachanam.com" and req.password == "admin":
        user = db.query(Teacher).filter(Teacher.email == req.email).first()
        if not user:
            user = Teacher(
                name="Admin",
                email="admin@vachanam.com",
                subject="All Subjects",
                is_admin=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
    else:
        from app.core.security import verify_password
        user = db.query(Teacher).filter(Teacher.email == req.email).first()
        if not user or not user.hashed_password or not verify_password(req.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "is_admin": user.is_admin,
            "requires_profile": False
        }
    }

@router.post("/signup")
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    from app.core.security import get_password_hash
    existing = db.query(Teacher).filter(Teacher.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = Teacher(
        name=req.name,
        email=req.email,
        subject=req.subject,
        hashed_password=get_password_hash(req.password),
        is_admin=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    token = create_access_token({"sub": user.email})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "is_admin": user.is_admin,
            "requires_profile": False
        }
    }

@router.post("/google")
def login_google(req: GoogleLoginRequest, db: Session = Depends(get_db)):
    try:
        # Verify the token with Google
        idinfo = id_token.verify_oauth2_token(
            req.token, google_requests.Request(), GOOGLE_CLIENT_ID
        )
        
        email = idinfo.get("email")
        name = idinfo.get("name")
        google_id = idinfo.get("sub")
        
        if not email:
            raise HTTPException(status_code=400, detail="Google token missing email")

        user = db.query(Teacher).filter(Teacher.email == email).first()
        requires_profile = False
        
        if not user:
            # Create a shell account, mark as requires profile setup
            user = Teacher(
                name=name,
                email=email,
                subject="",  # Needs to be filled by teacher
                is_admin=(email == "admin@vachanam.com"),
                google_id=google_id
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
            if email != "admin@vachanam.com":
                requires_profile = True
                
        token = create_access_token({"sub": user.email})
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "is_admin": user.is_admin,
                "requires_profile": requires_profile or (not user.subject)
            }
        }
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Google token")

class CompleteProfileRequest(BaseModel):
    name: str
    subject: str

from app.core.security import get_current_user

@router.post("/complete-profile")
def complete_profile(req: CompleteProfileRequest, db: Session = Depends(get_db), current_user: Teacher = Depends(get_current_user)):
    current_user.name = req.name
    current_user.subject = req.subject
    db.commit()
    db.refresh(current_user)
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "is_admin": current_user.is_admin,
        "requires_profile": False
    }
