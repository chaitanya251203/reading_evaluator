from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TeacherCreate(BaseModel):
    name: str
    email: str
    password: str
    subject: str


class TeacherOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    subject: str
    is_admin: bool
    created_at: datetime
