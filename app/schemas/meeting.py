from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.core.time import as_utc_aware, normalize_to_utc_naive
from app.schemas.equipment import MeetingEquipmentItemInput, MeetingEquipmentItemOutput


# 1. Schema cho dữ liệu gửi lên khi đặt lịch họp mới (Request)
class MeetingCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    # meeting_type: 'online' | 'offline'
    meeting_type: str = 'offline'
    # online_link: bắt buộc khi meeting_type='online'
    online_link: Optional[str] = None
    # room_id: bắt buộc khi meeting_type='offline', phải NULL khi 'online'
    room_id: Optional[int] = None
    start_time: datetime
    end_time: datetime

    # Bổ sung các trường để hỗ trợ đặt lịch định kỳ
    is_recurring: Optional[bool] = False
    recurrence_type: Optional[str] = "none"  # "none", "weekly", "monthly", "until_changed"
    recurrence_end_date: Optional[datetime] = None

    # Thiết bị mượn kèm & Người tham dự
    equipments: Optional[List[MeetingEquipmentItemInput]] = []
    participant_ids: Optional[List[int]] = []

    @field_validator('start_time', 'end_time', 'recurrence_end_date')
    @classmethod
    def normalize_meeting_times_to_utc(cls, value: datetime | None) -> datetime | None:
        return normalize_to_utc_naive(value) if value is not None else None

    @field_validator('meeting_type')
    @classmethod
    def validate_meeting_type(cls, v: str) -> str:
        if v not in ('online', 'offline'):
            raise ValueError("meeting_type phải là 'online' hoặc 'offline'")
        return v

    @field_validator('recurrence_type')
    @classmethod
    def validate_recurrence_type(cls, value: str | None) -> str | None:
        if value not in (None, 'none', 'weekly', 'monthly', 'until_changed'):
            raise ValueError(
                "recurrence_type phải là 'none', 'weekly', 'monthly' "
                "hoặc 'until_changed'"
            )
        return value

    @model_validator(mode='after')
    def validate_meeting_mode(self) -> 'MeetingCreateRequest':
        if self.recurrence_type in ('weekly', 'monthly'):
            if self.recurrence_end_date is None:
                raise ValueError(
                    "Lịch lặp tuần/tháng cần có recurrence_end_date."
                )
            if self.recurrence_end_date.date() < self.start_time.date():
                raise ValueError(
                    "recurrence_end_date không được trước ngày bắt đầu."
                )
        if self.meeting_type == 'online':
            if self.room_id is not None:
                raise ValueError(
                    "Cuộc họp online không được có room_id. Hãy gửi room_id = null."
                )
            if not self.online_link or not self.online_link.strip():
                raise ValueError("Cuộc họp online cần có online_link.")
        elif self.meeting_type == 'offline':
            if not self.room_id:
                raise ValueError("Cuộc họp offline cần có room_id hợp lệ.")
        return self


class MeetingUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    meeting_type: Optional[str] = None
    online_link: Optional[str] = None
    room_id: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    participant_ids: Optional[List[int]] = None

    @field_validator('start_time', 'end_time')
    @classmethod
    def normalize_meeting_times_to_utc(cls, value: datetime | None) -> datetime | None:
        return normalize_to_utc_naive(value) if value is not None else None

    @field_validator('meeting_type')
    @classmethod
    def validate_meeting_type(cls, value: str | None) -> str | None:
        if value is not None and value not in ('online', 'offline'):
            raise ValueError("meeting_type phải là 'online' hoặc 'offline'")
        return value


# 2. Schema phản hồi thông tin cuộc họp trả về cho Client (Response)
class MeetingResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    meeting_type: str = 'offline'
    online_link: Optional[str] = None
    room_id: Optional[int] = None
    organizer_id: Optional[int] = None
    start_time: datetime
    end_time: datetime
    is_recurring: bool = False
    recurring_type: Optional[str] = None
    status: str
    equipments: Optional[List[MeetingEquipmentItemOutput]] = []
    participant_ids: Optional[List[int]] = []

    model_config = ConfigDict(from_attributes=True)

    @field_validator('start_time', 'end_time', mode='before')
    @classmethod
    def serialize_meeting_times_as_utc(cls, value: datetime) -> datetime:
        return as_utc_aware(value)

    @field_validator('equipments', mode='before')
    @classmethod
    def parse_equipments(cls, v: Any):
        if not v:
            return []
        res = []
        for item in v:
            if isinstance(item, dict):
                res.append(item)
            else:
                eq_name = getattr(getattr(item, 'equipment', None), 'name', 'Thiết bị')
                res.append({
                    'equipment_id': item.equipment_id,
                    'equipment_name': eq_name,
                    'quantity': item.quantity,
                    'note': getattr(item, 'note', None)
                })
        return res


# 3. Schema phản hồi người dùng thường xuyên họp
class FrequentUserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    invite_count: int

    model_config = ConfigDict(from_attributes=True)


# 4. Schema phản hồi thông báo
class NotificationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    content: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# 5. Schema cho tính năng gợi ý khung giờ trống
class SuggestTimeRequest(BaseModel):
    participant_ids: List[int]
    date: str  # Định dạng: "YYYY-MM-DD"
    duration_minutes: int


class TimeSlot(BaseModel):
    start_time: str  # Định dạng ISO 8601: "YYYY-MM-DDTHH:MM:SS"
    end_time: str    # Định dạng ISO 8601: "YYYY-MM-DDTHH:MM:SS"


class SuggestTimeResponse(BaseModel):
    suggested_slots: List[TimeSlot]