import logging
from datetime import date, datetime, time, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.chat import ChatMessage, ChatSession
from app.models.room import Room
from app.models.user import User
from app.schemas.chat import ChatMessageResponse, ChatSessionResponse
from app.schemas.meeting import MeetingCreateRequest, MeetingResponse
from app.services.chatbot_service import ChatbotService
from app.services.gemini_service import BookingSlots, GeminiChatResponse
from app.services.meeting_service import MeetingService

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatSessionCreateRequest(BaseModel):
    title: str = Field(default="Cuộc trò chuyện mới", min_length=1, max_length=200)


class ChatUserMessageRequest(BaseModel):
    content: str = Field(min_length=1)


class ChatSessionListItem(BaseModel):
    id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConfirmBookingRequest(BaseModel):
    slots: BookingSlots
    description: Optional[str] = None
    participant_ids: List[int] = Field(default_factory=list)


def _get_owned_session(db: Session, session_id: int, user_id: int) -> ChatSession:
    chat_session = db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id,
        )
    ).scalar_one_or_none()
    if chat_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy phiên chat.",
        )
    return chat_session


@router.get(
    "/sessions",
    response_model=List[ChatSessionListItem],
    summary="Lấy danh sách phiên chatbot của người dùng hiện tại",
)
def list_chat_sessions(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.updated_at.desc(), ChatSession.id.desc())
        .offset(skip)
        .limit(limit)
    ).scalars().all()


@router.post(
    "/sessions",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo phiên chatbot mới",
)
def create_chat_session(
    payload: ChatSessionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    title = payload.title.strip()
    if not title:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Tiêu đề phiên chat không được để trống.",
        )

    chat_session = ChatSession(user_id=current_user.id, title=title)
    db.add(chat_session)
    try:
        db.commit()
        db.refresh(chat_session)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Failed to create chat session for user_id=%s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Không thể tạo phiên chat.",
        ) from exc
    return chat_session


@router.get(
    "/sessions/{session_id}/messages",
    response_model=List[ChatMessageResponse],
    summary="Lấy tin nhắn trong một phiên chatbot",
)
def list_chat_messages(
    session_id: int,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_session(db, session_id, current_user.id)
    return db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at, ChatMessage.id)
        .offset(skip)
        .limit(limit)
    ).scalars().all()


@router.post(
    "/sessions/{session_id}/message",
    response_model=GeminiChatResponse,
    summary="Gửi tin nhắn tới trợ lý RoomSync",
)
def send_chat_message(
    session_id: int,
    payload: ChatUserMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        _get_owned_session(db, session_id, current_user.id)
        available_rooms = MeetingService.get_all_active_rooms(db)
        return ChatbotService.process_message(
            db=db,
            chat_session_id=session_id,
            user_message=payload.content,
            available_rooms=available_rooms,
        )
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception(
            "Database error while processing chat message for chat_session_id=%s user_id=%s",
            session_id,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Trợ lý hiện không thể xử lý yêu cầu. Vui lòng thử lại sau.",
        ) from exc


@router.post(
    "/confirm-booking",
    response_model=List[MeetingResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Xác nhận đặt phòng từ bản xem trước chatbot",
)
def confirm_chatbot_booking(
    payload: ConfirmBookingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    slots = payload.slots
    required_values = {
        "title": slots.title,
        "booking_date": slots.booking_date,
        "start_time": slots.start_time,
        "duration_minutes": slots.duration_minutes,
        "capacity": slots.capacity,
        "room_id": slots.room_id,
    }
    missing_fields = [name for name, value in required_values.items() if value is None]
    if missing_fields:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Thông tin đặt phòng chưa đầy đủ.",
                "missing_fields": missing_fields,
            },
        )

    room = db.execute(
        select(Room).where(Room.id == slots.room_id, Room.is_active.is_(True))
    ).scalar_one_or_none()
    if room is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phòng họp không tồn tại hoặc đã ngưng hoạt động.",
        )
    if room.capacity < slots.capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sức chứa của phòng không đủ cho số người tham dự.",
        )

    booking_date = date.fromisoformat(slots.booking_date)
    start_clock = time.fromisoformat(slots.start_time)
    start_time = datetime.combine(booking_date, start_clock)
    end_time = start_time + timedelta(minutes=slots.duration_minutes)
    meeting_payload = MeetingCreateRequest(
        title=slots.title,
        description=payload.description,
        meeting_type="offline",
        room_id=slots.room_id,
        start_time=start_time,
        end_time=end_time,
        participant_ids=payload.participant_ids,
    )
    return MeetingService.create_meeting(
        db=db,
        payload=meeting_payload,
        organizer_id=current_user.id,
    )
