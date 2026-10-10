import asyncio
import logging
import os
import smtplib
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import gettempdir

from filelock import FileLock, Timeout
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.database import SessionLocal, engine
from app.models.email_delivery import EmailDelivery
from app.models.meeting import Meeting, MeetingParticipant
from app.models.notification import Notification
from app.models.user import User
from app.services import email_service


logger = logging.getLogger(__name__)

_VIETNAM_TZ = timezone(timedelta(hours=7))
_SCHEDULER_LOCK_NAME = "meeting_reminder_scheduler"
_MAX_EMAIL_ATTEMPTS = 6
_SCHEDULER_FILE_LOCK = str(
    Path(gettempdir()) / "roomsync-meeting-reminder-scheduler.lock"
)
_REMINDER_WINDOWS = (
    (
        timedelta(hours=24),
        "is_reminded_24h",
        "24 giờ",
        timedelta(minutes=15),
    ),
    (timedelta(minutes=15), "is_reminded_15m", "15 phút", timedelta(0)),
)


def _format_start_time(start_time: datetime) -> str:
    utc_start = (
        start_time.replace(tzinfo=timezone.utc)
        if start_time.tzinfo is None
        else start_time.astimezone(timezone.utc)
    )
    return utc_start.astimezone(_VIETNAM_TZ).strftime("%H:%M %d/%m/%Y")


def process_pending_email_retries(
    db: Session,
    now: datetime | None = None,
) -> int:
    current_time = now or datetime.now(timezone.utc).replace(tzinfo=None)
    if current_time.tzinfo is not None:
        current_time = current_time.astimezone(timezone.utc).replace(tzinfo=None)

    try:
        smtp_settings = email_service.get_smtp_settings()
    except ValueError:
        logger.exception("Invalid SMTP configuration; email retries are deferred")
        return 0
    if smtp_settings is None:
        return 0

    deliveries = (
        db.query(EmailDelivery)
        .filter(
            EmailDelivery.status == "PENDING",
            EmailDelivery.next_attempt_at <= current_time,
            EmailDelivery.attempts < _MAX_EMAIL_ATTEMPTS,
        )
        .order_by(EmailDelivery.next_attempt_at, EmailDelivery.id)
        .with_for_update()
        .all()
    )
    processed = 0
    for delivery in deliveries:
        delivery.attempts += 1
        try:
            email_service.send_email(
                delivery.recipient,
                delivery.subject,
                delivery.content,
                smtp_settings,
            )
        except (OSError, smtplib.SMTPException) as exc:
            delivery.last_error = str(exc)[:1000]
            if delivery.attempts >= _MAX_EMAIL_ATTEMPTS:
                delivery.status = "FAILED"
            else:
                retry_seconds = min(30 * (2 ** (delivery.attempts - 1)), 3600)
                delivery.next_attempt_at = current_time + timedelta(
                    seconds=retry_seconds
                )
            logger.exception(
                "Reminder email retry failed (delivery_id=%s attempt=%s)",
                delivery.id,
                delivery.attempts,
            )
        else:
            delivery.status = "SENT"
            delivery.last_error = None
        processed += 1

    if processed:
        db.commit()
    return processed


def process_due_meeting_reminders(
    db: Session,
    now: datetime | None = None,
    scan_interval: timedelta = timedelta(minutes=1),
) -> int:
    """Send reminders to upcoming meetings awaiting confirmation or already confirmed."""
    if scan_interval <= timedelta(0):
        raise ValueError("scan_interval must be greater than zero")

    current_time = now or datetime.now(timezone.utc).replace(tzinfo=None)
    if current_time.tzinfo is not None:
        current_time = current_time.astimezone(timezone.utc).replace(tzinfo=None)

    completed_count = db.query(Meeting).filter(
        Meeting.status == "CONFIRMED",
        Meeting.end_time < current_time,
    ).update(
        {Meeting.status: "COMPLETED"},
        synchronize_session=False,
    )
    if completed_count:
        db.commit()
    try:
        smtp_settings = email_service.get_smtp_settings()
    except ValueError:
        logger.exception(
            "Invalid SMTP configuration; reminders will be stored in-app only"
        )
        smtp_settings = None
    process_pending_email_retries(db, current_time)
    processed_reminders = 0

    for lead_time, reminder_flag, lead_label, minimum_lead_time in _REMINDER_WINDOWS:
        due_before = current_time + lead_time
        due_after = current_time + minimum_lead_time
        meetings = (
            db.query(Meeting)
            .options(
                joinedload(Meeting.organizer),
                joinedload(Meeting.room),
                selectinload(Meeting.participants).joinedload(MeetingParticipant.user),
            )
            .filter(
                Meeting.status == "CONFIRMED",
                getattr(Meeting, reminder_flag).is_(False),
                Meeting.start_time > due_after,
                Meeting.start_time <= due_before,
            )
            .with_for_update()
            .all()
        )

        flag_name = reminder_flag.removeprefix("is_reminded_")
        for meeting in meetings:
            recipients: dict[int, User] = {}
            if meeting.organizer is not None:
                recipients[meeting.organizer.id] = meeting.organizer
            for participant in meeting.participants:
                if participant.user is not None:
                    recipients[participant.user.id] = participant.user
            if not recipients:
                continue

            start_time = _format_start_time(meeting.start_time)
            title = f"Nhắc họp: {meeting.title} (nhắc trước {lead_label})"
            room_name = (
                meeting.room.name
                if meeting.room is not None
                else (
                    f"Trực tuyến ({meeting.online_link})"
                    if meeting.meeting_type == "online" and meeting.online_link
                    else "Chưa xác định"
                )
            )
            meeting_url = (
                os.getenv("FRONTEND_BASE_URL", "http://localhost:3000").rstrip("/")
                + f"/dashboard.html?meeting_id={meeting.id}"
            )
            content = (
                f"Đây là lời nhắc được thiết lập trước {lead_label}. "
                f"Cuộc họp '{meeting.title}' bắt đầu lúc {start_time} "
                f"(giờ Việt Nam) tại {room_name}. "
                f"Chi tiết cuộc họp: {meeting_url}"
            )

            for user in recipients.values():
                db.add(
                    Notification(
                        user_id=user.id,
                        meeting_id=meeting.id,
                        title=title,
                        content=content,
                    )
                )

            setattr(meeting, reminder_flag, True)
            db.commit()
            processed_reminders += 1

            for user in recipients.values():
                if smtp_settings is None:
                    logger.info(
                        "SMTP is not configured; sending in-app reminder only "
                        "for meeting_id=%s user_id=%s",
                        meeting.id,
                        user.id,
                    )
                elif user.email:
                    try:
                        email_service.send_email(
                            user.email,
                            title,
                            content,
                            smtp_settings,
                        )
                    except (OSError, smtplib.SMTPException) as exc:
                        logger.exception(
                            "Meeting reminder email failed "
                            "(meeting_id=%s user_id=%s)",
                            meeting.id,
                            user.id,
                        )
                        existing = (
                            db.query(EmailDelivery)
                            .filter_by(
                                meeting_id=meeting.id,
                                user_id=user.id,
                                reminder_type=flag_name,
                            )
                            .one_or_none()
                        )
                        if existing is None:
                            db.add(
                                EmailDelivery(
                                    meeting_id=meeting.id,
                                    user_id=user.id,
                                    reminder_type=flag_name,
                                    recipient=user.email,
                                    subject=title,
                                    content=content,
                                    attempts=1,
                                    next_attempt_at=(
                                        current_time + timedelta(seconds=30)
                                    ),
                                    last_error=str(exc)[:1000],
                                )
                            )
                            db.commit()
                else:
                    logger.warning(
                        "Skipping reminder email because user has no email address "
                        "(meeting_id=%s user_id=%s)",
                        meeting.id,
                        user.id,
                    )
    return processed_reminders


@contextmanager
def _scheduler_lock():
    if engine.dialect.name == "mysql":
        connection = None
        try:
            connection = engine.connect()
            acquired = connection.execute(
                text("SELECT GET_LOCK(:lock_name, 0)"),
                {"lock_name": _SCHEDULER_LOCK_NAME},
            ).scalar()
        except SQLAlchemyError:
            logger.exception(
                "MySQL reminder lock failed; falling back to a file lock"
            )
            if connection is not None:
                connection.close()
            connection = None
        else:
            if acquired == 0:
                connection.close()
                yield False
                return
            if acquired == 1:
                try:
                    yield True
                finally:
                    try:
                        connection.execute(
                            text("SELECT RELEASE_LOCK(:lock_name)"),
                            {"lock_name": _SCHEDULER_LOCK_NAME},
                        )
                    finally:
                        connection.close()
                return
            logger.warning(
                "MySQL GET_LOCK returned NULL; falling back to a file lock"
            )
            connection.close()

    lock = FileLock(_SCHEDULER_FILE_LOCK)
    try:
        lock.acquire(timeout=0)
    except Timeout:
        yield False
        return

    try:
        yield True
    finally:
        lock.release()


def _scan_for_due_meeting_reminders() -> None:
    with _scheduler_lock() as acquired:
        if not acquired:
            logger.debug("Another worker owns the meeting reminder scheduler lock")
            return
        db = SessionLocal()
        try:
            process_due_meeting_reminders(db)
        finally:
            db.close()


async def run_meeting_reminder_scheduler() -> None:
    """Poll for reminders without blocking FastAPI's event loop."""
    while True:
        try:
            await asyncio.to_thread(_scan_for_due_meeting_reminders)
        except (SQLAlchemyError, smtplib.SMTPException, OSError, ValueError):
            logger.exception("Meeting reminder scan failed; it will retry shortly")
        await asyncio.sleep(30)
