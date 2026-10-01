from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.equipment import Equipment, MeetingEquipment
from tests.helpers import _auth_header, _create_meeting, _create_room, _create_user, _make_token


def _future_window(offset_days: int = 2, start_hour: int = 10):
    start = datetime.utcnow() + timedelta(days=offset_days)
    start = start.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    return start, start + timedelta(hours=1)


def _create_equipment(db: Session, name: str, *, is_active: bool = True, status: str = "available") -> Equipment:
    equipment = Equipment(name=name, is_active=is_active, status=status)
    db.add(equipment)
    db.commit()
    db.refresh(equipment)
    return equipment


def _book(client: TestClient, meeting_id: int, user, equipment_ids: list[int]):
    return client.post(
        f"/api/meetings/{meeting_id}/equipments",
        json={"equipment_ids": equipment_ids},
        headers=_auth_header(_make_token(user)),
    )


def _meeting(db: Session, username: str, room_name: str, *, offset_days: int = 2, start_hour: int = 10, status: str = "scheduled"):
    organizer = _create_user(db, username)
    room = _create_room(db, room_name)
    start, end = _future_window(offset_days, start_hour)
    meeting = _create_meeting(db, room, organizer, start, end, status=status)
    return organizer, room, meeting


def test_organizer_can_book_equipment(client: TestClient, db_session: Session):
    organizer, _, meeting = _meeting(db_session, "equipment-organizer", "Equipment Room")
    equipment = _create_equipment(db_session, "Projector")

    response = _book(client, meeting.id, organizer, [equipment.id])

    assert response.status_code == 200
    assert response.json() == {"meeting_id": meeting.id, "equipment_ids": [equipment.id]}
    assert db_session.query(MeetingEquipment).filter_by(meeting_id=meeting.id, equipment_id=equipment.id).count() == 1


def test_admin_can_book_equipment(client: TestClient, db_session: Session):
    organizer, _, meeting = _meeting(db_session, "equipment-admin-target", "Equipment Admin Room")
    admin = _create_user(db_session, "equipment-admin", role="admin")
    equipment = _create_equipment(db_session, "Admin projector")

    response = _book(client, meeting.id, admin, [equipment.id])

    assert response.status_code == 200
    assert response.json()["equipment_ids"] == [equipment.id]
    assert organizer.id != admin.id


def test_other_user_gets_403(client: TestClient, db_session: Session):
    organizer, _, meeting = _meeting(db_session, "equipment-owner", "Permission Room")
    other = _create_user(db_session, "equipment-other")
    equipment = _create_equipment(db_session, "Restricted projector")

    response = _book(client, meeting.id, other, [equipment.id])

    assert response.status_code == 403
    assert db_session.query(MeetingEquipment).count() == 0


def test_booking_requires_authentication(client: TestClient, db_session: Session):
    organizer, _, meeting = _meeting(db_session, "equipment-auth", "Auth Equipment Room")
    equipment = _create_equipment(db_session, "Auth projector")

    response = client.post(
        f"/api/meetings/{meeting.id}/equipments",
        json={"equipment_ids": [equipment.id]},
    )

    assert response.status_code == 401
    assert organizer.id


def test_missing_meeting_or_equipment_returns_404(client: TestClient, db_session: Session):
    user = _create_user(db_session, "equipment-missing")
    equipment = _create_equipment(db_session, "Existing equipment")

    missing_meeting = client.post(
        "/api/meetings/999999/equipments",
        json={"equipment_ids": [equipment.id]},
        headers=_auth_header(_make_token(user)),
    )
    assert missing_meeting.status_code == 404

    target_user, _, meeting = _meeting(db_session, "equipment-missing-target", "Missing Equipment Room")
    missing_equipment = _book(client, meeting.id, target_user, [999999])
    assert missing_equipment.status_code == 404


def test_maintenance_equipment_is_rejected(client: TestClient, db_session: Session):
    organizer, _, meeting = _meeting(db_session, "equipment-maintenance", "Maintenance Room")
    equipment = _create_equipment(db_session, "Maintenance projector", status="maintenance")

    response = _book(client, meeting.id, organizer, [equipment.id])

    assert response.status_code == 400
    assert db_session.query(MeetingEquipment).count() == 0


def test_overlapping_equipment_booking_is_rejected(client: TestClient, db_session: Session):
    first_organizer, room, first_meeting = _meeting(db_session, "equipment-first", "Overlap Room")
    equipment = _create_equipment(db_session, "Shared camera")
    assert _book(client, first_meeting.id, first_organizer, [equipment.id]).status_code == 200

    second_organizer = _create_user(db_session, "equipment-second")
    second_start = first_meeting.start_time + timedelta(minutes=30)
    second_meeting = _create_meeting(
        db_session, room, second_organizer, second_start, second_start + timedelta(hours=1)
    )

    response = _book(client, second_meeting.id, second_organizer, [equipment.id])

    assert response.status_code == 400
    assert db_session.query(MeetingEquipment).filter_by(meeting_id=second_meeting.id).count() == 0


def test_non_overlapping_equipment_booking_is_allowed(client: TestClient, db_session: Session):
    first_organizer, room, first_meeting = _meeting(db_session, "equipment-slot-first", "Reuse Room")
    equipment = _create_equipment(db_session, "Reusable microphone")
    assert _book(client, first_meeting.id, first_organizer, [equipment.id]).status_code == 200

    second_organizer = _create_user(db_session, "equipment-slot-second")
    second_start = first_meeting.end_time + timedelta(minutes=30)
    second_meeting = _create_meeting(
        db_session, room, second_organizer, second_start, second_start + timedelta(hours=1)
    )

    response = _book(client, second_meeting.id, second_organizer, [equipment.id])

    assert response.status_code == 200
    assert db_session.query(MeetingEquipment).filter_by(equipment_id=equipment.id).count() == 2


def test_cancelled_meeting_releases_equipment(client: TestClient, db_session: Session):
    first_organizer, room, first_meeting = _meeting(
        db_session, "equipment-cancelled", "Cancelled Equipment Room", status="CANCELLED"
    )
    equipment = _create_equipment(db_session, "Released speaker")
    assert _book(client, first_meeting.id, first_organizer, [equipment.id]).status_code == 200

    second_organizer = _create_user(db_session, "equipment-after-cancel")
    second_start = first_meeting.start_time + timedelta(minutes=30)
    second_meeting = _create_meeting(
        db_session, room, second_organizer, second_start, second_start + timedelta(hours=1)
    )

    response = _book(client, second_meeting.id, second_organizer, [equipment.id])

    assert response.status_code == 200


def test_duplicate_ids_create_one_link(client: TestClient, db_session: Session):
    organizer, _, meeting = _meeting(db_session, "equipment-duplicates", "Duplicate Equipment Room")
    equipment = _create_equipment(db_session, "Duplicate-safe camera")

    response = _book(client, meeting.id, organizer, [equipment.id, equipment.id, equipment.id])

    assert response.status_code == 200
    assert db_session.query(MeetingEquipment).filter_by(meeting_id=meeting.id, equipment_id=equipment.id).count() == 1
    assert response.json()["equipment_ids"] == [equipment.id]


def test_invalid_equipment_rolls_back_all_assignments(client: TestClient, db_session: Session):
    organizer, _, meeting = _meeting(db_session, "equipment-atomic", "Atomic Equipment Room")
    valid = _create_equipment(db_session, "Atomic valid camera")
    unavailable = _create_equipment(db_session, "Atomic maintenance camera", status="maintenance")

    response = _book(client, meeting.id, organizer, [valid.id, unavailable.id])

    assert response.status_code == 400
    assert db_session.query(MeetingEquipment).filter_by(meeting_id=meeting.id).count() == 0
