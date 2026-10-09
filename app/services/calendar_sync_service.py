import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote

import httpx
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.database import SessionLocal
from app.core.meeting_events import (
    EVENT_MEETING_CANCELLED,
    EVENT_MEETING_CREATED,
    EVENT_MEETING_UPDATED,
)
from app.models.calendar import UserCalendarEvent, UserCalendarToken
from app.models.meeting import Meeting, MeetingParticipant
from app.models.user import User


logger = logging.getLogger(__name__)

_TOKEN_REFRESH_MARGIN = timedelta(minutes=2)
_ENV_ALIASES = {
    "MICROSOFT_CLIENT_ID": "OUTLOOK_CLIENT_ID",
    "MICROSOFT_CLIENT_SECRET": "OUTLOOK_CLIENT_SECRET",
}
_PROVIDER_CONFIG = {
    "google": {
        "client_id_env": "GOOGLE_CLIENT_ID",
        "client_secret_env": "GOOGLE_CLIENT_SECRET",
        "token_url": "https://oauth2.googleapis.com/token",
        "events_url": "https://www.googleapis.com/calendar/v3/calendars/primary/events",
    },
    "outlook": {
        "client_id_env": "MICROSOFT_CLIENT_ID",
        "client_secret_env": "MICROSOFT_CLIENT_SECRET",
        "token_url": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "events_url": "https://graph.microsoft.com/v1.0/me/events",
    },
}


def _get_provider_setting(name: str) -> str | None:
    return os.getenv(name) or os.getenv(_ENV_ALIASES.get(name, ""))


class CalendarSyncError(RuntimeError):
    """Raised when provider credentials or calendar synchronization fail."""


def _get_fernet() -> Fernet:
    key = os.getenv("CALENDAR_TOKEN_ENCRYPTION_KEY")
    if not key:
        raise CalendarSyncError("CALENDAR_TOKEN_ENCRYPTION_KEY is not configured")
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise CalendarSyncError(
            "CALENDAR_TOKEN_ENCRYPTION_KEY must be a valid Fernet key"
        ) from exc


def _encrypt_token(token: str) -> str:
    return _get_fernet().encrypt(token.encode("utf-8")).decode("ascii")


def _decrypt_token(token: str) -> str:
    try:
        return _get_fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeEncodeError) as exc:
        raise CalendarSyncError("Stored calendar token cannot be decrypted") from exc


def store_authorized_tokens(
    db: Session,
    user_id: int,
    provider: str,
    token_data: dict[str, Any],
) -> UserCalendarToken:
    if provider not in _PROVIDER_CONFIG:
        raise ValueError(f"Unsupported calendar provider: {provider}")

    access_token = token_data.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise CalendarSyncError("OAuth response did not include an access token")

    refresh_token = token_data.get("refresh_token")
    if refresh_token is not None and not isinstance(refresh_token, str):
        raise CalendarSyncError("OAuth response contained an invalid refresh token")

    expires_in = token_data.get("expires_in")
    expires_at = None
    if expires_in is not None:
        try:
            expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
                seconds=int(expires_in)
            )
        except (TypeError, ValueError) as exc:
            raise CalendarSyncError("OAuth response contained an invalid expires_in") from exc

    token = (
        db.query(UserCalendarToken)
        .filter_by(user_id=user_id, provider=provider)
        .one_or_none()
    )
    if token is None:
        token = UserCalendarToken(user_id=user_id, provider=provider)

    token.access_token = _encrypt_token(access_token)
    if refresh_token:
        token.refresh_token = _encrypt_token(refresh_token)
    token.expires_at = expires_at
    token.is_active = True
    db.add(token)
    db.commit()
    db.refresh(token)
    return token


def get_valid_access_token(user_id: int, provider: str) -> str:
    if provider not in _PROVIDER_CONFIG:
        raise ValueError(f"Unsupported calendar provider: {provider}")

    db = SessionLocal()
    try:
        token = (
            db.query(UserCalendarToken)
            .filter_by(user_id=user_id, provider=provider, is_active=True)
            .with_for_update()
            .one_or_none()
        )
        if token is None:
            raise CalendarSyncError(
                f"No active {provider} calendar connection for user {user_id}"
            )

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if token.expires_at is None or token.expires_at > now + _TOKEN_REFRESH_MARGIN:
            return _decrypt_token(token.access_token)

        if not token.refresh_token:
            raise CalendarSyncError(
                f"The {provider} connection for user {user_id} has expired and "
                "does not have a refresh token"
            )

        config = _PROVIDER_CONFIG[provider]
        client_id = _get_provider_setting(config["client_id_env"])
        client_secret = _get_provider_setting(config["client_secret_env"])
        if not client_id or not client_secret:
            client_id_alias = _ENV_ALIASES.get(config["client_id_env"])
            client_secret_alias = _ENV_ALIASES.get(config["client_secret_env"])
            client_id_label = (
                f"{config['client_id_env']} or {client_id_alias}"
                if client_id_alias
                else config["client_id_env"]
            )
            client_secret_label = (
                f"{config['client_secret_env']} or {client_secret_alias}"
                if client_secret_alias
                else config["client_secret_env"]
            )
            raise CalendarSyncError(
                f"{client_id_label} and {client_secret_label} "
                "must be configured to refresh calendar tokens"
            )

        form_data = {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": _decrypt_token(token.refresh_token),
            "grant_type": "refresh_token",
        }
        if provider == "outlook":
            form_data["scope"] = (
                "offline_access https://graph.microsoft.com/Calendars.ReadWrite"
            )

        try:
            response = httpx.post(
                config["token_url"],
                data=form_data,
                timeout=15.0,
            )
            response.raise_for_status()
            token_data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.exception(
                "Failed to refresh %s calendar token for user_id=%s",
                provider,
                user_id,
            )
            raise CalendarSyncError(
                f"Could not refresh {provider} calendar access token"
            ) from exc

        new_access_token = token_data.get("access_token")
        if not isinstance(new_access_token, str) or not new_access_token:
            raise CalendarSyncError(
                f"{provider} refresh response did not include an access token"
            )
        token.access_token = _encrypt_token(new_access_token)

        new_refresh_token = token_data.get("refresh_token")
        if new_refresh_token:
            if not isinstance(new_refresh_token, str):
                raise CalendarSyncError(
                    f"{provider} refresh response contained an invalid refresh token"
                )
            token.refresh_token = _encrypt_token(new_refresh_token)

        expires_in = token_data.get("expires_in")
        if expires_in is not None:
            try:
                token.expires_at = now + timedelta(seconds=int(expires_in))
            except (TypeError, ValueError) as exc:
                raise CalendarSyncError(
                    f"{provider} refresh response contained an invalid expires_in"
                ) from exc

        db.commit()
        return new_access_token
    finally:
        db.close()


def _meeting_event_payload(
    meeting: Meeting,
    provider: str,
    recurrence_count: int | None = None,
) -> dict[str, Any]:
    start_time = meeting.start_time.replace(tzinfo=timezone.utc)
    end_time = meeting.end_time.replace(tzinfo=timezone.utc)
    description = meeting.description or ""
    if meeting.participants:
        attendee_names = [
            participant.user.full_name or participant.user.username
            for participant in meeting.participants
            if participant.user is not None
        ]
        if attendee_names:
            description = "\n".join(
                part
                for part in (
                    description,
                    "RoomSync participants: " + ", ".join(attendee_names),
                )
                if part
            )

    if provider == "google":
        payload: dict[str, Any] = {
            "summary": meeting.title,
            "description": description,
            "start": {"dateTime": start_time.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end_time.isoformat(), "timeZone": "UTC"},
        }
        if meeting.meeting_type == "online" and meeting.online_link:
            payload["location"] = meeting.online_link
        elif meeting.room is not None:
            payload["location"] = meeting.room.name
        if recurrence_count and recurrence_count > 1:
            frequency = "WEEKLY" if meeting.recurring_type == "weekly" else "MONTHLY"
            interval = ""
            if meeting.recurring_type == "monthly":
                interval = f";BYMONTHDAY={meeting.start_time.day}"
            elif meeting.recurring_type == "until_changed":
                frequency = "DAILY"
                interval = ";INTERVAL=30"
            payload["recurrence"] = [
                f"RRULE:FREQ={frequency}{interval};COUNT={recurrence_count}"
            ]
        return payload

    location = meeting.online_link if meeting.meeting_type == "online" else None
    if not location and meeting.room is not None:
        location = meeting.room.name
    payload = {
        "subject": meeting.title,
        "body": {"contentType": "text", "content": description},
        "start": {"dateTime": start_time.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": end_time.isoformat(), "timeZone": "UTC"},
        "location": {"displayName": location or ""},
    }
    if recurrence_count and recurrence_count > 1:
        if meeting.recurring_type == "weekly":
            pattern = {
                "type": "weekly",
                "interval": 1,
                "daysOfWeek": [meeting.start_time.strftime("%A").lower()],
                "firstDayOfWeek": "sunday",
            }
        elif meeting.recurring_type == "until_changed":
            pattern = {"type": "daily", "interval": 30}
        else:
            pattern = {
                "type": "absoluteMonthly",
                "interval": 1,
                "dayOfMonth": meeting.start_time.day,
            }
        payload["recurrence"] = {
            "pattern": pattern,
            "range": {
                "type": "numbered",
                "startDate": meeting.start_time.date().isoformat(),
                "numberOfOccurrences": recurrence_count,
            },
        }
    return payload


def _provider_event_request(
    provider: str,
    access_token: str,
    method: str,
    event_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> str | None:
    if provider not in _PROVIDER_CONFIG:
        raise ValueError(f"Unsupported calendar provider: {provider}")
    url = _PROVIDER_CONFIG[provider]["events_url"]
    if event_id:
        url = f"{url}/{quote(event_id, safe='')}"
    try:
        response = httpx.request(
            method,
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            json=payload,
            timeout=20.0,
        )
        if method == "DELETE" and response.status_code == 404:
            return None
        response.raise_for_status()
        if method == "DELETE":
            return None
        response_data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.exception("Calendar provider request failed (provider=%s method=%s)", provider, method)
        raise CalendarSyncError(
            f"{provider} calendar event request failed ({method})"
        ) from exc

    returned_event_id = response_data.get("id")
    if method == "POST" and (
        not isinstance(returned_event_id, str) or not returned_event_id
    ):
        raise CalendarSyncError(
            f"{provider} did not return an ID for the created calendar event"
        )
    return returned_event_id if isinstance(returned_event_id, str) else event_id


def _parse_provider_datetime(value: Any) -> datetime | None:
    if isinstance(value, dict):
        value = value.get("dateTime")
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _get_occurrence_event_id(
    provider: str,
    access_token: str,
    series_event_id: str,
    original_start: datetime,
) -> str | None:
    if provider not in _PROVIDER_CONFIG:
        raise ValueError(f"Unsupported calendar provider: {provider}")
    original_start_utc = original_start.replace(tzinfo=timezone.utc)
    query_start = (original_start_utc - timedelta(days=2)).isoformat()
    query_end = (original_start_utc + timedelta(days=2)).isoformat()
    url = (
        f"{_PROVIDER_CONFIG[provider]['events_url']}/"
        f"{quote(series_event_id, safe='')}/instances"
    )
    params = (
        {"timeMin": query_start, "timeMax": query_end, "maxResults": 100}
        if provider == "google"
        else {
            "startDateTime": query_start,
            "endDateTime": query_end,
            "$top": 100,
        }
    )
    try:
        response = httpx.get(
            url,
            params=params,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=20.0,
        )
        response.raise_for_status()
        instances = response.json().get(
            "items" if provider == "google" else "value",
            [],
        )
    except (httpx.HTTPError, ValueError) as exc:
        logger.exception(
            "Failed to find recurring event instance "
            "(provider=%s series_event_id=%s)",
            provider,
            series_event_id,
        )
        raise CalendarSyncError(
            f"Could not find {provider} recurring calendar event instance"
        ) from exc

    for instance in instances:
        original_start_value = instance.get(
            "originalStartTime" if provider == "google" else "originalStart"
        )
        instance_start = _parse_provider_datetime(original_start_value)
        instance_id = instance.get("id")
        if (
            instance_start is not None
            and abs((instance_start - original_start_utc).total_seconds()) <= 1
            and isinstance(instance_id, str)
            and instance_id
        ):
            return instance_id
    return None


def _event_id_for_meeting(
    meeting: Meeting,
    event_link: UserCalendarEvent,
    provider: str,
    access_token: str,
) -> str | None:
    if meeting.recurring_series_id is None:
        return event_link.external_event_id
    if meeting.recurrence_is_detached:
        return event_link.external_event_id
    original_start = meeting.recurrence_original_start or meeting.start_time
    return _get_occurrence_event_id(
        provider,
        access_token,
        event_link.external_series_event_id or event_link.external_event_id,
        original_start,
    )


def _meeting_recipients(meeting: Meeting) -> list[User]:
    recipients: dict[int, User] = {}
    if meeting.organizer is not None:
        recipients[meeting.organizer.id] = meeting.organizer
    for participant in meeting.participants:
        if participant.user is not None:
            recipients[participant.user.id] = participant.user
    return list(recipients.values())


def _load_meeting(db: Session, meeting_id: int) -> Meeting:
    meeting = (
        db.query(Meeting)
        .options(
            joinedload(Meeting.organizer),
            joinedload(Meeting.room),
            selectinload(Meeting.participants).joinedload(MeetingParticipant.user),
        )
        .filter(Meeting.id == meeting_id)
        .one_or_none()
    )
    if meeting is None:
        raise CalendarSyncError(f"Meeting {meeting_id} does not exist")
    return meeting


def _sync_meeting_events(meeting_id: int, update_existing: bool) -> None:
    db = SessionLocal()
    try:
        meeting = _load_meeting(db, meeting_id)
        if meeting.status in ("CANCELLED", "COMPLETED"):
            return

        series_meetings = [meeting]
        if meeting.recurring_series_id is not None:
            series_meetings = (
                db.query(Meeting)
                .options(
                    joinedload(Meeting.organizer),
                    joinedload(Meeting.room),
                    selectinload(Meeting.participants).joinedload(
                        MeetingParticipant.user
                    ),
                )
                .filter(Meeting.recurring_series_id == meeting.recurring_series_id)
                .order_by(Meeting.start_time, Meeting.id)
                .all()
            )
        series_anchor = series_meetings[0]

        users = _meeting_recipients(meeting)
        if not users:
            return
        user_ids = [user.id for user in users]
        linked_user_ids = {
            user_id
            for (user_id,) in db.query(UserCalendarEvent.user_id)
            .filter(UserCalendarEvent.meeting_id == meeting.id)
            .distinct()
            .all()
        }
        token_rows = (
            db.query(UserCalendarToken)
            .filter(
                UserCalendarToken.user_id.in_(set(user_ids) | linked_user_ids),
                UserCalendarToken.is_active.is_(True),
            )
            .all()
        )
        token_by_key = {
            (token.user_id, token.provider): token
            for token in token_rows
        }
        active_recipient_ids = set(user_ids)
        failed_syncs: list[tuple[int, str, Exception]] = []

        for event_link in (
            db.query(UserCalendarEvent)
            .filter(UserCalendarEvent.meeting_id == meeting.id)
            .all()
        ):
            if event_link.user_id in active_recipient_ids:
                continue
            if (event_link.user_id, event_link.provider) not in token_by_key:
                continue
            try:
                access_token = get_valid_access_token(
                    event_link.user_id,
                    event_link.provider,
                )
                if event_link.external_occurrence_id is not None:
                    _provider_event_request(
                        event_link.provider,
                        access_token,
                        "DELETE",
                        event_id=event_link.external_occurrence_id,
                    )
                occurrence_id = _event_id_for_meeting(
                    meeting,
                    event_link,
                    event_link.provider,
                    access_token,
                )
                if occurrence_id is not None:
                    _provider_event_request(
                        event_link.provider,
                        access_token,
                        "DELETE",
                        event_id=occurrence_id,
                    )
            except CalendarSyncError as exc:
                logger.exception(
                    "Failed to remove calendar event for removed participant "
                    "(meeting_id=%s user_id=%s provider=%s)",
                    meeting.id,
                    event_link.user_id,
                    event_link.provider,
                )
                failed_syncs.append((event_link.user_id, event_link.provider, exc))
                continue
            db.delete(event_link)
            db.commit()

        payload_by_provider = {
            provider: _meeting_event_payload(
                meeting,
                provider,
            )
            for provider in _PROVIDER_CONFIG
        }

        for token in token_rows:
            if token.user_id not in active_recipient_ids:
                continue
            event_link = (
                db.query(UserCalendarEvent)
                .filter_by(
                    meeting_id=meeting.id,
                    user_id=token.user_id,
                    provider=token.provider,
                )
                .one_or_none()
            )
            if event_link is not None and not update_existing:
                continue

            try:
                access_token = get_valid_access_token(token.user_id, token.provider)
                if (
                    meeting.recurring_series_id is not None
                    and not update_existing
                ):
                    series_event_link = (
                        db.query(UserCalendarEvent)
                        .filter(
                            UserCalendarEvent.meeting_id.in_(
                                [item.id for item in series_meetings]
                            ),
                            UserCalendarEvent.user_id == token.user_id,
                            UserCalendarEvent.provider == token.provider,
                        )
                        .order_by(UserCalendarEvent.id)
                        .first()
                    )
                    if series_event_link is None:
                        recurrence_payload = _meeting_event_payload(
                            series_anchor,
                            token.provider,
                            recurrence_count=len(series_meetings),
                        )
                        series_event_id = _provider_event_request(
                            token.provider,
                            access_token,
                            "POST",
                            payload=recurrence_payload,
                        )
                        if not series_event_id:
                            raise CalendarSyncError(
                                f"{token.provider} did not return a recurring "
                                "event ID"
                            )
                    else:
                        series_event_id = (
                            series_event_link.external_series_event_id
                            or series_event_link.external_event_id
                        )

                    for series_meeting in series_meetings:
                        existing_link = (
                            db.query(UserCalendarEvent)
                            .filter_by(
                                meeting_id=series_meeting.id,
                                user_id=token.user_id,
                                provider=token.provider,
                            )
                            .one_or_none()
                        )
                        if existing_link is None:
                            db.add(
                                UserCalendarEvent(
                                    meeting_id=series_meeting.id,
                                    user_id=token.user_id,
                                    provider=token.provider,
                                    external_event_id=series_event_id,
                                    external_series_event_id=series_event_id,
                                )
                            )
                        elif (
                            existing_link.external_series_event_id is None
                            and not series_meeting.recurrence_is_detached
                        ):
                            existing_link.external_series_event_id = series_event_id
                    db.commit()
                    logger.info(
                        "Recurring calendar series synced "
                        "(series_id=%s user_id=%s provider=%s occurrences=%s)",
                        meeting.recurring_series_id,
                        token.user_id,
                        token.provider,
                        len(series_meetings),
                    )
                    continue

                if event_link is None:
                    event_id = _provider_event_request(
                        token.provider,
                        access_token,
                        "POST",
                        payload=payload_by_provider[token.provider],
                    )
                    if event_id is None:
                        raise CalendarSyncError(
                            f"{token.provider} did not return an event ID"
                        )
                    event_link = UserCalendarEvent(
                        meeting_id=meeting.id,
                        user_id=token.user_id,
                        provider=token.provider,
                        external_event_id=event_id,
                    )
                    db.add(event_link)
                elif (
                    meeting.recurrence_is_detached
                    and event_link.external_occurrence_id is not None
                ):
                    _provider_event_request(
                        token.provider,
                        access_token,
                        "DELETE",
                        event_id=event_link.external_occurrence_id,
                    )
                    event_link.external_occurrence_id = None
                    db.commit()
                    _provider_event_request(
                        token.provider,
                        access_token,
                        "PATCH",
                        event_id=event_link.external_event_id,
                        payload=payload_by_provider[token.provider],
                    )
                elif (
                    meeting.recurrence_is_detached
                    and event_link.external_event_id
                    == (
                        event_link.external_series_event_id
                        or event_link.external_event_id
                    )
                ):
                    series_event_id = (
                        event_link.external_series_event_id
                        or event_link.external_event_id
                    )
                    original_start = (
                        meeting.recurrence_original_start or meeting.start_time
                    )
                    occurrence_id = _get_occurrence_event_id(
                        token.provider,
                        access_token,
                        series_event_id,
                        original_start,
                    )
                    if occurrence_id is None:
                        raise CalendarSyncError(
                            f"Could not find recurring {token.provider} occurrence "
                            f"to detach for meeting {meeting.id}"
                        )
                    standalone_event_id = _provider_event_request(
                        token.provider,
                        access_token,
                        "POST",
                        payload=payload_by_provider[token.provider],
                    )
                    if not standalone_event_id:
                        raise CalendarSyncError(
                            f"{token.provider} did not return an ID for the "
                            "detached calendar event"
                        )
                    event_link.external_occurrence_id = occurrence_id
                    event_link.external_event_id = standalone_event_id
                    event_link.external_series_event_id = series_event_id
                    db.commit()
                    _provider_event_request(
                        token.provider,
                        access_token,
                        "DELETE",
                        event_id=occurrence_id,
                    )
                    event_link.external_occurrence_id = None
                else:
                    occurrence_id = _event_id_for_meeting(
                        meeting,
                        event_link,
                        token.provider,
                        access_token,
                    )
                    if occurrence_id is None:
                        raise CalendarSyncError(
                            f"Could not find recurring {token.provider} event "
                            f"occurrence for meeting {meeting.id}"
                        )
                    _provider_event_request(
                        token.provider,
                        access_token,
                        "PATCH",
                        event_id=occurrence_id,
                        payload=payload_by_provider[token.provider],
                    )
                db.commit()
                logger.info(
                    "Calendar event synced (meeting_id=%s user_id=%s provider=%s)",
                    meeting.id,
                    token.user_id,
                    token.provider,
                )
            except CalendarSyncError as exc:
                db.rollback()
                logger.exception(
                    "Failed to sync meeting for one calendar account "
                    "(meeting_id=%s user_id=%s provider=%s)",
                    meeting.id,
                    token.user_id,
                    token.provider,
                )
                failed_syncs.append((token.user_id, token.provider, exc))

        if failed_syncs:
            failed_accounts = ", ".join(
                f"user_id={user_id}/{provider}"
                for user_id, provider, _ in failed_syncs
            )
            raise CalendarSyncError(
                f"Calendar sync failed for: {failed_accounts}"
            ) from failed_syncs[0][2]
    finally:
        db.close()


def sync_create_event(meeting_id: int) -> None:
    _sync_meeting_events(meeting_id, update_existing=False)


def sync_update_event(meeting_id: int) -> None:
    _sync_meeting_events(meeting_id, update_existing=True)


def sync_delete_event(meeting_id: int) -> None:
    db = SessionLocal()
    try:
        meeting = _load_meeting(db, meeting_id)
        event_links = (
            db.query(UserCalendarEvent)
            .filter(UserCalendarEvent.meeting_id == meeting_id)
            .all()
        )
        failed_deletes: list[tuple[int, str, Exception]] = []
        for event_link in event_links:
            meeting_id_for_log = event_link.meeting_id
            user_id_for_log = event_link.user_id
            provider_for_log = event_link.provider
            try:
                access_token = get_valid_access_token(
                    user_id_for_log,
                    provider_for_log,
                )
                if event_link.external_occurrence_id is not None:
                    _provider_event_request(
                        provider_for_log,
                        access_token,
                        "DELETE",
                        event_id=event_link.external_occurrence_id,
                    )
                occurrence_id = _event_id_for_meeting(
                    meeting,
                    event_link,
                    provider_for_log,
                    access_token,
                )
                if occurrence_id is not None:
                    _provider_event_request(
                        provider_for_log,
                        access_token,
                        "DELETE",
                        event_id=occurrence_id,
                    )
                db.delete(event_link)
                db.commit()
                logger.info(
                    "Calendar event deleted (meeting_id=%s user_id=%s provider=%s)",
                    meeting_id_for_log,
                    user_id_for_log,
                    provider_for_log,
                )
            except CalendarSyncError as exc:
                db.rollback()
                logger.exception(
                    "Failed to delete calendar event "
                    "(meeting_id=%s user_id=%s provider=%s)",
                    meeting_id_for_log,
                    user_id_for_log,
                    provider_for_log,
                )
                failed_deletes.append((user_id_for_log, provider_for_log, exc))
        if failed_deletes:
            failed_accounts = ", ".join(
                f"user_id={user_id}/{provider}"
                for user_id, provider, _ in failed_deletes
            )
            raise CalendarSyncError(
                f"Calendar event deletion failed for: {failed_accounts}"
            ) from failed_deletes[0][2]
    finally:
        db.close()


def sync_event_task(
    meeting_id: int,
    event_type: str,
    reason: str | None = None,
) -> None:
    """Background hook for meeting lifecycle events."""
    actions = {
        EVENT_MEETING_CREATED: sync_create_event,
        EVENT_MEETING_UPDATED: sync_update_event,
        EVENT_MEETING_CANCELLED: sync_delete_event,
    }
    sync_action = actions.get(event_type)
    if sync_action is None:
        raise ValueError("Unsupported meeting event type")
    if event_type == EVENT_MEETING_CANCELLED and not (reason and reason.strip()):
        raise ValueError("A cancellation reason is required for cancellation events")
    if event_type == EVENT_MEETING_CANCELLED:
        logger.info(
            "Processing meeting cancellation calendar sync (meeting_id=%s)",
            meeting_id,
        )
    try:
        sync_action(meeting_id)
    except CalendarSyncError:
        logger.exception(
            "Background calendar synchronization failed "
            "(meeting_id=%s event_type=%s)",
            meeting_id,
            event_type,
        )
