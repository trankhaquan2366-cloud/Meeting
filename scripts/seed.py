"""Create repeatable demo data for local feature testing."""

from datetime import datetime, time, timedelta
import json
from pathlib import Path
import os
import secrets
import sys

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from app.core.database import SessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.equipment import Equipment, MeetingEquipment, RoomEquipment  # noqa: E402
from app.models.meeting import Meeting, MeetingParticipant  # noqa: E402
from app.models.notification import Notification  # noqa: E402
from app.models.room import Room  # noqa: E402
from app.models.user import User  # noqa: E402
import app.models  # noqa: E402,F401


DEMO_USERS = (
    ("demo.admin", "demo.admin@example.test", "Demo Admin", "admin", True),
    ("demo.alex", "demo.alex@example.test", "Alex Nguyen", "employee", True),
    ("demo.linh", "demo.linh@example.test", "Linh Tran", "employee", True),
    ("demo.inactive", "demo.inactive@example.test", "Inactive User", "employee", False),
    ("demo.manager", "demo.manager@example.test", "Quản lý Bùi Văn Nam", "manager", True),
    ("demo.tester1", "demo.tester1@example.test", "Tester Nguyễn Thu Hoa", "employee", True),
    ("demo.tester2", "demo.tester2@example.test", "Tester Trần Văn Bình", "employee", True),
)


DEMO_ROOMS = (
    {
        "name": "DEMO - Huddle Room",
        "location": "Tầng 2 - Tòa A",
        "capacity": 4,
        "description": "Phòng nhỏ dành cho nhóm dự án.",
        "amenities": ["Màn hình", "Bảng trắng"],
        "is_active": True,
    },
    {
        "name": "DEMO - Lotus Room",
        "location": "Tầng 3 - Tòa A",
        "capacity": 8,
        "description": "Phòng họp tiêu chuẩn.",
        "amenities": ["Máy chiếu", "Hội nghị trực tuyến"],
        "is_active": True,
    },
    {
        "name": "DEMO - Skyline Room",
        "location": "Tầng 8 - Tòa B",
        "capacity": 20,
        "description": "Phòng lớn cho buổi trình bày.",
        "amenities": ["Màn hình lớn", "Micro", "Bảng trắng"],
        "is_active": True,
    },
    {
        "name": "DEMO - Maintenance Room",
        "location": "Tầng 1 - Tòa B",
        "capacity": 6,
        "description": "Phòng mẫu đang bảo trì.",
        "amenities": [],
        "is_active": False,
    },
    {
        "name": "DEMO - Aurora Room",
        "location": "Tầng 2 - Tòa B",
        "capacity": 4,
        "description": "Phòng trao đổi nhanh cho nhóm nhỏ.",
        "amenities": ["Màn hình", "Bảng trắng"],
        "is_active": True,
    },
    {
        "name": "DEMO - Cedar Room",
        "location": "Tầng 4 - Tòa A",
        "capacity": 6,
        "description": "Phòng họp nhóm với thiết bị trình chiếu.",
        "amenities": ["Máy chiếu", "Bảng trắng"],
        "is_active": True,
    },
    {
        "name": "DEMO - River Room",
        "location": "Tầng 5 - Tòa B",
        "capacity": 10,
        "description": "Phòng họp nhóm liên phòng ban.",
        "amenities": ["Màn hình lớn", "Hội nghị trực tuyến"],
        "is_active": True,
    },
    {
        "name": "DEMO - Orion Room",
        "location": "Tầng 6 - Tòa A",
        "capacity": 14,
        "description": "Phòng họp rộng cho buổi lập kế hoạch.",
        "amenities": ["Máy chiếu", "Micro", "Bảng trắng"],
        "is_active": True,
    },
    {
        "name": "DEMO - Summit Room",
        "location": "Tầng 9 - Tòa B",
        "capacity": 30,
        "description": "Phòng hội thảo cho nhóm đông người.",
        "amenities": ["Màn hình lớn", "Micro", "Hội nghị trực tuyến"],
        "is_active": True,
    },
)

DEMO_EQUIPMENT = (
    ("DEMO-PROJECTOR", "Máy chiếu demo", "Presentation", 3, True),
    ("DEMO-MIC", "Micro hội nghị demo", "Audio", 8, True),
    ("DEMO-LAPTOP", "Laptop demo", "Computer", 5, True),
    ("DEMO-WEBCAM", "Webcam demo", "Video", 10, True),
    ("DEMO-WHITEBOARD", "Bảng di động demo", "Office", 2, True),
    ("DEMO-RETIRED", "Thiết bị ngừng hoạt động demo", "Office", 1, False),
)


def _get_or_create_user(db, username, email, full_name, role, is_active, password):
    user = db.query(User).filter(User.username == username).first()
    if user:
        return user, False

    user = User(
        username=username,
        email=email,
        full_name=full_name,
        hashed_password=hash_password(password),
        role=role,
        is_active=is_active,
    )
    db.add(user)
    db.flush()
    return user, True


def _get_or_create_meeting(db, title, room, organizer, start_time, end_time, **values):
    meeting = db.query(Meeting).filter(Meeting.title == title).first()
    if meeting:
        return meeting, False

    meeting = Meeting(
        title=title,
        room_id=room.id,
        organizer_id=organizer.id,
        start_time=start_time,
        end_time=end_time,
        **values,
    )
    db.add(meeting)
    db.flush()
    return meeting, True


def _add_participant(db, meeting, user):
    exists = (
        db.query(MeetingParticipant)
        .filter_by(meeting_id=meeting.id, user_id=user.id)
        .first()
    )
    if not exists:
        db.add(MeetingParticipant(meeting_id=meeting.id, user_id=user.id))


def _add_equipment(db, meeting, equipment, quantity, note):
    exists = (
        db.query(MeetingEquipment)
        .filter_by(meeting_id=meeting.id, equipment_id=equipment.id)
        .first()
    )
    if not exists:
        db.add(
            MeetingEquipment(
                meeting_id=meeting.id,
                equipment_id=equipment.id,
                quantity=quantity,
                note=note,
            )
        )


def _add_notification(db, user, title, content, is_read=False):
    exists = (
        db.query(Notification.id)
        .filter_by(user_id=user.id, title=title, content=content)
        .first()
    )
    if not exists:
        db.add(
            Notification(
                user_id=user.id,
                title=title,
                content=content,
                is_read=is_read,
            )
        )
    if not exists:
        db.add(
            Notification(
                user_id=user.id,
                title=title,
                content=content,
                is_read=is_read,
            )
        )


def seed() -> None:
    db = SessionLocal()
    created = {"users": 0, "rooms": 0, "equipment": 0, "meetings": 0}
    configured_admin_password = os.getenv("SEED_ADMIN_PASSWORD")
    configured_demo_password = (
        os.getenv("SEED_DEMO_PASSWORD") or configured_admin_password
    )
    generated_admin_password = configured_admin_password is None
    generated_demo_password = configured_demo_password is None
    admin_password = configured_admin_password or secrets.token_urlsafe(16)
    demo_password = configured_demo_password or secrets.token_urlsafe(16)
    demo_users_created = 0

    try:
        _, admin_created = _get_or_create_user(
            db,
            "admin",
            "admin@meeting.local",
            "Quản trị viên",
            "admin",
            True,
            admin_password,
        )
        if admin_created:
            created["users"] += 1

        users = {}
        for username, email, full_name, role, is_active in DEMO_USERS:
            user, was_created = _get_or_create_user(
                db, username, email, full_name, role, is_active, demo_password
            )
            users[username] = user
            created["users"] += int(was_created)
            demo_users_created += int(was_created)

        rooms = {}
        for room_data in DEMO_ROOMS:
            room = db.query(Room).filter(Room.name == room_data["name"]).first()
            if room is None:
                room = Room(
                    **{
                        **room_data,
                        "amenities": json.dumps(room_data["amenities"], ensure_ascii=False),
                    }
                )
                db.add(room)
                db.flush()
                created["rooms"] += 1
            rooms[room_data["name"]] = room

        equipment_by_code = {}
        for code, name, category, total_qty, is_active in DEMO_EQUIPMENT:
            equipment = db.query(Equipment).filter(Equipment.code == code).first()
            if equipment is None:
                equipment = Equipment(
                    code=code,
                    name=name,
                    category=category,
                    total_qty=total_qty,
                    description="Dữ liệu mẫu để kiểm thử quản lý và tồn kho thiết bị.",
                    is_active=is_active,
                )
                db.add(equipment)
                db.flush()
                created["equipment"] += 1
            equipment_by_code[code] = equipment

        room_equipment = {
            "DEMO - Huddle Room": {"DEMO-WHITEBOARD": 1, "DEMO-WEBCAM": 1},
            "DEMO - Lotus Room": {"DEMO-PROJECTOR": 1, "DEMO-MIC": 2},
            "DEMO - Skyline Room": {"DEMO-PROJECTOR": 1, "DEMO-MIC": 4},
        }
        for room_name, defaults in room_equipment.items():
            for code, quantity in defaults.items():
                equipment = equipment_by_code[code]
                exists = (
                    db.query(RoomEquipment)
                    .filter_by(room_id=rooms[room_name].id, equipment_id=equipment.id)
                    .first()
                )
                if not exists:
                    db.add(
                        RoomEquipment(
                            room_id=rooms[room_name].id,
                            equipment_id=equipment.id,
                            quantity=quantity,
                        )
                    )

        today = datetime.now().date()
        past_start = datetime.combine(today - timedelta(days=2), time(10, 0))
        future_start = datetime.combine(today + timedelta(days=1), time(9, 0))
        recurring_start = datetime.combine(today + timedelta(days=2), time(13, 0))

        past_meeting, was_created = _get_or_create_meeting(
            db,
            "[DEMO] Project review - completed",
            rooms["DEMO - Huddle Room"],
            users["demo.alex"],
            past_start,
            past_start + timedelta(hours=1),
            description="Lịch mẫu đã kết thúc để kiểm thử lịch sử cuộc họp.",
            status="completed",
        )
        created["meetings"] += int(was_created)
        _add_participant(db, past_meeting, users["demo.linh"])

        upcoming, was_created = _get_or_create_meeting(
            db,
            "[DEMO] Product planning",
            rooms["DEMO - Lotus Room"],
            users["demo.alex"],
            future_start,
            future_start + timedelta(hours=1),
            description="Lịch sắp tới có người tham dự và mượn thiết bị.",
            status="scheduled",
        )
        created["meetings"] += int(was_created)
        _add_participant(db, upcoming, users["demo.linh"])
        _add_participant(db, upcoming, users["demo.admin"])
        _add_equipment(
            db, upcoming, equipment_by_code["DEMO-PROJECTOR"], 1, "Trình chiếu kế hoạch"
        )
        _add_equipment(
            db, upcoming, equipment_by_code["DEMO-MIC"], 2, "Micro cho người tham dự"
        )

        for occurrence in range(1, 4):
            occurrence_start = recurring_start + timedelta(weeks=occurrence - 1)
            meeting, was_created = _get_or_create_meeting(
                db,
                f"[DEMO] Weekly planning {occurrence}/3",
                rooms["DEMO - Skyline Room"],
                users["demo.admin"],
                occurrence_start,
                occurrence_start + timedelta(minutes=45),
                description="Một buổi trong chuỗi họp định kỳ hàng tuần.",
                is_recurring=True,
                recurring_type="weekly",
                status="scheduled",
            )
            created["meetings"] += int(was_created)
            _add_participant(db, meeting, users["demo.alex"])
            _add_participant(db, meeting, users["demo.linh"])

        canceled_start = datetime.combine(today + timedelta(days=1), time(14, 0))
        canceled, was_created = _get_or_create_meeting(
            db,
            "[DEMO] Canceled meeting",
            rooms["DEMO - Huddle Room"],
            users["demo.linh"],
            canceled_start,
            canceled_start + timedelta(hours=1),
            description="Lịch mẫu đã hủy; phòng được xem là trống ở khung giờ này.",
            status="CANCELLED",
        )
        created["meetings"] += int(was_created)
        _add_participant(db, canceled, users["demo.alex"])

        _add_notification(
            db,
            users["demo.linh"],
            "Lời mời họp: Product planning",
            "Alex Nguyen đã mời bạn tham gia cuộc họp Product planning.",
            False,
        )
        _add_notification(
            db,
            users["demo.alex"],
            "Đặt phòng thành công",
            "Cuộc họp Product planning đã được lưu cùng các thiết bị yêu cầu.",
            True,
        )

        db.commit()
        print("Demo data ready:", ", ".join(f"{key}={value}" for key, value in created.items()))
        print("Login users: admin, demo.admin, demo.alex, demo.linh")
        if admin_created and generated_admin_password:
            print(f"One-time admin password: {admin_password}")
        if demo_users_created and generated_demo_password:
            print(f"One-time demo password: {demo_password}")
        else:
            print("Demo password: SEED_DEMO_PASSWORD or SEED_ADMIN_PASSWORD from .env")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
