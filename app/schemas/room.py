from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

# 1. Class cơ sở định nghĩa tất cả thuộc tính chung của Phòng
class RoomBase(BaseModel):
    name: str = Field(..., description="Tên phòng họp")
    capacity: int = Field(..., gt=0, description="Sức chứa (số người), phải lớn hơn 0")
    location: Optional[str] = Field(None, description="Vị trí/Tầng")
    description: Optional[str] = Field(None, description="Mô tả/Trang thiết bị phòng họp")
    is_active: bool = Field(True, description="Trạng thái: True (Hoạt động) / False (Bảo trì/Khóa)")

# 2. Schema nhận dữ liệu khi Tạo phòng mới (POST)
class RoomCreate(RoomBase):
    pass

# 3. Schema nhận dữ liệu khi Cập nhật phòng (PUT)
class RoomUpdate(BaseModel):
    name: Optional[str] = None
    capacity: Optional[int] = Field(None, gt=0)
    location: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

# 4. Schema trả dữ liệu về cho Client (Response)
class RoomResponse(RoomBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # Pydantic v2 (Dùng orm_mode = True nếu là Pydantic v1)