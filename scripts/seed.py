"""Seed dữ liệu mẫu an toàn cho Meeting Management System.

Cách chạy (từ thư mục gốc dự án):
    python scripts/seed.py

Script chỉ thêm bản ghi khi chưa tồn tại (theo username/email với users,
theo name với rooms), nên có thể chạy lại nhiều lần mà không tạo trùng.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Cho phép import package `app` khi chạy trực tiếp: python scripts/seed.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models import Room, User  # noqa: E402

ADMIN_PASSWORD = "Admin@123"
NORMAL_USER_PASSWORD = "User@123"

ADMIN_ACCOUNT = {
    "username": "admin",
    "email": "admin@example.com",
    "full_name": "Quản trị viên",
    "role": "admin",
    "password": ADMIN_PASSWORD,
}

NORMAL_ACCOUNTS = [
    {
        "username": "user1",
        "email": "user1@example.com",
        "full_name": "Người dùng 1",
        "role": "user",
        "password": NORMAL_USER_PASSWORD,
    },
    {
        "username": "user2",
        "email": "user2@example.com",
        "full_name": "Người dùng 2",
        "role": "user",
        "password": NORMAL_USER_PASSWORD,
    },
]

ROOMS = [
    {
        "name": "Phòng họp A",
        "location": "Tầng 2 - Tòa A",
        "capacity": 8,
        "description": "Phòng họp nhỏ cho nhóm 4-8 người.",
    },
    {
        "name": "Phòng họp B",
        "location": "Tầng 3 - Tòa A",
        "capacity": 16,
        "description": "Phòng họp trung bình cho các buổi làm việc nhóm.",
    },
    {
        "name": "Phòng VIP",
        "location": "Tầng 5 - Tòa A",
        "capacity": 12,
        "description": "Phòng họp VIP với đầy đủ thiết bị trình chiếu và hội nghị truyền hình.",
    },
]


def _seed_users(db) -> tuple[int, int]:
    """Thêm admin và 2 người dùng thường nếu chưa tồn tại."""
    created = 0
    skipped = 0

    for account in (ADMIN_ACCOUNT, *NORMAL_ACCOUNTS):
        exists = db.query(User).filter(User.username == account["username"]).first()
        if exists is None:
            # Kiểm tra cả email vì cột này có UNIQUE constraint.
            exists_by_email = None
            if account["email"]:
                exists_by_email = db.query(User).filter(User.email == account["email"]).first()
            if exists_by_email is None:
                db.add(
                    User(
                        username=account["username"],
                        email=account["email"],
                        full_name=account["full_name"],
                        hashed_password=hash_password(account["password"]),
                        role=account["role"],
                        is_active=True,
                    )
                )
                created += 1
                continue
        skipped += 1

    db.flush()
    return created, skipped


def _seed_rooms(db) -> tuple[int, int]:
    """Thêm 3 phòng họp mẫu nếu chưa tồn tại (theo name)."""
    created = 0
    skipped = 0

    for room_data in ROOMS:
        exists = db.query(Room).filter(Room.name == room_data["name"]).first()
        if exists is None:
            db.add(Room(is_active=True, **room_data))
            created += 1
        else:
            skipped += 1

    db.flush()
    return created, skipped


def seed() -> None:
    # Tạo bảng nếu chưa có; create_all an toàn khi bảng đã tồn tại.
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        user_created, user_skipped = _seed_users(db)
        room_created, room_skipped = _seed_rooms(db)
        db.commit()
        print(
            "Seed complete: "
            f"users created={user_created}, skipped={user_skipped}; "
            f"rooms created={room_created}, skipped={room_skipped}"
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()