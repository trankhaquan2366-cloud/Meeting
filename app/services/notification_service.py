import logging
import smtplib

from app.core.database import SessionLocal
from app.models.notification import Notification
from app.models.user import User
from app.services import email_service


logger = logging.getLogger(__name__)


def send_meeting_notification_task(
    recipient_ids: list[int],
    subject: str,
    content: str,
) -> None:
    db = SessionLocal()
    try:
        recipients = (
            db.query(User)
            .filter(User.id.in_(set(recipient_ids)), User.is_active.is_(True))
            .all()
        )
        if not recipients:
            return

        db.add_all(
            Notification(user_id=user.id, title=subject, content=content)
            for user in recipients
        )
        db.commit()

        smtp_settings = email_service.get_smtp_settings()
        if smtp_settings is None:
            logger.info(
                "SMTP is not configured; meeting notification is in-app only "
                "(recipient_count=%s)",
                len(recipients),
            )
            return

        failed_recipients: list[str] = []
        for user in recipients:
            if not user.email:
                logger.warning(
                    "Skipping meeting email because user has no email address "
                    "(user_id=%s)",
                    user.id,
                )
                continue
            try:
                email_service.send_email(
                    user.email,
                    subject,
                    content,
                    smtp_settings,
                )
            except (OSError, smtplib.SMTPException):
                failed_recipients.append(user.email)
                logger.exception(
                    "Meeting notification email failed (user_id=%s)",
                    user.id,
                )
        if failed_recipients:
            raise RuntimeError(
                "Meeting email notification failed for "
                + ", ".join(failed_recipients)
            )
    finally:
        db.close()
