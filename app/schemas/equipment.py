from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

# 1. Base Schema cho thiết bị
class EquipmentBase(BaseModel):
    code: str
    name: str
    category: str
    total_qty: int
    description: Optional[str] = None
    is_active: bool = True

# 2. Schema dùng khi tạo mới thiết bị
class EquipmentCreate(EquipmentBase):
    pass

# 3. Schema dùng khi cập nhật thiết bị
class EquipmentUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    total_qty: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

# 4. Schema phản hồi thông tin chi tiết thiết bị
class EquipmentResponse(EquipmentBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# 5. Schema phản hồi trạng thái thiết bị
class EquipmentStatusResponse(BaseModel):
    code: str
    name: str
    category: str
    total_qty: int
    booked_qty: int
    available_qty: int
    status_label: str

    model_config = ConfigDict(from_attributes=True)

# 6. Schema thiết bị trong cuộc họp (Bổ sung để tránh lỗi import từ app/schemas/meeting.py)
class MeetingEquipmentItemInput(BaseModel):
    equipment_id: int
    quantity: int = 1

class MeetingEquipmentItemOutput(BaseModel):
    equipment_id: int
    equipment_name: Optional[str] = None
    quantity: int

    model_config = ConfigDict(from_attributes=True)