from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from tests.helpers import _auth_header, _create_user, _make_token


def test_admin_cannot_edit_or_downgrade_another_admin(
    client: TestClient,
    db_session: Session,
):
    admin_a = _create_user(db_session, "equal-admin-a", role="admin")
    admin_b = _create_user(db_session, "equal-admin-b", role="admin")
    headers = _auth_header(_make_token(admin_a))

    role_response = client.patch(
        f"/api/v1/users/{admin_b.id}",
        json={"role": "employee"},
        headers=headers,
    )
    status_response = client.patch(
        f"/api/v1/users/{admin_b.id}",
        json={"status": "INACTIVE"},
        headers=headers,
    )
    permissions_response = client.put(
        f"/api/v1/users/{admin_b.id}/permissions",
        json={
            "systemRole": "NHAN_VIEN",
            "canBook": False,
            "canAttend": False,
        },
        headers=headers,
    )

    assert role_response.status_code == 403
    assert status_response.status_code == 403
    assert permissions_response.status_code == 403
    assert role_response.json()["detail"] == (
        "Không được phép chỉnh sửa hoặc hạ cấp tài khoản Admin khác"
    )
    db_session.refresh(admin_b)
    assert admin_b.role == "admin"
    assert admin_b.status == "ACTIVE"
    assert admin_b.is_active is True


def test_pending_user_activates_when_temporary_password_is_changed(
    client: TestClient,
    db_session: Session,
):
    temporary_password = "TempPass123"
    user = User(
        username="pending-activation",
        email="pending.activation@example.test",
        full_name="Pending Activation",
        hashed_password=hash_password(temporary_password),
        role="employee",
        is_active=False,
        status="PENDING",
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/change-password",
        json={
            "email": user.email.upper(),
            "current_password": temporary_password,
            "new_password": "NewSecurePass456",
            "confirm_password": "NewSecurePass456",
        },
    )

    assert response.status_code == 200
    db_session.refresh(user)
    assert user.status == "ACTIVE"
    assert user.is_active is True
    assert verify_password("NewSecurePass456", user.hashed_password)
    assert client.post(
        "/api/v1/auth/login",
        json={"username": user.username, "password": "NewSecurePass456"},
    ).status_code == 200


def test_change_password_accepts_six_character_password(
    client: TestClient,
    db_session: Session,
):
    current_password = "TemporaryPass123"
    user = _create_user(db_session, "six-character-password", password=current_password)
    payload = {
        "email": user.email,
        "current_password": current_password,
        "new_password": "123456",
        "confirm_password": "123456",
    }

    response = client.post("/api/v1/auth/change-password", json=payload)

    assert response.status_code == 200
    db_session.refresh(user)
    assert verify_password("123456", user.hashed_password)

    payload["new_password"] = "12345"
    payload["confirm_password"] = "12345"
    too_short_response = client.post("/api/v1/auth/change-password", json=payload)
    assert too_short_response.status_code == 422


def test_admin_user_directory_shows_pending_and_inactive_newest_first(
    client: TestClient,
    db_session: Session,
):
    admin = _create_user(db_session, "user-list-admin", role="admin")
    inactive = _create_user(db_session, "directory-inactive")
    inactive.status = "INACTIVE"
    inactive.is_active = False
    pending = _create_user(db_session, "directory-pending")
    pending.status = "PENDING"
    pending.is_active = False
    db_session.commit()

    response = client.get(
        "/api/v1/users/?search=directory",
        headers=_auth_header(_make_token(admin)),
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [pending.id, inactive.id]
    assert [item["status"] for item in response.json()] == ["PENDING", "INACTIVE"]


def test_create_and_resend_invitation_only_email_pending_accounts(
    client: TestClient,
    db_session: Session,
    monkeypatch,
):
    from app.routers import users as users_router

    emitted = []
    monkeypatch.setattr(users_router, "generate_temporary_password", lambda: "InvitePass12")
    monkeypatch.setattr(
        users_router,
        "send_account_activation_email",
        lambda *args: emitted.append(args) or True,
    )
    admin = _create_user(db_session, "invite-admin", role="admin")
    headers = _auth_header(_make_token(admin))

    created = client.post(
        "/api/v1/users/",
        json={
            "full_name": "Invited Employee",
            "email": "invited@example.test",
            "role": "employee",
        },
        headers=headers,
    )

    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "PENDING"
    assert body["is_active"] is False
    assert body["email_sent"] is True
    account = db_session.query(User).filter_by(id=body["id"]).one()
    assert verify_password("InvitePass12", account.hashed_password)
    assert emitted[0][0] == "invited@example.test"
    assert emitted[0][4].endswith("/static/change-password.html")

    resent = client.post(
        f"/api/v1/users/{account.id}/resend-invite",
        headers=headers,
    )
    assert resent.status_code == 200
    assert resent.json()["email_sent"] is True
    assert len(emitted) == 2
    assert client.post(
        f"/api/v1/users/{admin.id}/resend-invite",
        headers=headers,
    ).status_code == 400
