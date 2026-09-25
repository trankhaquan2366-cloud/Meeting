from datetime import datetime
from pydantic import BaseModel, model_validator

class MeetingCreate(BaseModel):
    room_id: int
    title: str
    description: str | None = None
    start_time: datetime
    end_time: datetime

    @model_validator(mode='after')
    def validate_meeting_times(self) -> 'MeetingCreate':
        if self.end_time <= self.start_time:
            raise ValueError("Giờ kết thúc phải lớn hơn giờ bắt đầu!")
        if self.start_time < datetime.now():
            raise ValueError("Không thể đặt lịch họp trong thời gian quá khứ!")
        return self

class MeetingResponse(MeetingCreate):
    id: int
    status: str

    class Config:
        from_attributes = True