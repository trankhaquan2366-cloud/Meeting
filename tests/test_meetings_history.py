"""Tests for GET /api/meetings/history."""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import (
    _create_user,
    _create_room,
    _create_meeting,
    _add_participant,
    _make_token,
    _auth_header,
)


class TestNoToken:
    def test_returns_401_without_token(self, client: TestClient):
        resp = client.get("/api/meetings/history")
        assert resp.status_code == 401


class TestOrganizerSeesMeeting:
    def test_organizer_in_history(self, client: TestClient, db_session: Session):
        org = _create_user(db_session, "organizer")
        room = _create_room(db_session)
        past = datetime.utcnow() - timedelta(days=3)
        end = datetime.utcnow() - timedelta(days=1)
        m = _create_meeting(db_session, room, org, past, end)

        resp = client.get("/api/meetings/history", headers=_auth_header(_make_token(org)))
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()]
        assert m.id in ids


class TestParticipantSeesMeeting:
    def test_invited_user_in_history(self, client: TestClient, db_session: Session):
        org = _create_user(db_session, "organizer2")
        invitee = _create_user(db_session, "invitee")
        room = _create_room(db_session, "Room B")
        past = datetime.utcnow() - timedelta(days=5)
        end = datetime.utcnow() - timedelta(days=4)
        m = _create_meeting(db_session, room, org, past, end)
        _add_participant(db_session, m, invitee)

        resp = client.get("/api/meetings/history", headers=_auth_header(_make_token(invitee)))
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()]
        assert m.id in ids


class TestNonParticipantExcluded:
    def test_outsider_sees_nothing(self, client: TestClient, db_session: Session):
        org = _create_user(db_session, "organizer3")
        outsider = _create_user(db_session, "outsider")
        room = _create_room(db_session, "Room C")
        past = datetime.utcnow() - timedelta(days=7)
        end = datetime.utcnow() - timedelta(days=6)
        _create_meeting(db_session, room, org, past, end)

        resp = client.get("/api/meetings/history", headers=_auth_header(_make_token(outsider)))
        assert resp.status_code == 200
        assert resp.json() == []


class TestFutureMeetingExcluded:
    def test_future_meeting_not_in_history(self, client: TestClient, db_session: Session):
        org = _create_user(db_session, "organizer4")
        room = _create_room(db_session, "Room D")
        future_start = datetime.utcnow() + timedelta(days=1)
        future_end = datetime.utcnow() + timedelta(days=2)
        m = _create_meeting(db_session, room, org, future_start, future_end)

        resp = client.get("/api/meetings/history", headers=_auth_header(_make_token(org)))
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()]
        assert m.id not in ids


class TestCanceledMeetingExcluded:
    def test_canceled_meeting_not_in_history(self, client: TestClient, db_session: Session):
        org = _create_user(db_session, "organizer5")
        room = _create_room(db_session, "Room E")
        past = datetime.utcnow() - timedelta(days=10)
        end = datetime.utcnow() - timedelta(days=9)
        m = _create_meeting(db_session, room, org, past, end, status="CANCELLED")

        resp = client.get("/api/meetings/history", headers=_auth_header(_make_token(org)))
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()]
        assert m.id not in ids


class TestNoDuplicates:
    def test_no_duplicate_when_organizer_and_participant(self, client: TestClient, db_session: Session):
        org = _create_user(db_session, "organizer6")
        room = _create_room(db_session, "Room F")
        past = datetime.utcnow() - timedelta(days=2)
        end = datetime.utcnow() - timedelta(hours=1)
        m = _create_meeting(db_session, room, org, past, end)
        _add_participant(db_session, m, org)

        resp = client.get("/api/meetings/history", headers=_auth_header(_make_token(org)))
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()]
        assert ids.count(m.id) == 1, "Duplicate records must not be returned"


class TestOrderByDesc:
    def test_ordered_by_end_time_desc(self, client: TestClient, db_session: Session):
        org = _create_user(db_session, "organizer7")
        room = _create_room(db_session, "Room G")
        m1 = _create_meeting(db_session, room, org,
                             datetime.utcnow() - timedelta(days=10),
                             datetime.utcnow() - timedelta(days=9))
        m2 = _create_meeting(db_session, room, org,
                             datetime.utcnow() - timedelta(days=3),
                             datetime.utcnow() - timedelta(days=2))
        m3 = _create_meeting(db_session, room, org,
                             datetime.utcnow() - timedelta(days=20),
                             datetime.utcnow() - timedelta(days=19))

        resp = client.get("/api/meetings/history", headers=_auth_header(_make_token(org)))
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()]
        assert ids == [m2.id, m1.id, m3.id]


class TestResponseShape:
    def test_response_has_expected_fields(self, client: TestClient, db_session: Session):
        org = _create_user(db_session, "organizer8")
        room = _create_room(db_session, "Room H")
        past = datetime.utcnow() - timedelta(days=5)
        end = datetime.utcnow() - timedelta(days=4)
        _create_meeting(db_session, room, org, past, end)

        resp = client.get("/api/meetings/history", headers=_auth_header(_make_token(org)))
        assert resp.status_code == 200
        item = resp.json()[0]
        expected = {
            "id", "title", "description",
            "meeting_type", "online_link",
            "room_id", "organizer_id",
            "start_time", "end_time", "status",
            "is_recurring", "recurring_type",
            "equipments", "participant_ids",
        }
        assert set(item.keys()) == expected
