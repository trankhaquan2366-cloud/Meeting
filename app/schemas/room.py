from pydantic import BaseModel
from typing import Optional, List

class RoomBase(BaseModel):
    name: str
    location: str
    capacity: str
    amenities: List[str] = []
    image_url: Optional[str] = "https://images.unsplash.com/photo-1497366216548-37526070297c"
    is_available: bool = True

class RoomCreate(RoomBase):
    pass

class RoomUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    capacity: Optional[str] = None
    amenities: Optional[List[str]] = None
    image_url: Optional[str] = None
    is_available: Optional[bool] = None

class RoomResponse(RoomBase):
    id: int

    class Config:
        from_attributes = True