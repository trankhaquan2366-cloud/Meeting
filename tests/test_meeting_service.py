from datetime import datetime, timedelta

from app.models.equipment import Equipment, MeetingEquipment
from app.models.meeting import Meeting
from app.schemas.meeting import MeetingCreateRequest
from app.services.equipment_service import check_equipment_availability
from app.services.meeting_service import MeetingService
from tests.helpers import _create_room, _create_user


def test_check_equipment_availability_counts_only_overlapping_active_meetings(
    db_session,
):
    organizer = _create_user(db_session, "equipment-overlap-organizer")
    room = _create_room(db_session, "Equipment overlap room")
    equipment = Equipment(
        name="Overlap projector",
        code="OVERLAP-EQ-01",
        total_qty=8,
        is_active=True,
    )
    db_session.add(equipment)
    db_session.flush()

    start = datetime.utcnow() + timedelta(days=5)
    first = Meeting(
        title="Overlap one",
        room_id=room.id,
        organizer_id=organizer.id,
        start_time=start,
        end_time=start + timedelta(hours=1),
        status="scheduled",
    )
    boundary_only = Meeting(
        title="Boundary only",
        room_id=room.id,
        organizer_id=organizer.id,
        start_time=start + timedelta(hours=1),
        end_time=start + timedelta(hours=2),
        status="scheduled",
    )
    cancelled = Meeting(
        title="Cancelled overlap",
        room_id=room.id,
        organizer_id=organizer.id,
        start_time=start,
        end_time=start + timedelta(hours=1),
        status="CANCELLED",
    )
    db_session.add_all([first, boundary_only, cancelled])
    db_session.flush()
    db_session.add_all([
        MeetingEquipment(
            meeting_id=first.id,
            equipment_id=equipment.id,
            quantity=3,
        ),
        MeetingEquipment(
            meeting_id=boundary_only.id,
            equipment_id=equipment.id,
            quantity=4,
        ),
        MeetingEquipment(
            meeting_id=cancelled.id,
            equipment_id=equipment.id,
            quantity=5,
        ),
    ])
    db_session.commit()

    available = check_equipment_availability(
        db_session,
        equipment.id,
        start,
        start + timedelta(hours=1),
        requested_qty=2,
    )

    assert available == 5


def test_validate_meeting_booking_reports_capacity_and_equipment_warnings(db_session):
    organizer = _create_user(db_session, "booking-warning-organizer")
    reservation_organizer = _create_user(
        db_session, "booking-warning-reservation-organizer"
    )
    room = _create_room(db_session, "Small warning room")
    room.capacity = 2
    equipment_storage_room = _create_room(db_session, "Equipment storage room")
    equipment = Equipment(
        name="Reserved warning projector",
        code="WARNING-EQ-01",
        total_qty=1,
        is_active=True,
    )
    db_session.add(equipment)
    db_session.flush()

    start = datetime.utcnow() + timedelta(days=6)
    reserved_meeting = Meeting(
        title="Existing equipment reservation",
        room_id=equipment_storage_room.id,
        organizer_id=reservation_organizer.id,
        start_time=start,
        end_time=start + timedelta(hours=1),
        status="scheduled",
    )
    db_session.add(reserved_meeting)
    db_session.flush()
    db_session.add(
        MeetingEquipment(
            meeting_id=reserved_meeting.id,
            equipment_id=equipment.id,
            quantity=1,
        )
    )
    db_session.commit()

    payload = MeetingCreateRequest(
        title="Meeting with soft warnings",
        meeting_type="offline",
        room_id=room.id,
        start_time=start,
        end_time=start + timedelta(minutes=30),
        external_guest_count=2,
        equipments=[{"equipment_id": equipment.id, "quantity": 1}],
    )
    result = MeetingService.validate_meeting_booking(
        db_session,
        payload,
        organizer_id=organizer.id,
    )

    assert result["is_valid"] is True
    assert {warning["type"] for warning in result["warnings"]} == {
        "OverCapacityWarning",
        "EquipmentShortageWarning",
    }


def test_validate_meeting_booking_blocks_room_time_conflict(db_session):
    organizer = _create_user(db_session, "booking-conflict-organizer")
    room = _create_room(db_session, "Conflicted booking room")
    start = datetime.utcnow() + timedelta(days=7)
    existing = Meeting(
        title="Existing room booking",
        room_id=room.id,
        organizer_id=organizer.id,
        start_time=start,
        end_time=start + timedelta(hours=1),
        status="scheduled",
    )
    db_session.add(existing)
    db_session.commit()

    payload = MeetingCreateRequest(
        title="Conflicting meeting",
        meeting_type="offline",
        room_id=room.id,
        start_time=start + timedelta(minutes=15),
        end_time=start + timedelta(minutes=45),
    )
    result = MeetingService.validate_meeting_booking(
        db_session,
        payload,
        organizer_id=organizer.id,
    )

    assert result["is_valid"] is False
    assert result["blocking_errors"][0]["type"] == "RoomConflictError"


def test_validate_meeting_booking_enforces_organizer_daily_hours_limit(db_session):
    organizer = _create_user(db_session, "booking-daily-limit-organizer")
    organizer.daily_booking_hours_limit = 2
    room = _create_room(db_session, "Daily limit room")
    start = datetime.utcnow() + timedelta(days=8)
    db_session.add(
        Meeting(
            title="Existing booking",
            room_id=room.id,
            organizer_id=organizer.id,
            start_time=start,
            end_time=start + timedelta(hours=1),
            status="scheduled",
        )
    )
    db_session.add(
        Meeting(
            title="Cancelled booking",
            room_id=room.id,
            organizer_id=organizer.id,
            start_time=start + timedelta(hours=1),
            end_time=start + timedelta(hours=4),
            status="CANCELLED",
        )
    )
    db_session.commit()

    within_limit = MeetingCreateRequest(
        title="Within daily limit",
        meeting_type="offline",
        room_id=room.id,
        start_time=start + timedelta(hours=4),
        end_time=start + timedelta(hours=5),
    )
    exceeded_limit = MeetingCreateRequest(
        title="Over daily limit",
        meeting_type="offline",
        room_id=room.id,
        start_time=start + timedelta(hours=5),
        end_time=start + timedelta(hours=6, minutes=30),
    )

    allowed = MeetingService.validate_meeting_booking(
        db_session,
        within_limit,
        organizer_id=organizer.id,
    )
    rejected = MeetingService.validate_meeting_booking(
        db_session,
        exceeded_limit,
        organizer_id=organizer.id,
    )

    assert allowed["is_valid"] is True
    assert rejected["is_valid"] is False
    assert rejected["blocking_errors"][0]["type"] == "DailyBookingHoursLimitError"
    assert rejected["blocking_errors"][0]["daily_limit_hours"] == 2
