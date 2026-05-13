from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MaterialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    filepath: str
    language: str
    class_level: str
    uploaded_at: datetime


class MaterialTextOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    text_content: str
