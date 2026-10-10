"""Real-time API smoke test for the QR check-in/check-out flow."""

from datetime import datetime, timedelta, timezone
import sys
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.equipment import Equipment, MeetingEquipment
from app.models.meeting import Meeting
from app.models.notification import Notification
from tests.helpers import _auth_header, _create_room, _create_user, _make_token


def test_live_checkin_notification_and_checkout(
    client: TestClient,
    db_session: Session,
) -> None:
    """Run both authenticated endpoints using the current UTC time."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    suffix = uuid4().hex
    organizer_user = _create_user(db_session, f"live-checkin-{suffix}")
    room = _create_room(db_session, f"Phòng Test 22h {suffix}")
    assert room.qr_token, "Test room did not receive a QR token"

    equipment = Equipment(
        name=f"Live check-in equipment {suffix}",
        code=f"LIVE-{suffix[:12]}",
        total_qty=1,
        is_active=True,
    )
    db_session.add(equipment)
    db_session.flush()

    start_time = datetime.now(timezone.utc).replace(tzinfo=None)
    end_time = start_time + timedelta(hours=1)
    meeting = Meeting(
        title=f"Live QR check-in test {suffix}",
        room_id=room.id,
        organizer_id=organizer_user.id,
        start_time=start_time,
        end_time=end_time,
        status="SCHEDULED",
    )
    db_session.add(meeting)
    db_session.flush()
    db_session.add(
        MeetingEquipment(
            meeting_id=meeting.id,
            equipment_id=equipment.id,
            quantity=1,
        )
    )
    db_session.commit()
    db_session.refresh(meeting)

    auth_headers = _auth_header(_make_token(organizer_user))
    failures: list[str] = []

    print(f"[STEP] Tạo cuộc họp '{meeting.title}' trong phòng '{room.name}'")
    print(
        f"[INFO] Bắt đầu UTC: {start_time.isoformat()} | "
        f"Kết thúc UTC: {end_time.isoformat()}"
    )

    check_in_response = client.post(
        f"/api/v1/meetings/{meeting.id}/check-in",
        json={"qr_token": room.qr_token},
        headers=auth_headers,
    )
    check_in_data = (
        check_in_response.json() if check_in_response.status_code == 200 else {}
    )
    check_in_time = check_in_data.get("check_in_time")
    if (
        check_in_response.status_code == 200
        and check_in_data.get("status", "").upper() == "IN_PROGRESS"
        and check_in_time
    ):
        print(f"[SUCCESS] Check-in thành công lúc: {check_in_time}")
    else:
        print(
            "[FAIL] Check-in không thành công: "
            f"HTTP {check_in_response.status_code} {check_in_response.text}"
        )
        failures.append("Check-in response/status/timestamp invalid")

    db_session.expire_all()
    organizer_notifications = (
        db_session.query(Notification)
        .filter(Notification.user_id == organizer_user.id)
        .all()
    )
    check_in_notification = next(
        (
            notification
            for notification in organizer_notifications
            if any(
                term in f"{notification.title} {notification.content}".casefold()
                for term in ("check-in", "check in", "đã bắt đầu")
            )
        ),
        None,
    )
    if check_in_notification is not None:
        print(
            "[NOTIFICATION] Đã gửi phản hồi tới Chủ trì: "
            f"{organizer_user.full_name} — {check_in_notification.title}"
        )
    else:
        print(
            "[FAIL] Chưa tìm thấy notification check-in/đã bắt đầu "
            f"cho Chủ trì: {organizer_user.full_name}"
        )
        failures.append("No check-in notification was created for the organizer")

    check_out_response = client.post(
        f"/api/v1/meetings/{meeting.id}/check-out",
        json={"qr_token": room.qr_token},
        headers=auth_headers,
    )
    check_out_data = (
        check_out_response.json() if check_out_response.status_code == 200 else {}
    )
    check_out_time = check_out_data.get("check_out_time")
    if (
        check_out_response.status_code == 200
        and check_out_data.get("status", "").upper() == "COMPLETED"
        and check_out_time
    ):
        print(f"[SUCCESS] Check-out thành công lúc: {check_out_time}")
    else:
        print(
            "[FAIL] Check-out không thành công: "
            f"HTTP {check_out_response.status_code} {check_out_response.text}"
        )
        failures.append("Check-out response/status/timestamp invalid")

    availability_start = datetime.now(timezone.utc).replace(tzinfo=None)
    availability_end = availability_start + timedelta(minutes=1)
    params = {
        "start_time": availability_start.isoformat(),
        "end_time": availability_end.isoformat(),
    }
    room_availability_response = client.get(
        "/api/rooms/available",
        params=params,
    )
    if room_availability_response.status_code == 200:
        room_is_available = any(
            available_room["id"] == room.id
            for available_room in room_availability_response.json()
        )
    else:
        room_is_available = False
        failures.append(
            "Could not verify room availability: "
            f"HTTP {room_availability_response.status_code}"
        )

    equipment_availability_response = client.get(
        "/api/equipments/availability",
        params={**params, "search": equipment.code},
    )
    if equipment_availability_response.status_code == 200:
        equipment_status = next(
            (
                item
                for item in equipment_availability_response.json()
                if item["id"] == equipment.id
            ),
            None,
        )
        equipment_is_available = (
            equipment_status is not None
            and equipment_status["available_qty"] == equipment.total_qty
        )
    else:
        equipment_is_available = False
        failures.append(
            "Could not verify equipment availability: "
            f"HTTP {equipment_availability_response.status_code}"
        )

    if not room_is_available:
        failures.append("Room is still reported unavailable after check-out")
    if not equipment_is_available:
        failures.append("Equipment is still reported unavailable after check-out")
    if room_is_available and equipment_is_available:
        print("[SUCCESS] Check-out thành công, đã giải phóng phòng và thiết bị!")
    else:
        print(
            "[FAIL] Tài nguyên sau check-out: "
            f"phòng khả dụng={room_is_available}, "
            f"thiết bị khả dụng={equipment_is_available}"
        )

    assert not failures, "Live QR flow failures:\n- " + "\n- ".join(failures)
