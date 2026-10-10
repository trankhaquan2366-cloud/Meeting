import logging
import os
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


def load_environment() -> None:
    """Load project environment variables without overriding process settings."""
    load_dotenv(dotenv_path=ENV_FILE, override=False)


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
