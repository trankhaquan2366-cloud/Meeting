from app.core.config import get_smtp_settings
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
    monkeypatch.setattr(
        email_service,
        "send_email",
        lambda to_email, subject, body_text, body_html: sent.update(
            to_email=to_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
        ) or True,
    )

    result = email_service.send_meeting_invitation_email(
        to_email="invitee@example.test",
        user_name="<Member>",
        meeting_title="Planning <Q&A>",
        start_time_str="09:00 ngày 01/07/2026",
        location_str="Trực tuyến",
        meeting_link="https://meet.example.test/a?x=1&y=2",
    )

    assert result is True
    assert sent["to_email"] == "invitee@example.test"
    assert "Planning <Q&A>" in sent["body_text"]
    assert "Planning &lt;Q&amp;A&gt;" in sent["body_html"]
    assert "https://meet.example.test/a?x=1&amp;y=2" in sent["body_html"]
