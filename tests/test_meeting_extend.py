from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.meeting_service import MeetingService
from tests.helpers import _auth_header, _create_meeting, _create_room, _create_user, _make_token


def test_extend_in_progress_meeting_updates_end_time(db_session: Session):
    organizer = _create_user(db_session, "extend-meeting-organizer")
    room = _create_room(db_session, "Extend meeting room")
    start = datetime.utcnow() - timedelta(minutes=30)
    original_end = start + timedelta(minutes=45)
    meeting = _create_meeting(
        db_session, room, organizer, start, original_end, status="IN_PROGRESS"
    )

    extended = MeetingService.extend_meeting(
        db_session, meeting.id, organizer.id, 15
    )

    assert extended.end_time == original_end + timedelta(minutes=15)


def test_extend_conflict_returns_two_rooms_free_for_full_meeting(db_session: Session):
    organizer = _create_user(db_session, "extend-conflict-organizer")
    current_room = _create_room(db_session, "Currently used room")
    replacement_rooms = [
        _create_room(db_session, "Available room one"),
        _create_room(db_session, "Available room two"),
    ]
    start = datetime.utcnow() - timedelta(minutes=30)
    original_end = start + timedelta(minutes=45)
    meeting = _create_meeting(
        db_session, current_room, organizer, start, original_end, status="IN_PROGRESS"
    )
    _create_meeting(
        db_session,
        current_room,
        organizer,
        original_end + timedelta(minutes=5),
        original_end + timedelta(minutes=35),
    )
    _create_meeting(
        db_session,
        replacement_rooms[0],
        organizer,
        start - timedelta(hours=2),
        start - timedelta(hours=1),
    )

    result = MeetingService.extend_meeting(
        db_session, meeting.id, organizer.id, 15
    )

    assert {room["name"] for room in result["available_rooms"]} == {
        "Available room one",
        "Available room two",
    }
    db_session.refresh(meeting)
    assert meeting.end_time == original_end


def test_extend_endpoint_requires_owner_and_supported_duration(
    client: TestClient,
    db_session: Session,
):
    organizer = _create_user(db_session, "extend-endpoint-organizer")
    other_user = _create_user(db_session, "extend-endpoint-other")
    room = _create_room(db_session, "Extend endpoint room")
    start = datetime.utcnow() - timedelta(minutes=20)
    meeting = _create_meeting(
        db_session,
        room,
        organizer,
        start,
        start + timedelta(minutes=50),
        status="IN_PROGRESS",
    )
    original_end = meeting.end_time
    url = f"/api/v1/meetings/{meeting.id}/extend"

    forbidden = client.post(
        url,
        json={"extend_minutes": 15},
        headers=_auth_header(_make_token(other_user)),
    )
    invalid_duration = client.post(
        url,
        json={"extend_minutes": 10},
        headers=_auth_header(_make_token(organizer)),
    )
    extended = client.post(
        url,
        json={"extend_minutes": 30},
        headers=_auth_header(_make_token(organizer)),
    )

    assert forbidden.status_code == 403
    assert invalid_duration.status_code == 422
    assert extended.status_code == 200
    assert extended.json()["end_time"] == (original_end + timedelta(minutes=30)).isoformat()

    _create_meeting(
        db_session,
        room,
        organizer,
        original_end + timedelta(minutes=35),
        original_end + timedelta(minutes=60),
    )
    conflict = client.post(
        url,
        json={"extend_minutes": 15},
        headers=_auth_header(_make_token(organizer)),
    )

    assert conflict.status_code == 409
    assert "available_rooms" in conflict.json()["detail"]
