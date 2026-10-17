from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.meeting import Meeting
from tests.helpers import (
    _add_participant,
    _auth_header,
    _create_room,
    _create_user,
    _make_token,
)


SMART_QR_URL = "/api/v1/meetings/smart-qr-action"


def _create_smart_qr_meeting(
    db_session: Session,
    *,
    room,
    organizer,
    start_time: datetime,
    status: str = "scheduled",
) -> Meeting:
    meeting = Meeting(
        title="Smart QR test meeting",
        room_id=room.id,
        organizer_id=organizer.id,
        start_time=start_time,
        end_time=start_time + timedelta(hours=1),
        status=status,
    )
    db_session.add(meeting)
    db_session.commit()
    db_session.refresh(meeting)
    return meeting


def _scan_room_qr(client: TestClient, user, room, payload: str | None = None):
    return client.post(
        SMART_QR_URL,
        json={"qr_payload": payload or str(room.id)},
        headers=_auth_header(_make_token(user)),
    )


@pytest.mark.parametrize("participant_scans", [False, True], ids=["organizer", "attendee"])
def test_smart_qr_checkin_success_within_time_window(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    participant_scans: bool,
):
    now = datetime(2026, 10, 11, 10, 0)
    monkeypatch.setattr("app.services.meeting_service._vietnam_now", lambda: now)
    organizer = _create_user(db_session, f"smart-qr-organizer-{participant_scans}")
    scanner = (
        _create_user(db_session, "smart-qr-attendee")
        if participant_scans
        else organizer
    )
    room = _create_room(db_session, f"Smart QR room {participant_scans}")
    meeting = _create_smart_qr_meeting(
        db_session,
        room=room,
        organizer=organizer,
        start_time=now + timedelta(minutes=10),
    )
    if participant_scans:
        _add_participant(db_session, meeting, scanner)

    response = _scan_room_qr(client, scanner, room)

    assert response.status_code == 200
    assert response.json()["action"] == "CHECK_IN"
    assert response.json()["meeting_id"] == meeting.id
    db_session.refresh(meeting)
    assert meeting.status == "IN_PROGRESS"
    assert meeting.check_in_time == now


@pytest.mark.parametrize("use_room_qr", [False, True], ids=["meeting-check-in", "smart-room-qr"])
def test_qr_checkin_uses_vietnam_time_when_server_clock_is_utc(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    use_room_qr: bool,
):
    now_vn = datetime(2026, 10, 11, 10, 0)
    monkeypatch.setattr(
        "app.services.meeting_service._vietnam_now",
        lambda: now_vn,
    )
    monkeypatch.setattr(
        "app.services.meeting_service._utc_now",
        lambda: now_vn - timedelta(hours=7),
    )
    organizer = _create_user(db_session, f"smart-qr-timezone-{use_room_qr}")
    room = _create_room(db_session, f"Smart QR timezone room {use_room_qr}")
    meeting = _create_smart_qr_meeting(
        db_session,
        room=room,
        organizer=organizer,
        start_time=now_vn + timedelta(minutes=10),
    )
    headers = _auth_header(_make_token(organizer))

    if use_room_qr:
        response = _scan_room_qr(client, organizer, room)
        assert response.status_code == 200
        assert response.json()["action"] == "CHECK_IN"
    else:
        response = client.post(
            f"/api/v1/meetings/{meeting.id}/check-in",
            json={"qr_token": room.qr_token},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "IN_PROGRESS"

    db_session.refresh(meeting)
    assert meeting.status == "IN_PROGRESS"
    assert meeting.check_in_time == now_vn


def test_smart_qr_checkin_rejected_too_early(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
):
    now = datetime(2026, 10, 11, 10, 0)
    monkeypatch.setattr("app.services.meeting_service._vietnam_now", lambda: now)
    organizer = _create_user(db_session, "smart-qr-early")
    room = _create_room(db_session, "Smart QR early room")
    _create_smart_qr_meeting(
        db_session,
        room=room,
        organizer=organizer,
        start_time=now + timedelta(minutes=30),
    )

    response = _scan_room_qr(client, organizer, room)

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Chưa đến giờ check-in. Bạn chỉ có thể check-in trước giờ "
        "bắt đầu tối đa 15 phút."
    )


def test_smart_qr_checkin_accepts_room_qr_token(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
):
    now = datetime(2026, 10, 11, 10, 0)
    monkeypatch.setattr("app.services.meeting_service._vietnam_now", lambda: now)
    organizer = _create_user(db_session, "smart-qr-token")
    room = _create_room(db_session, "Smart QR token room")
    meeting = _create_smart_qr_meeting(
        db_session,
        room=room,
        organizer=organizer,
        start_time=now + timedelta(minutes=10),
    )

    response = _scan_room_qr(client, organizer, room, room.qr_token)

    assert response.status_code == 200
    assert response.json()["action"] == "CHECK_IN"
    assert response.json()["meeting_id"] == meeting.id


def test_smart_qr_checkin_rejected_too_late(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
):
    now = datetime(2026, 10, 11, 10, 0)
    monkeypatch.setattr("app.services.meeting_service._vietnam_now", lambda: now)
    organizer = _create_user(db_session, "smart-qr-late")
    room = _create_room(db_session, "Smart QR late room")
    _create_smart_qr_meeting(
        db_session,
        room=room,
        organizer=organizer,
        start_time=now - timedelta(minutes=16),
    )

    response = _scan_room_qr(client, organizer, room)

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Đã quá thời hạn check-in cuộc họp (quá 15 phút so với giờ bắt đầu)."
    )


def test_smart_qr_checkin_rejected_unauthorized_user(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
):
    now = datetime(2026, 10, 11, 10, 0)
    monkeypatch.setattr("app.services.meeting_service._vietnam_now", lambda: now)
    organizer = _create_user(db_session, "smart-qr-owner")
    unauthorized = _create_user(db_session, "smart-qr-outsider")
    room = _create_room(db_session, "Smart QR private room")
    _create_smart_qr_meeting(
        db_session,
        room=room,
        organizer=organizer,
        start_time=now + timedelta(minutes=10),
    )

    response = _scan_room_qr(client, unauthorized, room)

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Bạn không nằm trong danh sách tham gia cuộc họp này."
    )


def test_smart_qr_checkout_success(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
):
    now = datetime(2026, 10, 11, 10, 0)
    monkeypatch.setattr("app.services.meeting_service._vietnam_now", lambda: now)
    organizer = _create_user(db_session, "smart-qr-checkout")
    room = _create_room(db_session, "Smart QR checkout room")
    meeting = _create_smart_qr_meeting(
        db_session,
        room=room,
        organizer=organizer,
        start_time=now - timedelta(minutes=10),
        status="IN_PROGRESS",
    )

    response = _scan_room_qr(client, organizer, room)

    assert response.status_code == 200
    assert response.json()["action"] == "CHECK_OUT"
    assert response.json()["message"] == (
        f"Đã Check-out & Giải phóng phòng {room.name} thành công!"
    )
    db_session.refresh(meeting)
    assert meeting.status == "COMPLETED"
    assert meeting.check_out_time == now
