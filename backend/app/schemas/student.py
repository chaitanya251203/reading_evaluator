from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StudentCreate(BaseModel):
    name: str
    class_name: str
    roll_no: str
    teacher_id: int


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    class_name: str
    roll_no: str
    teacher_id: int
    created_at: datetime
