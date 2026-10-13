from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.models import Base
from app.models.meeting import Meeting


def test_upgrade_head_creates_current_schema_for_empty_database(tmp_path, monkeypatch):
    database_path = tmp_path / "fresh.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)

    project_root = Path(__file__).resolve().parents[1]
    config = Config(str(project_root / "alembic.ini"))
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        assert {
            "users",
            "rooms",
            "meetings",
            "meeting_participants",
            "equipments",
            "meeting_equipments",
            "room_equipments",
            "google_calendar_events",
            "departments",
        } <= tables
        assert tables - {"alembic_version"} == set(Base.metadata.tables)
        for table in Base.metadata.sorted_tables:
            actual_columns = {
                column["name"] for column in inspector.get_columns(table.name)
            }
            assert actual_columns == set(table.columns.keys())

        assert {
            "google_refresh_token",
            "department_id",
        } <= {column["name"] for column in inspector.get_columns("users")}
        assert {
            "meeting_link",
            "check_in_time",
            "check_out_time",
            "reminder_sent",
            "cancellation_reason",
            "cancelled_at",
        } <= {column["name"] for column in inspector.get_columns("meetings")}
        assert "qr_token" in {
            column["name"] for column in inspector.get_columns("rooms")
        }
        assert "response_status" in {
            column["name"]
            for column in inspector.get_columns("meeting_participants")
        }
    finally:
        engine.dispose()

    command.downgrade(config, "base")
    engine = create_engine(database_url)
    try:
        assert "users" not in inspect(engine).get_table_names()
    finally:
        engine.dispose()


def test_upgrade_head_creates_roomsync_chat_tables(tmp_path, monkeypatch):
    database_path = tmp_path / "roomsync-chat.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)

    project_root = Path(__file__).resolve().parents[1]
    config = Config(str(project_root / "alembic.ini"))
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        assert {
            "chat_sessions",
            "chat_messages",
        } <= set(inspector.get_table_names())
        for table_name in ("chat_sessions", "chat_messages"):
            assert {
                column["name"] for column in inspector.get_columns(table_name)
            } == set(Base.metadata.tables[table_name].columns.keys())

        session_foreign_keys = inspector.get_foreign_keys("chat_sessions")
        assert any(
            foreign_key["referred_table"] == "users"
            and foreign_key["constrained_columns"] == ["user_id"]
            for foreign_key in session_foreign_keys
        )
        message_foreign_keys = inspector.get_foreign_keys("chat_messages")
        assert any(
            foreign_key["referred_table"] == "chat_sessions"
            and foreign_key["constrained_columns"] == ["session_id"]
            for foreign_key in message_foreign_keys
        )
    finally:
        engine.dispose()


def test_legacy_online_link_remains_available_through_compatibility_property():
    meeting = Meeting(legacy_online_link="https://meet.example.test/legacy")

    assert meeting.online_link == "https://meet.example.test/legacy"

    meeting.online_link = "https://meet.example.test/new"
    assert meeting.meeting_link == "https://meet.example.test/new"
    assert meeting.legacy_online_link == "https://meet.example.test/new"
