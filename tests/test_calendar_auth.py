from urllib.parse import parse_qs, urlparse
from datetime import datetime

import pytest
from fastapi import HTTPException
from cryptography.fernet import Fernet

from app.models.calendar import UserCalendarEvent
from app.models.meeting import Meeting
from app.models.user import User
from app.routers import calendar_auth
from tests.helpers import _auth_header, _create_user, _make_token


def test_oauth_state_is_signed_and_expired_or_modified_state_is_rejected():
    state = calendar_auth._encode_state(42, "google")
    payload = calendar_auth._decode_state(state)

    assert payload["user_id"] == 42
    assert payload["provider"] == "google"

    with pytest.raises(HTTPException) as error:
        calendar_auth._decode_state(state + "tampered")
    assert error.value.status_code == 400


def test_google_auth_url_contains_calendar_scope_and_state(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "google-client")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "google-secret")
    monkeypatch.setenv(
        "GOOGLE_REDIRECT_URI",
        "http://localhost:8000/api/calendar/callback",
    )
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:3000/dashboard")
    user = User(
        id=27,
        username="oauth-user",
        email="oauth-user@example.com",
        hashed_password="unused",
    )

    result = calendar_auth.get_calendar_auth_url("google", user)
    query = parse_qs(urlparse(result["authorization_url"]).query)
    state = calendar_auth._decode_state(query["state"][0])

    assert urlparse(result["authorization_url"]).netloc == "accounts.google.com"
    assert "https://www.googleapis.com/auth/calendar.events" in query["scope"][0]
    assert query["access_type"] == ["offline"]
    assert state["user_id"] == 27
    assert state["provider"] == "google"


def test_oauth_config_requires_client_credentials(monkeypatch):
    monkeypatch.delenv("MICROSOFT_CLIENT_ID", raising=False)
    monkeypatch.delenv("MICROSOFT_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("MICROSOFT_REDIRECT_URI", raising=False)

    with pytest.raises(HTTPException) as error:
        calendar_auth._get_provider_config("outlook")

    assert error.value.status_code == 503
    assert "MICROSOFT_CLIENT_ID" in error.value.detail


def test_outlook_oauth_config_accepts_outlook_environment_names(monkeypatch):
    monkeypatch.setenv("OUTLOOK_CLIENT_ID", "outlook-client")
    monkeypatch.setenv("OUTLOOK_CLIENT_SECRET", "outlook-secret")
    monkeypatch.setenv(
        "OUTLOOK_REDIRECT_URI",
        "http://localhost:8000/api/calendar/callback",
    )

    config = calendar_auth._get_provider_config("outlook")

    assert config["client_id"] == "outlook-client"
    assert config["client_secret"] == "outlook-secret"
    assert config["redirect_uri"] == "http://localhost:8000/api/calendar/callback"


def test_google_oauth_connect_status_and_disconnect(
    client,
    db_session,
    monkeypatch,
):
    user = _create_user(db_session, "calendar-oauth-user")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "google-client")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "google-secret")
    monkeypatch.setenv(
        "GOOGLE_REDIRECT_URI",
        "http://localhost:8000/api/calendar/callback",
    )
    monkeypatch.setenv(
        "CALENDAR_TOKEN_ENCRYPTION_KEY",
        Fernet.generate_key().decode("ascii"),
    )
    def fake_post(url, data, timeout):
        assert url == "https://oauth2.googleapis.com/token"
        assert data["code"] == "one-time-code"
        assert timeout == 20.0
        return _FakeTokenResponse()

    monkeypatch.setattr(calendar_auth.httpx, "post", fake_post)
    headers = _auth_header(_make_token(user))

    response = client.get(
        "/api/calendar/auth-url",
        params={"provider": "google"},
        headers=headers,
    )
    assert response.status_code == 200
    state = parse_qs(urlparse(response.json()["authorization_url"]).query)["state"][0]

    response = client.get(
        "/api/calendar/callback",
        params={"code": "one-time-code", "state": state},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == (
        "http://localhost:3000/dashboard?calendar_connected=google#settings"
    )

    response = client.get("/api/calendar/status", headers=headers)
    assert response.status_code == 200
    assert response.json()["google"]["connected"] is True
    assert response.json()["outlook"]["connected"] is False

    meeting = Meeting(
        title="Keep external calendar event",
        organizer_id=user.id,
        start_time=datetime(2030, 1, 1, 13),
        end_time=datetime(2030, 1, 1, 14),
        status="CONFIRMED",
    )
    db_session.add(meeting)
    db_session.commit()
    db_session.add(
        UserCalendarEvent(
            meeting_id=meeting.id,
            user_id=user.id,
            provider="google",
            external_event_id="preserved-event-id",
        )
    )
    db_session.commit()

    response = client.post(
        "/api/calendar/disconnect",
        params={"provider": "google"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["connected"] is False
    assert (
        db_session.query(UserCalendarEvent)
        .filter_by(meeting_id=meeting.id, user_id=user.id)
        .count()
        == 1
    )

    response = client.get("/api/calendar/status", headers=headers)
    assert response.json()["google"]["connected"] is False


class _FakeTokenResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "access_token": "provider-access-token",
            "refresh_token": "provider-refresh-token",
            "expires_in": 3600,
        }
