from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.equipment import Equipment, MeetingEquipment
from app.models.meeting import Meeting
from tests.helpers import _create_room, _create_user


def test_equipment_availability_api_sums_overlapping_meeting_allocations(
    client: TestClient,
    db_session: Session,
):
    organizer = _create_user(db_session, "equipment-availability-organizer")
    room = _create_room(db_session, "Equipment availability room")
    equipment = Equipment(
        name="Real-time availability projector",
        code="REALTIME-EQ-01",
        total_qty=8,
        is_active=True,
    )
    db_session.add(equipment)
    db_session.flush()

    requested_start = datetime.utcnow() + timedelta(days=8)
    requested_end = requested_start + timedelta(hours=2)
    meetings = [
        Meeting(
            title="Overlapping allocation one",
            room_id=room.id,
            organizer_id=organizer.id,
            start_time=requested_start - timedelta(minutes=30),
            end_time=requested_start + timedelta(minutes=30),
            status="scheduled",
        ),
        Meeting(
            title="Overlapping allocation two",
            room_id=room.id,
            organizer_id=organizer.id,
            start_time=requested_start + timedelta(minutes=45),
            end_time=requested_end + timedelta(minutes=15),
            status="scheduled",
        ),
    ]
    db_session.add_all(meetings)
    db_session.flush()
    db_session.add_all([
        MeetingEquipment(
            meeting_id=meetings[0].id,
            equipment_id=equipment.id,
            quantity=2,
        ),
        MeetingEquipment(
            meeting_id=meetings[1].id,
            equipment_id=equipment.id,
            quantity=3,
        ),
    ])
    db_session.commit()

    response = client.get(
        "/api/equipments/availability",
        params={
            "start_time": requested_start.isoformat(),
            "end_time": requested_end.isoformat(),
        },
    )

    assert response.status_code == 200
    item = next(
        row for row in response.json() if row["id"] == equipment.id
    )
    assert item["total_quantity"] == 8
    assert item["allocated_quantity"] == 5
    assert item["available_quantity"] == 3
    assert item["total_qty"] == 8
    assert item["booked_qty"] == 5
    assert item["available_qty"] == 3


def test_equipment_availability_api_requires_valid_time_range(client: TestClient):
    response = client.get(
        "/api/equipments/availability",
        params={
            "start_time": "2026-10-20T12:00:00",
            "end_time": "2026-10-20T12:00:00",
        },
    )

    assert response.status_code == 400
