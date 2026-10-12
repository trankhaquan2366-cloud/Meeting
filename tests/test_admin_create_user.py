from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.user import User
from tests.helpers import (
    _add_participant,
    _auth_header,
    _create_meeting,
    _create_room,
    _create_user,
    _make_token,
)


def test_create_user_requires_admin_role(client: TestClient, db_session: Session):
    payload = {
        "full_name": "Nhân viên mới",
        "email": "new.staff@example.test",
        "role": "employee",
    }

    assert client.post("/api/users/", json=payload).status_code == 401

    employee = _create_user(db_session, username="create-user-employee")
    response = client.post(
        "/api/users/",
        json=payload,
        headers=_auth_header(_make_token(employee)),
    )

    assert response.status_code == 403
    assert db_session.query(User).filter_by(email=payload["email"]).first() is None


def test_admin_creates_user_with_generated_password(
    client: TestClient,
    db_session: Session,
    monkeypatch,
):
    from app.routers import users as users_router

    monkeypatch.setattr(users_router.secrets, "token_urlsafe", lambda _: "one-time-secret")
    admin = _create_user(db_session, username="create-user-admin", role="admin")
    response = client.post(
        "/api/users/",
        json={
            "full_name": "Nhân viên mới",
            "email": "new.staff@example.test",
            "role": "employee",
        },
        headers=_auth_header(_make_token(admin)),
    )

    assert response.status_code == 201
    result = response.json()
    assert result["email"] == "new.staff@example.test"
    assert result["full_name"] == "Nhân viên mới"
    assert result["role"] == "employee"
    assert result["is_active"] is True
    assert result["username"] == "new.staff"
    assert "hashed_password" not in result
    assert "temporary_password" not in result
    assert "password" not in result

    created_user = db_session.query(User).filter_by(id=result["id"]).one()
    assert verify_password("one-time-secret", created_user.hashed_password)


def test_admin_create_user_rejects_duplicate_email_and_invalid_role(
    client: TestClient,
    db_session: Session,
):
    admin = _create_user(db_session, username="create-user-duplicate-admin", role="admin")
    headers = _auth_header(_make_token(admin))
    payload = {
        "full_name": "Tài khoản đầu tiên",
        "email": "duplicate@example.test",
        "role": "employee",
    }
    assert client.post("/api/users/", json=payload, headers=headers).status_code == 201

    duplicate = client.post(
        "/api/users/",
        json={**payload, "email": "DUPLICATE@example.test"},
        headers=headers,
    )
    invalid_role = client.post(
        "/api/users/",
        json={**payload, "email": "another@example.test", "role": "manager"},
        headers=headers,
    )

    assert duplicate.status_code == 400
    assert invalid_role.status_code == 422
    assert db_session.query(User).filter_by(email="another@example.test").first() is None


def test_admin_create_user_accepts_username_and_password_without_returning_password(
    client: TestClient,
    db_session: Session,
):
    admin = _create_user(db_session, username="create-user-explicit-admin", role="admin")
    headers = _auth_header(_make_token(admin))
    payload = {
        "full_name": "Tài khoản có tên đăng nhập",
        "email": "explicit@example.test",
        "username": "explicit.staff",
        "password": "correct-horse-battery",
        "role": "employee",
    }

    created = client.post("/api/users/", json=payload, headers=headers)
    duplicate_username = client.post(
        "/api/users/",
        json={
            **payload,
            "email": "another.explicit@example.test",
        },
        headers=headers,
    )

    assert created.status_code == 201
    assert created.json()["username"] == "explicit.staff"
    assert "password" not in created.json()
    assert "hashed_password" not in created.json()
    created_user = db_session.query(User).filter_by(email=payload["email"]).one()
    assert verify_password(payload["password"], created_user.hashed_password)
    assert duplicate_username.status_code == 400


def test_username_is_made_unique_when_email_local_parts_match(
    client: TestClient,
    db_session: Session,
):
    admin = _create_user(db_session, username="create-user-username-admin", role="admin")
    headers = _auth_header(_make_token(admin))

    first = client.post(
        "/api/users/",
        json={
            "full_name": "Nhân viên một",
            "email": "staff@first.example.test",
            "role": "employee",
        },
        headers=headers,
    )
    second = client.post(
        "/api/users/",
        json={
            "full_name": "Nhân viên hai",
            "email": "staff@second.example.test",
            "role": "employee",
        },
        headers=headers,
    )

    assert first.status_code == second.status_code == 201
    assert first.json()["username"] == "staff"
    assert second.json()["username"] == "staff1"


def test_user_directory_returns_frontend_fields_and_allows_null_email(
    client: TestClient,
    db_session: Session,
):
    admin = _create_user(db_session, username="user-directory-admin", role="admin")
    legacy_user = _create_user(db_session, username="legacy-no-email")
    legacy_user.email = None
    db_session.commit()

    response = client.get(
        "/api/users/",
        headers=_auth_header(_make_token(admin)),
    )

    assert response.status_code == 200
    users = {user["id"]: user for user in response.json()}
    legacy_response = users[legacy_user.id]
    assert legacy_response == {
        "id": legacy_user.id,
        "full_name": legacy_user.full_name,
        "email": None,
        "username": legacy_user.username,
    }


def test_user_directory_search_and_frequent_users(
    client: TestClient,
    db_session: Session,
):
    organizer = _create_user(db_session, username="frequent-organizer")
    frequent_user = _create_user(db_session, username="frequent-colleague")
    other_user = _create_user(db_session, username="other-colleague")
    room = _create_room(db_session)
    now = datetime.utcnow()

    for index in range(2):
        meeting = _create_meeting(
            db_session,
            room,
            organizer,
            now + timedelta(days=index + 1),
            now + timedelta(days=index + 1, hours=1),
        )
        _add_participant(db_session, meeting, frequent_user)

    headers = _auth_header(_make_token(organizer))
    search_response = client.get(
        "/api/users/?search=frequent-colleague",
        headers=headers,
    )
    frequent_response = client.get("/api/users/frequent", headers=headers)

    assert search_response.status_code == 200
    assert [user["id"] for user in search_response.json()] == [frequent_user.id]
    assert frequent_response.status_code == 200
    assert [user["id"] for user in frequent_response.json()] == [frequent_user.id]
    assert all(user["id"] != organizer.id for user in frequent_response.json())
    assert all(user["id"] != other_user.id for user in frequent_response.json())
