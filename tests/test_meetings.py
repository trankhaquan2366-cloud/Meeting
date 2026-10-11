from datetime import datetime, timedelta, timezone, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.equipment import Equipment, MeetingEquipment
from app.models.notification import Notification
from app.services.meeting_service import MeetingService
from app.services.scheduler import (
    process_auto_checkouts,
    process_meeting_reminders,
    process_no_show_meetings,
)
from tests.helpers import (
    _add_participant,
    _auth_header,
    _create_meeting,
    _create_room,
    _create_user,
    _make_token,
)


def _meeting_at(
    db_session: Session,
    start_time: datetime,
    status: str = "scheduled",
):
    identifier = uuid4().hex
    organizer = _create_user(db_session, f"qr-organizer-{identifier}")
    room = _create_room(db_session, f"QR Room {identifier}")
    meeting = _create_meeting(
        db_session,
        room,
        organizer,
        start_time,
        start_time + timedelta(hours=1),
        status=status,
    )
    return meeting, room, organizer


def test_check_in_succeeds_within_fifteen_minute_window(db_session: Session):
    now = datetime(2026, 10, 10, 10, 0)
    meeting, room, organizer = _meeting_at(db_session, now + timedelta(minutes=15))

    checked_in = MeetingService.check_in_meeting(
        db_session, meeting.id, room.qr_token, organizer, now=now
    )

    assert checked_in.status == "IN_PROGRESS"
    assert checked_in.check_in_time == now
    notification = (
        db_session.query(Notification)
        .filter(Notification.user_id == organizer.id)
        .one()
    )
    assert "Test meeting" in notification.content
    assert "check-in thành công và bắt đầu" in notification.content


@pytest.mark.parametrize("failure", ["wrong_qr", "not_accepted"])
def test_check_in_rejects_wrong_qr_or_unaccepted_participant(
    db_session: Session,
    failure: str,
):
    now = datetime(2026, 10, 10, 10, 0)
    meeting, room, organizer = _meeting_at(db_session, now)
    participant = _create_user(db_session, f"qr-participant-{failure}")
    participant_row = _add_participant(db_session, meeting, participant)

    qr_token = room.qr_token
    if failure == "wrong_qr":
        participant_row.response_status = "accepted"
        db_session.commit()
        qr_token = "invalid-token"

    with pytest.raises(HTTPException) as error:
        MeetingService.check_in_meeting(
            db_session, meeting.id, qr_token, participant, now=now
        )

    assert error.value.status_code == (400 if failure == "wrong_qr" else 403)


@pytest.mark.parametrize(
    ("offset_minutes", "message"),
    [
        (-16, "Chưa đến thời gian check-in (cho phép trước 15 phút)"),
        (16, "Đã quá thời gian check-in"),
    ],
)
def test_check_in_rejects_outside_allowed_time_window(
    db_session: Session,
    offset_minutes: int,
    message: str,
):
    start_time = datetime(2026, 10, 10, 10, 0)
    now = start_time + timedelta(minutes=offset_minutes)
    meeting, room, organizer = _meeting_at(db_session, start_time)

    with pytest.raises(HTTPException) as error:
        MeetingService.check_in_meeting(
            db_session, meeting.id, room.qr_token, organizer, now=now
        )

    assert error.value.status_code == 400
    assert error.value.detail == message


@pytest.mark.parametrize("offset_minutes", [-15, 15])
def test_check_in_accepts_exact_window_boundaries(
    db_session: Session,
    offset_minutes: int,
):
    start_time = datetime(2026, 10, 10, 10, 0)
    meeting, room, organizer = _meeting_at(db_session, start_time)

    checked_in = MeetingService.check_in_meeting(
        db_session,
        meeting.id,
        room.qr_token,
        organizer,
        now=start_time + timedelta(minutes=offset_minutes),
    )
    assert checked_in.status == "IN_PROGRESS"


def test_check_out_completes_meeting_with_room_qr(db_session: Session):
    now = datetime(2026, 10, 10, 10, 0)
    meeting, room, organizer = _meeting_at(db_session, now, status="IN_PROGRESS")
    equipment = Equipment(
        name=f"Early checkout equipment {uuid4().hex}",
        total_qty=1,
        is_active=True,
    )
    db_session.add(equipment)
    db_session.flush()
    db_session.add(
        MeetingEquipment(meeting_id=meeting.id, equipment_id=equipment.id, quantity=1)
    )
    db_session.commit()

    checked_out = MeetingService.check_out_meeting(
        db_session,
        meeting.id,
        room.qr_token,
        organizer,
        now=now + timedelta(minutes=20),
    )

    assert checked_out.status == "COMPLETED"
    assert checked_out.check_out_time == now + timedelta(minutes=20)
    from app.services.equipment_service import get_equipment_availability
    from app.services.room_service import get_available_rooms

    available_rooms = get_available_rooms(
        db_session,
        start_time=now + timedelta(minutes=21),
        end_time=now + timedelta(minutes=30),
    )
    assert room.id in {available_room.id for available_room in available_rooms}

    equipment_availability = get_equipment_availability(
        db_session,
        start_time=now + timedelta(minutes=21),
        end_time=now + timedelta(minutes=30),
    )
    equipment_status = next(item for item in equipment_availability if item.id == equipment.id)
    assert equipment_status.booked_qty == 0
    assert equipment_status.available_qty == equipment.total_qty


def test_versioned_check_in_endpoint(client: TestClient, db_session: Session):
    organizer = _create_user(db_session, f"api-organizer-{uuid4().hex}")
    room = _create_room(db_session, f"API QR Room {uuid4().hex}")
    start_time = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=5)
    meeting = _create_meeting(
        db_session,
        room,
        organizer,
        start_time,
        start_time + timedelta(hours=1),
    )

    response = client.post(
        f"/api/v1/meetings/{meeting.id}/check-in",
        json={"qr_token": room.qr_token},
        headers=_auth_header(_make_token(organizer)),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "IN_PROGRESS"
    assert response.json()["check_in_time"] is not None


def test_manager_can_retrieve_room_qr_code(client: TestClient, db_session: Session):
    manager = _create_user(db_session, f"qr-manager-{uuid4().hex}", role="manager")
    room = _create_room(db_session, f"Manager QR Room {uuid4().hex}")

    response = client.get(
        f"/api/v1/rooms/{room.id}/qr-code",
        headers=_auth_header(_make_token(manager)),
    )

    assert response.status_code == 200
    assert response.json() == {
        "room_id": room.id,
        "room_name": room.name,
        "qr_token": room.qr_token,
    }


def test_meeting_organizer_can_retrieve_qr_for_their_scheduled_meeting(
    client: TestClient,
    db_session: Session,
):
    organizer = _create_user(db_session, f"qr-owner-{uuid4().hex}")
    outsider = _create_user(db_session, f"qr-outsider-{uuid4().hex}")
    room = _create_room(db_session, f"Organizer QR Room {uuid4().hex}")
    start_time = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=5)
    meeting = _create_meeting(
        db_session, room, organizer, start_time, start_time + timedelta(hours=1)
    )

    owner_response = client.get(
        f"/api/v1/rooms/{room.id}/qr-code",
        params={"meeting_id": meeting.id},
        headers=_auth_header(_make_token(organizer)),
    )
    outsider_response = client.get(
        f"/api/v1/rooms/{room.id}/qr-code",
        params={"meeting_id": meeting.id},
        headers=_auth_header(_make_token(outsider)),
    )

    assert owner_response.status_code == 200
    assert owner_response.json()["qr_token"] == room.qr_token
    assert outsider_response.status_code == 403


def test_no_show_scheduler_cancels_meeting_after_grace_period(db_session: Session):
    now = datetime(2026, 10, 10, 10, 16)
    meeting, _, _ = _meeting_at(
        db_session,
        now - timedelta(minutes=16),
    )

    processed = process_no_show_meetings(db_session, now=now)

    db_session.refresh(meeting)
    assert processed == 1
    assert meeting.status == "CANCELLED_NO_SHOW"


def test_no_show_meeting_releases_equipment_inventory(db_session: Session):
    now = datetime(2026, 10, 10, 10, 16)
    meeting, _, _ = _meeting_at(db_session, now - timedelta(minutes=16))
    equipment = Equipment(
        name=f"QR scheduler equipment {uuid4().hex}",
        total_qty=1,
        is_active=True,
    )
    db_session.add(equipment)
    db_session.flush()
    db_session.add(
        MeetingEquipment(meeting_id=meeting.id, equipment_id=equipment.id, quantity=1)
    )
    db_session.commit()

    process_no_show_meetings(db_session, now=now)

    from app.services.equipment_service import get_equipment_availability

    availability = get_equipment_availability(
        db_session,
        now - timedelta(minutes=1),
        now + timedelta(minutes=1),
    )
    equipment_status = next(item for item in availability if item.id == equipment.id)
    assert equipment_status.booked_qty == 0
    assert equipment_status.available_qty == 1


def test_no_show_scheduler_does_not_cancel_before_grace_period(db_session: Session):
    now = datetime(2026, 10, 10, 10, 14)
    meeting, _, _ = _meeting_at(
        db_session,
        now - timedelta(minutes=14),
    )

    processed = process_no_show_meetings(db_session, now=now)

    db_session.refresh(meeting)
    assert processed == 0
    assert meeting.status == "scheduled"


def test_reminder_scheduler_notifies_organizer_and_accepted_attendees(db_session: Session):
    now = datetime(2026, 10, 10, 10, 5)
    meeting, _, organizer = _meeting_at(db_session, now - timedelta(minutes=5))
    accepted = _create_user(db_session, f"reminder-accepted-{uuid4().hex}")
    pending = _create_user(db_session, f"reminder-pending-{uuid4().hex}")
    accepted_invitation = _add_participant(db_session, meeting, accepted)
    accepted_invitation.response_status = "accepted"
    _add_participant(db_session, meeting, pending)
    db_session.commit()

    processed = process_meeting_reminders(db_session, now=now)

    assert processed == 1
    assert meeting.reminder_sent is True
    notifications = db_session.query(Notification).all()
    assert {notification.user_id for notification in notifications} == {
        organizer.id,
        accepted.id,
    }


def test_auto_checkout_uses_scheduled_end_time(db_session: Session):
    now = datetime(2026, 10, 10, 11, 0)
    meeting, _, _ = _meeting_at(
        db_session,
        now - timedelta(hours=2),
        status="IN_PROGRESS",
    )

    processed = process_auto_checkouts(db_session, now=now)

    db_session.refresh(meeting)
    assert processed == 1
    assert meeting.status == "COMPLETED"
    assert meeting.check_out_time == meeting.end_time
