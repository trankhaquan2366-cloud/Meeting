from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

from cryptography.fernet import Fernet

from app.models.user import User
from app.routers import auth as auth_router
from app.core.security import hash_password
from app.services.google_calendar_service import decrypt_refresh_token, make_calendar_consent_url


class MockGoogleResponse:
    def __init__(self, body):
        self.body = body

    def raise_for_status(self):
        return None

    def json(self):
        return self.body


def _configure_google_oauth(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-google-client")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-google-secret")
    monkeypatch.setenv(
        "GOOGLE_REDIRECT_URI",
        "http://localhost:8000/api/auth/google/callback",
    )
    monkeypatch.setenv(
        "FRONTEND_LOGIN_URL",
        "http://localhost:8000/static/login.html",
    )


def _mock_google_profile(monkeypatch, profile, token_data=None):
    token_data = token_data or {"access_token": "google-access-token"}
    monkeypatch.setattr(
        auth_router.httpx,
        "post",
        lambda *args, **kwargs: MockGoogleResponse(token_data),
    )
    monkeypatch.setattr(
        auth_router.httpx,
        "get",
        lambda *args, **kwargs: MockGoogleResponse(profile),
    )


def _start_google_login(client):
    response = client.get("/api/auth/google/login", follow_redirects=False)
    assert response.status_code == 307
    return response, urlsplit(response.headers["location"])


def _complete_google_login(client, login_response, location):
    state = login_response.cookies[auth_router.GOOGLE_STATE_COOKIE].split("|", 1)[0]
    return client.get(
        f"/api/auth/google/callback?code=test-code&state={state}",
        follow_redirects=False,
    )


def test_google_login_redirect_requests_openid_email_profile(client, monkeypatch):
    _configure_google_oauth(monkeypatch)

    response, location = _start_google_login(client)
    query = parse_qs(location.query)

    assert location.hostname == "accounts.google.com"
    assert query["scope"] == ["openid email profile"]
    assert query["response_type"] == ["code"]
    assert response.cookies[auth_router.GOOGLE_STATE_COOKIE].startswith(query["state"][0] + "|")


def test_google_callback_registers_new_user_and_redirects_with_token(
    client, db_session, monkeypatch
):
    _configure_google_oauth(monkeypatch)
    _mock_google_profile(
        monkeypatch,
        {
            "email": "new.person@example.test",
            "email_verified": True,
            "name": "New Person",
            "picture": "https://images.example.test/person.png",
        },
    )
    login_response, location = _start_google_login(client)

    response = _complete_google_login(client, login_response, location)

    assert response.status_code == 303
    redirect = urlsplit(response.headers["location"])
    values = parse_qs(redirect.fragment)
    user = db_session.query(User).filter_by(email="new.person@example.test").one()
    assert user.full_name == "New Person"
    assert user.role == "employee"
    assert values["access_token"]
    assert values["email"] == [user.email]
    assert values["picture"] == ["https://images.example.test/person.png"]


def test_google_callback_logs_in_existing_user(client, db_session, monkeypatch):
    _configure_google_oauth(monkeypatch)
    user = User(
        username="known-google-user",
        email="known@example.test",
        full_name="Existing User",
        hashed_password=hash_password("local-password"),
        role="employee",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    _mock_google_profile(
        monkeypatch,
        {
            "email": "known@example.test",
            "email_verified": True,
            "name": "Google Display Name",
            "picture": "https://images.example.test/known.png",
        },
    )
    login_response, location = _start_google_login(client)

    response = _complete_google_login(client, login_response, location)

    assert response.status_code == 303
    values = parse_qs(urlsplit(response.headers["location"]).fragment)
    assert values["username"] == ["known-google-user"]
    assert db_session.query(User).filter_by(email="known@example.test").count() == 1


def test_google_callback_rejects_invalid_state(client, monkeypatch):
    _configure_google_oauth(monkeypatch)
    _start_google_login(client)

    response = client.get(
        "/api/auth/google/callback?code=test-code&state=wrong-state",
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid OAuth state"


def test_invitee_calendar_consent_stores_encrypted_token_and_starts_sync(
    client, db_session, monkeypatch
):
    _configure_google_oauth(monkeypatch)
    monkeypatch.setenv("GOOGLE_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    user = User(
        username="calendar-invitee",
        email="invitee@example.test",
        full_name="Calendar Invitee",
        hashed_password=hash_password("local-password"),
        role="employee",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    consent_url = make_calendar_consent_url(user)
    consent_parts = urlsplit(consent_url)

    consent_response = client.get(
        f"{consent_parts.path}?{consent_parts.query}",
        follow_redirects=False,
    )
    assert consent_response.status_code == 307
    consent_query = parse_qs(urlsplit(consent_response.headers["location"]).query)
    assert "https://www.googleapis.com/auth/calendar.events" in consent_query["scope"][0]
    assert consent_query["access_type"] == ["offline"]

    _mock_google_profile(
        monkeypatch,
        {"email": "invitee@example.test", "email_verified": True, "name": "Calendar Invitee"},
        {"access_token": "google-access-token", "refresh_token": "private-refresh-token"},
    )
    state = consent_response.cookies[auth_router.GOOGLE_STATE_COOKIE].split("|", 1)[0]
    monkeypatch.setattr(auth_router, "sync_user_meetings_to_google", lambda user_id: None)
    callback = client.get(
        f"/api/auth/google/callback?code=calendar-code&state={state}",
        follow_redirects=False,
    )

    assert callback.status_code == 303
    assert "calendar_connected=1" in callback.headers["location"]
    db_session.expire_all()
    saved_user = db_session.query(User).filter_by(id=user.id).one()
    assert saved_user.google_refresh_token != "private-refresh-token"
    assert decrypt_refresh_token(saved_user.google_refresh_token) == "private-refresh-token"
    assert saved_user.google_calendar_connected_at is not None


def test_calendar_consent_rejects_google_email_mismatch(client, db_session, monkeypatch):
    _configure_google_oauth(monkeypatch)
    monkeypatch.setenv("GOOGLE_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    user = User(
        username="calendar-owner",
        email="owner@example.test",
        full_name="Calendar Owner",
        hashed_password=hash_password("local-password"),
        role="employee",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    consent_parts = urlsplit(make_calendar_consent_url(user))
    consent_response = client.get(
        f"{consent_parts.path}?{consent_parts.query}",
        follow_redirects=False,
    )
    _mock_google_profile(
        monkeypatch,
        {"email": "other@example.test", "email_verified": True, "name": "Different Account"},
        {"access_token": "google-access-token", "refresh_token": "private-refresh-token"},
    )
    state = consent_response.cookies[auth_router.GOOGLE_STATE_COOKIE].split("|", 1)[0]

    callback = client.get(
        f"/api/auth/google/callback?code=calendar-code&state={state}",
        follow_redirects=False,
    )

    assert callback.status_code == 403
    db_session.expire_all()
    saved_user = db_session.query(User).filter_by(id=user.id).one()
    assert saved_user.google_refresh_token is None
