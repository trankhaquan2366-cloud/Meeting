from datetime import datetime, timedelta

from sqlalchemy.exc import SQLAlchemyError

from app.models.meeting import Meeting, MeetingParticipant
from app.models.email_delivery import EmailDelivery
from app.models.notification import Notification
from app.models.user import User
from app.services import email_service, reminder_service


def _create_meeting(
    db_session,
    start_time: datetime,
    status: str = "CONFIRMED",
    suffix: str = "",
):
    organizer = User(
        username=f"organizer{suffix}",
        email=f"organizer{suffix}@example.com",
        hashed_password="unused",
    )
    participant = User(
        username=f"participant{suffix}",
        email=f"participant{suffix}@example.com",
        hashed_password="unused",
    )
    meeting = Meeting(
        title="Planning",
        organizer=organizer,
        start_time=start_time,
        end_time=start_time + timedelta(minutes=30),
        status=status,
    )
    meeting.participants.append(MeetingParticipant(user=participant))
    db_session.add(meeting)
    db_session.commit()
    return meeting, organizer, participant


def _clear_smtp_config(monkeypatch):
    for name in (
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USERNAME",
        "SMTP_USER",
        "SMTP_PASSWORD",
        "SMTP_FROM_EMAIL",
    ):
        monkeypatch.delenv(name, raising=False)


def test_sends_in_app_reminder_once_for_confirmed_meeting(db_session, monkeypatch):
    _clear_smtp_config(monkeypatch)
    now = datetime(2030, 1, 1, 12)
    meeting, organizer, participant = _create_meeting(
        db_session,
        now + timedelta(hours=24) - timedelta(seconds=30),
    )

    assert reminder_service.process_due_meeting_reminders(db_session, now) == 1
    db_session.refresh(meeting)

    assert meeting.is_reminded_24h is True
    assert meeting.is_reminded_15m is False
    assert {
        notice.user_id
        for notice in db_session.query(Notification).all()
    } == {organizer.id, participant.id}
    assert reminder_service.process_due_meeting_reminders(db_session, now) == 0
    assert db_session.query(Notification).count() == 2


def test_sends_email_and_in_app_reminder_for_15_minute_window(db_session, monkeypatch):
    now = datetime(2030, 1, 1, 12)
    meeting, organizer, participant = _create_meeting(
        db_session,
        now + timedelta(minutes=15) - timedelta(seconds=30),
    )
    sent_emails = []
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "meetings@example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setattr(
        email_service,
        "send_email",
        lambda recipient, subject, content, settings: sent_emails.append(
            (recipient, subject, content, settings)
        ),
    )

    assert reminder_service.process_due_meeting_reminders(db_session, now) == 1
    db_session.refresh(meeting)

    assert meeting.is_reminded_15m is True
    assert {email[0] for email in sent_emails} == {organizer.email, participant.email}
    assert db_session.query(Notification).count() == 2


def test_sends_message_over_configured_smtp(monkeypatch):
    smtp_calls = []

    class FakeSMTP:
        def __init__(self, host, port, timeout):
            smtp_calls.append(("connect", host, port, timeout))

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def starttls(self, context):
            smtp_calls.append(("starttls", context))

        def login(self, username, password):
            smtp_calls.append(("login", username, password))

        def send_message(self, message):
            smtp_calls.append(("send", message["To"], message["Subject"]))

    monkeypatch.setattr(email_service.smtplib, "SMTP", FakeSMTP)

    email_service.send_email(
        "employee@example.com",
        "Meeting reminder",
        "Meeting starts soon",
        email_service.SMTPSettings(
            host="smtp.example.com",
            port=587,
            sender="meetings@example.com",
            username="mailer",
            password="test-password",
        ),
    )

    assert smtp_calls[0] == ("connect", "smtp.example.com", 587, 10)
    assert smtp_calls[1][0] == "starttls"
    assert smtp_calls[2] == ("login", "mailer", "test-password")
    assert smtp_calls[3] == ("send", "employee@example.com", "Meeting reminder")


def test_smtp_user_environment_alias_is_supported(monkeypatch):
    _clear_smtp_config(monkeypatch)
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "meetings@example.com")
    monkeypatch.setenv("SMTP_USER", "mailer")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")

    settings = email_service.get_smtp_settings()

    assert settings is not None
    assert settings.username == "mailer"


def test_sends_in_app_reminder_for_confirmed_meeting(db_session, monkeypatch):
    _clear_smtp_config(monkeypatch)
    now = datetime(2030, 1, 1, 12)
    meeting, _, _ = _create_meeting(
        db_session,
        now + timedelta(hours=24) - timedelta(seconds=30),
        status="CONFIRMED",
    )

    assert reminder_service.process_due_meeting_reminders(db_session, now) == 1
    db_session.refresh(meeting)

    assert meeting.is_reminded_24h is True
    assert db_session.query(Notification).count() == 2


def test_catches_up_missed_24_hour_reminder_for_upcoming_meeting(
    db_session,
    monkeypatch,
):
    _clear_smtp_config(monkeypatch)
    now = datetime(2030, 1, 1, 12)
    meeting, _, _ = _create_meeting(
        db_session,
        now + timedelta(hours=2),
    )

    assert reminder_service.process_due_meeting_reminders(db_session, now) == 1

    db_session.refresh(meeting)
    assert meeting.is_reminded_24h is True
    assert meeting.is_reminded_15m is False
    assert db_session.query(Notification).count() == 2


def test_email_failure_does_not_block_in_app_or_later_reminders(
    db_session,
    monkeypatch,
):
    now = datetime(2030, 1, 1, 12)
    first_meeting, first_organizer, first_participant = _create_meeting(
        db_session,
        now + timedelta(hours=2),
        suffix="1",
    )
    second_meeting, second_organizer, second_participant = _create_meeting(
        db_session,
        now + timedelta(hours=3),
        suffix="2",
    )
    attempted_recipients = []
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "meetings@example.com")
    monkeypatch.setenv("SMTP_PORT", "587")

    def send_email(recipient, subject, content, settings):
        attempted_recipients.append(recipient)
        if recipient == first_participant.email:
            raise OSError("SMTP unavailable")

    monkeypatch.setattr(email_service, "send_email", send_email)

    assert reminder_service.process_due_meeting_reminders(db_session, now) == 2

    db_session.refresh(first_meeting)
    db_session.refresh(second_meeting)
    assert first_meeting.is_reminded_24h is True
    assert second_meeting.is_reminded_24h is True
    assert set(attempted_recipients) == {
        first_organizer.email,
        first_participant.email,
        second_organizer.email,
        second_participant.email,
    }
    assert db_session.query(Notification).count() == 4
    delivery = db_session.query(EmailDelivery).one()
    assert delivery.status == "PENDING"
    assert delivery.attempts == 1
    assert delivery.last_error == "SMTP unavailable"


def test_failed_email_is_retried_and_marked_sent(db_session, monkeypatch):
    now = datetime(2030, 1, 1, 12)
    meeting, _, participant = _create_meeting(
        db_session,
        now + timedelta(hours=2),
        suffix="retry",
    )
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "meetings@example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    def fail_send_for_participant(recipient, subject, content, settings):
        if recipient == participant.email:
            raise OSError("SMTP unavailable")

    monkeypatch.setattr(email_service, "send_email", fail_send_for_participant)

    assert reminder_service.process_due_meeting_reminders(db_session, now) == 1
    delivery = db_session.query(EmailDelivery).filter_by(
        user_id=participant.id
    ).one()
    assert delivery.status == "PENDING"
    assert delivery.attempts == 1

    sent_recipients = []
    monkeypatch.setattr(
        email_service,
        "send_email",
        lambda recipient, subject, content, settings: sent_recipients.append(
            recipient
        ),
    )

    assert (
        reminder_service.process_pending_email_retries(
            db_session,
            now + timedelta(seconds=31),
        )
        == 1
    )
    db_session.refresh(delivery)
    assert delivery.status == "SENT"
    assert delivery.attempts == 2
    assert sent_recipients == [participant.email]


def test_scheduler_lock_skips_a_second_local_worker(monkeypatch):
    from filelock import FileLock

    from app.services.reminder_service import _SCHEDULER_FILE_LOCK, _scheduler_lock

    monkeypatch.setattr(reminder_service.engine.dialect, "name", "sqlite")
    lock = FileLock(_SCHEDULER_FILE_LOCK)
    lock.acquire(timeout=0)
    try:
        with _scheduler_lock() as acquired:
            assert acquired is False
    finally:
        lock.release()


def test_scheduler_lock_falls_back_when_mysql_lock_fails(
    monkeypatch,
    tmp_path,
):
    from app.services.reminder_service import _scheduler_lock

    monkeypatch.setattr(reminder_service.engine.dialect, "name", "mysql")
    monkeypatch.setattr(
        reminder_service.engine,
        "connect",
        lambda: (_ for _ in ()).throw(SQLAlchemyError("permission denied")),
    )
    monkeypatch.setattr(
        reminder_service,
        "_SCHEDULER_FILE_LOCK",
        str(tmp_path / "reminder.lock"),
    )

    with _scheduler_lock() as acquired:
        assert acquired is True


def test_marks_past_confirmed_meetings_completed(db_session, monkeypatch):
    _clear_smtp_config(monkeypatch)
    now = datetime(2030, 1, 1, 12)
    meeting, _, _ = _create_meeting(
        db_session,
        now - timedelta(hours=1),
    )

    assert reminder_service.process_due_meeting_reminders(db_session, now) == 0

    db_session.refresh(meeting)
    assert meeting.status == "COMPLETED"
    assert db_session.query(Notification).count() == 0
