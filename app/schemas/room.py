import json
from typing import Literal, Optional, List, Union
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from urllib.parse import urlsplit

# 1. Class cơ sở định nghĩa tất cả thuộc tính chung của Phòng
class RoomBase(BaseModel):
    name: str = Field(..., description="Tên phòng họp")
    capacity: int = Field(..., gt=0, description="Sức chứa (số người), phải lớn hơn 0")
    location: Optional[str] = Field(None, description="Vị trí/Tầng")
    description: Optional[str] = Field(None, description="Mô tả/Trang thiết bị phòng họp")
    amenities: Optional[Union[List[str], str]] = Field(default_factory=list, description="Danh sách tiện ích")
    is_active: bool = Field(True, description="Trạng thái: True (Hoạt động) / False (Bảo trì/Khóa)")
    room_status: Literal["active", "maintenance", "locked"] = "active"
    equipment_ids: List[int] = Field(default_factory=list)
    room_image: Optional[str] = Field(None, max_length=2048)
    layout_type: Optional[Literal["boardroom", "classroom", "open_space"]] = None

    @field_validator('amenities', mode='before')
    @classmethod
    def parse_amenities(cls, v):
        if v is None:
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v_str = v.strip()
            if not v_str:
                return []
            try:
                parsed = json.loads(v_str)
                if isinstance(parsed, list):
                    return [str(x).strip() for x in parsed if str(x).strip()]
            except Exception:
                pass
            return [s.strip() for s in v_str.split(',') if s.strip()]
        return []

    @field_validator("room_image", mode="before")
    @classmethod
    def validate_room_image(cls, value):
        if value is None:
            return None
        value = str(value).strip()
        if not value:
            return None
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("room_image must be an http or https URL")
        return value

# 2. Schema nhận dữ liệu khi Tạo phòng mới (POST)
class RoomCreate(RoomBase):
    pass

# 3. Schema nhận dữ liệu khi Cập nhật phòng (PUT)
class RoomUpdate(BaseModel):
    name: Optional[str] = None
    capacity: Optional[int] = Field(None, gt=0)
    location: Optional[str] = None
    description: Optional[str] = None
    amenities: Optional[Union[List[str], str]] = None
    is_active: Optional[bool] = None
    room_status: Optional[Literal["active", "maintenance", "locked"]] = None
    equipment_ids: Optional[List[int]] = None
    room_image: Optional[str] = Field(None, max_length=2048)
    layout_type: Optional[Literal["boardroom", "classroom", "open_space"]] = None

    @field_validator("room_image", mode="before")
    @classmethod
    def validate_room_image(cls, value):
        if value is None:
            return None
        value = str(value).strip()
        if not value:
            return None
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("room_image must be an http or https URL")
        return value

# 4. Schema trả dữ liệu về cho Client (Response)
class RoomResponse(RoomBase):
    id: int
    amenities: Optional[List[str]] = []
    equipment_ids: List[int] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RoomQRResponse(BaseModel):
    room_id: int
    room_name: str
    qr_token: str