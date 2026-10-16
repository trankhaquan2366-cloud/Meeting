"""Idempotently seed RoomSync with a realistic development dataset.

Run from the repository root with ``python -m app.seed_data`` after applying
the database migrations. The script only removes meetings carrying its private
seed marker; it never truncates application tables.
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, time, timedelta
from typing import Callable
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.department import Department
from app.models.equipment import Equipment, MeetingEquipment, RoomEquipment
from app.models.google_calendar_event import GoogleCalendarEvent
from app.models.meeting import Meeting, MeetingParticipant
from app.models.meeting_reminder import MeetingReminder
from app.models.notification import Notification
from app.models.project_group import ProjectGroup
from app.models.room import Room
from app.models.user import User

logger = logging.getLogger(__name__)
ROOMSYNC_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")
SEED_MARKER = "[ROOMSYNC_DEVELOPMENT_SEED]"
DEFAULT_PASSWORD = "Password123!"

DEPARTMENTS = (
    ("Ban Giám Đốc", "SEED-EXEC"),
    ("Kỹ thuật (Dev)", "SEED-DEV"),
    ("Marketing", "SEED-MARKETING"),
    ("Nhân sự (HR)", "SEED-HR"),
    ("Kinh doanh (Sales)", "SEED-SALES"),
)

PROJECT_GROUPS = (
    ("Nền tảng RoomSync", "SEED-PLATFORM"),
    ("Chiến dịch thương hiệu", "SEED-BRAND"),
    ("Trải nghiệm nhân viên", "SEED-PEOPLE"),
    ("Phát triển khách hàng", "SEED-CUSTOMER"),
)

USERS = (
    {
        "full_name": "Nguyễn Văn An",
        "email": "an.nguyen@roomsync.test",
        "role": "admin",
        "department": "SEED-EXEC",
        "position": "Tổng Giám đốc",
        "status": "ACTIVE",
        "group": "SEED-PLATFORM",
    },
    {
        "full_name": "Trần Thị Bích",
        "email": "bich.tran@roomsync.test",
        "role": "admin",
        "department": "SEED-EXEC",
        "position": "Giám đốc vận hành",
        "status": "ACTIVE",
        "group": "SEED-PEOPLE",
    },
    {
        "full_name": "Lê Hoàng Cường",
        "email": "cuong.le@roomsync.test",
        "role": "manager",
        "department": "SEED-DEV",
        "position": "Trưởng phòng Kỹ thuật",
        "status": "ACTIVE",
        "group": "SEED-PLATFORM",
    },
    {
        "full_name": "Phạm Minh Đức",
        "email": "duc.pham@roomsync.test",
        "role": "manager",
        "department": "SEED-MARKETING",
        "position": "Trưởng phòng Marketing",
        "status": "ACTIVE",
        "group": "SEED-BRAND",
    },
    {
        "full_name": "Vũ Thị Hoa",
        "email": "hoa.vu@roomsync.test",
        "role": "manager",
        "department": "SEED-HR",
        "position": "Trưởng phòng Nhân sự",
        "status": "ACTIVE",
        "group": "SEED-PEOPLE",
    },
    {
        "full_name": "Đặng Quốc Khánh",
        "email": "khanh.dang@roomsync.test",
        "role": "manager",
        "department": "SEED-SALES",
        "position": "Trưởng phòng Kinh doanh",
        "status": "ACTIVE",
        "group": "SEED-CUSTOMER",
    },
    {
        "full_name": "Nguyễn Thu Trang",
        "email": "trang.nguyen@roomsync.test",
        "role": "employee",
        "department": "SEED-DEV",
        "position": "Kỹ sư phần mềm",
        "status": "ACTIVE",
        "group": "SEED-PLATFORM",
    },
    {
        "full_name": "Bùi Văn Nam",
        "email": "nam.bui@roomsync.test",
        "role": "employee",
        "department": "SEED-DEV",
        "position": "Kỹ sư QA",
        "status": "ACTIVE",
        "group": "SEED-PLATFORM",
    },
    {
        "full_name": "Đỗ Hoàng Linh",
        "email": "linh.do@roomsync.test",
        "role": "employee",
        "department": "SEED-MARKETING",
        "position": "Chuyên viên nội dung",
        "status": "ACTIVE",
        "group": "SEED-BRAND",
    },
    {
        "full_name": "Trịnh Quốc Bảo",
        "email": "bao.trinh@roomsync.test",
        "role": "employee",
        "department": "SEED-SALES",
        "position": "Chuyên viên phát triển kinh doanh",
        "status": "ACTIVE",
        "group": "SEED-CUSTOMER",
    },
    {
        "full_name": "Hồ Phương Thảo",
        "email": "thao.ho@roomsync.test",
        "role": "employee",
        "department": "SEED-HR",
        "position": "Chuyên viên tuyển dụng",
        "status": "ACTIVE",
        "group": "SEED-PEOPLE",
    },
    {
        "full_name": "Ngô Anh Tuấn",
        "email": "tuan.ngo@roomsync.test",
        "role": "employee",
        "department": "SEED-DEV",
        "position": "Kỹ sư dữ liệu",
        "status": "ACTIVE",
        "group": "SEED-PLATFORM",
    },
    {
        "full_name": "Hoàng Trọng Nghĩa",
        "email": "nghia.hoang@roomsync.test",
        "role": "employee",
        "department": "SEED-SALES",
        "position": "Nhân viên kinh doanh",
        "status": "PENDING",
        "group": "SEED-CUSTOMER",
    },
    {
        "full_name": "Mai Phương Thảo",
        "email": "thao.mai@roomsync.test",
        "role": "employee",
        "department": "SEED-HR",
        "position": "Điều phối viên nhân sự",
        "status": "PENDING",
        "group": "SEED-PEOPLE",
    },
    {
        "full_name": "Phan Văn Hùng",
        "email": "hung.phan@roomsync.test",
        "role": "employee",
        "department": "SEED-DEV",
        "position": "Kỹ thuật viên hệ thống",
        "status": "LOCKED",
        "group": "SEED-PLATFORM",
    },
)

ROOMS = (
    ("SEED - Huddle Room", 4, "Tầng 1", "Phòng trao đổi nhanh cho nhóm nhỏ."),
    ("SEED - Lotus Room", 6, "Tầng 2", "Phòng họp nhóm với màn hình trình chiếu."),
    ("SEED - Cedar Room", 8, "Tầng 3", "Phòng họp nhóm dự án yên tĩnh."),
    ("SEED - River Room", 10, "Tầng 4", "Không gian họp liên phòng ban."),
    ("SEED - Aurora Room", 12, "Tầng 5", "Phòng hội thảo với video conference."),
    ("SEED - Skyline Room", 16, "Tầng 6", "Phòng họp khách hàng và đối tác."),
    ("SEED - Summit Room", 20, "Tầng 7", "Phòng đào tạo quy mô vừa."),
    ("SEED - Grand Hall", 30, "Tầng 8", "Không gian họp toàn công ty."),
)

EQUIPMENTS = (
    ("SEED-TV65", "Màn hình TV 65 inch", "Hiển thị", 12),
    ("SEED-PROJECTOR", "Máy chiếu HD", "Trình chiếu", 8),
    ("SEED-VC", "Hệ thống Video Conference", "Hội nghị trực tuyến", 6),
    ("SEED-MIC", "Micro không dây", "Âm thanh", 14),
    ("SEED-FLIPCHART", "Bảng trắng flipchart", "Văn phòng", 10),
)

ROOM_EQUIPMENT_CODES = {
    "SEED - Huddle Room": (("SEED-TV65", 1), ("SEED-FLIPCHART", 1)),
    "SEED - Lotus Room": (("SEED-TV65", 1), ("SEED-MIC", 2)),
    "SEED - Cedar Room": (("SEED-TV65", 1), ("SEED-FLIPCHART", 1)),
    "SEED - River Room": (("SEED-PROJECTOR", 1), ("SEED-MIC", 2)),
    "SEED - Aurora Room": (("SEED-TV65", 1), ("SEED-VC", 1), ("SEED-MIC", 2)),
    "SEED - Skyline Room": (("SEED-PROJECTOR", 1), ("SEED-VC", 1), ("SEED-MIC", 3)),
    "SEED - Summit Room": (("SEED-PROJECTOR", 1), ("SEED-VC", 1), ("SEED-FLIPCHART", 1)),
    "SEED - Grand Hall": (("SEED-PROJECTOR", 2), ("SEED-VC", 1), ("SEED-MIC", 4)),
}

CANCELLATION_REASONS = (
    "Tự động hủy do quá 15 phút không check-in",
    "Trùng lịch đột xuất với cuộc họp khách hàng",
    "Thay đổi kế hoạch của nhóm dự án",
    "Người chủ trì bận xử lý sự cố hệ thống",
    "Đã chuyển nội dung sang cuộc họp trực tuyến",
    "Thiếu thành phần tham dự quan trọng",
)


def _upsert_department(
    db: Session,
    name: str,
    code: str,
) -> Department:
    department = db.scalar(select(Department).where(Department.code == code))
    if department is None:
        department = Department(name=name, code=code)
        db.add(department)
    else:
        department.name = name
    return department


def _upsert_project_group(
    db: Session,
    name: str,
    code: str,
) -> ProjectGroup:
    group = db.scalar(select(ProjectGroup).where(ProjectGroup.code == code))
    if group is None:
        group = ProjectGroup(name=name, code=code)
        db.add(group)
    else:
        group.name = name
    return group


def _remove_previous_seed_meetings(db: Session) -> None:
    meeting_ids = select(Meeting.id).where(Meeting.description == SEED_MARKER)
    db.execute(
        delete(GoogleCalendarEvent).where(GoogleCalendarEvent.meeting_id.in_(meeting_ids))
    )
    db.execute(
        delete(MeetingReminder).where(MeetingReminder.meeting_id.in_(meeting_ids))
    )
    db.execute(
        delete(Notification).where(Notification.meeting_id.in_(meeting_ids))
    )
    db.execute(
        delete(MeetingParticipant).where(MeetingParticipant.meeting_id.in_(meeting_ids))
    )
    db.execute(
        delete(MeetingEquipment).where(MeetingEquipment.meeting_id.in_(meeting_ids))
    )
    db.execute(delete(Meeting).where(Meeting.description == SEED_MARKER))


def _upsert_users(
    db: Session,
    departments: dict[str, Department],
    groups: dict[str, ProjectGroup],
) -> list[User]:
    seeded_users: list[User] = []
    password_hash = hash_password(DEFAULT_PASSWORD)
    for index, row in enumerate(USERS, start=1):
        username = row["email"].split("@", maxsplit=1)[0]
        user = db.scalar(select(User).where(User.email == row["email"]))
        if user is None:
            username_owner = db.scalar(select(User).where(User.username == username))
            if username_owner is not None:
                raise ValueError(
                    f"Seed username {username!r} already belongs to a different email."
                )
            user = User(username=username, email=row["email"])
            db.add(user)

        user.username = username
        user.email = row["email"]
        user.full_name = row["full_name"]
        user.hashed_password = password_hash
        user.role = row["role"]
        user.status = row["status"]
        user.is_active = row["status"] == "ACTIVE"
        user.can_book = user.is_active
        user.can_attend = user.is_active
        user.department = departments[row["department"]]
        user.position = row["position"]
        user.external_id = f"SEED-EMP-{index:03d}"
        user.daily_booking_hours_limit = 4.0 if row["role"] == "employee" else 8.0
        user.can_bypass_room_approval = row["role"] == "admin"
        user.project_groups = [groups[row["group"]]]
        seeded_users.append(user)

    db.flush()
    return seeded_users


def _upsert_rooms(db: Session) -> dict[str, Room]:
    rooms: dict[str, Room] = {}
    for name, capacity, location, description in ROOMS:
        room = db.scalar(select(Room).where(Room.name == name))
        if room is None:
            room = Room(name=name)
            db.add(room)
        room.capacity = capacity
        room.location = location
        room.description = description
        room.amenities = '["Wi-Fi", "Điều hòa", "Ổ cắm điện"]'
        room.is_active = True
        rooms[name] = room
    db.flush()
    return rooms


def _upsert_equipments(db: Session) -> dict[str, Equipment]:
    equipments: dict[str, Equipment] = {}
    for code, name, category, quantity in EQUIPMENTS:
        equipment = db.scalar(select(Equipment).where(Equipment.code == code))
        if equipment is None:
            equipment = Equipment(code=code, name=name)
            db.add(equipment)
        equipment.name = name
        equipment.category = category
        equipment.total_qty = quantity
        equipment.description = f"Thiết bị mẫu RoomSync ({code})."
        equipment.is_active = True
        equipments[code] = equipment
    db.flush()
    return equipments


def _replace_seed_room_equipment(
    db: Session,
    rooms: dict[str, Room],
    equipments: dict[str, Equipment],
) -> None:
    room_ids = [room.id for room in rooms.values()]
    db.execute(delete(RoomEquipment).where(RoomEquipment.room_id.in_(room_ids)))
    for room_name, assignments in ROOM_EQUIPMENT_CODES.items():
        for equipment_code, quantity in assignments:
            db.add(
                RoomEquipment(
                    room_id=rooms[room_name].id,
                    equipment_id=equipments[equipment_code].id,
                    quantity=quantity,
                )
            )


def _add_meeting(
    db: Session,
    *,
    title: str,
    room: Room,
    organizer: User,
    start_time: datetime,
    end_time: datetime,
    status: str,
    participants: list[User],
    equipments: list[Equipment],
    cancellation_reason: str | None = None,
    check_in_time: datetime | None = None,
    check_out_time: datetime | None = None,
) -> Meeting:
    meeting = Meeting(
        title=title,
        description=SEED_MARKER,
        meeting_type="offline",
        room_id=room.id,
        organizer_id=organizer.id,
        start_time=start_time,
        end_time=end_time,
        status=status,
        cancellation_reason=cancellation_reason,
        cancelled_at=start_time - timedelta(hours=1) if cancellation_reason else None,
        check_in_time=check_in_time,
        check_out_time=check_out_time,
    )
    db.add(meeting)
    db.flush()
    for participant in participants:
        if participant.id != organizer.id:
            db.add(
                MeetingParticipant(
                    meeting_id=meeting.id,
                    user_id=participant.id,
                    response_status="accepted",
                )
            )
    for equipment in equipments:
        db.add(
            MeetingEquipment(
                meeting_id=meeting.id,
                equipment_id=equipment.id,
                quantity=1,
            )
        )
    return meeting


def _seed_meetings(
    db: Session,
    *,
    now: datetime,
    users: list[User],
    rooms: dict[str, Room],
    equipments: dict[str, Equipment],
) -> int:
    active_users = [user for user in users if user.is_active]
    room_list = list(rooms.values())
    equipment_list = list(equipments.values())
    meetings_created = 0

    # Completed meetings are distributed over the trailing 30 days.
    for index in range(24):
        start = datetime.combine(
            (now - timedelta(days=(index % 30) + 1)).date(),
            time(hour=9 + index % 8, minute=(index % 2) * 30),
        )
        room = room_list[index % len(room_list)]
        organizer = active_users[index % len(active_users)]
        participants = [
            active_users[(index + 1) % len(active_users)],
            active_users[(index + 4) % len(active_users)],
        ]
        _add_meeting(
            db,
            title=f"Hoàn tất · {('Sprint review', 'Kế hoạch tuần', 'Cập nhật khách hàng')[index % 3]} #{index + 1:02d}",
            room=room,
            organizer=organizer,
            start_time=start,
            end_time=start + timedelta(minutes=45 + (index % 4) * 15),
            status="COMPLETED",
            participants=participants,
            equipments=[equipment_list[index % len(equipment_list)]],
            check_in_time=start + timedelta(minutes=2),
            check_out_time=start + timedelta(minutes=45 + (index % 4) * 15),
        )
        meetings_created += 1

    # Cancellations include operational reasons for the cancellation reports.
    for index, reason in enumerate(CANCELLATION_REASONS):
        start = datetime.combine(
            (now - timedelta(days=index + 1)).date(),
            time(hour=10 + index % 6),
        )
        _add_meeting(
            db,
            title=f"Đã hủy · {('Trao đổi dự án', 'Họp khách hàng')[index % 2]} #{index + 1}",
            room=room_list[(index + 2) % len(room_list)],
            organizer=active_users[(index + 2) % len(active_users)],
            start_time=start,
            end_time=start + timedelta(hours=1),
            status="CANCELLED",
            participants=[active_users[(index + 3) % len(active_users)]],
            equipments=[],
            cancellation_reason=reason,
        )
        meetings_created += 1

    # One current meeting makes the extend-meeting controls immediately testable.
    in_progress_start = now - timedelta(minutes=25)
    _add_meeting(
        db,
        title="Đang diễn ra · Kiểm tra vận hành RoomSync",
        room=room_list[0],
        organizer=active_users[0],
        start_time=in_progress_start,
        end_time=now + timedelta(minutes=35),
        status="IN_PROGRESS",
        participants=[active_users[1], active_users[2]],
        equipments=[equipment_list[0]],
        check_in_time=in_progress_start + timedelta(minutes=3),
    )
    meetings_created += 1

    # Add up to three scannable meetings later today without crossing midnight.
    today_end = datetime.combine(now.date() + timedelta(days=1), time.min)
    upcoming_starts = (
        now + timedelta(minutes=30),
        now + timedelta(minutes=90),
        now + timedelta(minutes=150),
    )
    today_count = 0
    for start in upcoming_starts:
        if start >= today_end:
            continue
        index = today_count
        _add_meeting(
            db,
            title=f"Sắp diễn ra · Đồng bộ nhóm #{index + 1}",
            room=room_list[(index + 1) % len(room_list)],
            organizer=active_users[(index + 3) % len(active_users)],
            start_time=start,
            end_time=start + timedelta(minutes=45),
            status="SCHEDULED",
            participants=[active_users[(index + 4) % len(active_users)]],
            equipments=[equipment_list[(index + 1) % len(equipment_list)]],
        )
        today_count += 1
        meetings_created += 1

    # Future bookings span this and next week to exercise calendar and conflicts.
    for index in range(9):
        day_offset = (index % 6) + 1 if index < 5 else (index - 4) + 7
        start_day = now.date() + timedelta(days=day_offset)
        start = datetime.combine(start_day, time(hour=9 + index % 7, minute=30))
        _add_meeting(
            db,
            title=f"Lịch sắp tới · {('Roadmap', 'Đào tạo', 'Kế hoạch kinh doanh')[index % 3]} #{index + 1}",
            room=room_list[(index + 4) % len(room_list)],
            organizer=active_users[(index + 5) % len(active_users)],
            start_time=start,
            end_time=start + timedelta(minutes=60 + (index % 2) * 30),
            status="SCHEDULED",
            participants=[
                active_users[(index + 6) % len(active_users)],
                active_users[(index + 7) % len(active_users)],
            ],
            equipments=[equipment_list[index % len(equipment_list)]],
        )
        meetings_created += 1

    return meetings_created


def seed_database(
    session_factory: Callable[[], Session] = SessionLocal,
    *,
    now: datetime | None = None,
) -> dict[str, int]:
    """Upsert seed entities and replace only this script's generated meetings."""
    db = session_factory()
    try:
        seed_now = now or datetime.now(ROOMSYNC_TIMEZONE)
        if seed_now.tzinfo is not None:
            seed_now = seed_now.astimezone(ROOMSYNC_TIMEZONE).replace(tzinfo=None)

        _remove_previous_seed_meetings(db)

        departments = {
            code: _upsert_department(db, name, code)
            for name, code in DEPARTMENTS
        }
        groups = {
            code: _upsert_project_group(db, name, code)
            for name, code in PROJECT_GROUPS
        }
        db.flush()
        users = _upsert_users(db, departments, groups)
        rooms = _upsert_rooms(db)
        equipments = _upsert_equipments(db)
        _replace_seed_room_equipment(db, rooms, equipments)
        meetings_created = _seed_meetings(
            db,
            now=seed_now,
            users=users,
            rooms=rooms,
            equipments=equipments,
        )
        db.commit()
        return {
            "users": len(users),
            "rooms": len(rooms),
            "equipments": len(equipments),
            "meetings": meetings_created,
        }
    except Exception:
        db.rollback()
        logger.exception("RoomSync development database seeding failed.")
        raise
    finally:
        db.close()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        result = seed_database()
    except Exception as exc:
        print(f"[ERROR] Database seeding failed: {exc}", file=sys.stderr)
        return 1

    print(
        "[SUCCESS] Created/updated "
        f"{result['users']} Users, {result['rooms']} Rooms, "
        f"{result['equipments']} Equipments, {result['meetings']} Meetings!"
    )
    print(f"[INFO] Test account password: {DEFAULT_PASSWORD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
