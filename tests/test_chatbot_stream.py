import asyncio
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sse_starlette.sse import AppStatus
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.chat import ChatMessage, ChatSession
from app.models.meeting import Meeting
from app.routers import chatbot as chatbot_router
from app.services import chatbot_service
from app.services.chatbot_service import extract_json_payload
from tests.helpers import _auth_header, _create_room, _create_user, _make_token

ROOMSYNC_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")


def test_chat_stream_endpoint_returns_sse(
    client: TestClient,
    db_session: Session,
    monkeypatch,
):
    AppStatus.should_exit_event = None
    AppStatus.should_exit = False
    user = _create_user(db_session, "chat-stream-user")
    chat_session = ChatSession(user_id=user.id, title="Streaming chat")
    db_session.add(chat_session)
    db_session.commit()

    async def fake_stream_message(**kwargs):
        yield {"type": "chunk", "text": "Xin chào"}
        yield {
            "type": "complete",
            "response": {
                "intent": "GENERAL_FAQ",
                "message": "Xin chào",
                "bot_message": "Xin chào",
                "slots": {},
                "preview_card": None,
                "is_ready_for_preview": False,
            },
        }

    monkeypatch.setattr(
        chatbot_router.ChatbotService,
        "stream_message",
        fake_stream_message,
    )

    response = client.post(
        f"/api/v1/chatbot/sessions/{chat_session.id}/message/stream",
        json={"content": "Xin chào"},
        headers=_auth_header(_make_token(user)),
    )
    AppStatus.should_exit_event = None
    AppStatus.should_exit = False

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.text.startswith(": keep-alive\r\n\r\n")
    assert "event: chunk" in response.text
    assert "event: complete" in response.text


def test_chat_stream_endpoint_emits_sse_error_when_service_raises(
    client: TestClient,
    db_session: Session,
    monkeypatch,
    caplog,
):
    AppStatus.should_exit_event = None
    AppStatus.should_exit = False
    user = _create_user(db_session, "chat-stream-error-user")
    chat_session = ChatSession(user_id=user.id, title="Streaming error chat")
    db_session.add(chat_session)
    db_session.commit()

    async def failing_stream_message(**kwargs):
        raise RuntimeError("simulated stream failure")
        yield

    monkeypatch.setattr(
        chatbot_router.ChatbotService,
        "stream_message",
        failing_stream_message,
    )

    response = client.post(
        f"/api/v1/chatbot/sessions/{chat_session.id}/message/stream",
        json={"content": "Xin chào"},
        headers=_auth_header(_make_token(user)),
    )

    assert response.status_code == 200
    assert response.text.startswith(": keep-alive\r\n\r\n")
    assert "event: error" in response.text
    assert (
        '"error": "Đã xảy ra lỗi trong quá trình xử lý luồng. Vui lòng thử lại."'
        in response.text
    )
    assert "SSE stream error: simulated stream failure" in caplog.text


def test_chat_stream_timeout_emits_fallback_message_and_complete(
    client: TestClient,
    db_session: Session,
    monkeypatch,
):
    AppStatus.should_exit_event = None
    AppStatus.should_exit = False
    user = _create_user(db_session, "chat-stream-timeout-user")
    chat_session = ChatSession(user_id=user.id, title="Timeout chat")
    db_session.add(chat_session)
    db_session.commit()

    async def slow_stream_message(**kwargs):
        raise TimeoutError("simulated stream timeout")
        yield

    monkeypatch.setattr(
        chatbot_router.ChatbotService,
        "stream_message",
        slow_stream_message,
    )
    response = client.post(
        f"/api/v1/chatbot/sessions/{chat_session.id}/message/stream",
        json={"content": "Xin chào"},
        headers=_auth_header(_make_token(user)),
    )

    AppStatus.should_exit_event = None
    AppStatus.should_exit = False
    assert response.status_code == 200
    assert "Trợ lý AI hiện chưa kết nối được máy chủ." in response.text
    assert "event: complete" in response.text


def test_simple_greeting_bypasses_gemini_and_streams_static_reply(
    db_session: Session,
    monkeypatch,
):
    user = _create_user(db_session, "chat-static-greeting-user")
    chat_session = ChatSession(user_id=user.id, title="Static greeting")
    db_session.add(chat_session)
    db_session.commit()

    def unexpected_gemini_call():
        raise AssertionError("A simple greeting must not call Gemini.")

    monkeypatch.setattr(chatbot_service, "GeminiService", unexpected_gemini_call)

    async def collect_events():
        return [
            event
            async for event in chatbot_service.ChatbotService.stream_message(
                db=db_session,
                chat_session_id=chat_session.id,
                user_message="Xin chào!",
                available_rooms=[],
            )
        ]

    events = asyncio.run(collect_events())

    assert [event["type"] for event in events] == ["chunk", "complete"]
    assert "Xin chào" in events[0]["text"]
    assert (
        db_session.query(ChatMessage)
        .filter_by(session_id=chat_session.id)
        .count()
        == 2
    )


def test_local_faq_handles_booking_limits_without_calling_gemini(
    db_session: Session,
    monkeypatch,
):
    user = _create_user(db_session, "chat-local-limit-user")
    chat_session = ChatSession(user_id=user.id, title="Local FAQ")
    db_session.add(chat_session)
    db_session.commit()

    def unexpected_gemini_call():
        raise AssertionError("A local FAQ must not call Gemini.")

    monkeypatch.setattr(chatbot_service, "GeminiService", unexpected_gemini_call)

    async def collect_events():
        return [
            event
            async for event in chatbot_service.ChatbotService.stream_message(
                db=db_session,
                chat_session_id=chat_session.id,
                user_message="Hạn mức người tham dự là bao nhiêu?",
                available_rooms=[],
            )
        ]

    events = asyncio.run(collect_events())

    assert [event["type"] for event in events] == ["chunk", "complete"]
    assert "Hạn mức" in events[0]["text"]


def test_local_intents_emit_schedule_and_cancel_confirmation_without_gemini(
    db_session: Session,
    monkeypatch,
):
    user = _create_user(db_session, "chat-local-intent-user")
    chat_session = ChatSession(user_id=user.id, title="Local intents")
    room = _create_room(db_session, "Local availability room")
    start_time = datetime.now(ROOMSYNC_TIMEZONE).replace(tzinfo=None) + timedelta(minutes=30)
    meeting = Meeting(
        title="Planning",
        organizer_id=user.id,
        start_time=start_time,
        end_time=start_time + timedelta(minutes=30),
        status="scheduled",
    )
    db_session.add_all([chat_session, meeting])
    db_session.commit()

    class UnexpectedGeminiCall:
        def __init__(self):
            raise AssertionError("Local intents must not call Gemini.")

        @staticmethod
        def _room_to_prompt(room):
            return {
                "id": room.id,
                "name": room.name,
                "capacity": room.capacity,
                "location": room.location,
            }

    monkeypatch.setattr(chatbot_service, "GeminiService", UnexpectedGeminiCall)

    async def collect(message):
        return [
            event
            async for event in chatbot_service.ChatbotService.stream_message(
                db=db_session,
                chat_session_id=chat_session.id,
                user_message=message,
                available_rooms=[],
            )
        ]

    schedule_events = asyncio.run(collect("Lịch họp hôm nay"))
    schedule_widget = next(
        event["widget"]
        for event in schedule_events
        if event["type"] == "room_widget"
    )
    assert schedule_widget["type"] == "MY_SCHEDULE_WIDGET"
    assert schedule_widget["data"][0]["title"] == "Planning"

    room_events = asyncio.run(collect("available_rooms"))
    room_widget = next(
        event["widget"]
        for event in room_events
        if event["type"] == "room_widget"
    )
    assert room_widget["type"] == "ROOM_LIST_WIDGET"
    assert room_widget["data"][0]["id"] == room.id

    capacity_events = asyncio.run(collect("Cần phòng họp cho 6 người"))
    capacity_widget = next(
        event["widget"]
        for event in capacity_events
        if event["type"] == "room_widget"
    )
    assert capacity_widget["type"] == "ROOM_LIST_WIDGET"
    assert capacity_widget["title"] == "Phòng trống cho 6 người"
    assert capacity_widget["data"][0]["id"] == room.id

    no_match_events = asyncio.run(collect("Tìm phòng cho 11 chỗ"))
    no_match_widget = next(
        event["widget"]
        for event in no_match_events
        if event["type"] == "room_widget"
    )
    assert no_match_widget["data"] == []
    assert "11 người" in no_match_events[0]["text"]

    cancel_events = asyncio.run(collect("Hủy lịch gần nhất"))
    cancel_widget = next(
        event["widget"]
        for event in cancel_events
        if event["type"] == "room_widget"
    )
    assert cancel_widget["type"] == "CANCEL_CONFIRM_WIDGET"
    assert cancel_widget["data"]["id"] == meeting.id
    assert db_session.get(Meeting, meeting.id).status == "scheduled"


def test_chatbot_stream_parses_json_inside_markdown_code_fence(
    db_session: Session,
    monkeypatch,
):
    user = _create_user(db_session, "chat-fenced-json-user")
    chat_session = ChatSession(user_id=user.id, title="Fenced JSON chat")
    db_session.add(chat_session)
    db_session.commit()
    response_payload = {
        "intent": "GENERAL_FAQ",
        "slots": {
            "title": None,
            "booking_date": None,
            "start_time": None,
            "duration_minutes": None,
            "capacity": None,
            "room_id": None,
            "room_name": None,
        },
        "missing_fields": [],
        "is_ready_for_preview": False,
        "bot_message": "Phản hồi đã được phân tích.",
    }
    fenced_response = (
        "Đây là phản hồi đã phân tích:\n"
        f"```json\n{json.dumps(response_payload, ensure_ascii=False)}\n```\n"
        "Hy vọng thông tin hữu ích."
    )

    class FakeGeminiService:
        def __init__(self):
            pass

        @staticmethod
        def _room_to_prompt(room):
            return {}

        @staticmethod
        def _validate_room_selection(response, available_rooms):
            return response

        async def stream_chat_response(self, **kwargs):
            yield {"type": "chunk", "text": fenced_response}

    monkeypatch.setattr(chatbot_service, "GeminiService", FakeGeminiService)

    async def collect_events():
        return [
            event
            async for event in chatbot_service.ChatbotService.stream_message(
                db=db_session,
                chat_session_id=chat_session.id,
                user_message="Hãy phân tích nội dung này",
                available_rooms=[],
            )
        ]

    events = asyncio.run(collect_events())

    complete_event = next(event for event in events if event["type"] == "complete")
    assert complete_event["response"]["bot_message"] == "Phản hồi đã được phân tích."


def test_extract_json_payload_returns_first_nested_json_object():
    payload = {
        "intent": "GENERAL_FAQ",
        "slots": {"title": None, "extra": {"enabled": True}},
        "bot_message": "JSON có dấu ngoặc } trong chuỗi.",
    }
    text = f"Phản hồi:\n```json\n{json.dumps(payload, ensure_ascii=False)}\n```\nKết thúc."

    assert json.loads(extract_json_payload(text)) == payload
