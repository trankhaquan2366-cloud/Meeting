from datetime import datetime
from enum import Enum
from typing import Any, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.equipment import MeetingEquipmentItemInput, MeetingEquipmentItemOutput


class RSVPStatusInput(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class RSVPRequest(BaseModel):
    status: Optional[RSVPStatusInput] = None
    response_status: Optional[RSVPStatusInput] = None
    raw_status_input: Optional[str] = Field(default=None, exclude=True)

    @model_validator(mode="before")
    @classmethod
    def capture_raw_status(cls, values):
        if isinstance(values, dict):
            raw = values.get("status") or values.get("response_status")
            if raw is not None:
                values["raw_status_input"] = str(raw).strip().lower()
        return values

    @field_validator("status", "response_status", mode="before")
    @classmethod
    def normalize_status(cls, value):
        if value is None:
            return value
        if isinstance(value, RSVPStatusInput):
            return value.value
        if not isinstance(value, str):
            raise TypeError("Trạng thái phản hồi phải là chuỗi.")
        norm = value.strip().lower()
        aliases = {
            "accepted": "accepted",
            "accept": "accepted",
            "rejected": "rejected",
            "reject": "rejected",
            "declined": "rejected",
            "decline": "rejected",
        }
        if norm not in aliases:
            raise ValueError("Trạng thái phải là 'accepted' hoặc 'rejected'")
        return aliases[norm]

    @model_validator(mode="after")
    def validate_rsvp(self) -> "RSVPRequest":
        raw = self.status or self.response_status
        if raw is None:
            raise ValueError("Trường 'status' (accepted/rejected) là bắt buộc.")
        self.status = RSVPStatusInput(raw.value if isinstance(raw, RSVPStatusInput) else raw)
        self.response_status = self.status
        if self.raw_status_input is None:
            self.raw_status_input = self.status.value
        return self


class MeetingParticipationResponse(RSVPRequest):
    pass



# 1. Schema cho dữ liệu gửi lên khi đặt lịch họp mới (Request)
class MeetingCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    # meeting_type: 'online' | 'offline'
    meeting_type: str = 'offline'
    meeting_link: Optional[str] = None
    # Retained for compatibility with existing clients and service code.
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
    equipments: Optional[List[MeetingEquipmentItemInput]] = Field(default_factory=list)
    participant_ids: Optional[List[int]] = Field(default_factory=list)

    @field_validator('meeting_type')
    @classmethod
    def validate_meeting_type(cls, v: str) -> str:
        if v not in ('online', 'offline'):
            raise ValueError("meeting_type phải là 'online' hoặc 'offline'")
        return v

    @model_validator(mode='after')
    def validate_meeting_mode(self) -> 'MeetingCreateRequest':
        link = (self.meeting_link or self.online_link or '').strip() or None
        self.meeting_link = link
        self.online_link = link
        return self


# 2. Schema phản hồi thông tin cuộc họp trả về cho Client (Response)
class MeetingResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    meeting_type: str = 'offline'
    meeting_link: Optional[str] = None
    online_link: Optional[str] = None
    room_id: Optional[int] = None
    organizer_id: Optional[int] = None
    start_time: datetime
    end_time: datetime
    is_recurring: bool = False
    recurring_type: Optional[str] = None
    status: str
    equipments: Optional[List[MeetingEquipmentItemOutput]] = Field(default_factory=list)
    participant_ids: Optional[List[int]] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

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
    meeting_id: Optional[int] = None
    meeting_title: Optional[str] = None
    meeting_status: Optional[str] = None
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