from contextlib import contextmanager
from datetime import datetime
from email import policy
from email.parser import BytesParser

from app.core.config import SMTPSettings, get_smtp_settings
from app.services import email_service


def test_smtp_settings_support_new_and_legacy_environment_names(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("SMTP_PORT", "465")
    monkeypatch.setenv("SMTP_USER", "new-user@example.test")
    monkeypatch.setenv("SMTP_USERNAME", "legacy-user@example.test")
    monkeypatch.setenv("SMTP_PASSWORD", "app-password")
    monkeypatch.setenv("EMAILS_FROM_EMAIL", "new-from@example.test")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "legacy-from@example.test")
    monkeypatch.setenv("SMTP_STARTTLS", "false")

    settings = get_smtp_settings()

    assert settings is not None
    assert settings.host == "smtp.example.test"
    assert settings.port == 465
    assert settings.username == "new-user@example.test"
    assert settings.password == "app-password"
    assert settings.from_email == "new-from@example.test"
    assert settings.starttls is False


def test_smtp_settings_default_to_gmail_and_support_legacy_names(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "")
    monkeypatch.setenv("SMTP_USER", "")
    monkeypatch.setenv("SMTP_USERNAME", "legacy-user@example.test")
    monkeypatch.setenv("EMAILS_FROM_EMAIL", "")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "legacy-from@example.test")
    monkeypatch.setenv("SMTP_PORT", "587")

    settings = get_smtp_settings()

    assert settings is not None
    assert settings.host == "smtp.gmail.com"
    assert settings.port == 587
    assert settings.username == "legacy-user@example.test"
    assert settings.from_email == "legacy-from@example.test"


def test_invitation_email_contains_escaped_meeting_details(monkeypatch):
    sent = {}
    monkeypatch.setenv(
        "FRONTEND_DASHBOARD_URL", "http://localhost:8000/static/dashboard.html"
    )
    monkeypatch.setattr(
        email_service,
        "send_email",
        lambda to_email, subject, body_text, body_html, calendar_invitation=None: sent.update(
            to_email=to_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            calendar_invitation=calendar_invitation,
        ) or True,
    )

    result = email_service.send_meeting_invitation_email(
        to_email="invitee@example.test",
        user_name="<Member>",
        meeting_title="Planning <Q&A>",
        start_time_str="09:00 ngày 01/07/2026",
        location_str="Trực tuyến",
        meeting_link="https://meet.google.com/a?x=1&y=2",
        meeting_id=42,
        start_time=datetime(2026, 7, 1, 9, 0),
        end_time=datetime(2026, 7, 1, 10, 0),
        organizer_email="host@example.test",
        organizer_name="Meeting Host",
    )

    assert result is True
    assert sent["to_email"] == "invitee@example.test"
    assert "Planning <Q&A>" in sent["body_text"]
    assert "Planning &lt;Q&amp;A&gt;" in sent["body_html"]
    assert "https://meet.google.com/a?x=1&amp;y=2" in sent["body_html"]
    assert 'href="http://localhost:8000/static/dashboard.html?meeting_id=42&amp;action=accept"' in sent["body_html"]
    assert 'href="http://localhost:8000/static/dashboard.html?meeting_id=42&amp;action=decline"' in sent["body_html"]
    assert 'href="https://meet.google.com/a?x=1&amp;y=2" target="_blank"' in sent["body_html"]
    assert "✅ Đồng ý tham gia" in sent["body_html"]
    assert "❌ Từ chối" in sent["body_html"]
    assert "📹 Vào họp Google Meet" in sent["body_html"]
    assert "METHOD:REQUEST" in sent["calendar_invitation"]
    assert "UID:meeting-42@roomsync" in sent["calendar_invitation"]
    assert "DTSTART:20260701T020000Z" in sent["calendar_invitation"]
    assert "DTEND:20260701T030000Z" in sent["calendar_invitation"]
    assert "ORGANIZER;CN=\"Meeting Host\":mailto:host@example.test" in sent["calendar_invitation"]
    assert "ATTENDEE;ROLE=REQ-PARTICIPANT;RSVP=TRUE;PARTSTAT=NEEDS-ACTION:mailto:invitee@example.test" in sent["calendar_invitation"]


def test_send_email_attaches_calendar_request(monkeypatch):
    captured = {}
    smtp_settings = SMTPSettings(
        host="smtp.example.test",
        port=587,
        username="sender@example.test",
        password="smtp-password",
        from_email="sender@example.test",
        starttls=True,
    )

    class FakeSMTP:
        def login(self, username, password):
            assert username == smtp_settings.username
            assert password == smtp_settings.password

        def send_message(self, message):
            captured["message"] = BytesParser(policy=policy.default).parsebytes(
                message.as_bytes()
            )

    @contextmanager
    def fake_smtp_connection(settings):
        assert settings == smtp_settings
        yield FakeSMTP()

    monkeypatch.setattr(email_service, "get_smtp_settings", lambda: smtp_settings)
    monkeypatch.setattr(email_service, "smtp_connection", fake_smtp_connection)

    assert email_service.send_email(
        to_email="invitee@example.test",
        subject="Meeting invitation",
        body_text="Invitation",
        body_html="<p>Invitation</p>",
        calendar_invitation="BEGIN:VCALENDAR\r\nMETHOD:REQUEST\r\nEND:VCALENDAR\r\n",
    )

    calendar_part = next(
        part
        for part in captured["message"].walk()
        if part.get_content_type() == "text/calendar"
    )
    assert calendar_part.get_param("method") == "REQUEST"
    assert calendar_part.get_filename() == "meeting-invitation.ics"
    assert "METHOD:REQUEST" in calendar_part.get_content()
