from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# Lớp dùng chung cho các trường cơ bản của Room
class RoomBase(BaseModel):
    name: str = Field(..., description="Tên phòng họp")
    capacity: int = Field(..., gt=0, description="Sức chứa (số người), phải lớn hơn 0")
    location: Optional[str] = Field(None, description="Vị trí/Tầng")
    description: Optional[str] = Field(None, description="Mô tả/Trang thiết bị phòng họp")
    is_active: bool = Field(True, description="Trạng thái: True (Hoạt động) / False (Bảo trì/Khóa)")

# Lớp dùng khi tạo phòng mới
class RoomCreate(RoomBase):
    pass

# Lớp dùng khi cập nhật phòng (cho phép các trường có thể null)
class RoomUpdate(BaseModel):
    name: Optional[str] = None
    capacity: Optional[int] = Field(None, gt=0)
    location: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

# Lớp dùng để trả kết quả (Response) ra ngoài
class RoomResponse(RoomBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True