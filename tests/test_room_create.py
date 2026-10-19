from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.equipment import Equipment
from app.models.room import Room
from app.services.room_service import get_available_rooms
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


def test_admin_can_create_room_with_inventory_status_and_details(
    client: TestClient,
    db_session: Session,
):
    admin = _create_user(db_session, "room-fields-admin", role="admin")
    display = Equipment(name="Room display", total_qty=2, is_active=True)
    db_session.add(display)
    db_session.commit()

    response = client.post(
        "/api/rooms/",
        json={
            "name": "Enterprise room",
            "location": "Floor 4",
            "capacity": 12,
            "room_status": "active",
            "equipment_ids": [display.id],
            "room_image": "https://example.com/room.jpg",
            "layout_type": "boardroom",
        },
        headers=_auth_header(_make_token(admin)),
    )

    assert response.status_code == 201
    room_data = response.json()
    assert room_data["room_status"] == "active"
    assert room_data["is_active"] is True
    assert room_data["equipment_ids"] == [display.id]
    assert room_data["amenities"] == ["Room display"]
    assert room_data["room_image"] == "https://example.com/room.jpg"
    assert room_data["layout_type"] == "boardroom"

    room = db_session.query(Room).filter(Room.id == room_data["id"]).one()
    assert [(item.equipment_id, item.quantity) for item in room.default_equipments] == [(display.id, 1)]

    update_response = client.put(
        f"/api/rooms/{room.id}/",
        json={"room_status": "maintenance", "equipment_ids": []},
        headers=_auth_header(_make_token(admin)),
    )
    assert update_response.status_code == 200
    assert update_response.json()["room_status"] == "maintenance"
    assert update_response.json()["is_active"] is False
    assert update_response.json()["equipment_ids"] == []
    assert client.get("/api/rooms/").json() == []


def test_room_equipment_ids_must_reference_active_inventory(client: TestClient, db_session: Session):
    admin = _create_user(db_session, "room-equipment-admin", role="admin")
    inactive_equipment = Equipment(name="Inactive room display", total_qty=1, is_active=False)
    db_session.add(inactive_equipment)
    db_session.commit()

    response = client.post(
        "/api/rooms/",
        json={
            "name": "Invalid equipment room",
            "capacity": 4,
            "equipment_ids": [inactive_equipment.id],
        },
        headers=_auth_header(_make_token(admin)),
    )

    assert response.status_code == 422
    assert response.json()["detail"]["equipment_ids"] == [inactive_equipment.id]


def test_room_search_excludes_non_active_operational_status(db_session: Session):
    active_room = Room(name="Bookable room", capacity=8, is_active=True, room_status="active")
    inconsistent_room = Room(name="Locked but flagged active", capacity=8, is_active=True, room_status="locked")
    db_session.add_all([active_room, inconsistent_room])
    db_session.commit()

    available = get_available_rooms(
        db_session,
        datetime(2035, 1, 1, 9, 0),
        datetime(2035, 1, 1, 10, 0),
    )

    assert [room.id for room in available] == [active_room.id]