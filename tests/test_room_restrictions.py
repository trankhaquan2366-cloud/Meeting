from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.restriction import UserRoomRestriction
from tests.helpers import _auth_header, _create_room, _create_user, _make_token


def test_admin_can_replace_and_clear_room_restrictions(
    client: TestClient,
    db_session: Session,
):
    admin = _create_user(db_session, "room-restriction-admin", role="admin")
    user = _create_user(db_session, "room-restriction-user")
    room = _create_room(db_session, "Room for restriction")
    headers = _auth_header(_make_token(admin))

    update_response = client.put(
        f"/api/admin/restrictions/users/{user.id}",
        json={"restrictedRoomIds": [room.id], "reason": "Dành cho ban điều hành."},
        headers=headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["restrictions"] == [
        {"room_id": room.id, "reason": "Dành cho ban điều hành."}
    ]

    get_response = client.get(
        f"/api/admin/restrictions/users/{user.id}",
        headers=headers,
    )
    assert get_response.status_code == 200
    assert get_response.json()["restrictions"] == update_response.json()["restrictions"]

    clear_response = client.put(
        f"/api/admin/restrictions/users/{user.id}",
        json={"restrictedRoomIds": [], "reason": None},
        headers=headers,
    )
    assert clear_response.status_code == 200
    assert clear_response.json()["restrictions"] == []


def test_only_admin_can_manage_room_restrictions(
    client: TestClient,
    db_session: Session,
):
    employee = _create_user(db_session, "room-restriction-employee")
    target = _create_user(db_session, "room-restriction-target")
    response = client.get(
        f"/api/admin/restrictions/users/{target.id}",
        headers=_auth_header(_make_token(employee)),
    )
    assert response.status_code == 403


def test_admin_cannot_be_restricted(
    client: TestClient,
    db_session: Session,
):
    admin = _create_user(db_session, "room-restriction-protected-admin", role="admin")
    room = _create_room(db_session, "Admin-only room")
    response = client.put(
        f"/api/admin/restrictions/users/{admin.id}",
        json={"restrictedRoomIds": [room.id], "reason": "Không áp dụng cho admin."},
        headers=_auth_header(_make_token(admin)),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Không thể giới hạn tài khoản quản trị viên."


def test_restricted_user_cannot_book_room_and_receives_reason(
    client: TestClient,
    db_session: Session,
):
    admin = _create_user(db_session, "room-restriction-booking-admin", role="admin")
    user = _create_user(db_session, "room-restriction-booking-user")
    room = _create_room(db_session, "Blocked meeting room")
    client.put(
        f"/api/admin/restrictions/users/{user.id}",
        json={"restrictedRoomIds": [room.id], "reason": "Ưu tiên cho ban điều hành."},
        headers=_auth_header(_make_token(admin)),
    )
    start = datetime.utcnow() + timedelta(days=2)
    end = start + timedelta(hours=1)

    response = client.post(
        "/api/meetings",
        json={
            "title": "Restricted booking",
            "meeting_type": "offline",
            "room_id": room.id,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        },
        headers=_auth_header(_make_token(user)),
    )

    assert response.status_code == 403
    assert "Ưu tiên cho ban điều hành." in response.json()["detail"]


def test_unrestricted_user_can_book_room(
    client: TestClient,
    db_session: Session,
):
    user = _create_user(db_session, "room-restriction-allowed-user")
    room = _create_room(db_session, "Allowed meeting room")
    start = datetime.utcnow() + timedelta(days=2)
    end = start + timedelta(hours=1)

    response = client.post(
        "/api/meetings",
        json={
            "title": "Allowed booking",
            "meeting_type": "offline",
            "room_id": room.id,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        },
        headers=_auth_header(_make_token(user)),
    )

    assert response.status_code == 201


def test_admin_can_book_a_room_with_an_existing_restriction(
    client: TestClient,
    db_session: Session,
):
    admin = _create_user(db_session, "room-restriction-admin-booking", role="admin")
    room = _create_room(db_session, "Admin unrestricted room")
    db_session.add(
        UserRoomRestriction(
            user_id=admin.id,
            room_id=room.id,
            reason="Legacy restriction should not affect admins.",
        )
    )
    db_session.commit()
    start = datetime.utcnow() + timedelta(days=2)
    end = start + timedelta(hours=1)

    response = client.post(
        "/api/meetings",
        json={
            "title": "Admin booking",
            "meeting_type": "offline",
            "room_id": room.id,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        },
        headers=_auth_header(_make_token(admin)),
    )

    assert response.status_code == 201
