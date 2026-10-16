from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.room import Room
from tests.helpers import _auth_header, _create_user, _make_token


def test_admin_can_create_room_with_amenities(client: TestClient, db_session: Session):
    admin = _create_user(db_session, "room-create-admin", role="admin")

    response = client.post(
        "/api/rooms/",
        json={
            "name": "API-created room",
            "location": "Floor 3",
            "capacity": 10,
            "amenities": ["Screen", "Wi-Fi"],
            "is_active": True,
        },
        headers=_auth_header(_make_token(admin)),
    )

    assert response.status_code == 201
    assert response.json()["name"] == "API-created room"
    assert response.json()["amenities"] == ["Screen", "Wi-Fi"]


def test_admin_can_list_rooms_including_maintenance(client: TestClient, db_session: Session):
    admin = _create_user(db_session, "room-status-admin", role="admin")
    user = _create_user(db_session, "room-status-user", role="user")
    db_session.add_all([
        Room(name="Active room", capacity=8, is_active=True),
        Room(name="Maintenance room", capacity=8, is_active=False),
    ])
    db_session.commit()

    headers = _auth_header(_make_token(admin))
    all_rooms_response = client.get("/api/rooms/all-status/", headers=headers)
    active_rooms_response = client.get("/api/rooms/", headers=headers)
    unauthorized_response = client.get("/api/rooms/all-status/")
    forbidden_response = client.get(
        "/api/rooms/all-status/",
        headers=_auth_header(_make_token(user)),
    )

    assert all_rooms_response.status_code == 200
    assert {room["name"] for room in all_rooms_response.json()} == {"Active room", "Maintenance room"}
    assert active_rooms_response.status_code == 200
    assert {room["name"] for room in active_rooms_response.json()} == {"Active room"}
    assert unauthorized_response.status_code == 401
    assert forbidden_response.status_code == 403