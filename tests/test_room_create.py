from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

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