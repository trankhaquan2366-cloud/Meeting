from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# --- Equipment Base & CRUD ---
class EquipmentBase(BaseModel):
    name: str = Field(..., max_length=150)
    code: Optional[str] = Field(None, max_length=50)
    category: Optional[str] = Field(None, max_length=50)
    total_qty: int = Field(1, ge=1)
    description: Optional[str] = None
    is_active: bool = True

class EquipmentCreate(EquipmentBase):
    pass

class EquipmentUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    category: Optional[str] = None
    total_qty: Optional[int] = Field(None, ge=1)
    description: Optional[str] = None
    is_active: Optional[bool] = None

class EquipmentResponse(EquipmentBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- Meeting Equipment Request/Response ---
class MeetingEquipmentItemInput(BaseModel):
    equipment_id: int
    quantity: int = Field(1, ge=1)
    note: Optional[str] = None

class MeetingEquipmentItemOutput(BaseModel):
    equipment_id: int
    equipment_name: str
    quantity: int
    note: Optional[str] = None

    class Config:
        from_attributes = True