"""Tests for the personal meeting list and invite responses."""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from app import main
from tests.helpers import (
    _add_participant,
    _auth_header,
    _create_meeting,
    _create_room,
    _create_user,
    _make_token,
)


def test_mine_separates_organizer_and_invitee_and_includes_rsvp(
    client: TestClient, db_session: Session
):
    organizer = _create_user(db_session, "mine_organizer")
    invitee = _create_user(db_session, "mine_invitee")
    outsider = _create_user(db_session, "mine_outsider")
    room = _create_room(db_session, "Mine Room")
    meeting = _create_meeting(
        db_session,
        room,
        organizer,
        datetime.utcnow() + timedelta(days=1),
        datetime.utcnow() + timedelta(days=1, hours=1),
    )
    canceled_meeting = _create_meeting(
        db_session,
        room,
        organizer,
        datetime.utcnow() + timedelta(days=3),
        datetime.utcnow() + timedelta(days=3, hours=1),
        status="canceled",
    )
    participation = _add_participant(db_session, meeting, invitee)
    participation.response_status = "accepted"
    db_session.commit()

    organizer_response = client.get(
        "/api/meetings/mine", headers=_auth_header(_make_token(organizer))
    )
    assert organizer_response.status_code == 200
    organizer_item = organizer_response.json()[0]
    assert organizer_item["id"] == meeting.id
    assert organizer_item["is_organizer"] is True
    assert organizer_item["participants"][0]["response_status"] == "accepted"
    assert all(item["id"] != canceled_meeting.id for item in organizer_response.json())

    invitee_response = client.get(
        "/api/meetings/mine", headers=_auth_header(_make_token(invitee))
    )
    assert invitee_response.status_code == 200
    invitee_item = invitee_response.json()[0]
    assert invitee_item["is_organizer"] is False
    assert invitee_item["my_response_status"] == "accepted"

    outsider_response = client.get(
        "/api/meetings/mine", headers=_auth_header(_make_token(outsider))
    )
    assert outsider_response.status_code == 200
    assert outsider_response.json() == []


def test_invitee_can_update_own_response_but_nonparticipant_cannot(
    client: TestClient, db_session: Session
):
    organizer = _create_user(db_session, "rsvp_organizer")
    invitee = _create_user(db_session, "rsvp_invitee")
    outsider = _create_user(db_session, "rsvp_outsider")
    room = _create_room(db_session, "RSVP Room")
    meeting = _create_meeting(
        db_session,
        room,
        organizer,
        datetime.utcnow() + timedelta(days=2),
        datetime.utcnow() + timedelta(days=2, hours=1),
    )
    _add_participant(db_session, meeting, invitee)

    response = client.patch(
        f"/api/meetings/{meeting.id}/response",
        headers=_auth_header(_make_token(invitee)),
        json={"response_status": "declined"},
    )
    assert response.status_code == 200
    assert response.json()["response_status"] == "declined"

    outsider_response = client.patch(
        f"/api/meetings/{meeting.id}/response",
        headers=_auth_header(_make_token(outsider)),
        json={"response_status": "accepted"},
    )
    assert outsider_response.status_code == 404

    invalid_response = client.patch(
        f"/api/meetings/{meeting.id}/response",
        headers=_auth_header(_make_token(invitee)),
        json={"response_status": "maybe"},
    )
    assert invalid_response.status_code == 422


def test_mine_handles_missing_organizer_and_room_relationships(
    client: TestClient, db_session: Session
):
    organizer = _create_user(db_session, "orphan_organizer")
    invitee = _create_user(db_session, "orphan_invitee")
    room = _create_room(db_session, "Orphan Room")
    meeting = _create_meeting(
        db_session,
        room,
        organizer,
        datetime.utcnow() + timedelta(days=2),
        datetime.utcnow() + timedelta(days=2, hours=1),
    )
    _add_participant(db_session, meeting, invitee)
    meeting.organizer_id = None
    meeting.room_id = None
    db_session.commit()

    response = client.get(
        "/api/meetings/mine", headers=_auth_header(_make_token(invitee))
    )

    assert response.status_code == 200
    item = response.json()[0]
    assert item["organizer_name"] == "Người tổ chức"
    assert item["room_name"] is None
    assert item["is_organizer"] is False


def test_missing_rsvp_column_returns_actionable_service_error(
    client: TestClient, db_session: Session
):
    organizer = _create_user(db_session, "schema_organizer")
    invitee = _create_user(db_session, "schema_invitee")
    room = _create_room(db_session, "Schema Room")
    meeting = _create_meeting(
        db_session,
        room,
        organizer,
        datetime.utcnow() - timedelta(days=4, hours=1),
        datetime.utcnow() - timedelta(days=4),
    )
    _add_participant(db_session, meeting, invitee)
    meeting_id = meeting.id
    db_session.execute(text("ALTER TABLE meeting_participants DROP COLUMN response_status"))
    db_session.commit()

    headers = _auth_header(_make_token(invitee))
    mine_response = client.get("/api/meetings/mine", headers=headers)
    assert mine_response.status_code == 503
    assert "schema/migration" in mine_response.json()["detail"]

    list_response = client.get("/api/meetings/")
    assert list_response.status_code == 503
    history_response = client.get("/api/meetings/history", headers=headers)
    assert history_response.status_code == 503

    rsvp_response = client.patch(
        f"/api/meetings/{meeting_id}/response",
        headers=headers,
        json={"response_status": "accepted"},
    )
    assert rsvp_response.status_code == 503
    assert "schema/migration" in rsvp_response.json()["detail"]


def test_startup_migration_adds_missing_rsvp_column(monkeypatch):
    migration_engine = create_engine("sqlite://")
    with migration_engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE meeting_participants "
            "(id INTEGER PRIMARY KEY, meeting_id INTEGER NOT NULL, user_id INTEGER NOT NULL)"
        ))

    monkeypatch.setattr(main, "engine", migration_engine)
    try:
        main._auto_migrate_schema()
        columns = {column["name"] for column in inspect(migration_engine).get_columns("meeting_participants")}
        assert "response_status" in columns
    finally:
        migration_engine.dispose()
