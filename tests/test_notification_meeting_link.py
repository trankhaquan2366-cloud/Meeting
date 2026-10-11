from datetime import datetime, timedelta

from app.models.notification import Notification
from app.services.notification_service import send_meeting_invitation_notifications
from tests.helpers import (
    _add_participant,
    _auth_header,
    _create_meeting,
    _create_room,
    _create_user,
    _make_token,
)


def test_invitation_notification_is_linked_to_the_invited_meeting(client, db_session):
    organizer = _create_user(db_session, "notification_link_organizer")
    invitee = _create_user(db_session, "notification_link_invitee")
    room = _create_room(db_session, "Notification Link Room")
    meeting = _create_meeting(
        db_session,
        room,
        organizer,
        datetime.utcnow() + timedelta(days=1),
        datetime.utcnow() + timedelta(days=1, hours=1),
    )
    _add_participant(db_session, meeting, invitee)

    send_meeting_invitation_notifications(
        db=db_session,
        participant_ids=[invitee.id],
        meeting_title=meeting.title,
        start_time_str=meeting.start_time.strftime("%H:%M %d/%m/%Y"),
        meeting_id=meeting.id,
    )

    notification = (
        db_session.query(Notification)
        .filter(Notification.user_id == invitee.id)
        .one()
    )
    assert notification.meeting_id == meeting.id

    response = client.get(
        "/api/notifications/",
        headers=_auth_header(_make_token(invitee)),
    )

    assert response.status_code == 200
    assert response.json()[0]["meeting_id"] == meeting.id
