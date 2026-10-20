import json
from datetime import date, datetime, timedelta

from fastapi.testclient import TestClient
from sse_starlette.sse import AppStatus
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.chat import ChatMessage, ChatSession
from app.models.department import Department
from app.models.equipment import Equipment
from app.models.meeting import Meeting
from app.models.project_group import ProjectGroup
from app.routers import chatbot as chatbot_router
from app.services import chatbot_service
from app.services.gemini_service import (
    BookingSlots,
    GeminiChatResponse,
    GeminiService,
)
from tests.helpers import (
    _auth_header,
    _create_meeting,
    _create_room,
    _create_user,
    _make_token,
)


def _stream_payload(response, event_type):
    normalized = response.text.replace("\r\n", "\n")
    for block in normalized.split("\n\n"):
        lines = block.splitlines()
        if f"event: {event_type}" in lines:
            data = "\n".join(
                line[6:] for line in lines if line.startswith("data: ")
            )
            return json.loads(data)
    raise AssertionError(f"Missing {event_type!r} SSE event.")


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
    async def fake_stream_message(**kwargs):
        calls.append(kwargs)
        yield {
            "type": "complete",
            "response": response_payload.model_dump(mode="json"),
        }

    monkeypatch.setattr(
        chatbot_router.ChatbotService, "stream_message", fake_stream_message
    )

    response = client.post(
        f"/api/v1/chatbot/sessions/{chat_session.id}/message",
        json={"content": "Tôi muốn đặt phòng họp"},
        headers=_auth_header(_make_token(user)),
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    response_data = _stream_payload(response, "complete")["response"]
    assert response_data["intent"] == "BOOK_ROOM"
    assert response_data["message"] == response_data["bot_message"]
    assert response_data["preview_card"] is None
    assert calls[0]["chat_session_id"] == chat_session.id
    assert calls[0]["user_message"] == "Tôi muốn đặt phòng họp"
    assert [item.id for item in calls[0]["available_rooms"]] == [room.id]


def test_roomsync_booking_message_persists_and_confirms_meeting(
    client: TestClient,
    db_session: Session,
    monkeypatch,
):
    AppStatus.should_exit_event = None
    AppStatus.should_exit = False
    user = _create_user(db_session, "roomsync-e2e-owner")
    room = _create_room(db_session, "RoomSync E2E Room")
    chat_session = ChatSession(user_id=user.id, title="RoomSync E2E")
    db_session.add(chat_session)
    db_session.commit()
    booking_dates = {}

    class FakeGeminiService(GeminiService):
        def __init__(self):
            pass

        async def stream_chat_response(
            self,
            messages,
            history,
            tool_executor=None,
            room_tool_executor=None,
        ):
            user_message = messages["current_user_message"]
            current_time = datetime.fromisoformat(messages["current_time"])
            if user_message == "Đặt cho tôi 1 phòng họp vào 17h30 chiều nay":
                assert not history
                booking_dates["today"] = current_time.date()
                response = GeminiChatResponse(
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
            else:
                assert history
                booking_dates["tomorrow"] = current_time.date() + timedelta(days=1)
                response = GeminiChatResponse(
                    intent="BOOK_ROOM",
                    slots=BookingSlots(
                        title="Lập kế hoạch",
                        booking_date=booking_dates["tomorrow"].isoformat(),
                        start_time="17:30",
                        duration_minutes=60,
                        capacity=5,
                        room_id=room.id,
                        room_name=room.name,
                    ),
                    missing_fields=[],
                    is_ready_for_preview=True,
                    bot_message="Đã đủ thông tin. Vui lòng kiểm tra và xác nhận.",
                )
            yield {
                "type": "chunk",
                "text": json.dumps(
                    response.model_dump(mode="json"),
                    ensure_ascii=False,
                ),
            }

    monkeypatch.setattr(chatbot_service, "GeminiService", FakeGeminiService)
    headers = _auth_header(_make_token(user))
    send_url = f"/api/v1/chatbot/sessions/{chat_session.id}/message"

    initial_response = client.post(
        send_url,
        json={"content": "Đặt cho tôi 1 phòng họp vào 17h30 chiều nay"},
        headers=headers,
    )

    assert initial_response.status_code == 200
    initial_data = _stream_payload(initial_response, "complete")["response"]
    assert initial_data["intent"] == "BOOK_ROOM"
    assert initial_data["slots"]["start_time"] == "17:30"
    assert initial_data["slots"]["booking_date"] == booking_dates["today"].isoformat()
    assert initial_data["preview_card"] is None
    assert initial_data["message"] == initial_data["bot_message"]

    AppStatus.should_exit_event = None
    AppStatus.should_exit = False
    follow_up_response = client.post(
        send_url,
        json={"content": "Ngày mai, cuộc họp lập kế hoạch 60 phút cho 5 người."},
        headers=headers,
    )

    assert follow_up_response.status_code == 200
    follow_up_data = _stream_payload(follow_up_response, "complete")["response"]
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


def test_assistant_meeting_form_options_require_authentication(client: TestClient):
    response = client.get("/api/v1/chatbot/meeting-form-options")

    assert response.status_code == 401


def test_assistant_meeting_form_options_expose_group_and_equipment_choices(
    client: TestClient,
    db_session: Session,
):
    user = _create_user(db_session, "assistant-form-options-user")
    department = Department(name="Form Department", code="FORM-DEPT")
    project = ProjectGroup(name="Form Project", code="FORM-PROJECT")
    television = Equipment(name="TV screen", code="TV-SCREEN", total_qty=2, is_active=True)
    db_session.add_all([department, project, television])
    db_session.commit()

    response = client.get(
        "/api/v1/chatbot/meeting-form-options",
        headers=_auth_header(_make_token(user)),
    )

    assert response.status_code == 200
    data = response.json()
    assert {"id": department.id, "name": department.name, "code": department.code} in data["departments"]
    assert {"id": project.id, "name": project.name, "code": project.code} in data["projects"]
    assert next(item for item in data["equipment"] if item["key"] == "tv") == {
        "key": "tv",
        "label": "TV",
        "id": television.id,
        "available": True,
    }


def test_assistant_meeting_creates_department_booking_and_saves_chat_history(
    client: TestClient,
    db_session: Session,
    monkeypatch,
):
    organizer = _create_user(db_session, "assistant-department-organizer")
    invitee = _create_user(db_session, "assistant-department-invitee")
    department = Department(name="Assistant Operations", code="ASST-OPS")
    db_session.add(department)
    db_session.flush()
    organizer.department_id = department.id
    invitee.department_id = department.id
    room = _create_room(db_session, "Assistant Department Room")
    room.capacity = 2
    chat_session = ChatSession(user_id=organizer.id, title="Group meeting")
    db_session.add(chat_session)
    db_session.commit()
    monkeypatch.setattr(
        chatbot_router,
        "schedule_meeting_invitations",
        lambda **_kwargs: None,
    )
    booking_day = date.today() + timedelta(days=2)

    response = client.post(
        "/api/v1/chatbot/meetings",
        json={
            "session_id": chat_session.id,
            "source_prompt": "Tạo họp phòng ban lúc 10h có tivi",
            "group_type": "department",
            "group_id": department.id,
            "title": "Operations planning",
            "start_time": datetime.combine(
                booking_day, datetime.strptime("10:00", "%H:%M").time()
            ).isoformat(),
            "end_time": datetime.combine(
                booking_day, datetime.strptime("11:00", "%H:%M").time()
            ).isoformat(),
        },
        headers=_auth_header(_make_token(organizer)),
    )

    assert response.status_code == 201, response.text
    assert response.json()[0]["room_name"] == room.name
    meeting = db_session.query(Meeting).filter_by(title="Operations planning").one()
    assert meeting.room_id == room.id
    assert {participant.user_id for participant in meeting.participants} == {invitee.id}
    saved_messages = (
        db_session.query(ChatMessage)
        .filter_by(session_id=chat_session.id)
        .order_by(ChatMessage.id)
        .all()
    )
    assert [message.sender for message in saved_messages] == ["user", "bot"]
    assert saved_messages[0].content == "Tạo họp phòng ban lúc 10h có tivi"
    assert saved_messages[1].slots["capacity"] == 2


def test_assistant_online_meeting_generates_a_join_link(
    client: TestClient,
    db_session: Session,
    monkeypatch,
):
    organizer = _create_user(db_session, "assistant-online-organizer")
    project = ProjectGroup(name="Online Project", code="ONLINE-PROJECT")
    db_session.add(project)
    db_session.commit()
    project.users.append(organizer)
    db_session.commit()
    monkeypatch.setattr(
        chatbot_router,
        "schedule_meeting_invitations",
        lambda **_kwargs: None,
    )
    booking_day = date.today() + timedelta(days=2)

    response = client.post(
        "/api/v1/chatbot/meetings",
        json={
            "group_type": "project",
            "group_id": project.id,
            "title": "Online project sync",
            "start_time": datetime.combine(
                booking_day, datetime.strptime("10:00", "%H:%M").time()
            ).isoformat(),
            "end_time": datetime.combine(
                booking_day, datetime.strptime("11:00", "%H:%M").time()
            ).isoformat(),
            "online_meeting": True,
        },
        headers=_auth_header(_make_token(organizer)),
    )

    assert response.status_code == 201, response.text
    meeting = db_session.query(Meeting).filter_by(title="Online project sync").one()
    assert meeting.meeting_type == "online"
    assert meeting.room_id is None
    assert meeting.meeting_link.startswith("https://meet.jit.si/RoomSync-")


def test_assistant_meeting_uses_an_alternative_room_when_requested_room_conflicts(
    client: TestClient,
    db_session: Session,
    monkeypatch,
):
    organizer = _create_user(db_session, "assistant-conflict-organizer")
    department = Department(name="Conflict Department", code="CONFLICT-DEPT")
    db_session.add(department)
    db_session.flush()
    organizer.department_id = department.id
    blocked_room = _create_room(db_session, "Assistant Blocked Room")
    alternative_room = _create_room(db_session, "Assistant Alternative Room")
    booking_day = date.today() + timedelta(days=3)
    start_time = datetime.combine(
        booking_day, datetime.strptime("10:00", "%H:%M").time()
    )
    conflict_organizer = _create_user(db_session, "assistant-conflict-owner")
    _create_meeting(
        db_session,
        blocked_room,
        conflict_organizer,
        start_time,
        start_time + timedelta(hours=1),
    )
    monkeypatch.setattr(
        chatbot_router,
        "schedule_meeting_invitations",
        lambda **_kwargs: None,
    )

    response = client.post(
        "/api/v1/chatbot/meetings",
        json={
            "group_type": "department",
            "group_id": department.id,
            "title": "Alternative room meeting",
            "start_time": start_time.isoformat(),
            "end_time": (start_time + timedelta(hours=1)).isoformat(),
        },
        headers=_auth_header(_make_token(organizer)),
    )

    assert response.status_code == 201, response.text
    meeting = db_session.query(Meeting).filter_by(title="Alternative room meeting").one()
    assert meeting.room_id == alternative_room.id


def test_assistant_meeting_returns_nearest_available_time_when_room_is_busy(
    client: TestClient,
    db_session: Session,
):
    organizer = _create_user(db_session, "assistant-time-suggestion-organizer")
    conflict_owner = _create_user(db_session, "assistant-time-suggestion-owner")
    department = Department(name="Time Suggestion Department", code="TIME-SUGGESTION")
    db_session.add(department)
    db_session.flush()
    organizer.department_id = department.id
    room = _create_room(db_session, "Assistant Time Suggestion Room")
    booking_day = date.today() + timedelta(days=3)
    start_time = datetime.combine(
        booking_day, datetime.strptime("10:00", "%H:%M").time()
    )
    _create_meeting(
        db_session,
        room,
        conflict_owner,
        start_time,
        start_time + timedelta(hours=1),
    )

    response = client.post(
        "/api/v1/chatbot/meetings",
        json={
            "group_type": "department",
            "group_id": department.id,
            "title": "Suggested time meeting",
            "start_time": start_time.isoformat(),
            "end_time": (start_time + timedelta(hours=1)).isoformat(),
        },
        headers=_auth_header(_make_token(organizer)),
    )

    assert response.status_code == 409
    suggestions = response.json()["detail"]["suggestions"]
    assert suggestions
    assert suggestions[0]["room_id"] == room.id
    assert suggestions[0]["start_time"] == (
        start_time + timedelta(hours=1)
    ).isoformat()
