import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.meeting import Meeting, MeetingParticipant
from app.models.user import User
from app.services.google_calendar_service import make_calendar_consent_url, sync_user_meetings_to_google

logger = logging.getLogger(__name__)


def _send_calendar_consent_email(user: User, meetings: list[Meeting]) -> None:
    host = os.getenv("SMTP_HOST")
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("SMTP_FROM_EMAIL") or username
    if not all((host, username, password, from_email)):
        logger.warning("Calendar permission email skipped: SMTP settings are incomplete")
        return

    try:
        consent_url = make_calendar_consent_url(user)
    except ValueError:
        logger.warning("Calendar permission email skipped: user_id=%s has no email", user.id)
        return

    meeting_lines = []
    for meeting in meetings:
        start_time = meeting.start_time.strftime("%d/%m/%Y %H:%M")
        meeting_lines.append(f"- {meeting.title} — {start_time}")

    message = EmailMessage()
    message["Subject"] = "Kết nối Google Calendar với RoomSync"
    message["From"] = from_email
    message["To"] = user.email
    message.set_content(
        f"Chào {user.full_name or user.username},\n\n"
        "Bạn được mời tham dự các cuộc họp sau trong RoomSync:\n"
        f"{chr(10).join(meeting_lines)}\n\n"
        "Để các cuộc họp được tự động thêm vào Google Calendar của bạn, hãy mở liên kết dưới đây "
        "và cấp quyền Calendar cho RoomSync. Google sẽ yêu cầu bạn xác nhận tài khoản trước khi cấp quyền.\n\n"
        f"{consent_url}\n\n"
        "Liên kết có hiệu lực trong 7 ngày và chỉ dùng để kết nối tài khoản có email đăng ký trong RoomSync.\n"
        "Nếu bạn không mong đợi email này, có thể bỏ qua."
    )

    port = int(os.getenv("SMTP_PORT", "587"))
    use_starttls = os.getenv("SMTP_STARTTLS", "true").strip().lower() in {"1", "true", "yes"}
    try:
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            smtp.ehlo()
            if use_starttls:
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
            smtp.login(username, password)
            smtp.send_message(message)
        logger.info("Calendar permission email sent to user_id=%s", user.id)
    except (OSError, smtplib.SMTPException):
        logger.exception("Calendar permission email failed for user_id=%s", user.id)


def request_calendar_access_for_invitees(user_ids: list[int], meeting_ids: list[int]) -> None:
    """Email unconnected invitees or sync their existing invited meetings."""
    unique_user_ids = list(dict.fromkeys(user_ids))
    unique_meeting_ids = list(dict.fromkeys(meeting_ids))
    if not unique_user_ids or not unique_meeting_ids:
        return

    db: Session = SessionLocal()
    try:
        meetings_by_user = {}
        for user_id in unique_user_ids:
            user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
            if not user:
                continue
            meetings = (
                db.query(Meeting)
                .join(MeetingParticipant, MeetingParticipant.meeting_id == Meeting.id)
                .filter(
                    MeetingParticipant.user_id == user_id,
                    Meeting.id.in_(unique_meeting_ids),
                    Meeting.status.notin_(["CANCELLED", "canceled"]),
                )
                .order_by(Meeting.start_time)
                .all()
            )
            if meetings:
                meetings_by_user[user_id] = (user, meetings)
    finally:
        db.close()

    for user, meetings in meetings_by_user.values():
        if user.google_refresh_token:
            sync_user_meetings_to_google(user.id)
        else:
            _send_calendar_consent_email(user, meetings)
