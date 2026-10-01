from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

# 1. Schema cho dữ liệu gửi lên khi đặt lịch họp mới (Request)
class MeetingCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    room_id: int
    start_time: datetime
    end_time: datetime

    # Bổ sung các trường để hỗ trợ đặt lịch định kỳ
    is_recurring: Optional[bool] = False
    recurrence_type: Optional[str] = "none" # Các giá trị: "none", "weekly", "monthly"
    recurrence_end_date: Optional[datetime] = None

# 2. Schema phản hồi thông tin cuộc họp trả về cho Client (Response)
class MeetingResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    room_id: int
    organizer_id: Optional[int] = None # Đã đổi từ user_id -> organizer_id cho khớp với Model
    start_time: datetime
    end_time: datetime
    is_recurring: bool = False
    recurring_type: Optional[str] = None
    status: str

    model_config = ConfigDict(from_attributes=True)


class MeetingEquipmentRequest(BaseModel):
    equipment_ids: List[int]


class MeetingEquipmentResponse(BaseModel):
    meeting_id: int
    equipment_ids: List[int]


# 3. Schema cho tính năng gợi ý khung giờ trống (Bổ sung mới)
class SuggestTimeRequest(BaseModel):
    participant_ids: List[int]
    date: str  # Định dạng: "YYYY-MM-DD"
    duration_minutes: int

class TimeSlot(BaseModel):
    start_time: str  # Định dạng ISO 8601: "YYYY-MM-DDTHH:MM:SS"
    end_time: str    # Định dạng ISO 8601: "YYYY-MM-DDTHH:MM:SS"

class SuggestTimeResponse(BaseModel):
    suggested_slots: List[TimeSlot]