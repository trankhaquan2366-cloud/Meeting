from datetime import datetime
from pydantic import BaseModel, Field

class RoomResponse(BaseModel):
    id: int
    name: str
    capacity: int
    location: str | None = None
    description: str | None = None
    is_active: bool

    class Config:
        from_attributes = True