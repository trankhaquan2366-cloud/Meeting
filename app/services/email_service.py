import logging
import os
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SMTPSettings:
    host: str
    port: int
    sender: str
    username: str | None
    password: str | None


def get_smtp_settings() -> SMTPSettings | None:
    host = os.getenv("SMTP_HOST")
    sender = os.getenv("SMTP_FROM_EMAIL")
    username = os.getenv("SMTP_USERNAME") or os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    if password:
        password = password.replace(" ", "")

    if not any((host, sender, username, password)):
        return None
    if not host or not sender:
        raise ValueError(
            "SMTP_HOST and SMTP_FROM_EMAIL are required to enable email"
        )
    if bool(username) != bool(password):
        raise ValueError("SMTP_USERNAME and SMTP_PASSWORD must be configured together")

    return SMTPSettings(
        host=host,
        port=int(os.getenv("SMTP_PORT", "587")),
        sender=sender,
        username=username,
        password=password,
    )


def send_email(
    recipient: str,
    subject: str,
    content: str,
    settings: SMTPSettings,
) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.sender
    message["To"] = recipient
    message.set_content(content)

    try:
        with smtplib.SMTP(settings.host, settings.port, timeout=10) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            if settings.username and settings.password:
                smtp.login(settings.username, settings.password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException):
        logger.exception("Failed to send meeting email (recipient=%s)", recipient)
        raise
