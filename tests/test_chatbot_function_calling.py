import asyncio
import json
from types import SimpleNamespace

from google.genai import types
from sqlalchemy.orm import Session

from app.models.chat import ChatSession
from app.models.equipment import Equipment, RoomEquipment
from app.models.project_group import ProjectGroup
from app.services import chatbot_service
from app.services.chatbot_service import ChatbotService
from app.services.gemini_service import GeminiService
from tests.helpers import _create_room, _create_user


def test_streaming_gemini_executes_search_users_tool():
    final_response = {
        "intent": "BOOK_ROOM",
        "slots": {
            "title": "Mobile planning",
            "booking_date": "2026-11-01",
            "start_time": "10:00",
            "duration_minutes": 60,
            "capacity": 2,
            "room_id": 7,
            "room_name": "Room 7",
        },
        "missing_fields": [],
        "is_ready_for_preview": True,
        "bot_message": "Đã tìm thấy team Mobile và chuẩn bị bản xem trước.",
    }
    function_call = types.FunctionCall(
        id="search-mobile",
        name="search_users",
        args={"group_code": "MOBILE", "keyword": "Mobile"},
    )
    call_chunk = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                content=types.Content(
                    role="model",
                    parts=[types.Part(function_call=function_call)],
                )
            )
        ]
    )
    final_chunk = SimpleNamespace(
        text=json.dumps(final_response, ensure_ascii=False)
    )

    class FakeModels:
        def __init__(self):
            self.requests = []

        def generate_content_stream(self, **kwargs):
            self.requests.append(kwargs)
            if len(self.requests) == 1:
                return iter([call_chunk])
            return iter([final_chunk])

    class FakeClient:
        def __init__(self):
            self.models = FakeModels()

    client = FakeClient()
    service = GeminiService(client=client)
    executed_calls = []

    def execute_local_search(arguments):
        executed_calls.append(arguments)
        return [
            {
                "id": 25,
                "full_name": "Nguyen Mobile",
                "email": "mobile@example.test",
                "position": "Engineer",
                "department": {"name": "Engineering", "code": "ENG"},
            }
        ]

    async def collect_events():
        return [
            event
            async for event in service.stream_chat_response(
                messages={"current_user_message": "Mời team Mobile"},
                history=[],
                tool_executor=execute_local_search,
            )
        ]

    events = asyncio.run(collect_events())

    declared_tools = client.models.requests[0]["config"].tools
    assert [
        declaration.name
        for tool in declared_tools
        for declaration in tool.function_declarations
    ] == ["search_users"]
    assert executed_calls == [
        {"group_code": "MOBILE", "keyword": "Mobile"}
    ]
    assert any(
        event["type"] == "tool_result"
        and event["users"][0]["id"] == 25
        for event in events
    )
    assert any(event["type"] == "chunk" for event in events)
    continuation = client.models.requests[1]["contents"]
    assert continuation[-1].parts[0].function_response.response == {
        "users": [
            {
                "id": 25,
                "full_name": "Nguyen Mobile",
                "email": "mobile@example.test",
                "position": "Engineer",
                "department": {"name": "Engineering", "code": "ENG"},
            }
        ]
    }


def test_streaming_gemini_executes_available_rooms_tool():
    function_call = types.FunctionCall(
        id="search-rooms",
        name="search_available_rooms",
        args={
            "room_name": "Boardroom",
            "start_time": "2026-11-01T10:00:00+07:00",
            "end_time": "2026-11-01T11:00:00+07:00",
            "capacity": 4,
        },
    )
    call_chunk = SimpleNamespace(
        candidates=[
            SimpleNamespace(
                content=types.Content(
                    role="model",
                    parts=[types.Part(function_call=function_call)],
                )
            )
        ]
    )
    final_response = {
        "intent": "BOOK_ROOM",
        "slots": {
            "title": "Planning",
            "booking_date": "2026-11-01",
            "start_time": "10:00",
            "duration_minutes": 60,
            "capacity": 4,
            "room_id": 9,
            "room_name": "Boardroom",
        },
        "missing_fields": [],
        "is_ready_for_preview": True,
        "bot_message": "Đã tìm thấy phòng phù hợp.",
    }

    class FakeModels:
        def __init__(self):
            self.requests = []

        def generate_content_stream(self, **kwargs):
            self.requests.append(kwargs)
            if len(self.requests) == 1:
                return iter([call_chunk])
            return iter([SimpleNamespace(text=json.dumps(final_response))])

    class FakeClient:
        def __init__(self):
            self.models = FakeModels()

    client = FakeClient()
    service = GeminiService(client=client)
    executed_arguments = []

    def search_rooms(arguments):
        executed_arguments.append(arguments)
        return [{"id": 9, "name": "Boardroom", "capacity": 8}]

    async def collect_events():
        return [
            event
            async for event in service.stream_chat_response(
                messages={"current_user_message": "Tìm phòng họp"},
                history=[],
                room_tool_executor=search_rooms,
            )
        ]

    events = asyncio.run(collect_events())
    declared_tools = client.models.requests[0]["config"].tools
    declaration = next(
        declaration
        for tool in declared_tools
        for declaration in tool.function_declarations
    )

    assert declaration.name == "search_available_rooms"
    assert set(declaration.parameters.properties) == {
        "room_name",
        "start_time",
        "end_time",
        "capacity",
    }
    assert executed_arguments == [function_call.args]
    room_result = next(
        event for event in events
        if event["type"] == "tool_result"
        and event["name"] == "search_available_rooms"
    )
    assert room_result["rooms"] == [
        {"id": 9, "name": "Boardroom", "capacity": 8, "location": None}
    ]


def test_chatbot_stream_emits_over_capacity_interactive_preview(
    db_session: Session,
    monkeypatch,
):
    user = _create_user(db_session, "function-calling-organizer")
    mobile_group = ProjectGroup(name="Mobile Team", code="MOBILE")
    mobile_users = [
        _create_user(db_session, "mobile-invitee-one"),
        _create_user(db_session, "mobile-invitee-two"),
    ]
    for index, invitee in enumerate(mobile_users, start=1):
        invitee.full_name = f"Mobile Engineer {index}"
        invitee.email = f"mobile{index}@example.test"
        invitee.position = "Engineer"
        invitee.project_groups.append(mobile_group)
    room = _create_room(db_session, "Small Mobile Room")
    room.capacity = 1
    chat_session = ChatSession(user_id=user.id, title="Mobile planning")
    db_session.add(chat_session)
    db_session.commit()

    response = {
        "intent": "BOOK_ROOM",
        "slots": {
            "title": "Mobile planning",
            "booking_date": "2099-11-01",
            "start_time": "10:00",
            "duration_minutes": 60,
            "capacity": 1,
            "room_id": room.id,
            "room_name": room.name,
        },
        "missing_fields": [],
        "is_ready_for_preview": True,
        "bot_message": "Đã chuẩn bị bản xem trước cuộc họp.",
    }

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
            assert messages["current_user_message"] == "Đặt phòng và mời team Mobile"
            assert history == []
            assert callable(tool_executor)
            assert callable(room_tool_executor)
            matched_users = tool_executor({"keyword": "Mobile"})
            matched_rooms = room_tool_executor(
                {
                    "start_time": "2099-11-01T10:00:00",
                    "end_time": "2099-11-01T11:00:00",
                    "capacity": 1,
                }
            )
            assert room.id in {item.id for item in matched_rooms}
            yield {
                "type": "tool_result",
                "name": "search_users",
                "users": matched_users,
            }
            yield {
                "type": "tool_result",
                "name": "search_available_rooms",
                "rooms": [
                    GeminiService._room_to_prompt(item)
                    for item in matched_rooms
                ],
            }
            yield {
                "type": "chunk",
                "text": json.dumps(response, ensure_ascii=False),
            }

    monkeypatch.setattr(
        chatbot_service,
        "GeminiService",
        FakeGeminiService,
    )

    async def collect_events():
        return [
            event
            async for event in ChatbotService.stream_message(
                db=db_session,
                chat_session_id=chat_session.id,
                user_message="Đặt phòng và mời team Mobile",
                available_rooms=[room],
            )
        ]

    events = asyncio.run(collect_events())
    preview = next(event for event in events if event["type"] == "preview_card")
    complete = next(event for event in events if event["type"] == "complete")

    assert preview["meeting"]["room_capacity"] == 1
    assert preview["widget"]["type"] == "ROOM_CARD_WIDGET"
    assert preview["widget"]["actions"][0]["label"] == "Đặt ngay"
    assert len(preview["participants"]) == 2
    assert {person["id"] for person in preview["participants"]} == {
        invitee.id for invitee in mobile_users
    }
    assert preview["is_over_capacity"] is True
    assert complete["response"]["ui_widget"]["type"] == "ROOM_CARD_WIDGET"
    room_widget = next(event for event in events if event["type"] == "room_widget")
    assert room_widget["widget"]["type"] == "ROOM_CARD_WIDGET"
    assert room_widget["widget"]["data"]["name"] == room.name
    assert room_widget["widget"]["actions"][0]["label"] == "Đặt ngay"


def test_chatbot_action_draft_emits_room_confirmation_widget(
    db_session: Session,
    monkeypatch,
):
    user = _create_user(db_session, "chat-draft-user")
    room = _create_room(db_session, "Draft Confirmation Room")
    room.capacity = 4
    other_room = _create_room(db_session, "Draft Room Without Equipment")
    equipment = Equipment(
        name="Projector",
        total_qty=3,
        is_active=True,
    )
    db_session.add(equipment)
    db_session.flush()
    db_session.add(
        RoomEquipment(
            room_id=room.id,
            equipment_id=equipment.id,
            quantity=1,
        )
    )
    chat_session = ChatSession(user_id=user.id, title="Draft confirmation")
    db_session.add(chat_session)
    db_session.commit()
    response = {
        "action": "CREATE_MEETING_DRAFT",
        "parameters": {
            "title": "Planning",
            "date": "2099-11-01",
            "start_time": "10:00",
            "end_time": "11:00",
            "target_group": None,
            "equipments_required": ["Projector"],
            "capacity": 2,
        },
        "intent": "BOOK_ROOM",
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
        "bot_message": "Preparing draft",
    }

    class FakeGeminiService(GeminiService):
        def __init__(self):
            pass

        async def stream_chat_response(self, **kwargs):
            yield {
                "type": "chunk",
                "text": json.dumps(response, ensure_ascii=False),
            }

    monkeypatch.setattr(chatbot_service, "GeminiService", FakeGeminiService)

    async def collect_events():
        return [
            event
            async for event in ChatbotService.stream_message(
                db=db_session,
                chat_session_id=chat_session.id,
                user_message="Đặt cuộc họp nhóm",
                available_rooms=[room, other_room],
            )
        ]

    events = asyncio.run(collect_events())
    widget = next(event["widget"] for event in events if event["type"] == "room_widget")

    assert widget["type"] == "ROOM_CONFIRMATION_WIDGET"
    assert widget["data"]["id"] == room.id
    assert widget["meeting"]["title"] == "Planning"
    assert widget["meeting"]["duration_minutes"] == 60
    assert widget["actions"][0]["type"] == "confirm_booking"
    assert widget["equipment_options"][0]["name"] == "Projector"
