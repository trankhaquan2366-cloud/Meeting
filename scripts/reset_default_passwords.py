"""Reset seeded accounts to the default password for local recovery."""

from pathlib import Path
import sys

from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.database import SessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.user import User  # noqa: E402
from scripts.seed import DEMO_USERS  # noqa: E402

DEFAULT_PASSWORD = "123456"
DEFAULT_USERNAMES = ("admin", *(user[0] for user in DEMO_USERS))


def reset_default_passwords(db: Session) -> int:
    if db.query(User.id).first() is None:
        db.add(
            User(
                username="admin",
                email="admin@gmail.com",
                full_name="Quản trị viên",
                hashed_password=hash_password(DEFAULT_PASSWORD),
                role="admin",
                is_active=True,
                status="ACTIVE",
            )
        )
        db.commit()
        return 1

    users = db.query(User).filter(User.username.in_(DEFAULT_USERNAMES)).all()
    try:
        for user in users:
            user.hashed_password = hash_password(DEFAULT_PASSWORD)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return len(users)


def main() -> None:
    db = SessionLocal()
    try:
        count = reset_default_passwords(db)
        print(f"Đã khôi phục mật khẩu mặc định cho {count} tài khoản.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
