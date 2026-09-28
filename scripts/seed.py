"""Create initial users and rooms without duplicating existing rows."""

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
from app.models.room import Room  # noqa: E402
from app.models.user import User  # noqa: E402
import app.models  # noqa: E402,F401


def seed() -> None:
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if admin is None:
            configured_password = os.getenv("SEED_ADMIN_PASSWORD")
            generated_password = configured_password is None
            password = configured_password or secrets.token_urlsafe(16)
            email = "admin@meeting.local"
            if db.query(User).filter(User.email == email).first():
                email = None
            admin = User(
                username="admin",
                email=email,
                full_name="Quản trị viên",
                hashed_password=hash_password(password),
                role="admin",
                is_active=True,
            )
            db.add(admin)
            db.commit()
            if generated_password:
                print(f"Created admin. One-time password: {password}")
            else:
                print("Created admin using SEED_ADMIN_PASSWORD from .env.")
        else:
            print("Admin already exists; no duplicate created.")

        if db.query(Room).filter(Room.name == "Phòng VIP").first() is None:
            db.add(
                Room(
                    name="Phòng VIP",
                    location="Tầng 5 - Tòa A",
                    capacity=12,
                    description="Phòng họp VIP.",
                    is_active=True,
                )
            )
            db.commit()
            print("Created room: Phòng VIP")
        else:
            print("Room already exists; no duplicate created.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
