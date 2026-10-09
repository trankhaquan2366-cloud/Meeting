import base64
import hashlib
import hmac
import logging
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import SECRET_KEY
from app.models.google_calendar_event import GoogleCalendarEvent
from app.models.meeting import Meeting, MeetingParticipant
from app.models.user import User

logger = logging.getLogger(__name__)
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"


def _fernet() -> Fernet:
    key = os.getenv("GOOGLE_TOKEN_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("GOOGLE_TOKEN_ENCRYPTION_KEY is not configured")
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise RuntimeError("GOOGLE_TOKEN_ENCRYPTION_KEY must be a valid Fernet key") from exc


def encrypt_refresh_token(refresh_token: str) -> str:
    return _fernet().encrypt(refresh_token.encode("utf-8")).decode("ascii")


def decrypt_refresh_token(encrypted_token: str) -> str:
    try:
        return _fernet().decrypt(encrypted_token.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeEncodeError) as exc:
        raise RuntimeError("Stored Google refresh token cannot be decrypted") from exc


def make_calendar_consent_url(user: User) -> str:
    if not user.email:
        raise ValueError("Calendar consent requires a user email")
    expires = int(datetime.now(timezone.utc).timestamp()) + 7 * 24 * 60 * 60
    message = f"{user.id}:{user.email.strip().lower()}:{expires}"
    signature = hmac.new(
        SECRET_KEY.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    backend_url = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000").rstrip("/")
    query = urlencode({"user_id": user.id, "expires": expires, "signature": signature})
    return f"{backend_url}/api/auth/google/calendar/connect?{query}"


def verify_calendar_consent_signature(user: User, expires: int, signature: str) -> bool:
    import time

    if expires < int(time.time()) or not user.email:
        return False
    message = f"{user.id}:{user.email.strip().lower()}:{expires}"
    expected = hmac.new(
        SECRET_KEY.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def _google_config() -> tuple[str, str]:
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("Google OAuth client credentials are not configured")
    return client_id, client_secret


def _access_token(refresh_token: str) -> str:
    client_id, client_secret = _google_config()
    response = httpx.post(
        GOOGLE_TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=15,
    )
    response.raise_for_status()
    access_token = response.json().get("access_token")
    if not access_token:
        raise RuntimeError("Google did not return an access token")
    return access_token


def _local_datetime(value: datetime) -> datetime:
    timezone_name = os.getenv("APP_TIMEZONE", "Asia/Ho_Chi_Minh")
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        zone = timezone(timedelta(hours=7))
    if value.tzinfo is None:
        return value.replace(tzinfo=zone)
    return value.astimezone(zone)


def _timezone_name() -> str:
    timezone_name = os.getenv("APP_TIMEZONE", "Asia/Ho_Chi_Minh")
    try:
        ZoneInfo(timezone_name)
        return timezone_name
    except ZoneInfoNotFoundError:
        return "Asia/Ho_Chi_Minh"


def _google_event_id(user_id: int, meeting_id: int) -> str:
    digest = hashlib.sha256(f"{user_id}:{meeting_id}".encode("ascii")).digest()
    return base64.b32hexencode(digest).decode("ascii").rstrip("=").lower()


def _event_payload(user_id: int, meeting: Meeting) -> dict:
    room = meeting.room
    if meeting.meeting_type == "online":
        location = meeting.meeting_link or ""
    elif room:
        location = " - ".join(part for part in (room.name, room.location) if part)
    else:
        location = ""

    details = [meeting.description or ""]
    if meeting.meeting_type == "online" and meeting.meeting_link:
        details.append(f"Meeting link: {meeting.meeting_link}")
    description = "\n".join(part for part in details if part)
    start = _local_datetime(meeting.start_time)
    end = _local_datetime(meeting.end_time)
    return {
        "id": _google_event_id(user_id, meeting.id),
        "summary": meeting.title,
        "description": description,
        "location": location,
        "start": {"dateTime": start.isoformat(), "timeZone": _timezone_name()},
        "end": {"dateTime": end.isoformat(), "timeZone": _timezone_name()},
    }


def sync_user_meetings_to_google(user_id: int) -> None:
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
        if not user or not user.google_refresh_token:
            return
        try:
            refresh_token = decrypt_refresh_token(user.google_refresh_token)
            access_token = _access_token(refresh_token)
        except (RuntimeError, httpx.HTTPError) as exc:
            logger.warning("Google Calendar authorization unavailable for user_id=%s: %s", user_id, exc)
            return

        meetings = (
            db.query(Meeting)
            .join(MeetingParticipant, MeetingParticipant.meeting_id == Meeting.id)
            .filter(
                MeetingParticipant.user_id == user_id,
                Meeting.status.notin_(["CANCELLED", "canceled"]),
            )
            .order_by(Meeting.start_time)
            .all()
        )
        existing_meeting_ids = {
            row[0]
            for row in db.query(GoogleCalendarEvent.meeting_id)
            .filter(GoogleCalendarEvent.user_id == user_id)
            .all()
        }
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        for meeting in meetings:
            if meeting.id in existing_meeting_ids:
                continue
            google_event_id = _google_event_id(user_id, meeting.id)
            try:
                response = httpx.post(
                    GOOGLE_EVENTS_URL,
                    headers=headers,
                    json=_event_payload(user_id, meeting),
                    timeout=15,
                )
                if response.status_code == 409:
                    pass
                else:
                    response.raise_for_status()
                db.add(
                    GoogleCalendarEvent(
                        user_id=user_id,
                        meeting_id=meeting.id,
                        google_event_id=google_event_id,
                    )
                )
                db.commit()
                existing_meeting_ids.add(meeting.id)
            except (httpx.HTTPError, RuntimeError):
                db.rollback()
                logger.exception(
                    "Could not sync meeting_id=%s to Google Calendar for user_id=%s",
                    meeting.id,
                    user_id,
                )
    finally:
        db.close()


def delete_google_calendar_event(user: User, google_event_id: str) -> bool:
    """Delete one event from the connected user's primary Google Calendar."""
    if not user.google_refresh_token:
        logger.warning(
            "Cannot delete Google event %s: user_id=%s has no refresh token",
            google_event_id,
            user.id,
        )
        return False

    try:
        refresh_token = decrypt_refresh_token(user.google_refresh_token)
        client_id, client_secret = _google_config()
        credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri=GOOGLE_TOKEN_URL,
            client_id=client_id,
            client_secret=client_secret,
            scopes=["https://www.googleapis.com/auth/calendar.events"],
        )
        credentials.refresh(GoogleAuthRequest())
        service = build("calendar", "v3", credentials=credentials, cache_discovery=False)
        service.events().delete(
            calendarId="primary",
            eventId=google_event_id,
        ).execute()
        return True
    except HttpError as exc:
        response_status = getattr(getattr(exc, "resp", None), "status", None)
        if response_status in {404, 410}:
            logger.warning(
                "Google event %s is already deleted (HTTP %s) for user_id=%s",
                google_event_id,
                response_status,
                user.id,
            )
            return True
        logger.exception(
            "Failed to delete Google event %s for user_id=%s (HTTP %s)",
            google_event_id,
            user.id,
            response_status,
        )
        return False
    except Exception:
        logger.exception(
            "Failed to delete Google event %s for user_id=%s",
            google_event_id,
            user.id,
        )
        return False


def delete_google_events_for_meeting(meeting_id: int) -> None:
    """Delete tracked attendee events and retain mappings if Google is unavailable."""
    db: Session = SessionLocal()
    try:
        event_records = (
            db.query(GoogleCalendarEvent)
            .filter(GoogleCalendarEvent.meeting_id == meeting_id)
            .all()
        )
        for event_record in event_records:
            user = db.query(User).filter(User.id == event_record.user_id).first()
            if user is None:
                db.delete(event_record)
                continue
            if delete_google_calendar_event(user, event_record.google_event_id):
                db.delete(event_record)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Could not process Google events for meeting_id=%s", meeting_id)
    finally:
        db.close()
