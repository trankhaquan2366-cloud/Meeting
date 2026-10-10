from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.meeting import MeetingParticipant
from tests.helpers import (
    _add_participant,
    _auth_header,
    _create_meeting,
    _create_room,
    _create_user,
    _make_token,
)


class TestRSVPValidation:
    def test_pending_status_is_rejected_in_validation(self, client, db_session: Session):
        organizer = _create_user(db_session, "organizer_pending")
        invitee = _create_user(db_session, "invitee_pending")
        room = _create_room(db_session, "Room Pending")
        meeting = _create_meeting(
            db_session,
            room,
            organizer,
            datetime.utcnow() + timedelta(days=1),
            datetime.utcnow() + timedelta(days=1, hours=1),
        )
        _add_participant(db_session, meeting, invitee)

        resp = client.put(
            f"/api/meetings/{meeting.id}/respond",
            json={"status": "pending"},
            headers=_auth_header(_make_token(invitee)),
        )

        assert resp.status_code == 422


class TestRSVPAuthorize:
    def test_user_not_invited_gets_403(self, client, db_session: Session):
        organizer = _create_user(db_session, "organizer_forbidden")
        outsider = _create_user(db_session, "outsider_forbidden")
        room = _create_room(db_session, "Room Forbidden")
        meeting = _create_meeting(
            db_session,
            room,
            organizer,
            datetime.utcnow() + timedelta(days=2),
            datetime.utcnow() + timedelta(days=2, hours=1),
        )

        resp = client.put(
            f"/api/meetings/{meeting.id}/respond",
            json={"status": "accepted"},
            headers=_auth_header(_make_token(outsider)),
        )

        assert resp.status_code == 403
        assert resp.json()["detail"] == "You are not invited to this meeting"

    def test_organizer_cannot_respond_to_own_meeting(self, client, db_session: Session):
        organizer = _create_user(db_session, "organizer_self")
        room = _create_room(db_session, "Room Organizer")
        meeting = _create_meeting(
            db_session,
            room,
            organizer,
            datetime.utcnow() + timedelta(days=3),
            datetime.utcnow() + timedelta(days=3, hours=1),
        )

        resp = client.put(
            f"/api/meetings/{meeting.id}/respond",
            json={"status": "accepted"},
            headers=_auth_header(_make_token(organizer)),
        )

        assert resp.status_code == 400
        assert resp.json()["detail"] == "Organizer cannot respond to their own meeting"


class TestRSVPSuccess:
    def test_accepted_response_updates_db(self, client, db_session: Session):
        organizer = _create_user(db_session, "organizer_success")
        invitee = _create_user(db_session, "invitee_success")
        room = _create_room(db_session, "Room Success")
        meeting = _create_meeting(
            db_session,
            room,
            organizer,
            datetime.utcnow() + timedelta(days=4),
            datetime.utcnow() + timedelta(days=4, hours=1),
        )
        participant = _add_participant(db_session, meeting, invitee)
        participant.response_status = "pending"
        db_session.commit()

        resp = client.put(
            f"/api/meetings/{meeting.id}/respond",
            json={"status": "accepted"},
            headers=_auth_header(_make_token(invitee)),
        )

        assert resp.status_code == 200
        assert resp.json()["status"] == "accepted"

        db_session.expire_all()
        updated = db_session.query(MeetingParticipant).filter_by(id=participant.id).one()
        assert updated.response_status == "accepted"
