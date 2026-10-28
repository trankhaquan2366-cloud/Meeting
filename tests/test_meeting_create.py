from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.equipment import Equipment, MeetingEquipment
from app.models.meeting import Meeting
from app.routers import meetings as meetings_router
from tests.helpers import _auth_header, _create_room, _create_user, _make_token


def _future_window():
    start = datetime.utcnow() + timedelta(days=2)
    return start, start + timedelta(hours=1)


def test_create_offline_meeting_with_room(client: TestClient, db_session: Session):
    organizer = _create_user(db_session, "create-offline-organizer")
    room = _create_room(db_session, "Create Offline Room")
    start, end = _future_window()

    response = client.post(
        "/api/meetings/book",
        json={
            "title": "Offline meeting",
            "meeting_type": "offline",
            "room_id": room.id,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        },
        headers=_auth_header(_make_token(organizer)),
    )

    assert response.status_code == 201
    meeting = response.json()["created"][0]
    assert meeting["meeting_type"] == "offline"
    assert meeting["room_id"] == room.id


def test_create_offline_meeting_without_room_returns_400(
    client: TestClient, db_session: Session
):
    organizer = _create_user(db_session, "create-offline-no-room")
    start, end = _future_window()

    response = client.post(
        "/api/meetings/book",
        json={
            "title": "Offline meeting without room",
            "meeting_type": "offline",
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        },
        headers=_auth_header(_make_token(organizer)),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Offline meetings require a room_id"


def test_create_online_meeting_with_link(client: TestClient, db_session: Session):
    organizer = _create_user(db_session, "create-online-organizer")
    start, end = _future_window()

    response = client.post(
        "/api/meetings/book",
        json={
            "title": "Online meeting",
            "meeting_type": "online",
            "meeting_link": "https://meet.test/room",
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        },
        headers=_auth_header(_make_token(organizer)),
    )

    assert response.status_code == 201
    meeting = response.json()["created"][0]
    assert meeting["meeting_type"] == "online"
    assert meeting["meeting_link"] == "https://meet.test/room"
    assert meeting["room_id"] is None


def test_create_online_meeting_without_link_returns_400(
    client: TestClient, db_session: Session
):
    """Online meetings bắt buộc phải có meeting_link.

    Frontend (create-meeting.js) tự sinh link Jitsi trước khi gửi, backend
    không tự điền để tránh tạo phòng họp "mồ côi" không ai mở.
    """
    organizer = _create_user(db_session, "create-online-no-link")
    start, end = _future_window()

    response = client.post(
        "/api/meetings/book",
        json={
            "title": "Online meeting without link",
            "meeting_type": "online",
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        },
        headers=_auth_header(_make_token(organizer)),
    )

    assert response.status_code == 400
    assert "meeting_link" in response.json()["detail"]


def test_create_meeting_with_available_equipment_and_availability_id(
    client: TestClient, db_session: Session
):
    organizer = _create_user(db_session, "create-equipment-organizer")
    room = _create_room(db_session, "Create Equipment Room")
    equipment = Equipment(
        name="Create Equipment Projector",
        code="CREATE-EQ-01",
        total_qty=2,
        is_active=True,
    )
    db_session.add(equipment)
    db_session.commit()
    start, end = _future_window()

    response = client.post(
        "/api/meetings/book",
        json={
            "title": "Meeting with equipment",
            "meeting_type": "offline",
            "room_id": room.id,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "equipments": [{"equipment_id": equipment.id, "quantity": 2}],
        },
        headers=_auth_header(_make_token(organizer)),
    )

    assert response.status_code == 201
    availability = client.get(
        "/api/equipments/availability",
        params={
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "search": equipment.name,
        },
    )
    assert availability.status_code == 200
    assert availability.json()[0]["id"] == equipment.id
    assert availability.json()[0]["available_qty"] == 0


@pytest.mark.parametrize(
    ("stock", "requested"),
    [(1, 2), (0, 1)],
)
def test_create_meeting_rejects_equipment_quantity_over_available_stock(
    client: TestClient, db_session: Session, stock: int, requested: int
):
    organizer = _create_user(db_session, "create-overstock-organizer")
    room = _create_room(db_session, "Create Overstock Room")
    equipment = Equipment(
        name="Create Equipment One",
        code="CREATE-EQ-02",
        total_qty=stock,
        is_active=True,
    )
    db_session.add(equipment)
    db_session.commit()
    start, end = _future_window()

    response = client.post(
        "/api/meetings/book",
        json={
            "title": "Meeting exceeding equipment stock",
            "meeting_type": "offline",
            "room_id": room.id,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "equipments": [{"equipment_id": equipment.id, "quantity": requested}],
        },
        headers=_auth_header(_make_token(organizer)),
    )

    assert response.status_code == 409
    warning = response.json()["detail"]["warnings"][0]
    assert warning["type"] == "EquipmentShortageWarning"
    assert warning["available_qty"] == stock
    assert db_session.query(Meeting).count() == 0


def test_validation_warnings_require_force_book_confirmation(
    client: TestClient, db_session: Session
):
    organizer = _create_user(db_session, "create-force-organizer")
    reservation_owner = _create_user(db_session, "create-force-reservation-owner")
    room = _create_room(db_session, "Create force warning room")
    room.capacity = 1
    storage_room = _create_room(db_session, "Create force storage room")
    equipment = Equipment(
        name="Create force projector",
        code="CREATE-EQ-FORCE",
        total_qty=1,
        is_active=True,
    )
    db_session.add(equipment)
    db_session.flush()
    start, end = _future_window()
    reservation = Meeting(
        title="Reserved projector",
        room_id=storage_room.id,
        organizer_id=reservation_owner.id,
        start_time=start,
        end_time=end,
        status="scheduled",
    )
    db_session.add(reservation)
    db_session.flush()
    db_session.add(
        MeetingEquipment(
            meeting_id=reservation.id,
            equipment_id=equipment.id,
            quantity=1,
        )
    )
    db_session.commit()

    payload = {
        "title": "Meeting with warnings",
        "meeting_type": "offline",
        "room_id": room.id,
        "start_time": start.isoformat(),
        "end_time": end.isoformat(),
        "external_guest_count": 2,
        "equipments": [{"equipment_id": equipment.id, "quantity": 1}],
    }
    headers = _auth_header(_make_token(organizer))
    validation = client.post(
        "/api/meetings/validate",
        json=payload,
        headers=headers,
    )
    assert validation.status_code == 200
    warnings = validation.json()["warnings"]
    assert {warning["type"] for warning in warnings} == {
        "OverCapacityWarning",
        "EquipmentShortageWarning",
    }

    rejected = client.post("/api/meetings/book", json=payload, headers=headers)
    assert rejected.status_code == 409
    assert rejected.json()["detail"]["warnings"] == warnings
    assert db_session.query(Meeting).filter(Meeting.title == payload["title"]).count() == 0

    accepted = client.post(
        "/api/meetings/book",
        json={**payload, "force_book": True},
        headers=headers,
    )
    assert accepted.status_code == 201


def test_create_meeting_rejects_negative_or_fractional_equipment_quantity(
    client: TestClient, db_session: Session
):
    organizer = _create_user(db_session, "create-invalid-qty-organizer")
    room = _create_room(db_session, "Create Invalid Qty Room")
    equipment = Equipment(
        name="Create Equipment Quantity",
        code="CREATE-EQ-03",
        total_qty=3,
        is_active=True,
    )
    db_session.add(equipment)
    db_session.commit()
    start, end = _future_window()

    for quantity in (-1, 1.5):
        response = client.post(
            "/api/meetings/book",
            json={
                "title": "Meeting with invalid equipment quantity",
                "meeting_type": "offline",
                "room_id": room.id,
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
                "equipments": [{"equipment_id": equipment.id, "quantity": quantity}],
            },
            headers=_auth_header(_make_token(organizer)),
        )

        assert response.status_code == 422
    assert db_session.query(Meeting).count() == 0


def test_create_meeting_schedules_google_sync_for_connected_organizer(
    client: TestClient, db_session: Session, monkeypatch
):
    organizer = _create_user(db_session, "create-connected-organizer")
    organizer.google_refresh_token = "encrypted-refresh-token"
    db_session.commit()
    room = _create_room(db_session, "Connected Organizer Room")
    start, end = _future_window()
    synced_user_ids = []
    monkeypatch.setattr(
        meetings_router,
        "sync_user_meetings_to_google",
        synced_user_ids.append,
    )

    response = client.post(
        "/api/meetings/book",
        json={
            "title": "Automatically synced meeting",
            "meeting_type": "offline",
            "room_id": room.id,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        },
        headers=_auth_header(_make_token(organizer)),
    )

    assert response.status_code == 201
    assert synced_user_ids == [organizer.id]


def test_create_meeting_schedules_invitation_email_for_invitee(
    client: TestClient, db_session: Session, monkeypatch
):
    organizer = _create_user(db_session, "create-email-organizer")
    invitee = _create_user(db_session, "create-email-invitee")
    room = _create_room(db_session, "Invitation Email Room")
    start, end = _future_window()
    sent_emails = []
    monkeypatch.setattr(
        meetings_router,
        "send_meeting_invitation_email",
        lambda **kwargs: sent_emails.append(kwargs),
    )
    monkeypatch.setattr(
        meetings_router,
        "request_calendar_access_for_invitees",
        lambda **kwargs: None,
    )

    response = client.post(
        "/api/meetings/book",
        json={
            "title": "Invitation email test",
            "meeting_type": "offline",
            "room_id": room.id,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "participant_ids": [organizer.id, invitee.id],
        },
        headers=_auth_header(_make_token(organizer)),
    )

    assert response.status_code == 201
    assert sent_emails == [{
        "to_email": invitee.email,
        "user_name": invitee.full_name,
        "meeting_title": "Invitation email test",
        "start_time_str": start.strftime("%H:%M %d/%m/%Y"),
        "location_str": f"Phòng {room.name}",
        "meeting_link": None,
        "meeting_id": response.json()["created"][0]["id"],
        "start_time": start,
        "end_time": end,
        "organizer_email": organizer.email,
        "organizer_name": organizer.full_name,
    }]