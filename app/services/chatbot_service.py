import logging
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.models.chat import ChatMessage, ChatSession
from app.services.gemini_service import (
    BookingSlots,
    GeminiChatResponse,
    GeminiService,
    GeminiServiceError,
)

logger = logging.getLogger(__name__)
ROOMSYNC_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")
MAX_HISTORY_MESSAGES = 20
REQUIRED_PREVIEW_FIELDS = (
    "title",
    "booking_date",
    "start_time",
    "duration_minutes",
    "capacity",
    "room_id",
)


class ChatbotService:
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

        db.add(
            ChatMessage(
                session_id=chat_session.id,
                sender="user",
                content=user_message.strip(),
            )
        )
        db.add(
            ChatMessage(
                session_id=chat_session.id,
                sender="bot",
                content=response.bot_message,
                intent=response.intent,
                slots=merged_slots.model_dump(mode="json"),
            )
        )
        chat_session.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

        try:
            db.commit()
            db.refresh(chat_session)
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
