"""Apply reminder-related migrations and verify the MySQL scheduler lock."""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def main() -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL is missing from .env")
        return 1

    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        if engine.dialect.name != "mysql":
            print(
                "ERROR: Reminder migrations and the named-lock check require MySQL; "
                f"detected dialect {engine.dialect.name!r}"
            )
            return 1

        with engine.begin() as connection:
            migrations = (
                (
                    "013",
                    "013_create_email_delivery_retry_queue.sql",
                    lambda inspector: inspector.has_table("email_deliveries"),
                ),
                (
                    "014",
                    "014_add_meeting_id_to_notifications.sql",
                    lambda inspector: any(
                        column["name"] == "meeting_id"
                        for column in inspector.get_columns("notifications")
                    ),
                ),
            )
            for migration_number, filename, already_applied in migrations:
                migration_path = PROJECT_ROOT / "migrations" / filename
                if not migration_path.is_file():
                    print(f"ERROR: Migration file not found: {migration_path}")
                    return 1
                inspector = inspect(connection)
                if not inspector.has_table(
                    "notifications"
                    if migration_number == "014"
                    else "email_deliveries"
                ):
                    if migration_number == "014":
                        print(
                            "ERROR: Migration 014 requires the notifications "
                            "table; apply earlier migrations first"
                        )
                        return 1
                elif already_applied(inspector):
                    print(
                        f"Migration {migration_number}: already applied; skipped"
                    )
                    continue

                statements = [
                    statement.strip()
                    for statement in migration_path.read_text(encoding="utf-8")
                    .split(";")
                    if statement.strip()
                    and not statement.strip().upper().startswith("USE ")
                ]
                for statement in statements:
                    connection.exec_driver_sql(statement)
                print(f"Migration {migration_number}: applied")

        with engine.connect() as connection:
            lock_name = "meeting_reminder_scheduler"
            acquired = connection.execute(
                text("SELECT GET_LOCK(:lock_name, 2)"),
                {"lock_name": lock_name},
            ).scalar()
            if acquired != 1:
                print(
                    "MySQL named lock: FAIL "
                    f"(GET_LOCK returned {acquired!r})"
                )
                return 1
            released = connection.execute(
                text("SELECT RELEASE_LOCK(:lock_name)"),
                {"lock_name": lock_name},
            ).scalar()
            if released != 1:
                print(
                    "MySQL named lock: FAIL "
                    f"(RELEASE_LOCK returned {released!r})"
                )
                return 1

        print("MySQL named lock: PASS (GET_LOCK and RELEASE_LOCK succeeded)")
        return 0
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
