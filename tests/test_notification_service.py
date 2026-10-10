from app.models.notification import Notification
from app.services import email_service, notification_service
from tests.helpers import _auth_header, _create_user, _make_token


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


def test_notification_read_supports_patch_and_legacy_put(
    client,
    db_session,
):
    user = _create_user(db_session, "notification-reader")
    notifications = [
        Notification(
            user_id=user.id,
            title="Reminder",
            content="Meeting details",
        )
        for _ in range(2)
    ]
    db_session.add_all(notifications)
    db_session.commit()
    headers = _auth_header(_make_token(user))

    patch_response = client.patch(
        f"/api/notifications/{notifications[0].id}/read",
        headers=headers,
    )
    put_response = client.put(
        f"/api/notifications/{notifications[1].id}/read",
        headers=headers,
    )

    assert patch_response.status_code == 200
    assert put_response.status_code == 200
    assert patch_response.json()["is_read"] is True
    assert put_response.json()["is_read"] is True
