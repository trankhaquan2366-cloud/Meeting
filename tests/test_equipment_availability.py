from app.services.equipment_service import get_equipment_availability

def test_equipment_availability_available():
    result = get_equipment_availability(None, "2026-10-02T10:00:00", "2026-10-02T12:00:00", search="Projector")
    assert len(result) == 1
    assert result[0]["id"] == 1
    assert result[0]["status_label"] == "Có sẵn"
    assert result[0]["available_qty"] == 4

def test_equipment_availability_booked_out():
    result = get_equipment_availability(None, "2026-10-02T10:00:00", "2026-10-02T12:00:00", search="Whiteboard")
    assert len(result) == 1
    assert result[0]["status_label"] == "Đã đặt hết"
    assert result[0]["available_qty"] == 0

def test_equipment_availability_maintenance():
    result = get_equipment_availability(None, "2026-10-02T10:00:00", "2026-10-02T12:00:00", search="Microphone")
    assert len(result) == 1
    assert result[0]["status_label"] == "Ngừng hoạt động / Bảo trì"
