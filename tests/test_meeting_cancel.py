from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from tests.helpers import (
    _add_participant,
    _auth_header,
    _create_meeting,
    _create_room,
    _create_user,
    _make_token,
)
from app.models.meeting import MeetingParticipant
from app.models.notification import Notification


def _future_window():
    start = datetime.utcnow() + timedelta(days=2)
    return start, start + timedelta(hours=1)


def test_organizer_can_cancel_and_repeat_safely(client: TestClient, db_session: Session):
    organizer = _create_user(db_session, "cancel-organizer")
    participant = _create_user(db_session, "cancel-participant")
    room = _create_room(db_session, "Cancel Room")
    start, end = _future_window()
    meeting = _create_meeting(db_session, room, organizer, start, end)
    _add_participant(db_session, meeting, participant)

    headers = _auth_header(_make_token(organizer))
    response = client.patch(f"/api/meetings/{meeting.id}/cancel", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"

    repeated = client.patch(f"/api/meetings/{meeting.id}/cancel", headers=headers)
    assert repeated.status_code == 200
    assert repeated.json()["status"] == "CANCELLED"

    db_session.expire_all()
    saved = db_session.get(type(meeting), meeting.id)
    assert saved.status == "CANCELLED"
    assert db_session.query(MeetingParticipant).filter_by(meeting_id=meeting.id).count() == 1


def test_cancel_updates_invitation_notification_for_invitee(client: TestClient, db_session: Session):
    organizer = _create_user(db_session, "cancel-notification-organizer")
    invitee = _create_user(db_session, "cancel-notification-invitee")
    room = _create_room(db_session, "Cancel Notification Room")
    start, end = _future_window()
    meeting = _create_meeting(db_session, room, organizer, start, end)
    _add_participant(db_session, meeting, invitee)
    invitation = Notification(
        user_id=invitee.id,
        meeting_id=meeting.id,
        title="Lời mời tham dự cuộc họp mới",
        content=f"Bạn được mời tham gia cuộc họp '{meeting.title}'.",
        is_read=True,
    )
    db_session.add(invitation)
    db_session.commit()

    response = client.patch(
        f"/api/meetings/{meeting.id}/cancel",
        headers=_auth_header(_make_token(organizer)),
    )
    notifications = client.get(
        "/api/notifications/",
        headers=_auth_header(_make_token(invitee)),
    )

    assert response.status_code == 200
    assert notifications.status_code == 200
    canceled_notification = next(
        item for item in notifications.json() if item["id"] == invitation.id
    )
    assert canceled_notification["title"] == "Cuộc họp đã bị hủy"
    assert canceled_notification["meeting_title"] == meeting.title
    assert canceled_notification["meeting_status"] == "CANCELLED"
    assert canceled_notification["is_read"] is False
    assert db_session.query(Notification).filter_by(meeting_id=meeting.id).count() == 1

    repeated = client.patch(
        f"/api/meetings/{meeting.id}/cancel",
        headers=_auth_header(_make_token(organizer)),
    )
    assert repeated.status_code == 200
    assert db_session.query(Notification).filter_by(meeting_id=meeting.id).count() == 1


def test_admin_can_cancel(client: TestClient, db_session: Session):
    organizer = _create_user(db_session, "admin-target-organizer")
    admin = _create_user(db_session, "cancel-admin", role="admin")
    room = _create_room(db_session, "Admin Cancel Room")
    start, end = _future_window()
    meeting = _create_meeting(db_session, room, organizer, start, end)

    response = client.patch(
        f"/api/meetings/{meeting.id}/cancel",
        headers=_auth_header(_make_token(admin)),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


def test_organizer_can_cancel_with_delete_endpoint(client: TestClient, db_session: Session):
    organizer = _create_user(db_session, "delete-organizer")
    room = _create_room(db_session, "Delete Organizer Room")
    start, end = _future_window()
    meeting = _create_meeting(db_session, room, organizer, start, end)

    response = client.delete(
        f"/api/meetings/{meeting.id}",
        headers=_auth_header(_make_token(organizer)),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


def test_admin_can_cancel_with_delete_endpoint(client: TestClient, db_session: Session):
    organizer = _create_user(db_session, "delete-admin-target")
    admin = _create_user(db_session, "delete-admin", role="admin")
    room = _create_room(db_session, "Delete Admin Room")
    start, end = _future_window()
    meeting = _create_meeting(db_session, room, organizer, start, end)

    response = client.delete(
        f"/api/meetings/{meeting.id}",
        headers=_auth_header(_make_token(admin)),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


def test_admin_role_is_case_insensitive(client: TestClient, db_session: Session):
    organizer = _create_user(db_session, "upper-admin-target")
    admin = _create_user(db_session, "upper-case-admin", role="ADMIN")
    room = _create_room(db_session, "Upper Admin Room")
    start, end = _future_window()
    meeting = _create_meeting(db_session, room, organizer, start, end)

    response = client.delete(
        f"/api/meetings/{meeting.id}",
        headers=_auth_header(_make_token(admin)),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


def test_invitee_cannot_cancel_with_delete_endpoint(client: TestClient, db_session: Session):
    organizer = _create_user(db_session, "delete-protected-organizer")
    invitee = _create_user(db_session, "delete-protected-invitee")
    room = _create_room(db_session, "Delete Protected Room")
    start, end = _future_window()
    meeting = _create_meeting(db_session, room, organizer, start, end)
    _add_participant(db_session, meeting, invitee)

    response = client.delete(
        f"/api/meetings/{meeting.id}",
        headers=_auth_header(_make_token(invitee)),
    )

    assert response.status_code == 403
    db_session.expire_all()
    assert db_session.get(type(meeting), meeting.id).status == "scheduled"


def test_non_organizer_cannot_cancel(client: TestClient, db_session: Session):
    organizer = _create_user(db_session, "protected-organizer")
    outsider = _create_user(db_session, "cancel-outsider")
    room = _create_room(db_session, "Protected Cancel Room")
    start, end = _future_window()
    meeting = _create_meeting(db_session, room, organizer, start, end)

    response = client.patch(
        f"/api/meetings/{meeting.id}/cancel",
        headers=_auth_header(_make_token(outsider)),
    )
    assert response.status_code == 403
    db_session.expire_all()
    assert db_session.get(type(meeting), meeting.id).status == "scheduled"


def test_cancel_requires_authentication(client: TestClient, db_session: Session):
    organizer = _create_user(db_session, "auth-cancel-organizer")
    room = _create_room(db_session, "Auth Cancel Room")
    start, end = _future_window()
    meeting = _create_meeting(db_session, room, organizer, start, end)

    response = client.patch(f"/api/meetings/{meeting.id}/cancel")
    assert response.status_code == 401


def test_cancel_missing_meeting_returns_404(client: TestClient, db_session: Session):
    user = _create_user(db_session, "missing-cancel-user")
    response = client.patch(
        "/api/meetings/999999/cancel",
        headers=_auth_header(_make_token(user)),
    )
    assert response.status_code == 404


def test_room_can_be_booked_again_after_cancel(client: TestClient, db_session: Session):
    organizer = _create_user(db_session, "reuse-organizer")
    room = _create_room(db_session, "Reusable Room")
    start, end = _future_window()
    meeting = _create_meeting(db_session, room, organizer, start, end)

    cancel = client.patch(
        f"/api/meetings/{meeting.id}/cancel",
        headers=_auth_header(_make_token(organizer)),
    )
    assert cancel.status_code == 200

    booking = client.post(
        "/api/meetings/book",
        json={
            "title": "Replacement meeting",
            "room_id": room.id,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        },
        headers=_auth_header(_make_token(organizer)),
    )
    assert booking.status_code == 201
    assert len(booking.json()) == 1

    available = client.get(
        "/api/rooms/available/",
        params={"start_time": start.isoformat(), "end_time": end.isoformat()},
    )
    assert available.status_code == 200
    assert room.id not in {item["id"] for item in available.json()}
