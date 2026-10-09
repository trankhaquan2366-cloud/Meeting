from datetime import datetime, timedelta
from types import SimpleNamespace

import httplib2
import pytest
from cryptography.fernet import Fernet
from googleapiclient.errors import HttpError
from sqlalchemy.orm import sessionmaker

from app.models.google_calendar_event import GoogleCalendarEvent
from app.services import google_calendar_service
from app.services.google_calendar_service import encrypt_refresh_token
from app.models.user import User
from tests.conftest import test_engine
from tests.helpers import _create_user


class FakeDeleteRequest:
    def __init__(self, error=None):
        self.error = error

    def execute(self):
        if self.error:
            raise self.error
        return None


class FakeCalendarEvents:
    def __init__(self, error=None):
        self.error = error
        self.arguments = None

    def delete(self, **kwargs):
        self.arguments = kwargs
        return FakeDeleteRequest(self.error)


class FakeCalendarService:
    def __init__(self, events):
        self._events = events

    def events(self):
        return self._events


def _http_error(status_code):
    response = httplib2.Response({"status": str(status_code), "reason": "test"})
    return HttpError(response, b'{"error":{"message":"test"}}')


@pytest.mark.parametrize("status_code", [404, 410])
def test_delete_calendar_event_treats_missing_google_event_as_success(
    monkeypatch, status_code
):
    monkeypatch.setenv("GOOGLE_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    user = User(id=42, google_refresh_token=encrypt_refresh_token("refresh-token"))
    events = FakeCalendarEvents(_http_error(status_code))
    monkeypatch.setattr(google_calendar_service.Credentials, "refresh", lambda self, request: None)
    monkeypatch.setattr(
        google_calendar_service,
        "build",
        lambda *args, **kwargs: FakeCalendarService(events),
    )

    assert google_calendar_service.delete_google_calendar_event(user, "event-42") is True
    assert events.arguments == {"calendarId": "primary", "eventId": "event-42"}


def test_delete_calendar_event_returns_false_for_other_google_errors(monkeypatch):
    monkeypatch.setenv("GOOGLE_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    user = User(id=43, google_refresh_token=encrypt_refresh_token("refresh-token"))
    events = FakeCalendarEvents(_http_error(500))
    monkeypatch.setattr(google_calendar_service.Credentials, "refresh", lambda self, request: None)
    monkeypatch.setattr(
        google_calendar_service,
        "build",
        lambda *args, **kwargs: FakeCalendarService(events),
    )

    assert google_calendar_service.delete_google_calendar_event(user, "event-43") is False


def test_cancel_worker_removes_mapping_only_after_success(db_session, monkeypatch):
    monkeypatch.setenv("GOOGLE_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    user = _create_user(db_session, "calendar-delete-user")
    user.google_refresh_token = encrypt_refresh_token("refresh-token")
    db_session.commit()

    from app.models.meeting import Meeting

    meeting = Meeting(
        title="Delete calendar event",
        room_id=None,
        organizer_id=user.id,
        start_time=datetime.now() + timedelta(days=2),
        end_time=datetime.now() + timedelta(days=2, hours=1),
        status="CANCELLED",
    )
    db_session.add(meeting)
    db_session.commit()
    db_session.add(
        GoogleCalendarEvent(
            user_id=user.id,
            meeting_id=meeting.id,
            google_event_id="event-to-delete",
        )
    )
    db_session.commit()

    session_factory = sessionmaker(bind=test_engine)
    monkeypatch.setattr(google_calendar_service, "SessionLocal", session_factory)
    deleted = []
    monkeypatch.setattr(
        google_calendar_service,
        "delete_google_calendar_event",
        lambda event_user, event_id: deleted.append((event_user.id, event_id)) or True,
    )

    google_calendar_service.delete_google_events_for_meeting(meeting.id)

    assert deleted == [(user.id, "event-to-delete")]
    assert db_session.query(GoogleCalendarEvent).filter_by(meeting_id=meeting.id).count() == 0
