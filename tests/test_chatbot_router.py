from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.chat import ChatMessage, ChatSession
from app.models.meeting import Meeting
from app.routers import chatbot as chatbot_router
from app.services import chatbot_service
from app.services.gemini_service import (
    BookingSlots,
    GeminiChatResponse,
    GeminiService,
)
from tests.helpers import _auth_header, _create_room, _create_user, _make_token


def test_create_and_list_chat_sessions(client: TestClient, db_session: Session):
    user = _create_user(db_session, "chat-session-owner")
    other_user = _create_user(db_session, "chat-session-other")
    owned_session = ChatSession(user_id=user.id, title="My chat")
    other_session = ChatSession(user_id=other_user.id, title="Other chat")
    db_session.add_all([owned_session, other_session])
    db_session.commit()

    created = client.post(
        "/api/v1/chatbot/sessions",
        json={"title": "New chatbot session"},
        headers=_auth_header(_make_token(user)),
    )
    listed = client.get(
        "/api/v1/chatbot/sessions",
        headers=_auth_header(_make_token(user)),
    )

    assert created.status_code == 201
    assert created.json()["title"] == "New chatbot session"
    assert listed.status_code == 200
    assert {item["title"] for item in listed.json()} == {"My chat", "New chatbot session"}


def test_chat_session_messages_are_private(client: TestClient, db_session: Session):
    owner = _create_user(db_session, "chat-message-owner")
    other_user = _create_user(db_session, "chat-message-other")
    chat_session = ChatSession(user_id=owner.id, title="Private chat")
    db_session.add(chat_session)
    db_session.flush()
    db_session.add(
        ChatMessage(
            session_id=chat_session.id,
            sender="user",
            content="Private message",
        )
    )
    db_session.commit()

    response = client.get(
        f"/api/v1/chatbot/sessions/{chat_session.id}/messages",
        headers=_auth_header(_make_token(other_user)),
    )

    assert response.status_code == 404


def test_send_chat_message_uses_active_rooms_and_service(
    client: TestClient,
    db_session: Session,
    monkeypatch,
):
    user = _create_user(db_session, "chat-message-sender")
    room = _create_room(db_session, "Chatbot Available Room")
    chat_session = ChatSession(user_id=user.id, title="Booking chat")
    db_session.add(chat_session)
    db_session.commit()
    calls = []
    response_payload = GeminiChatResponse(
        intent="BOOK_ROOM",
        slots=BookingSlots(title="Planning"),
        missing_fields=["booking_date", "start_time", "duration_minutes", "capacity", "room_id"],
        bot_message="Bạn muốn họp vào ngày nào?",
    )
    monkeypatch.setattr(
        chatbot_router.ChatbotService,
        "process_message",
        lambda **kwargs: calls.append(kwargs) or response_payload,
    )

    response = client.post(
        f"/api/v1/chatbot/sessions/{chat_session.id}/message",
        json={"content": "Tôi muốn đặt phòng họp"},
        headers=_auth_header(_make_token(user)),
    )

    assert response.status_code == 200
    assert response.json()["intent"] == "BOOK_ROOM"
    assert response.json()["message"] == response.json()["bot_message"]
    assert response.json()["preview_card"] is None
    assert calls[0]["chat_session_id"] == chat_session.id
    assert calls[0]["user_message"] == "Tôi muốn đặt phòng họp"
    assert [item.id for item in calls[0]["available_rooms"]] == [room.id]


def test_roomsync_booking_message_persists_and_confirms_meeting(
    client: TestClient,
    db_session: Session,
    monkeypatch,
):
    user = _create_user(db_session, "roomsync-e2e-owner")
    room = _create_room(db_session, "RoomSync E2E Room")
    chat_session = ChatSession(user_id=user.id, title="RoomSync E2E")
    db_session.add(chat_session)
    db_session.commit()
    booking_dates = {}

    class FakeGeminiService(GeminiService):
        def __init__(self):
            pass

        def generate_chat_response(
            self,
            user_message,
            history,
            current_time,
            available_rooms,
        ):
            if user_message == "Đặt cho tôi 1 phòng họp vào 17h30 chiều nay":
                assert not history
                booking_dates["today"] = current_time.date()
                return GeminiChatResponse(
                    intent="BOOK_ROOM",
                    slots=BookingSlots(
                        booking_date=booking_dates["today"].isoformat(),
                        start_time="17:30",
                    ),
                    missing_fields=[
                        "title",
                        "duration_minutes",
                        "capacity",
                        "room_id",
                    ],
                    bot_message=(
                        "Bạn muốn họp về chủ đề gì, trong bao lâu và có bao nhiêu người?"
                    ),
                )

            assert history
            booking_dates["tomorrow"] = current_time.date() + timedelta(days=1)
            return GeminiChatResponse(
                intent="BOOK_ROOM",
                slots=BookingSlots(
                    title="Lập kế hoạch",
                    booking_date=booking_dates["tomorrow"].isoformat(),
                    start_time="17:30",
                    duration_minutes=60,
                    capacity=5,
                    room_id=available_rooms[0].id,
                    room_name=available_rooms[0].name,
                ),
                missing_fields=[],
                is_ready_for_preview=True,
                bot_message="Đã đủ thông tin. Vui lòng kiểm tra và xác nhận.",
            )

    monkeypatch.setattr(chatbot_service, "GeminiService", FakeGeminiService)
    headers = _auth_header(_make_token(user))
    send_url = f"/api/v1/chatbot/sessions/{chat_session.id}/message"

    initial_response = client.post(
        send_url,
        json={"content": "Đặt cho tôi 1 phòng họp vào 17h30 chiều nay"},
        headers=headers,
    )

    assert initial_response.status_code == 200
    initial_data = initial_response.json()
    assert initial_data["intent"] == "BOOK_ROOM"
    assert initial_data["slots"]["start_time"] == "17:30"
    assert initial_data["slots"]["booking_date"] == booking_dates["today"].isoformat()
    assert initial_data["preview_card"] is None
    assert initial_data["message"] == initial_data["bot_message"]

    follow_up_response = client.post(
        send_url,
        json={"content": "Ngày mai, cuộc họp lập kế hoạch 60 phút cho 5 người."},
        headers=headers,
    )

    assert follow_up_response.status_code == 200
    follow_up_data = follow_up_response.json()
    assert follow_up_data["intent"] == "BOOK_ROOM"
    assert (
        follow_up_data["slots"]["booking_date"]
        == booking_dates["tomorrow"].isoformat()
    )
    assert follow_up_data["preview_card"]["title"] == "Lập kế hoạch"
    assert follow_up_data["preview_card"]["room_id"] == room.id
    assert follow_up_data["preview_card"]["start_time"] == "17:30"
    assert follow_up_data["message"] == follow_up_data["bot_message"]

    saved_messages = (
        db_session.query(ChatMessage)
        .filter_by(session_id=chat_session.id)
        .order_by(ChatMessage.id)
        .all()
    )
    assert [message.sender for message in saved_messages] == [
        "user",
        "bot",
        "user",
        "bot",
    ]
    assert saved_messages[0].content == "Đặt cho tôi 1 phòng họp vào 17h30 chiều nay"
    assert saved_messages[1].intent == "BOOK_ROOM"
    assert saved_messages[3].slots["room_id"] == room.id

    booking_response = client.post(
        "/api/v1/chatbot/confirm-booking",
        json={"slots": follow_up_data["preview_card"], "participant_ids": []},
        headers=headers,
    )

    assert booking_response.status_code == 201
    meeting = db_session.query(Meeting).filter_by(title="Lập kế hoạch").one()
    assert meeting.organizer_id == user.id
    assert meeting.room_id == room.id
    assert meeting.start_time == datetime.combine(
        date.fromisoformat(follow_up_data["slots"]["booking_date"]),
        datetime.strptime("17:30", "%H:%M").time(),
    )


def test_send_chat_message_returns_service_unavailable_when_database_fails(
    client: TestClient,
    db_session: Session,
    monkeypatch,
):
    user = _create_user(db_session, "chat-database-error")
    chat_session = ChatSession(user_id=user.id, title="Database error chat")
    db_session.add(chat_session)
    db_session.commit()

    def raise_database_error(_db):
        raise SQLAlchemyError("database unavailable")

    monkeypatch.setattr(
        chatbot_router.MeetingService,
        "get_all_active_rooms",
        raise_database_error,
    )

    response = client.post(
        f"/api/v1/chatbot/sessions/{chat_session.id}/message",
        json={"content": "Xin chào"},
        headers=_auth_header(_make_token(user)),
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Trợ lý hiện không thể xử lý yêu cầu. Vui lòng thử lại sau."
    )


def test_confirm_chatbot_booking_creates_meeting(
    client: TestClient,
    db_session: Session,
):
    user = _create_user(db_session, "chat-booking-organizer")
    room = _create_room(db_session, "Chatbot Confirm Room")
    booking_day = date.today() + timedelta(days=3)

    response = client.post(
        "/api/v1/chatbot/confirm-booking",
        json={
            "slots": {
                "title": "Chatbot confirmed meeting",
                "booking_date": booking_day.isoformat(),
                "start_time": "14:30",
                "duration_minutes": 60,
                "capacity": 5,
                "room_id": room.id,
                "room_name": room.name,
            },
        },
        headers=_auth_header(_make_token(user)),
    )

    assert response.status_code == 201
    assert len(response.json()) == 1
    meeting = db_session.query(Meeting).filter_by(title="Chatbot confirmed meeting").one()
    assert meeting.organizer_id == user.id
    assert meeting.room_id == room.id
    assert meeting.start_time == datetime.combine(booking_day, datetime.strptime("14:30", "%H:%M").time())


def test_confirm_chatbot_booking_rejects_incomplete_slots(
    client: TestClient,
    db_session: Session,
):
    user = _create_user(db_session, "chat-incomplete-organizer")

    response = client.post(
        "/api/v1/chatbot/confirm-booking",
        json={"slots": {"title": "Incomplete booking"}},
        headers=_auth_header(_make_token(user)),
    )

    assert response.status_code == 422
    assert db_session.query(Meeting).count() == 0
