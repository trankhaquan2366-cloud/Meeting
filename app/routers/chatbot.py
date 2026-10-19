import json
import logging
import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse, ServerSentEvent
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.chat import ChatMessage, ChatSession
from app.models.department import Department
from app.models.equipment import Equipment
from app.models.project_group import ProjectGroup
from app.models.room import Room
from app.models.user import User
from app.schemas.chat import ChatMessageResponse, ChatSessionResponse
from app.schemas.meeting import MeetingCreateRequest, MeetingResponse
from app.services.chatbot_service import ChatbotService
from app.services.gemini_service import BookingSlots
from app.services.meeting_service import MeetingService
from app.services.meeting_invitation_service import schedule_meeting_invitations
from app.services.room_service import get_available_rooms

logger = logging.getLogger(__name__)
router = APIRouter()
CHAT_STREAM_FALLBACK_MESSAGE = (
    "Trợ lý AI hiện chưa kết nối được máy chủ. Bạn có thể bấm nút "
    "[Tìm phòng 6 người] ở bên dưới hoặc chọn phòng trực tiếp từ danh sách."
)


def _chat_stream_fallback_events() -> list[dict[str, str]]:
    response = {
        "intent": "GENERAL_FAQ",
        "message": CHAT_STREAM_FALLBACK_MESSAGE,
        "bot_message": CHAT_STREAM_FALLBACK_MESSAGE,
        "slots": {},
        "preview_card": None,
        "is_ready_for_preview": False,
    }
    return [
        {
            "event": "chunk",
            "data": json.dumps(
                {"type": "chunk", "text": CHAT_STREAM_FALLBACK_MESSAGE},
                ensure_ascii=False,
            ),
        },
        {
            "event": "complete",
            "data": json.dumps(
                {"type": "complete", "response": response},
                ensure_ascii=False,
            ),
        },
    ]


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


class AssistantMeetingRequest(BaseModel):
    session_id: Optional[int] = Field(default=None, gt=0)
    source_prompt: Optional[str] = Field(default=None, max_length=4000)
    group_type: Literal["department", "project"]
    group_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=200)
    start_time: datetime
    end_time: datetime
    equipment_ids: List[int] = Field(default_factory=list, max_length=4)
    online_meeting: bool = False


class AssistantMeetingResponse(MeetingResponse):
    room_name: Optional[str] = None


def _meeting_candidate_is_valid(
    db: Session,
    *,
    title: str,
    start_time: datetime,
    end_time: datetime,
    participant_ids: list[int],
    organizer_id: int,
    room: Room | None,
    equipment_ids: list[int],
    meeting_link: str | None = None,
) -> bool:
    payload = MeetingCreateRequest(
        title=title,
        meeting_type="online" if meeting_link else "offline",
        meeting_link=meeting_link,
        room_id=room.id if room else None,
        start_time=start_time,
        end_time=end_time,
        participant_ids=participant_ids,
        equipments=[
            {"equipment_id": equipment_id, "quantity": 1}
            for equipment_id in equipment_ids
        ],
    )
    validation = MeetingService.validate_meeting_booking(
        db,
        payload,
        organizer_id=organizer_id,
    )
    return not validation["blocking_errors"] and not any(
        warning.get("type") in {
            "ParticipantConflictWarning",
            "EquipmentShortageWarning",
            "OverCapacityWarning",
        }
        for warning in validation["warnings"]
    )


def _alternative_meeting_slots(
    db: Session,
    *,
    title: str,
    start_time: datetime,
    end_time: datetime,
    capacity: int,
    participant_ids: list[int],
    organizer_id: int,
    equipment_ids: list[int],
    online_meeting: bool,
) -> list[dict]:
    duration = end_time - start_time
    suggestions: list[dict] = []
    first_day = start_time.date()
    for day_offset in range(4):
        day = first_day + timedelta(days=day_offset)
        for hour in range(8, 18):
            for minute in (0, 30):
                candidate_start = datetime.combine(day, time(hour, minute))
                if candidate_start < start_time:
                    continue
                candidate_end = candidate_start + duration
                if candidate_end.time() > time(18, 0):
                    continue
                rooms = (
                    [None]
                    if online_meeting
                    else get_available_rooms(db, candidate_start, candidate_end, capacity)
                )
                found_slot = False
                for room in rooms:
                    if _meeting_candidate_is_valid(
                        db,
                        title=title,
                        start_time=candidate_start,
                        end_time=candidate_end,
                        participant_ids=participant_ids,
                        organizer_id=organizer_id,
                        room=room,
                        equipment_ids=equipment_ids,
                        meeting_link="https://meet.jit.si/roomsync-alternative"
                        if online_meeting
                        else None,
                    ):
                        suggestions.append({
                            "room_id": room.id if room else None,
                            "room_name": room.name if room else "Trực tuyến",
                            "start_time": candidate_start.isoformat(),
                            "end_time": candidate_end.isoformat(),
                        })
                        found_slot = True
                        break
                if found_slot or len(suggestions) >= 3:
                    break
            if len(suggestions) >= 3:
                break
        if len(suggestions) >= 3:
            break
    return suggestions


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


def _assistant_equipment_options(db: Session) -> list[dict]:
    equipment_rows = (
        db.query(Equipment)
        .filter(Equipment.is_active.is_(True))
        .order_by(Equipment.name, Equipment.id)
        .all()
    )
    aliases = {
        "tv": ("tv", "tivi", "television"),
        "projector": ("projector", "máy chiếu", "may chieu"),
        "mic": ("mic", "micro", "microphone", "micro không dây"),
        "whiteboard": ("whiteboard", "bảng trắng", "bang trang"),
    }
    equipment_options = []
    for key, terms in aliases.items():
        equipment = next(
            (
                row
                for row in equipment_rows
                if any(term in row.name.casefold() for term in terms)
            ),
            None,
        )
        equipment_options.append({
            "key": key,
            "label": {
                "tv": "TV",
                "projector": "Projector",
                "mic": "Mic",
                "whiteboard": "Whiteboard",
            }[key],
            "id": equipment.id if equipment else None,
            "available": equipment is not None,
        })
    return equipment_options


@router.get(
    "/meeting-form-options",
    summary="Lấy danh mục cho biểu mẫu tạo cuộc họp của trợ lý",
)
def get_assistant_meeting_form_options(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    departments = db.query(Department).order_by(Department.name, Department.id).all()
    project_groups = db.query(ProjectGroup).order_by(ProjectGroup.name, ProjectGroup.id).all()
    return {
        "departments": [
            {"id": item.id, "name": item.name, "code": item.code}
            for item in departments
        ],
        "projects": [
            {"id": item.id, "name": item.name, "code": item.code}
            for item in project_groups
        ],
        "equipment": _assistant_equipment_options(db),
    }


@router.post(
    "/meetings",
    response_model=List[AssistantMeetingResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Tạo và mời thành viên phòng ban hoặc nhóm dự án qua trợ lý",
)
def create_assistant_meeting(
    payload: AssistantMeetingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat_session = None
    if payload.session_id is not None:
        chat_session = db.execute(
            select(ChatSession).where(
                ChatSession.id == payload.session_id,
                ChatSession.user_id == current_user.id,
            )
        ).scalar_one_or_none()
        if chat_session is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên chat.")

    if payload.end_time <= payload.start_time:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Thời gian kết thúc phải sau thời gian bắt đầu.",
        )

    if payload.group_type == "department":
        group = db.get(Department, payload.group_id)
        if group is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy phòng ban.")
        members = (
            db.query(User)
            .filter(User.department_id == group.id, User.is_active.is_(True))
            .order_by(User.id)
            .all()
        )
    else:
        group = db.get(ProjectGroup, payload.group_id)
        if group is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy nhóm dự án.")
        members = (
            db.query(User)
            .filter(
                User.project_groups.any(ProjectGroup.id == group.id),
                User.is_active.is_(True),
            )
            .order_by(User.id)
            .all()
        )

    participant_ids = sorted({member.id for member in members if member.id != current_user.id})
    capacity = len(participant_ids) + 1
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Tên cuộc họp không được để trống.")

    equipment_ids = sorted(set(payload.equipment_ids))
    allowed_equipment_ids = {
        item["id"]
        for item in _assistant_equipment_options(db)
        if item["id"] is not None
    }
    if not set(equipment_ids).issubset(allowed_equipment_ids):
        raise HTTPException(
            status_code=422,
            detail="Chỉ có thể chọn TV, Projector, Mic hoặc Whiteboard đang hoạt động.",
        )

    meeting_link = (
        f"https://meet.jit.si/roomsync-{uuid.uuid4().hex}"
        if payload.online_meeting
        else None
    )
    if payload.online_meeting:
        if not _meeting_candidate_is_valid(
            db,
            title=title,
            start_time=payload.start_time,
            end_time=payload.end_time,
            participant_ids=participant_ids,
            organizer_id=current_user.id,
            room=None,
            equipment_ids=[],
            meeting_link=meeting_link,
        ):
            suggestions = _alternative_meeting_slots(
                db,
                title=title,
                start_time=payload.start_time + timedelta(minutes=30),
                end_time=payload.end_time + timedelta(minutes=30),
                capacity=capacity,
                participant_ids=participant_ids,
                organizer_id=current_user.id,
                equipment_ids=[],
                online_meeting=True,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Người tham dự có lịch trùng. Hãy chọn khung giờ gợi ý.",
                    "suggestions": suggestions,
                },
            )
        room = None
    else:
        room = None
        rooms = get_available_rooms(
            db,
            payload.start_time,
            payload.end_time,
            min_capacity=capacity,
        )
        rooms.sort(key=lambda item: (item.capacity, item.id))
        room = next(
            (
                candidate
                for candidate in rooms
                if _meeting_candidate_is_valid(
                    db,
                    title=title,
                    start_time=payload.start_time,
                    end_time=payload.end_time,
                    participant_ids=participant_ids,
                    organizer_id=current_user.id,
                    room=candidate,
                    equipment_ids=equipment_ids,
                )
            ),
            None,
        )
        if room is None:
            suggestions = _alternative_meeting_slots(
                db,
                title=title,
                start_time=payload.start_time + timedelta(minutes=30),
                end_time=payload.end_time + timedelta(minutes=30),
                capacity=capacity,
                participant_ids=participant_ids,
                organizer_id=current_user.id,
                equipment_ids=equipment_ids,
                online_meeting=False,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": (
                        "Không có phòng phù hợp vào khung giờ này. "
                        "Bạn có thể chọn phòng hoặc thời gian gần nhất bên dưới."
                    ),
                    "suggestions": suggestions,
                },
            )

    meeting_payload = MeetingCreateRequest(
        title=title,
        description=f"Cuộc họp {group.name} được tạo từ trợ lý RoomSync.",
        meeting_type="online" if payload.online_meeting else "offline",
        meeting_link=meeting_link,
        room_id=room.id if room else None,
        start_time=payload.start_time,
        end_time=payload.end_time,
        participant_ids=participant_ids,
        equipments=[
            {"equipment_id": equipment_id, "quantity": 1}
            for equipment_id in equipment_ids
        ],
    )
    created_meetings = MeetingService.create_meeting(
        db=db,
        payload=meeting_payload,
        organizer_id=current_user.id,
    )
    if chat_session is not None and created_meetings:
        meeting = created_meetings[0]
        assistant_message = (
            f"Đã tạo cuộc họp “{meeting.title}” cho {group.name} "
            f"vào {meeting.start_time:%H:%M %d/%m/%Y}."
        )
        if meeting.meeting_link:
            assistant_message += f" Link tham gia: {meeting.meeting_link}"
        try:
            db.add_all([
                ChatMessage(
                    session_id=chat_session.id,
                    sender="user",
                    content=(payload.source_prompt or f"Tạo cuộc họp {group.name}").strip(),
                ),
                ChatMessage(
                    session_id=chat_session.id,
                    sender="bot",
                    content=assistant_message,
                    intent="BOOK_ROOM",
                    slots={
                        "title": meeting.title,
                        "booking_date": meeting.start_time.date().isoformat(),
                        "start_time": meeting.start_time.strftime("%H:%M"),
                        "duration_minutes": int(
                            (meeting.end_time - meeting.start_time).total_seconds() // 60
                        ),
                        "capacity": capacity,
                        "room_id": meeting.room_id,
                        "room_name": meeting.room.name if meeting.room else None,
                        "meeting_link": meeting.meeting_link,
                    },
                ),
            ])
            chat_session.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            logger.exception(
                "Meeting created but chatbot transcript could not be saved "
                "for session_id=%s meeting_id=%s",
                chat_session.id,
                meeting.id,
            )
    schedule_meeting_invitations(
        background_tasks=background_tasks,
        db=db,
        meetings=created_meetings,
        participant_ids=participant_ids,
        organizer=current_user,
    )
    return created_meetings


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
    "/sessions/{session_id}/message/stream",
    summary="Gửi tin nhắn tới trợ lý RoomSync bằng SSE",
)
@router.post(
    "/sessions/{session_id}/message",
    summary="Gửi tin nhắn tới trợ lý RoomSync bằng SSE",
)
def stream_chat_message(
    session_id: int,
    payload: ChatUserMessageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_session(db, session_id, current_user.id)
    try:
        available_rooms = MeetingService.get_all_active_rooms(db)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception(
            "Database error while starting streamed chat for session_id=%s user_id=%s",
            session_id,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Trợ lý hiện không thể xử lý yêu cầu. Vui lòng thử lại sau.",
        ) from exc

    async def content_generator():
        yield ServerSentEvent(comment="keep-alive")
        try:
            async for event in ChatbotService.stream_message(
                db=db,
                chat_session_id=session_id,
                user_message=payload.content,
                available_rooms=available_rooms,
            ):
                if event.get("type") == "error" and (
                    event.get("message") == CHAT_STREAM_FALLBACK_MESSAGE
                    or "429" in str(event.get("message", ""))
                    or "503" in str(event.get("message", ""))
                ):
                    for fallback_event in _chat_stream_fallback_events():
                        yield fallback_event
                    return
                if event.get("type") == "room_widget":
                    yield {
                        "event": "room_widget",
                        "data": json.dumps(event, ensure_ascii=False),
                    }
                    continue
                event_type = event.get("type", "message")
                yield {
                    "event": event_type,
                    "data": json.dumps(event, ensure_ascii=False),
                }
        except TimeoutError:
            logger.warning(
                "Chat stream timed out for session_id=%s user_id=%s",
                session_id,
                current_user.id,
            )
            for fallback_event in _chat_stream_fallback_events():
                yield fallback_event
        except Exception as exc:
            if isinstance(exc, SQLAlchemyError):
                db.rollback()
            if getattr(exc, "code", None) in (429, 503) or any(
                marker in str(exc).upper()
                for marker in ("429", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE")
            ):
                logger.warning("Gemini upstream overload during SSE: %s", exc)
                for fallback_event in _chat_stream_fallback_events():
                    yield fallback_event
                return
            logger.error(f"SSE stream error: {exc}", exc_info=True)
            err_data = json.dumps(
                {
                    "error": (
                        "Đã xảy ra lỗi trong quá trình xử lý luồng. "
                        "Vui lòng thử lại."
                    ),
                    "message": (
                        "Đã xảy ra lỗi trong quá trình xử lý luồng. "
                        "Vui lòng thử lại."
                    ),
                },
                ensure_ascii=False,
            )
            yield {"event": "error", "data": err_data}

    return EventSourceResponse(
        content_generator(),
        ping=5,
        sep="\n",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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
        select(Room).where(
            Room.id == slots.room_id,
            Room.is_active.is_(True),
            Room.room_status == "active",
        )
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
