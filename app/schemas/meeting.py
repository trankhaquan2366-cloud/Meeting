from datetime import datetime
from pydantic import BaseModel, Field, model_validator

class MeetingCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Tiêu đề cuộc họp")
    description: str | None = Field(None, description="Nội dung cuộc họp")
    room_id: int = Field(..., description="ID phòng họp")
    start_time: datetime = Field(..., description="Thời gian bắt đầu (YYYY-MM-DD HH:MM:SS)")
    end_time: datetime = Field(..., description="Thời gian kết thúc (YYYY-MM-DD HH:MM:SS)")

    @model_validator(mode="after")
    def validate_times(self):
        if self.end_time <= self.start_time:
            raise ValueError("Thời gian kết thúc phải lớn hơn thời gian bắt đầu!")
        return self

class MeetingResponse(BaseModel):
    id: int
    title: str
    description: str | None = None
    room_id: int
    organizer_id: int | None = None
    start_time: datetime
    end_time: datetime
    status: str
    created_at: datetime

    class Config:
        from_attributes = True