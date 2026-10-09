from app.models.notification import Notification
from app.services import email_service, notification_service
from tests.helpers import _create_user


def test_meeting_notification_task_sends_email_and_persists_in_app_notice(
    db_session,
    monkeypatch,
):
    user = _create_user(db_session, "meeting-email-recipient")
    sent_emails = []
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "meetings@example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.delenv("SMTP_USERNAME", raising=False)
    monkeypatch.delenv("SMTP_PASSWORD", raising=False)
    monkeypatch.setattr(
        email_service,
        "send_email",
        lambda recipient, subject, content, settings: sent_emails.append(
            (recipient, subject, content)
        ),
    )

    notification_service.send_meeting_notification_task(
        [user.id],
        "Cuộc họp đã bị hủy",
        "Lý do: lịch thay đổi. Chúng tôi xin lỗi.",
    )

    saved_notice = db_session.query(Notification).filter_by(user_id=user.id).one()
    assert saved_notice.title == "Cuộc họp đã bị hủy"
    assert "lịch thay đổi" in saved_notice.content
    assert sent_emails == [
        (
            user.email,
            "Cuộc họp đã bị hủy",
            "Lý do: lịch thay đổi. Chúng tôi xin lỗi.",
        )
    ]
