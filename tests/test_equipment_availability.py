from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.equipment import Equipment, MeetingEquipment
from tests.helpers import _create_meeting, _create_room, _create_user


def _create_equipment(db: Session, total_qty: int = 5) -> Equipment:
    equipment = Equipment(
        name="Conference microphone",
        code="MIC-01",
        category="Audio",
        total_qty=total_qty,
        is_active=True,
    )
    db.add(equipment)
    db.commit()
    db.refresh(equipment)
    return equipment


def _attach_equipment(db: Session, meeting_id: int, equipment_id: int, quantity: int):
    allocation = MeetingEquipment(
        meeting_id=meeting_id,
        equipment_id=equipment_id,
        quantity=quantity,
    )
    db.add(allocation)
    db.commit()
    return allocation


def test_availability_tracks_overlapping_bookings_and_inactive_status(
    client: TestClient, db_session: Session
):
    organizer = _create_user(db_session, "equipment-organizer")
    room = _create_room(db_session, "Equipment Room")
    equipment = _create_equipment(db_session)

    first_meeting = _create_meeting(
        db_session,
        room,
        organizer,
        datetime(2026, 10, 5, 2, 0),
        datetime(2026, 10, 5, 3, 0),
    )
    _attach_equipment(db_session, first_meeting.id, equipment.id, 2)

    params = {
        "start_time": "2026-10-05T09:30:00",
        "end_time": "2026-10-05T10:30:00",
    }
    response = client.get("/api/equipments/availability", params=params)
    assert response.status_code == 200
    item = response.json()[0]
    assert item["booked_qty"] == 2
    assert item["available_qty"] == 3
    assert item["status_label"] == "Có sẵn"

    second_meeting = _create_meeting(
        db_session,
        room,
        organizer,
        datetime(2026, 10, 5, 2, 45),
        datetime(2026, 10, 5, 3, 15),
    )
    _attach_equipment(db_session, second_meeting.id, equipment.id, 3)

    response = client.get("/api/equipments/availability", params=params)
    assert response.status_code == 200
    item = response.json()[0]
    assert item["booked_qty"] == 5
    assert item["available_qty"] == 0
    assert item["status_label"] == "Đã đặt hết"

    equipment.is_active = False
    db_session.commit()
    response = client.get("/api/equipments/availability", params=params)
    assert response.status_code == 200
    item = response.json()[0]
    assert item["status_label"] == "Ngừng hoạt động / Bảo trì"


def test_availability_ignores_canceled_meetings_and_supports_filters(
    client: TestClient, db_session: Session
):
    organizer = _create_user(db_session, "equipment-canceled-organizer")
    room = _create_room(db_session, "Equipment Canceled Room")
    equipment = _create_equipment(db_session)
    canceled_meeting = _create_meeting(
        db_session,
        room,
        organizer,
        datetime(2026, 10, 5, 2, 0),
        datetime(2026, 10, 5, 3, 0),
        status="CANCELLED",
    )
    _attach_equipment(db_session, canceled_meeting.id, equipment.id, 5)

    response = client.get(
        "/api/equipments/availability",
        params={
            "start_time": "2026-10-05T09:30:00",
            "end_time": "2026-10-05T10:30:00",
            "category": "Audio",
            "search": "MIC-01",
        },
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["booked_qty"] == 0


def test_availability_defaults_to_current_time(client: TestClient, db_session: Session):
    _create_equipment(db_session)

    response = client.get("/api/equipments/availability")

    assert response.status_code == 200
    assert response.json()[0]["available_qty"] == 5