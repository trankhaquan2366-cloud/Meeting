import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
DEFAULT_MODEL = "gemini-3.8-flash"


@dataclass(frozen=True)
class SMTPSettings:
    host: str
    port: int
    username: str | None
    password: str | None
    from_email: str | None
    starttls: bool


@dataclass(frozen=True)
class GeminiSettings:
    api_key: str | None
    model: str


def load_environment() -> None:
    """Load project environment variables without overriding process settings."""
    load_dotenv(dotenv_path=ENV_FILE, override=False)


def get_gemini_settings() -> GeminiSettings:
    load_environment()
    api_key = next(
        (
            value.strip()
            for value in (os.getenv("GEMINI_API_KEY"), os.getenv("GOOGLE_API_KEY"))
            if value and value.strip()
        ),
        None,
    )
    return GeminiSettings(
        api_key=api_key,
        model=os.getenv("GEMINI_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
    )


def get_smtp_settings() -> SMTPSettings | None:
    load_environment()
    try:
        port = int(os.getenv("SMTP_PORT", "587"))
    except ValueError:
        logger.error("SMTP_PORT must be a valid integer")
        return None

    username = os.getenv("SMTP_USER") or os.getenv("SMTP_USERNAME")
    return SMTPSettings(
        host=os.getenv("SMTP_HOST") or "smtp.gmail.com",
        port=port,
        username=username,
        password=os.getenv("SMTP_PASSWORD"),
        from_email=os.getenv("EMAILS_FROM_EMAIL") or os.getenv("SMTP_FROM_EMAIL") or username,
        starttls=os.getenv("SMTP_STARTTLS", "true").strip().casefold() in {"1", "true", "yes"},
    )


def get_google_oauth_credentials() -> tuple[str, str] | None:
    load_environment()
    credentials = {
        "GOOGLE_CLIENT_ID": os.getenv("GOOGLE_CLIENT_ID"),
        "GOOGLE_CLIENT_SECRET": os.getenv("GOOGLE_CLIENT_SECRET"),
    }
    invalid_variables = [
        name
        for name, value in credentials.items()
        if (
            not value
            or not value.strip()
            or value.strip().lower().startswith(("your_", "your-", "replace_", "replace-"))
            or "placeholder" in value.strip().lower()
        )
    ]
    if invalid_variables:
        logger.error(
            "Google OAuth is not configured; missing or placeholder environment variable(s): %s",
            ", ".join(invalid_variables),
        )
        return None

    client_id = credentials["GOOGLE_CLIENT_ID"]
    client_secret = credentials["GOOGLE_CLIENT_SECRET"]
    assert client_id is not None and client_secret is not None
    return client_id, client_secret


load_environment()
