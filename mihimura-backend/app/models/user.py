from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    name: str
    mobile: str
    language: str = "Sinhala"
    region: Optional[str] = None
    role: str = "farmer"

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: str
    verified: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True
