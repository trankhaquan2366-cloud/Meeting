from datetime import datetime, timedelta, timezone
from datetime import date, time
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.meeting import Meeting
from app.services.scheduler import process_no_show_meetings
from tests.helpers import (
    _auth_header,
    _create_meeting,
    _create_room,
    _create_user,
    _make_token,
)


def _today_window(duration_minutes: int = 60) -> tuple[datetime, datetime]:
    start = datetime.now(timezone.utc).replace(tzinfo=None)
    return start, start + timedelta(minutes=duration_minutes)


def test_manual_cancel_saves_cancellation_reason(
    client: TestClient,
    db_session: Session,
) -> None:
    organizer = _create_user(db_session, f"cancel-reason-{uuid4().hex}")
    room = _create_room(db_session, f"Cancel reason room {uuid4().hex}")
    start, end = _today_window()
    meeting = _create_meeting(db_session, room, organizer, start, end)
    reason = "Người chủ trì bận việc đột xuất"

    response = client.patch(
        f"/api/meetings/{meeting.id}/cancel",
        json={"cancellation_reason": reason},
        headers=_auth_header(_make_token(organizer)),
    )

    assert response.status_code == 200
    assert response.json()["cancellation_reason"] == reason
    db_session.refresh(meeting)
    assert meeting.status == "CANCELLED"
    assert meeting.cancellation_reason == reason
    assert meeting.cancelled_at is not None


def test_no_show_scheduler_saves_default_cancellation_reason(
    db_session: Session,
) -> None:
    organizer = _create_user(db_session, f"no-show-reason-{uuid4().hex}")
    room = _create_room(db_session, f"No-show room {uuid4().hex}")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    start = now - timedelta(minutes=16)
    meeting = _create_meeting(
        db_session,
        room,
        organizer,
        start,
        start + timedelta(hours=1),
    )

    assert process_no_show_meetings(db_session, now=now) == 1

    db_session.refresh(meeting)
    assert meeting.status == "CANCELLED_NO_SHOW"
    assert meeting.cancellation_reason == "Tự động hủy do quá 15 phút không check-in"
    assert meeting.cancelled_at == now


def test_admin_cancellation_analytics_filters_and_permissions(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = _create_user(db_session, f"analytics-admin-{uuid4().hex}", role="admin")
    employee = _create_user(db_session, f"analytics-user-{uuid4().hex}")
    organizer = _create_user(db_session, f"analytics-organizer-{uuid4().hex}")
    first_room = _create_room(db_session, f"Analytics room A {uuid4().hex}")
    second_room = _create_room(db_session, f"Analytics room B {uuid4().hex}")
    headers = _auth_header(_make_token(organizer))

    start, end = _today_window(60)
    manual_one = _create_meeting(
        db_session, first_room, organizer, start, end
    )
    response = client.patch(
        f"/api/meetings/{manual_one.id}/cancel",
        json={"cancellation_reason": "Khách mời không thể tham dự"},
        headers=headers,
    )
    assert response.status_code == 200

    start, end = _today_window(30)
    no_show = Meeting(
        title="Analytics no-show",
        room_id=first_room.id,
        organizer_id=organizer.id,
        start_time=start - timedelta(minutes=16),
        end_time=start - timedelta(minutes=16) + timedelta(minutes=30),
        status="SCHEDULED",
    )
    db_session.add(no_show)
    db_session.commit()
    assert process_no_show_meetings(
        db_session,
        now=start,
    ) == 1

    start, end = _today_window(120)
    manual_two = _create_meeting(
        db_session, second_room, organizer, start, end
    )
    response = client.patch(
        f"/api/meetings/{manual_two.id}/cancel",
        json={"cancellation_reason": "Khách mời không thể tham dự"},
        headers=headers,
    )
    assert response.status_code == 200

    response = client.get(
        "/api/v1/admin/analytics/cancellations",
        headers=_auth_header(_make_token(admin)),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["summary"] == {
        "total_cancelled": 3,
        "cancelled_by_user": 2,
        "cancelled_no_show": 1,
        "total_wasted_hours": 3.5,
    }
    assert data["breakdown_by_reason"] == [
        {"reason": "Khách mời không thể tham dự", "cancel_count": 2},
        {
            "reason": "Tự động hủy do quá 15 phút không check-in",
            "cancel_count": 1,
        },
    ]
    assert data["top_cancelled_rooms"][0] == {
        "room_id": first_room.id,
        "room_name": first_room.name,
        "cancel_count": 2,
    }
    assert data["top_offenders"][0] == {
        "user_id": organizer.id,
        "user_name": organizer.full_name,
        "cancel_count": 3,
    }

    filtered = client.get(
        "/api/v1/admin/analytics/cancellations",
        params={"room_id": second_room.id},
        headers=_auth_header(_make_token(admin)),
    )
    assert filtered.status_code == 200
    assert filtered.json()["summary"]["total_cancelled"] == 1

    forbidden = client.get(
        "/api/v1/admin/analytics/cancellations",
        headers=_auth_header(_make_token(employee)),
    )
    assert forbidden.status_code == 403

    unauthorized = client.get("/api/v1/admin/analytics/cancellations")
    assert unauthorized.status_code == 401


def test_analytics_labels_missing_reasons_and_includes_end_date_boundary(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = _create_user(db_session, f"analytics-legacy-admin-{uuid4().hex}", role="admin")
    organizer = _create_user(db_session, f"analytics-legacy-organizer-{uuid4().hex}")
    room = _create_room(db_session, f"Analytics legacy room {uuid4().hex}")
    report_date = date.today()
    start_of_day = datetime.combine(report_date, time.min)
    end_of_day = datetime.combine(report_date, time.max)

    old_manual = _create_meeting(
        db_session,
        room,
        organizer,
        start_of_day,
        start_of_day + timedelta(minutes=30),
    )
    old_manual.status = "CANCELLED"
    old_manual.cancellation_reason = None
    old_manual.cancelled_at = end_of_day

    old_no_show = _create_meeting(
        db_session,
        room,
        organizer,
        start_of_day + timedelta(hours=1),
        start_of_day + timedelta(hours=2),
    )
    old_no_show.status = "CANCELLED_NO_SHOW"
    old_no_show.cancellation_reason = ""
    old_no_show.cancelled_at = end_of_day
    db_session.commit()

    response = client.get(
        "/api/v1/admin/analytics/cancellations",
        params={
            "start_date": report_date.isoformat(),
            "end_date": report_date.isoformat(),
        },
        headers=_auth_header(_make_token(admin)),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["total_cancelled"] == 2
    assert {
        item["reason"]: item["cancel_count"]
        for item in data["breakdown_by_reason"]
    } == {
        "Tự động hủy (No-Show)": 1,
        "Không có lý do (Hủy cũ)": 1,
    }


def test_export_cancellation_analytics_excel_success(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = _create_user(db_session, f"export-excel-admin-{uuid4().hex}", role="admin")
    response = client.get(
        "/api/v1/admin/analytics/cancellations/export",
        params={"format": "excel"},
        headers=_auth_header(_make_token(admin)),
    )

    assert response.status_code == 200
    assert "filename=" in response.headers["content-disposition"]
    assert response.headers["content-disposition"].endswith(".xlsx\"")
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert response.content.startswith(b"PK")


def test_export_cancellation_analytics_pdf_success(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = _create_user(db_session, f"export-pdf-admin-{uuid4().hex}", role="admin")
    response = client.get(
        "/api/v1/admin/analytics/cancellations/export",
        params={"format": "pdf"},
        headers=_auth_header(_make_token(admin)),
    )

    assert response.status_code == 200
    assert response.headers["content-disposition"].endswith(".pdf\"")
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.content.startswith(b"%PDF")


def test_export_cancellation_analytics_unauthorized(
    client: TestClient,
    db_session: Session,
) -> None:
    employee = _create_user(db_session, f"export-employee-{uuid4().hex}")
    response = client.get(
        "/api/v1/admin/analytics/cancellations/export",
        params={"format": "excel"},
        headers=_auth_header(_make_token(employee)),
    )

    assert response.status_code == 403
