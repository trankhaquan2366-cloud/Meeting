"""Unit tests for Equipment Admin flow (POST, PUT, GET include_inactive, permission checks)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.equipment import Equipment, MeetingEquipment
from app.models.user import User
from tests.helpers import _auth_header, _create_meeting, _create_room, _create_user, _make_token


def _create_test_equipment(db: Session, name: str = "Mic Test", total_qty: int = 5, is_active: bool = True) -> Equipment:
    equip = Equipment(
        name=name,
        code="TEST-01",
        category="Audio",
        total_qty=total_qty,
        is_active=is_active,
    )
    db.add(equip)
    db.commit()
    db.refresh(equip)
    return equip


def test_post_and_put_require_admin_token(client: TestClient, db_session: Session):
    """Test API POST và PUT: Phải trả về 403 Forbidden hoặc 401 Unauthorized nếu không có token Admin."""
    employee = _create_user(db_session, username="employee1", role="employee")
    emp_token = _make_token(employee)

    payload = {
        "name": "Projector Ultra HD",
        "code": "PRJ-999",
        "category": "Visual",
        "total_qty": 2,
    }

    # 1. POST without token -> 401 Unauthorized
    resp_no_auth = client.post("/api/equipments/", json=payload)
    assert resp_no_auth.status_code in (401, 403)

    # 2. POST with employee token -> 403 Forbidden
    resp_emp = client.post("/api/equipments/", json=payload, headers=_auth_header(emp_token))
    assert resp_emp.status_code == 403

    # Create an equipment for testing PUT permission
    equip = _create_test_equipment(db_session)

    update_payload = {"name": "Mic Test Updated"}

    # 3. PUT without token -> 401/403
    resp_put_no_auth = client.put(f"/api/equipments/{equip.id}", json=update_payload)
    assert resp_put_no_auth.status_code in (401, 403)

    # 4. PUT with employee token -> 403 Forbidden
    resp_put_emp = client.put(f"/api/equipments/{equip.id}", json=update_payload, headers=_auth_header(emp_token))
    assert resp_put_emp.status_code == 403


def test_toggle_is_active_and_include_inactive_query(client: TestClient, db_session: Session):
    """Tạo 1 thiết bị, sau đó gọi PUT để đổi is_active từ True sang False.

    Gọi GET /?include_inactive=true để kiểm tra thiết bị vừa tắt vẫn hiển thị trong list của Admin.
    """
    admin = _create_user(db_session, username="admin1", role="admin")
    admin_token = _make_token(admin)
    headers = _auth_header(admin_token)

    # 1. Admin POST to create a new equipment (is_active Defaults to True)
    create_payload = {
        "name": "Smart Board 75 inch",
        "code": "SB-075",
        "category": "Display",
        "total_qty": 3,
        "is_active": True,
    }
    create_resp = client.post("/api/equipments/", json=create_payload, headers=headers)
    assert create_resp.status_code == 201
    created_id = create_resp.json()["id"]
    assert create_resp.json()["is_active"] is True

    # 2. Call PUT to change is_active from True to False
    put_payload = {"is_active": False}
    put_resp = client.put(f"/api/equipments/{created_id}", json=put_payload, headers=headers)
    assert put_resp.status_code == 200
    assert put_resp.json()["is_active"] is False

    # 3. GET /api/equipments/ (default include_inactive=false) -> Should NOT contain the inactive equipment
    get_active_resp = client.get("/api/equipments/", headers=headers)
    assert get_active_resp.status_code == 200
    active_ids = [item["id"] for item in get_active_resp.json()]
    assert created_id not in active_ids

    # 4. GET /api/equipments/?include_inactive=true -> MUST contain the inactive equipment for Admin
    get_all_resp = client.get("/api/equipments/?include_inactive=true", headers=headers)
    assert get_all_resp.status_code == 200
    all_ids = [item["id"] for item in get_all_resp.json()]
    assert created_id in all_ids


def test_update_total_qty_does_not_corrupt_meeting_equipments(client: TestClient, db_session: Session):
    """AC 4: Khi Admin sửa total_qty của 1 thiết bị, sự thay đổi lưu thành công mà không làm hỏng dữ liệu meeting_equipments."""
    admin = _create_user(db_session, username="admin_qty", role="admin")
    admin_token = _make_token(admin)
    headers = _auth_header(admin_token)

    equip = _create_test_equipment(db_session, total_qty=5)
    organizer = _create_user(db_session, username="organizer_qty")
    room = _create_room(db_session, name="Room Qty")
    from datetime import datetime
    meeting = _create_meeting(db_session, room, organizer, datetime.now(), datetime.now())

    # Link meeting to equipment
    me = MeetingEquipment(meeting_id=meeting.id, equipment_id=equip.id, quantity=2, note="For workshop")
    db_session.add(me)
    db_session.commit()

    # Admin updates total_qty from 5 to 12
    put_resp = client.put(f"/api/equipments/{equip.id}", json={"total_qty": 12}, headers=headers)
    assert put_resp.status_code == 200
    assert put_resp.json()["total_qty"] == 12

    # Verify meeting_equipments link is intact
    db_session.rollback()
    me_db = db_session.query(MeetingEquipment).filter_by(meeting_id=meeting.id, equipment_id=equip.id).first()
    assert me_db is not None
    assert me_db.quantity == 2
    db_session.expire(me_db, ["equipment"])
    assert me_db.equipment.total_qty == 12
