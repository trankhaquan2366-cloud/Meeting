from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class DraftBookingSlot(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    meeting_type: Optional[Literal["online", "offline"]] = None
    meeting_link: Optional[str] = None
    room_id: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    participant_ids: List[int] = Field(default_factory=list)


class ChatMessageCreate(BaseModel):
    sender: Literal["user", "bot"] = "user"
    content: str = Field(min_length=1)
    intent: Optional[str] = None
    slots: Optional[Dict[str, Any]] = None


class ChatMessageResponse(BaseModel):
    id: int
    session_id: int
    sender: Literal["user", "bot"]
    content: str
    intent: Optional[str] = None
    slots: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatSessionResponse(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessageResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
