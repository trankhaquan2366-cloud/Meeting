from datetime import datetime, timedelta

from cryptography.fernet import Fernet
import httpx
from sqlalchemy.orm import sessionmaker

from app.models.google_calendar_event import GoogleCalendarEvent
from app.models.meeting import MeetingParticipant
from app.services import google_calendar_service
from app.services.google_calendar_service import encrypt_refresh_token
from tests.conftest import test_engine
from tests.helpers import _add_participant, _create_meeting, _create_room, _create_user


class FakeGoogleResponse:
    status_code = 200

    def raise_for_status(self):
        return None



def test_invitee_meeting_is_inserted_once_in_google_calendar(db_session, monkeypatch):
    monkeypatch.setenv("GOOGLE_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    monkeypatch.setenv("APP_TIMEZONE", "Asia/Ho_Chi_Minh")
    organizer = _create_user(db_session, "calendar-sync-organizer")
    invitee = _create_user(db_session, "calendar-sync-invitee")
    invitee.google_refresh_token = encrypt_refresh_token("stored-refresh-token")
    db_session.commit()
    room = _create_room(db_session, "Calendar Sync Room")
    start = datetime.now() + timedelta(days=3)
    meeting = _create_meeting(db_session, room, organizer, start, start + timedelta(hours=1))
    meeting.title = "Project sync"
    meeting.description = "Planning session"
    db_session.add(MeetingParticipant(meeting_id=meeting.id, user_id=invitee.id))
    db_session.commit()

    session_factory = sessionmaker(bind=test_engine)
    monkeypatch.setattr(google_calendar_service, "SessionLocal", session_factory)
    monkeypatch.setattr(google_calendar_service, "_access_token", lambda token: "google-access-token")
    inserted_events = []

    def fake_insert(url, **kwargs):
        inserted_events.append((url, kwargs))
        return FakeGoogleResponse()

    monkeypatch.setattr(google_calendar_service.httpx, "post", fake_insert)

    google_calendar_service.sync_user_meetings_to_google(invitee.id)
    google_calendar_service.sync_user_meetings_to_google(invitee.id)

    assert len(inserted_events) == 1
    url, request = inserted_events[0]
    payload = request["json"]
    assert url == google_calendar_service.GOOGLE_EVENTS_URL
    assert request["headers"]["Authorization"] == "Bearer google-access-token"
    assert payload["summary"] == "Project sync"
    assert payload["location"] == "Calendar Sync Room - Floor 1"
    assert payload["start"]["timeZone"] == "Asia/Ho_Chi_Minh"
    assert db_session.query(GoogleCalendarEvent).filter_by(user_id=invitee.id, meeting_id=meeting.id).count() == 1


def test_organizer_meeting_is_inserted_with_invitees(db_session, monkeypatch):
    monkeypatch.setenv("GOOGLE_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    organizer = _create_user(db_session, "calendar-sync-connected-organizer")
    organizer.google_refresh_token = encrypt_refresh_token("organizer-refresh-token")
    invitee = _create_user(db_session, "calendar-sync-organizer-invitee")
    db_session.commit()
    room = _create_room(db_session, "Organizer Calendar Room")
    start = datetime.now() + timedelta(days=3)
    meeting = _create_meeting(db_session, room, organizer, start, start + timedelta(hours=1))
    _add_participant(db_session, meeting, invitee)

    monkeypatch.setattr(google_calendar_service, "SessionLocal", sessionmaker(bind=test_engine))
    monkeypatch.setattr(google_calendar_service, "_access_token", lambda token: "google-access-token")
    inserted_events = []

    def fake_insert(url, **kwargs):
        inserted_events.append((url, kwargs))
        return FakeGoogleResponse()

    monkeypatch.setattr(google_calendar_service.httpx, "post", fake_insert)
    google_calendar_service.sync_user_meetings_to_google(organizer.id)

    assert len(inserted_events) == 1
    url, request = inserted_events[0]
    assert url == google_calendar_service.GOOGLE_EVENTS_URL
    assert request["params"] == {"sendUpdates": "all"}
    assert request["json"]["attendees"] == [{"email": invitee.email}]
    assert db_session.query(GoogleCalendarEvent).filter_by(
        user_id=organizer.id,
        meeting_id=meeting.id,
    ).count() == 1


def test_calendar_permission_403_logs_reconnect_guidance(db_session, monkeypatch, caplog):
    monkeypatch.setenv("GOOGLE_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    organizer = _create_user(db_session, "calendar-sync-403-organizer")
    organizer.google_refresh_token = encrypt_refresh_token("organizer-refresh-token")
    db_session.commit()
    room = _create_room(db_session, "Calendar 403 Room")
    start = datetime.now() + timedelta(days=3)
    meeting = _create_meeting(db_session, room, organizer, start, start + timedelta(hours=1))

    monkeypatch.setattr(google_calendar_service, "SessionLocal", sessionmaker(bind=test_engine))
    monkeypatch.setattr(google_calendar_service, "_access_token", lambda token: "google-access-token")

    def forbidden_insert(url, **kwargs):
        response = httpx.Response(
            403,
            json={
                "error": {
                    "code": 403,
                    "message": "Insufficient Permission",
                    "errors": [{"reason": "insufficientPermissions"}],
                }
            },
            request=httpx.Request("POST", url),
        )
        response.raise_for_status()

    monkeypatch.setattr(google_calendar_service.httpx, "post", forbidden_insert)

    google_calendar_service.sync_user_meetings_to_google(organizer.id)

    assert "insufficientPermissions" in caplog.text
    assert "disconnect Google Calendar in Settings and connect again" in caplog.text
    assert db_session.query(GoogleCalendarEvent).filter_by(
        user_id=organizer.id,
        meeting_id=meeting.id,
    ).count() == 0


def test_access_token_refresh_sends_client_credentials(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "oauth-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "oauth-client-secret")
    requests = []

    class TokenResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"access_token": "fresh-access-token"}

    def fake_post(url, **kwargs):
        requests.append((url, kwargs))
        return TokenResponse()

    monkeypatch.setattr(google_calendar_service.httpx, "post", fake_post)

    assert google_calendar_service._access_token("refresh-token") == "fresh-access-token"
    url, request = requests[0]
    assert url == google_calendar_service.GOOGLE_TOKEN_URL
    assert request["data"] == {
        "client_id": "oauth-client-id",
        "client_secret": "oauth-client-secret",
        "refresh_token": "refresh-token",
        "grant_type": "refresh_token",
    }


def test_access_token_refresh_logs_google_oauth_error(monkeypatch, caplog):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "oauth-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "oauth-client-secret")

    def failed_refresh(url, **kwargs):
        response = httpx.Response(
            400,
            json={
                "error": "invalid_grant",
                "error_description": "Token has been expired or revoked.",
            },
            request=httpx.Request("POST", url),
        )
        return response

    monkeypatch.setattr(google_calendar_service.httpx, "post", failed_refresh)

    try:
        google_calendar_service._access_token("secret-refresh-token-value")
    except httpx.HTTPStatusError:
        pass
    else:
        raise AssertionError("Expected the Google token refresh request to fail")

    assert "invalid_grant" in caplog.text
    assert "Token has been expired or revoked." in caplog.text
    assert "oauth-client-secret" not in caplog.text
    assert "secret-refresh-token-value" not in caplog.text
