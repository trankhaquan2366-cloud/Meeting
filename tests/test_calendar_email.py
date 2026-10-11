from datetime import datetime, timedelta

from app.models.meeting import MeetingParticipant
from app.services import calendar_email_service
from tests.helpers import _create_meeting, _create_room, _create_user


class FakeSMTP:
    sent_messages = []

    def __init__(self, host, port, timeout):
        self.host = host
        self.port = port
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def ehlo(self):
        return None

    def starttls(self, context):
        return None

    def login(self, username, password):
        return None

    def send_message(self, message):
        self.sent_messages.append(message)


def test_unconnected_invitee_receives_calendar_consent_email(
    db_session, monkeypatch
):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "calendar@example.test")
    monkeypatch.setenv("SMTP_PASSWORD", "test-smtp-password")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "calendar@example.test")
    monkeypatch.setenv("SMTP_STARTTLS", "false")
    monkeypatch.setenv("BACKEND_PUBLIC_URL", "https://roomsync.example.test")
    FakeSMTP.sent_messages = []
    monkeypatch.setattr(calendar_email_service.smtplib, "SMTP", FakeSMTP)

    organizer = _create_user(db_session, "email-organizer")
    invitee = _create_user(db_session, "email-invitee")
    invitee.email = "invitee@example.test"
    db_session.commit()
    room = _create_room(db_session, "Calendar Email Room")
    start = datetime.now() + timedelta(days=2)
    meeting = _create_meeting(db_session, room, organizer, start, start + timedelta(hours=1))
    db_session.add(MeetingParticipant(meeting_id=meeting.id, user_id=invitee.id))
    db_session.commit()

    calendar_email_service.request_calendar_access_for_invitees([invitee.id], [meeting.id])

    assert len(FakeSMTP.sent_messages) == 1
    sent = FakeSMTP.sent_messages[0]
    assert sent["To"] == "invitee@example.test"
    assert "Kết nối Google Calendar" in sent["Subject"]
    assert "/api/auth/google/calendar/connect?" in sent.get_content()
    assert "Calendar Email Room" not in sent.get_content()
    assert meeting.title in sent.get_content()
