from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import _auth_header, _create_room, _create_user, _make_token


def _future_window():
    start = datetime.utcnow() + timedelta(days=2)
    return start, start + timedelta(hours=1)


def test_create_offline_meeting_with_room(client: TestClient, db_session: Session):
    organizer = _create_user(db_session, "create-offline-organizer")
    room = _create_room(db_session, "Create Offline Room")
    start, end = _future_window()

    response = client.post(
        "/api/meetings/book",
        json={
            "title": "Offline meeting",
            "meeting_type": "offline",
            "room_id": room.id,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        },
        headers=_auth_header(_make_token(organizer)),
    )

    assert response.status_code == 201
    meeting = response.json()[0]
    assert meeting["meeting_type"] == "offline"
    assert meeting["room_id"] == room.id


def test_create_offline_meeting_without_room_returns_400(
    client: TestClient, db_session: Session
):
    organizer = _create_user(db_session, "create-offline-no-room")
    start, end = _future_window()

    response = client.post(
        "/api/meetings/book",
        json={
            "title": "Offline meeting without room",
            "meeting_type": "offline",
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        },
        headers=_auth_header(_make_token(organizer)),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Offline meetings require a room_id"


def test_create_online_meeting_with_link(client: TestClient, db_session: Session):
    organizer = _create_user(db_session, "create-online-organizer")
    start, end = _future_window()

    response = client.post(
        "/api/meetings/book",
        json={
            "title": "Online meeting",
            "meeting_type": "online",
            "meeting_link": "https://meet.test/room",
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        },
        headers=_auth_header(_make_token(organizer)),
    )

    assert response.status_code == 201
    meeting = response.json()[0]
    assert meeting["meeting_type"] == "online"
    assert meeting["meeting_link"] == "https://meet.test/room"
    assert meeting["room_id"] is None


def test_create_online_meeting_without_link_returns_400(
    client: TestClient, db_session: Session
):
    organizer = _create_user(db_session, "create-online-no-link")
    start, end = _future_window()

    response = client.post(
        "/api/meetings/book",
        json={
            "title": "Online meeting without link",
            "meeting_type": "online",
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        },
        headers=_auth_header(_make_token(organizer)),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Online meetings require a meeting_link"