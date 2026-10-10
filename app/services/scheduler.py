"""Periodic meeting lifecycle jobs."""

import logging
import os
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.meeting import Meeting, MeetingParticipant
from app.models.notification import Notification
from app.models.user import User

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _meeting_recipients(db: Session, meeting: Meeting, accepted_only: bool) -> list[User]:
    users: dict[int, User] = {}
    if meeting.organizer is not None:
        users[meeting.organizer.id] = meeting.organizer
    participants = db.query(MeetingParticipant).filter(
        MeetingParticipant.meeting_id == meeting.id
    ).all()
    for participant in participants:
        if accepted_only and (participant.response_status or "").casefold() != "accepted":
            continue
        if participant.user is not None:
            users[participant.user.id] = participant.user
    return list(users.values())


def _send_meeting_email(recipients: list[User], subject: str, body: str) -> None:
    host = os.getenv("SMTP_HOST")
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("SMTP_FROM_EMAIL") or username
    if not all((host, username, password, from_email)):
        logger.warning("Meeting lifecycle email skipped: SMTP settings are incomplete")
        return

    port = int(os.getenv("SMTP_PORT", "587"))
    use_starttls = os.getenv("SMTP_STARTTLS", "true").strip().casefold() in {
        "1", "true", "yes",
    }
    for user in recipients:
        if not user.email:
            logger.warning("Meeting lifecycle email skipped: user_id=%s has no email", user.id)
            continue
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = from_email
        message["To"] = user.email
        message.set_content(f"Chào {user.full_name or user.username},\n\n{body}")
        try:
            with smtplib.SMTP(host, port, timeout=20) as smtp:
                smtp.ehlo()
                if use_starttls:
                    smtp.starttls(context=ssl.create_default_context())
                    smtp.ehlo()
                smtp.login(username, password)
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException):
            logger.exception("Meeting lifecycle email failed for user_id=%s", user.id)


def process_meeting_reminders(db: Session, now: datetime | None = None) -> int:
    """Notify organizers and confirmed attendees during the check-in window."""
    current_time = now or _utc_now()
    meetings = (
        db.query(Meeting)
        .filter(
            func.upper(Meeting.status) == "SCHEDULED",
            Meeting.reminder_sent.is_(False),
            Meeting.start_time <= current_time,
            Meeting.start_time > current_time - timedelta(minutes=15),
        )
        .all()
    )
    for meeting in meetings:
        recipients = _meeting_recipients(db, meeting, accepted_only=True)
        for user in recipients:
            db.add(
                Notification(
                    user_id=user.id,
                    title="Nhắc check-in cuộc họp",
                    content=(
                        f"Cuộc họp '{meeting.title}' đã bắt đầu. "
                        "Vui lòng quét mã QR của phòng để check-in."
                    ),
                )
            )
        meeting.reminder_sent = True

    if meetings:
        try:
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Failed to process meeting reminders")
            raise
    return len(meetings)


def process_no_show_meetings(db: Session, now: datetime | None = None) -> int:
    """Cancel meetings that have not been checked in within the grace period."""
    current_time = now or _utc_now()
    meetings = (
        db.query(Meeting)
        .filter(
            func.upper(Meeting.status) == "SCHEDULED",
            Meeting.check_in_time.is_(None),
            Meeting.start_time <= current_time - timedelta(minutes=15),
        )
        .all()
    )
    recipients_by_meeting: list[tuple[Meeting, list[User]]] = []
    for meeting in meetings:
        recipients_by_meeting.append(
            (meeting, _meeting_recipients(db, meeting, accepted_only=False))
        )
        meeting.status = "CANCELLED_NO_SHOW"
        meeting.cancellation_reason = "Tự động hủy do quá 15 phút không check-in"
        meeting.cancelled_at = current_time

    if meetings:
        try:
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Failed to cancel no-show meetings")
            raise

    for meeting, recipients in recipients_by_meeting:
        _send_meeting_email(
            recipients,
            "Cuộc họp đã bị hủy do không check-in",
            (
                f"Cuộc họp '{meeting.title}' đã bị hủy vì không có check-in "
                "trong vòng 15 phút kể từ giờ bắt đầu."
            ),
        )
    return len(meetings)


def process_auto_checkouts(db: Session, now: datetime | None = None) -> int:
    """Complete in-progress meetings after their scheduled end time."""
    current_time = now or _utc_now()
    meetings = (
        db.query(Meeting)
        .filter(
            func.upper(Meeting.status) == "IN_PROGRESS",
            Meeting.end_time <= current_time,
        )
        .all()
    )
    for meeting in meetings:
        meeting.status = "COMPLETED"
        meeting.check_out_time = meeting.end_time

    if meetings:
        try:
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Failed to process automatic meeting check-outs")
            raise
    return len(meetings)
