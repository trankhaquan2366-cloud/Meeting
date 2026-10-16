import json
import logging
import re
import unicodedata
from collections.abc import AsyncIterator
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.models.chat import ChatMessage, ChatSession
from app.models.meeting import Meeting, MeetingParticipant
from app.models.room import Room
from app.schemas.meeting import MeetingCreateRequest
from app.services.user_service import search_participants
from app.services.equipment_service import get_equipment_availability
from app.services.gemini_service import (
    BookingSlots,
    GeminiChatResponse,
    GeminiService,
    GeminiServiceError,
)
from app.services.meeting_service import MeetingService
from app.services.room_service import get_available_rooms

logger = logging.getLogger(__name__)
ROOMSYNC_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")
MAX_HISTORY_MESSAGES = 4
REQUIRED_PREVIEW_FIELDS = (
    "title",
    "booking_date",
    "start_time",
    "duration_minutes",
    "capacity",
    "room_id",
)

_FENCED_JSON_START = re.compile(r"```(?:json)?\s*(\{)", re.DOTALL | re.IGNORECASE)
_ROOM_SEARCH_CAPACITY = re.compile(
    r"(?:(?:tim|can|dat)\s+)?phong(?:\s+hop)?\b.*?"
    r"(?:\bcho\s*)?(\d+)\s*(?:nguoi|cho)\b"
)
_BOOKING_INTENT = re.compile(
    r"\b(dat phong|tim phong|dat cuoc hop|tao cuoc hop|phong hop|phong trong|book(?:ing)?|meeting room)\b"
)
_LOCAL_FAQ_KEYWORDS = (
    "huong dan",
    "cach dat",
    "quy trinh",
    "tro giup",
    "han muc",
)
_LOCAL_BOOKING_GUIDE = (
    "### Hướng dẫn đặt phòng\n\n"
    "1. Chọn phòng hoặc mô tả nhu cầu đặt phòng họp.\n"
    "2. Cung cấp tiêu đề, ngày, giờ bắt đầu, thời lượng và số người tham dự.\n"
    "3. Chọn phòng phù hợp từ kết quả gợi ý.\n"
    "4. Kiểm tra thông tin trong thẻ xem trước và chọn **Đặt ngay** để xác nhận.\n\n"
    "Hạn mức người tham dự phụ thuộc vào sức chứa của phòng; hãy chọn phòng có đủ chỗ "
    "cho toàn bộ người tham dự.\n\n"
    "Bạn cũng có thể dùng các nút thao tác nhanh ở danh sách phòng để đặt trực tiếp."
)
_QUICK_REPLIES = {
    "xin chao": "Xin chào! Tôi có thể giúp bạn tìm phòng họp hoặc chuẩn bị đặt phòng.",
    "chao": "Xin chào! Tôi có thể giúp bạn tìm phòng họp hoặc chuẩn bị đặt phòng.",
    "chao ban": "Xin chào! Tôi có thể giúp bạn tìm phòng họp hoặc chuẩn bị đặt phòng.",
    "hello": "Xin chào! Tôi có thể giúp bạn tìm phòng họp hoặc chuẩn bị đặt phòng.",
    "hi": "Xin chào! Tôi có thể giúp bạn tìm phòng họp hoặc chuẩn bị đặt phòng.",
    "alo": "Xin chào! Tôi có thể giúp bạn tìm phòng họp hoặc chuẩn bị đặt phòng.",
    "cam on": "Rất vui được hỗ trợ bạn!",
    "tro giup": "Tôi có thể giúp tìm phòng họp và chuẩn bị thông tin đặt phòng.",
    "help": "Tôi có thể giúp tìm phòng họp và chuẩn bị thông tin đặt phòng.",
    "ban la ai": "Tôi là trợ lý RoomSync, có thể giúp tìm và đặt phòng họp.",
    "giup toi": "Tôi có thể giúp tìm phòng họp và chuẩn bị thông tin đặt phòng.",
}


def extract_json_payload(text: str) -> str:
    """Extract the first valid JSON object from model output, including fenced output."""
    text = text.strip()
    decoder = json.JSONDecoder()
    fenced_match = _FENCED_JSON_START.search(text)
    candidate_starts = (
        [fenced_match.start(1)]
        if fenced_match
        else [match.start() for match in re.finditer(r"\{", text)]
    )
    if fenced_match:
        candidate_starts.extend(
            match.start()
            for match in re.finditer(r"\{", text)
            if match.start() != fenced_match.start(1)
        )

    for start in candidate_starts:
        try:
            _, end = decoder.raw_decode(text[start:])
        except json.JSONDecodeError:
            continue
        return text[start:start + end].strip()
    return text


def _normalize_intent_text(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text.casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return normalized.replace("đ", "d")


def _quick_reply(user_message: str) -> str | None:
    normalized_message = _normalize_intent_text(user_message.strip())
    return _QUICK_REPLIES.get(normalized_message.strip(" .,!?:;"))


def check_local_faq(user_message: str) -> str | None:
    normalized_message = _normalize_intent_text(user_message.strip())
    if any(keyword in normalized_message for keyword in _LOCAL_FAQ_KEYWORDS):
        return _LOCAL_BOOKING_GUIDE
    return None


def _local_intent_for_message(normalized_message: str) -> str | None:
    text = normalized_message.strip(" .,!?:;")
    if "my_schedule" in text or "lich hop" in text or "lich hom nay" in text:
        return "my_schedule"
    if "available_rooms" in text or "phong trong" in text:
        return "available_rooms"
    if "cancel_latest" in text or "huy cuoc hop" in text or "huy lich" in text:
        return "cancel_latest"
    return None


def _room_search_capacity(normalized_message: str) -> int | None:
    match = _ROOM_SEARCH_CAPACITY.search(normalized_message)
    if match is None:
        return None
    capacity = int(match.group(1))
    return capacity if capacity > 0 else None


def _room_floor_sort_key(room: Room) -> tuple[int, int, str]:
    location = str(room.location or "").casefold()
    floor_match = re.search(r"\b(?:floor|tầng|tang)\s*(-?\d+)\b", location)
    if floor_match:
        return (0, int(floor_match.group(1)), location)
    return (1, 0, location)


def _room_equipment_count(room: Room) -> int:
    return sum(int(item.quantity or 0) for item in room.default_equipments)


class ChatbotService:
    @staticmethod
    async def stream_message(
        db: Session,
        chat_session_id: int,
        user_message: str,
        available_rooms: Sequence[Mapping[str, Any] | Any],
    ) -> AsyncIterator[dict[str, Any]]:
        if not user_message or not user_message.strip():
            yield {
                "type": "error",
                "message": "Tin nhắn không được để trống.",
            }
            return

        chat_session = db.execute(
            select(ChatSession)
            .where(ChatSession.id == chat_session_id)
            .options(selectinload(ChatSession.messages))
            .with_for_update()
        ).scalar_one_or_none()
        if chat_session is None:
            yield {
                "type": "error",
                "message": "Không tìm thấy phiên chat.",
            }
            return

        history = sorted(
            chat_session.messages,
            key=lambda message: (message.created_at or datetime.min, message.id or 0),
        )
        normalized_message = _normalize_intent_text(user_message.strip())
        local_intent = _local_intent_for_message(normalized_message)
        capacity_needed = _room_search_capacity(normalized_message)
        if capacity_needed is not None:
            local_intent = "room_search"
        if local_intent is not None:
            request_time = datetime.now(ROOMSYNC_TIMEZONE).replace(tzinfo=None)
            local_day_start = datetime.combine(request_time.date(), time.min)
            local_day_end = local_day_start + timedelta(days=1)
            user_id = chat_session.user_id
            widget: dict[str, Any] | None = None
            if local_intent == "my_schedule":
                participant_meeting_ids = select(MeetingParticipant.meeting_id).where(
                    MeetingParticipant.user_id == user_id
                )
                meetings = db.execute(
                    select(Meeting)
                    .where(
                        Meeting.start_time >= local_day_start,
                        Meeting.start_time < local_day_end,
                        func.upper(Meeting.status).notin_(
                            ["CANCELLED", "CANCELED", "CANCELLED_NO_SHOW"]
                        ),
                        or_(
                            Meeting.organizer_id == user_id,
                            Meeting.id.in_(participant_meeting_ids),
                        ),
                    )
                    .order_by(Meeting.start_time)
                    .limit(20)
                ).scalars().all()
                data = [
                    {
                        "id": meeting.id,
                        "title": meeting.title,
                        "start_time": meeting.start_time.isoformat(),
                        "end_time": meeting.end_time.isoformat(),
                        "room_name": meeting.room.name if meeting.room else "Trực tuyến",
                        "status": meeting.status,
                    }
                    for meeting in meetings
                ]
                message = (
                    f"Hôm nay bạn có {len(data)} cuộc họp."
                    if data
                    else "Hôm nay bạn chưa có cuộc họp nào."
                )
                widget = {
                    "type": "MY_SCHEDULE_WIDGET",
                    "title": "Lịch họp hôm nay",
                    "data": data,
                    "actions": [],
                }
            elif local_intent in {"available_rooms", "room_search"}:
                end_time = request_time + timedelta(hours=1)
                rooms = get_available_rooms(
                    db,
                    request_time,
                    end_time,
                    capacity_needed or 0,
                )
                rooms.sort(
                    key=lambda room: (
                        -_room_equipment_count(room),
                        *_room_floor_sort_key(room),
                        room.id,
                    )
                )
                room_data = [
                    {
                        **GeminiService._room_to_prompt(room),
                        "location": room.location,
                        "equipment_count": _room_equipment_count(room),
                    }
                    for room in rooms
                ]
                if room_data and capacity_needed is not None:
                    message = (
                        f"Có {len(room_data)} phòng phù hợp sức chứa từ "
                        f"{capacity_needed} người trong giờ tới."
                    )
                elif room_data:
                    message = f"Có {len(room_data)} phòng đang trống trong giờ tới."
                elif capacity_needed is not None:
                    message = (
                        f"Hiện không có phòng trống đủ sức chứa {capacity_needed} người "
                        "trong giờ tới."
                    )
                else:
                    message = "Hiện không có phòng trống trong giờ tới."
                widget = {
                    "type": "ROOM_LIST_WIDGET",
                    "title": (
                        f"Phòng trống cho {capacity_needed} người"
                        if capacity_needed is not None
                        else "Phòng đang trống"
                    ),
                    "data": room_data,
                    "actions": [],
                }
            else:
                meeting = db.execute(
                    select(Meeting)
                    .where(
                        Meeting.organizer_id == user_id,
                        Meeting.start_time >= request_time,
                        func.upper(Meeting.status).notin_(
                            ["CANCELLED", "CANCELED", "CANCELLED_NO_SHOW", "COMPLETED"]
                        ),
                    )
                    .order_by(Meeting.start_time)
                    .limit(1)
                ).scalar_one_or_none()
                if meeting is None:
                    message = "Không tìm thấy cuộc họp sắp tới nào do bạn tổ chức để hủy."
                else:
                    message = f"Bạn muốn hủy cuộc họp “{meeting.title}”?"
                    widget = {
                        "type": "CANCEL_CONFIRM_WIDGET",
                        "title": "Xác nhận hủy cuộc họp",
                        "data": {
                            "id": meeting.id,
                            "title": meeting.title,
                            "start_time": meeting.start_time.isoformat(),
                            "room_name": meeting.room.name if meeting.room else "Trực tuyến",
                        },
                        "actions": [
                            {"type": "confirm_cancel", "label": "Xác nhận hủy"}
                        ],
                    }

            response = GeminiChatResponse(
                intent="GENERAL_FAQ",
                slots=BookingSlots(),
                bot_message=message,
            )
            try:
                ChatbotService._persist_exchange(
                    db, chat_session, user_message.strip(), response
                )
            except SQLAlchemyError:
                logger.exception(
                    "Failed to persist local chatbot intent for chat_session_id=%s",
                    chat_session_id,
                )
                yield {
                    "type": "error",
                    "message": "Không thể lưu lịch sử hội thoại. Vui lòng thử lại.",
                }
                return
            yield {"type": "chunk", "text": message}
            if widget is not None:
                yield {"type": "room_widget", "widget": widget}
            yield {
                "type": "complete",
                "response": response.model_dump(mode="json"),
            }
            return

        quick_reply = check_local_faq(user_message) or _quick_reply(user_message)
        if quick_reply is not None:
            response = GeminiChatResponse(
                intent="GENERAL_FAQ",
                slots=BookingSlots(),
                bot_message=quick_reply,
            )
            try:
                ChatbotService._persist_exchange(
                    db, chat_session, user_message.strip(), response
                )
            except SQLAlchemyError:
                logger.exception(
                    "Failed to persist quick chatbot reply for chat_session_id=%s",
                    chat_session_id,
                )
                yield {
                    "type": "error",
                    "message": "Không thể lưu lịch sử hội thoại. Vui lòng thử lại.",
                }
                return
            yield {"type": "chunk", "text": response.bot_message}
            yield {
                "type": "complete",
                "response": response.model_dump(mode="json"),
            }
            return

        previous_slots = ChatbotService._latest_booking_slots(history)
        request_time = datetime.now(ROOMSYNC_TIMEZONE)
        prompt_data = {
            "current_time": request_time.isoformat(),
            "timezone": "Asia/Ho_Chi_Minh",
            "available_rooms": [
                GeminiService._room_to_prompt(room) for room in available_rooms
            ],
            "current_user_message": user_message.strip(),
        }

        def execute_search_users(arguments: Mapping[str, Any]) -> list[dict[str, Any]]:
            allowed_filters = (
                "department_code",
                "group_code",
                "position",
                "keyword",
            )
            filters = {
                key: value
                for key in allowed_filters
                if isinstance((value := arguments.get(key)), str) and value.strip()
            }
            if not filters:
                logger.warning("Gemini requested an unfiltered search_users call.")
                return []
            participants = search_participants(
                db,
                department_code=filters.get("department_code"),
                group_code=filters.get("group_code"),
                position=filters.get("position"),
                keyword=filters.get("keyword"),
            )
            return [
                {
                    "id": participant.id,
                    "full_name": participant.full_name or participant.username,
                    "email": participant.email,
                    "position": participant.position,
                    "department": (
                        {
                            "name": participant.department.name,
                            "code": participant.department.code,
                        }
                        if participant.department
                        else None
                    ),
                }
                for participant in participants
            ]

        def execute_search_available_rooms(
            arguments: Mapping[str, Any],
        ) -> list[Any]:
            start_value = arguments.get("start_time")
            end_value = arguments.get("end_time")
            capacity_value = arguments.get("capacity")
            if not isinstance(start_value, str) or not isinstance(end_value, str):
                raise ValueError("Room search requires ISO start_time and end_time.")
            if isinstance(capacity_value, bool) or not isinstance(capacity_value, int):
                raise ValueError("Room search capacity must be an integer.")
            try:
                start_time = datetime.fromisoformat(
                    start_value.replace("Z", "+00:00")
                )
                end_time = datetime.fromisoformat(end_value.replace("Z", "+00:00"))
                capacity = capacity_value
            except ValueError as exc:
                raise ValueError("Room search received invalid time or capacity.") from exc
            if end_time <= start_time or capacity < 1:
                raise ValueError("Room search requires a valid interval and capacity.")
            if start_time.tzinfo is not None:
                start_time = GeminiService._to_local_time(start_time).replace(tzinfo=None)
            if end_time.tzinfo is not None:
                end_time = GeminiService._to_local_time(end_time).replace(tzinfo=None)

            rooms = get_available_rooms(db, start_time, end_time, capacity)
            room_name = arguments.get("room_name")
            if isinstance(room_name, str) and room_name.strip():
                requested_name = room_name.strip().casefold()
                rooms = [
                    room for room in rooms
                    if requested_name in str(GeminiService._value(room, "name", "")).casefold()
                ]
            return rooms

        try:
            service = GeminiService()
        except GeminiServiceError:
            yield {
                "type": "error",
                "message": "Trợ lý hiện không thể xử lý yêu cầu. Vui lòng thử lại sau.",
            }
            return

        raw_response = ""
        emitted_message = ""
        resolved_attendees: list[dict[str, Any]] = []
        participant_search_called = False
        room_search_candidates: list[Mapping[str, Any]] = []
        draft_widget: dict[str, Any] | None = None
        async for event in service.stream_chat_response(
            messages=prompt_data,
            history=history[-MAX_HISTORY_MESSAGES:],
            tool_executor=execute_search_users,
            room_tool_executor=(
                execute_search_available_rooms
                if _BOOKING_INTENT.search(normalized_message)
                else None
            ),
        ):
            if event["type"] == "tool_result":
                if event.get("name") == "search_users":
                    participant_search_called = True
                    resolved_attendees = event.get("users", [])
                elif event.get("name") == "search_available_rooms":
                    room_search_candidates = event.get("rooms", [])
                continue
            if event["type"] == "error":
                yield event
                return
            chunk_text = event.get("text", "")
            raw_response += chunk_text
            streamed_message = ChatbotService._extract_streamed_bot_message(
                raw_response
            )
            if streamed_message.startswith(emitted_message):
                new_text = streamed_message[len(emitted_message):]
                if new_text:
                    emitted_message = streamed_message
                    yield {"type": "chunk", "text": new_text}

        try:
            cleaned = extract_json_payload(raw_response)
            generated = GeminiChatResponse.model_validate_json(cleaned)
        except ValueError:
            logger.exception("Gemini returned invalid streamed chatbot JSON.")
            yield {
                "type": "error",
                "message": "Trợ lý trả về phản hồi không hợp lệ. Vui lòng thử lại sau.",
            }
            return

        if generated.action == "CREATE_MEETING_DRAFT" and generated.parameters:
            parameters = generated.parameters
            try:
                if (
                    parameters.title is None
                    or parameters.date is None
                    or parameters.start_time is None
                    or parameters.end_time is None
                ):
                    raise ValueError("Draft is missing title or meeting time.")
                draft_title = parameters.title
                booking_date = date.fromisoformat(parameters.date)
                start_clock = time.fromisoformat(parameters.start_time)
                end_clock = time.fromisoformat(parameters.end_time)
                start_time = datetime.combine(booking_date, start_clock)
                end_time = datetime.combine(booking_date, end_clock)
                if end_time <= start_time:
                    raise ValueError("Draft end time must be later than start time.")
            except ValueError:
                logger.warning("Gemini returned an invalid meeting draft.")
                yield {
                    "type": "error",
                    "message": "Thông tin ngày hoặc giờ họp chưa hợp lệ. Vui lòng thử lại.",
                }
                return

            if parameters.target_group and not participant_search_called:
                resolved_attendees = execute_search_users(
                    {"keyword": parameters.target_group}
                )
                participant_search_called = True

            resolved_attendees = [
                participant
                for participant in resolved_attendees
                if participant.get("id") != chat_session.user_id
            ]
            participant_ids = [
                participant["id"]
                for participant in resolved_attendees
                if isinstance(participant.get("id"), int)
            ]
            capacity = parameters.capacity or max(1, len(set(participant_ids)) + 1)
            requested_equipment = [
                name.strip().casefold()
                for name in parameters.equipments_required
                if name.strip()
            ]
            equipment_options = get_equipment_availability(
                db, start_time, end_time, active_only=True
            )
            available_equipment_names = [
                str(equipment["name"]).casefold()
                for equipment in equipment_options
                if equipment["available_qty"] > 0
            ]
            draft_candidates = get_available_rooms(
                db, start_time, end_time, capacity
            )

            def room_equipment_names(room: Room) -> list[str]:
                return [
                    str(item.equipment.name).casefold()
                    for item in room.default_equipments
                    if item.equipment is not None
                ]

            draft_candidates = [
                room
                for room in draft_candidates
                if all(
                    any(
                        required in installed or installed in required
                        for installed in room_equipment_names(room)
                    )
                    or any(
                        required in available or available in required
                        for available in available_equipment_names
                    )
                    for required in requested_equipment
                )
            ]
            if not requested_equipment:
                draft_candidates.sort(
                    key=lambda room: (
                        -_room_equipment_count(room),
                        *_room_floor_sort_key(room),
                        room.id,
                    )
                )
            else:
                draft_candidates.sort(
                    key=lambda room: (
                        -sum(
                            any(
                                required in installed or installed in required
                                for installed in room_equipment_names(room)
                            )
                            for required in requested_equipment
                        ),
                        -_room_equipment_count(room),
                        *_room_floor_sort_key(room),
                        room.id,
                    )
                )

            valid_candidates: list[Room] = []
            participant_conflict_found = False
            for room in draft_candidates:
                validation = MeetingService.validate_meeting_booking(
                    db,
                    MeetingCreateRequest(
                        title=draft_title,
                        meeting_type="offline",
                        room_id=room.id,
                        start_time=start_time,
                        end_time=end_time,
                        participant_ids=participant_ids,
                    ),
                    organizer_id=chat_session.user_id,
                )
                if validation["blocking_errors"]:
                    continue
                if any(
                    warning.get("type") == "ParticipantConflictWarning"
                    for warning in validation["warnings"]
                ):
                    participant_conflict_found = True
                    continue
                valid_candidates.append(room)

            if valid_candidates:
                selected_room = valid_candidates[0]
                generated.intent = "BOOK_ROOM"
                generated.slots = BookingSlots(
                    title=draft_title,
                    booking_date=booking_date.isoformat(),
                    start_time=start_clock.strftime("%H:%M"),
                    duration_minutes=int((end_time - start_time).total_seconds() // 60),
                    capacity=capacity,
                    room_id=selected_room.id,
                    room_name=selected_room.name,
                )
                generated.bot_message = "Đã chuẩn bị bản nháp. Kiểm tra thông tin trước khi tạo cuộc họp."
                draft_widget = {
                    "type": "ROOM_CONFIRMATION_WIDGET",
                    "title": "Xác nhận cuộc họp",
                    "data": GeminiService._room_to_prompt(selected_room),
                    "meeting": generated.slots.model_dump(mode="json"),
                    "participants": resolved_attendees,
                    "equipments_required": [
                        required
                        for required in parameters.equipments_required
                        if not any(
                            required.casefold() in installed
                            or installed in required.casefold()
                            for installed in room_equipment_names(selected_room)
                        )
                    ],
                    "equipment_options": [
                        {
                            "id": equipment["id"],
                            "name": equipment["name"],
                            "available_quantity": equipment["available_qty"],
                        }
                        for equipment in equipment_options
                    ],
                    "actions": [
                        {"type": "confirm_booking", "label": "Đồng ý tạo cuộc họp"}
                    ],
                }
            else:
                generated.intent = "BOOK_ROOM"
                generated.slots = BookingSlots(
                    title=draft_title,
                    booking_date=booking_date.isoformat(),
                    start_time=start_clock.strftime("%H:%M"),
                    duration_minutes=int((end_time - start_time).total_seconds() // 60),
                    capacity=capacity,
                )
                generated.bot_message = (
                    "Không tìm thấy phòng phù hợp với sức chứa, thiết bị và lịch "
                    "của người tham dự."
                    if not participant_conflict_found
                    else "Người tham dự đã có cuộc họp trùng giờ. Hãy chọn thời gian khác."
                )
                generated.is_ready_for_preview = False
                generated.missing_fields = ["room_id"]

        room_candidates = (
            room_search_candidates
            if _BOOKING_INTENT.search(normalized_message)
            and generated.intent == "BOOK_ROOM"
            else available_rooms
        )
        if draft_widget is not None:
            room_candidates = [draft_widget["data"]]
        generated = GeminiService._validate_room_selection(generated, room_candidates)
        merged_slots = ChatbotService._merge_slots(previous_slots, generated.slots)
        ChatbotService._validate_merged_room(merged_slots, room_candidates)
        response = ChatbotService._finalize_response(generated, merged_slots)

        try:
            ChatbotService._persist_exchange(
                db,
                chat_session,
                user_message.strip(),
                response,
            )
        except SQLAlchemyError:
            logger.exception(
                "Failed to persist streamed chatbot exchange for chat_session_id=%s",
                chat_session_id,
            )
            yield {
                "type": "error",
                "message": "Không thể lưu lịch sử hội thoại.",
            }
            return

        if draft_widget is not None:
            yield {"type": "room_widget", "widget": draft_widget}

        if (
            draft_widget is None
            and
            _BOOKING_INTENT.search(normalized_message)
            and generated.intent == "BOOK_ROOM"
            and room_search_candidates
        ):
            selected_room = next(
                (
                    room for room in room_search_candidates
                    if GeminiService._value(room, "id") == merged_slots.room_id
                ),
                room_search_candidates[0],
            )
            room_slots = merged_slots.model_copy(
                update={
                    "room_id": GeminiService._value(selected_room, "id"),
                    "room_name": GeminiService._value(selected_room, "name"),
                }
            )
            yield {
                "type": "room_widget",
                "widget": {
                    "type": "ROOM_CARD_WIDGET",
                    "title": "Phòng họp phù hợp",
                    "data": GeminiService._room_to_prompt(selected_room),
                    "actions": [{"type": "confirm_booking", "label": "Đặt ngay"}],
                },
                "meeting": room_slots.model_dump(mode="json"),
            }

        if response.is_ready_for_preview and participant_search_called:
            room = next(
                (
                    item
                    for item in room_candidates
                    if GeminiService._value(item, "id") == merged_slots.room_id
                ),
                None,
            )
            room_capacity = GeminiService._value(room, "capacity") if room else None
            yield {
                "type": "preview_card",
                "widget": (
                    response.ui_widget.model_dump(mode="json")
                    if response.ui_widget
                    else None
                ),
                "meeting": {
                    **merged_slots.model_dump(mode="json"),
                    "room_capacity": room_capacity,
                },
                "participants": resolved_attendees,
                "is_over_capacity": (
                    room_capacity is not None
                    and len(resolved_attendees) > room_capacity
                ),
            }

        yield {
            "type": "complete",
            "response": response.model_dump(mode="json"),
        }

    @staticmethod
    def _persist_exchange(
        db: Session,
        chat_session: ChatSession,
        user_message: str,
        response: GeminiChatResponse,
    ) -> None:
        db.add(
            ChatMessage(
                session_id=chat_session.id,
                sender="user",
                content=user_message,
            )
        )
        db.add(
            ChatMessage(
                session_id=chat_session.id,
                sender="bot",
                content=response.bot_message,
                intent=response.intent,
                slots=response.slots.model_dump(mode="json"),
            )
        )
        chat_session.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        try:
            db.commit()
            db.refresh(chat_session)
        except SQLAlchemyError:
            db.rollback()
            raise

    @staticmethod
    def _extract_streamed_bot_message(raw_response: str) -> str:
        field_start = raw_response.find('"bot_message"')
        if field_start == -1:
            return ""
        value_start = raw_response.find('"', raw_response.find(":", field_start) + 1)
        if value_start == -1:
            return ""

        encoded = raw_response[value_start + 1:]
        escaped = False
        value_end = len(encoded)
        complete = False
        for index, character in enumerate(encoded):
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                value_end = index
                complete = True
                break

        candidate = encoded[:value_end]
        max_trim = 0 if complete else min(6, len(candidate))
        for trim in range(max_trim + 1):
            partial = candidate[: len(candidate) - trim] if trim else candidate
            try:
                return json.loads(f'"{partial}"')
            except json.JSONDecodeError:
                continue
        return ""

    @staticmethod
    def process_message(
        db: Session,
        chat_session_id: int,
        user_message: str,
        available_rooms: Sequence[Mapping[str, Any] | Any],
        current_time: datetime | None = None,
        gemini_service: GeminiService | None = None,
    ) -> GeminiChatResponse:
        if not user_message or not user_message.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Tin nhắn không được để trống.",
            )

        chat_session = db.execute(
            select(ChatSession)
            .where(ChatSession.id == chat_session_id)
            .options(selectinload(ChatSession.messages))
            .with_for_update()
        ).scalar_one_or_none()
        if chat_session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy phiên chat.",
            )

        history = sorted(
            chat_session.messages,
            key=lambda message: (message.created_at or datetime.min, message.id or 0),
        )
        quick_reply = check_local_faq(user_message) or _quick_reply(user_message)
        if quick_reply is not None:
            response = GeminiChatResponse(
                intent="GENERAL_FAQ",
                slots=BookingSlots(),
                bot_message=quick_reply,
            )
            ChatbotService._persist_exchange(
                db, chat_session, user_message.strip(), response
            )
            return response

        previous_slots = ChatbotService._latest_booking_slots(history)
        request_time = current_time or datetime.now(ROOMSYNC_TIMEZONE)

        try:
            service = gemini_service or GeminiService()
            generated = service.generate_chat_response(
                user_message=user_message,
                history=history[-MAX_HISTORY_MESSAGES:],
                current_time=request_time,
                available_rooms=available_rooms,
            )
        except GeminiServiceError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Trợ lý hiện không thể xử lý yêu cầu. Vui lòng thử lại sau.",
            ) from exc

        merged_slots = ChatbotService._merge_slots(previous_slots, generated.slots)
        ChatbotService._validate_merged_room(merged_slots, available_rooms)
        response = ChatbotService._finalize_response(generated, merged_slots)

        try:
            ChatbotService._persist_exchange(
                db,
                chat_session,
                user_message.strip(),
                response,
            )
        except SQLAlchemyError as exc:
            db.rollback()
            logger.exception(
                "Failed to persist chatbot exchange for chat_session_id=%s",
                chat_session_id,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Không thể lưu lịch sử hội thoại.",
            ) from exc

        return response

    @staticmethod
    def _latest_booking_slots(history: Sequence[ChatMessage]) -> BookingSlots:
        for message in reversed(history):
            if message.sender == "bot" and message.slots:
                return BookingSlots.model_validate(message.slots)
        return BookingSlots()

    @staticmethod
    def _merge_slots(previous: BookingSlots, extracted: BookingSlots) -> BookingSlots:
        merged = previous.model_dump()
        merged.update(extracted.model_dump(exclude_none=True))
        return BookingSlots.model_validate(merged)

    @staticmethod
    def _validate_merged_room(
        slots: BookingSlots,
        available_rooms: Sequence[Mapping[str, Any] | Any],
    ) -> None:
        if slots.room_id is None:
            slots.room_name = None
            return

        room = next(
            (
                item
                for item in available_rooms
                if GeminiService._value(item, "id") == slots.room_id
            ),
            None,
        )
        capacity = GeminiService._value(room, "capacity") if room is not None else None
        if room is None or (capacity is not None and slots.capacity is not None and capacity < slots.capacity):
            slots.room_id = None
            slots.room_name = None
            return
        slots.room_name = GeminiService._value(room, "name")

    @staticmethod
    def _finalize_response(
        generated: GeminiChatResponse,
        merged_slots: BookingSlots,
    ) -> GeminiChatResponse:
        generated.slots = merged_slots
        if generated.intent == "GENERAL_FAQ":
            generated.missing_fields = []
            generated.is_ready_for_preview = False
            return generated

        model_missing_fields = set(generated.missing_fields)
        model_ready = generated.is_ready_for_preview
        missing = [
            field
            for field in REQUIRED_PREVIEW_FIELDS
            if getattr(merged_slots, field) is None
        ]
        generated.missing_fields = missing
        generated.is_ready_for_preview = not missing
        if missing and (
            model_ready or model_missing_fields != set(missing)
        ):
            field_labels = {
                "title": "tiêu đề cuộc họp",
                "booking_date": "ngày họp",
                "start_time": "giờ bắt đầu",
                "duration_minutes": "thời lượng cuộc họp",
                "capacity": "số người tham dự",
                "room_id": "phòng họp phù hợp",
            }
            labels = ", ".join(field_labels[field] for field in missing)
            generated.bot_message = (
                f"Để tiếp tục đặt phòng, vui lòng cho tôi biết thêm: {labels}."
            )
        elif not missing and (not model_ready or model_missing_fields):
            generated.bot_message = (
                "Đã đủ thông tin để chuẩn bị bản xem trước đặt phòng. "
                "Bạn có thể kiểm tra lại trước khi xác nhận."
            )
        return generated
