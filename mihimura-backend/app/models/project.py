from pydantic import BaseModel
from typing import Optional
from datetime import date

class ProjectBase(BaseModel):
    farm_id: str
    crop: str = "Paddy"
    variety: str
    season: str
    start_date: date
    target_harvest: date
    status: str = "active"

class ProjectCreate(ProjectBase):
    pass

class Project(ProjectBase):
    id: str

    class Config:
        from_attributes = True
