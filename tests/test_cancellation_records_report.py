from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.meeting import Meeting
from tests.helpers import (
    _auth_header,
    _create_meeting,
    _create_room,
    _create_user,
    _make_token,
)


def test_cancellation_records_report_requires_admin(client: TestClient, db_session: Session):
    employee = _create_user(db_session, "cancellation-records-employee")

    assert client.get("/api/reports/cancellations").status_code == 401
    response = client.get(
        "/api/reports/cancellations",
        headers=_auth_header(_make_token(employee)),
    )

    assert response.status_code == 403


def test_cancellation_records_report_filters_date_and_returns_relations(
    client: TestClient,
    db_session: Session,
):
    admin = _create_user(db_session, "cancellation-records-admin", role="admin")
    organizer = _create_user(db_session, "cancellation-records-organizer")
    room = _create_room(db_session, "Cancellation report room")
    now = datetime.utcnow().replace(microsecond=0)

    included = _create_meeting(
        db_session,
        room,
        organizer,
        now + timedelta(days=2),
        now + timedelta(days=2, hours=1),
    )
    included.status = "CANCELLED"
    included.cancellation_reason = "Phòng cần bảo trì"
    included.cancelled_at = now
    included.cancel_reason = "Phòng cần bảo trì"

    excluded = _create_meeting(
        db_session,
        room,
        organizer,
        now + timedelta(days=3),
        now + timedelta(days=3, hours=1),
    )
    excluded.status = "CANCELLED"
    excluded.cancelled_at = now - timedelta(days=2)
    db_session.commit()

    response = client.get(
        f"/api/reports/cancellations?start_date={now.date()}&end_date={now.date()}",
        headers=_auth_header(_make_token(admin)),
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": included.id,
            "title": included.title,
            "status": "CANCELLED",
            "cancel_reason": "Phòng cần bảo trì",
            "cancellation_reason": "Phòng cần bảo trì",
            "cancelled_at": now.isoformat(),
            "start_time": included.start_time.isoformat(),
            "end_time": included.end_time.isoformat(),
            "organizer": {
                "id": organizer.id,
                "full_name": organizer.full_name,
                "username": organizer.username,
            },
            "room": {"id": room.id, "name": room.name},
        }
    ]


def test_meeting_cancel_reason_alias_uses_existing_database_column():
    meeting = Meeting(cancellation_reason="Organizer unavailable")

    assert meeting.cancel_reason == "Organizer unavailable"
    meeting.cancel_reason = "Room unavailable"
    assert meeting.cancellation_reason == "Room unavailable"
