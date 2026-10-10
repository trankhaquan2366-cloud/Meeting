from datetime import datetime, timedelta

from cryptography.fernet import Fernet
from sqlalchemy.orm import sessionmaker

from app.models.google_calendar_event import GoogleCalendarEvent
from app.models.meeting import MeetingParticipant
from app.services import google_calendar_service
from app.services.google_calendar_service import encrypt_refresh_token
from tests.conftest import test_engine
from tests.helpers import _create_meeting, _create_room, _create_user


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
