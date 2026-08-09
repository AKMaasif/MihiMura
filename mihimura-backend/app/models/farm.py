from pydantic import BaseModel
from typing import Optional

class FarmBase(BaseModel):
    name: str
    owner_id: str
    area: float
    land_type: Optional[str] = None
    water_source: Optional[str] = None

class FarmCreate(FarmBase):
    pass

class Farm(FarmBase):
    id: str
    
    class Config:
        from_attributes = True
