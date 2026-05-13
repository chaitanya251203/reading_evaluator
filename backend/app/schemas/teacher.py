from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TeacherCreate(BaseModel):
    name: str
    subject: str


class TeacherOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    subject: str
    created_at: datetime
