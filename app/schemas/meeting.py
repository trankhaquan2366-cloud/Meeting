from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

# 1. Khai báo Schema cho dữ liệu tạo cuộc họp mới
class MeetingCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    room_id: int
    start_time: datetime
    end_time: datetime
    is_recurring: Optional[bool] = False

# 2. Khai báo Schema phản hồi trả về cho Client
class MeetingResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    room_id: int
    user_id: Optional[int] = None
    start_time: datetime
    end_time: datetime
    is_recurring: bool

    model_config = ConfigDict(from_attributes=True)