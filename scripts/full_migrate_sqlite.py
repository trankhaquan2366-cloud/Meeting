"""
full_migrate_sqlite.py — Tao tat ca bang thieu va them cot thieu cho SQLite.

- Tao cac bang con thieu: departments, equipments, meeting_equipments, etc.
- Them cot thieu vao bang users.
- Su dung Base.metadata.create_all cho cac bang moi.
"""
import sys
import os
import sqlite3

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "meeting.db")


def get_column_names(conn, table):
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cursor.fetchall()]


def get_tables(conn):
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def migrate():
    print(f"[INFO] DB path: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = OFF")

    existing_tables = get_tables(conn)
    print(f"[INFO] Existing tables: {existing_tables}")

    # =========================================================
    # 1. CREATE missing tables
    # =========================================================

    if "departments" not in existing_tables:
        print("[CREATE] departments")
        conn.execute("""
            CREATE TABLE departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(120) NOT NULL UNIQUE,
                code VARCHAR(50) UNIQUE,
                external_id VARCHAR(50)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS ix_departments_name ON departments(name)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_departments_code ON departments(code)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_departments_external_id ON departments(external_id)")

    if "equipments" not in existing_tables:
        print("[CREATE] equipments")
        conn.execute("""
            CREATE TABLE equipments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(150) NOT NULL,
                code VARCHAR(50) UNIQUE,
                category VARCHAR(50),
                total_qty INTEGER NOT NULL DEFAULT 1,
                description TEXT,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME
            )
        """)

    if "meeting_equipments" not in existing_tables:
        print("[CREATE] meeting_equipments")
        conn.execute("""
            CREATE TABLE meeting_equipments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
                equipment_id INTEGER NOT NULL REFERENCES equipments(id) ON DELETE RESTRICT,
                quantity INTEGER NOT NULL DEFAULT 1,
                note VARCHAR(255),
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(meeting_id, equipment_id)
            )
        """)

    if "room_equipments" not in existing_tables:
        print("[CREATE] room_equipments")
        conn.execute("""
            CREATE TABLE room_equipments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
                equipment_id INTEGER NOT NULL REFERENCES equipments(id) ON DELETE CASCADE,
                quantity INTEGER NOT NULL DEFAULT 1,
                UNIQUE(room_id, equipment_id)
            )
        """)

    if "notifications" not in existing_tables:
        print("[CREATE] notifications")
        conn.execute("""
            CREATE TABLE notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                meeting_id INTEGER REFERENCES meetings(id) ON DELETE SET NULL,
                title VARCHAR(200) NOT NULL,
                content TEXT NOT NULL,
                is_read BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS ix_notifications_meeting_id ON notifications(meeting_id)")

    if "meeting_reminders" not in existing_tables:
        print("[CREATE] meeting_reminders")
        conn.execute("""
            CREATE TABLE meeting_reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                reminder_type VARCHAR(50) NOT NULL,
                sent_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(meeting_id, user_id, reminder_type)
            )
        """)

    if "google_calendar_events" not in existing_tables:
        print("[CREATE] google_calendar_events")
        conn.execute("""
            CREATE TABLE google_calendar_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
                google_event_id VARCHAR(255) NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, meeting_id),
                UNIQUE(user_id, google_event_id)
            )
        """)

    if "chat_sessions" not in existing_tables:
        print("[CREATE] chat_sessions")
        conn.execute("""
            CREATE TABLE chat_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title VARCHAR(200) NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

    if "chat_messages" not in existing_tables:
        print("[CREATE] chat_messages")
        conn.execute("""
            CREATE TABLE chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
                sender VARCHAR(10) NOT NULL,
                content TEXT NOT NULL,
                intent VARCHAR(100),
                slots TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

    if "project_groups" not in existing_tables:
        print("[CREATE] project_groups")
        conn.execute("""
            CREATE TABLE project_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(120) NOT NULL,
                code VARCHAR(50) NOT NULL UNIQUE,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

    if "user_project_groups" not in existing_tables:
        print("[CREATE] user_project_groups")
        conn.execute("""
            CREATE TABLE user_project_groups (
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                project_group_id INTEGER NOT NULL REFERENCES project_groups(id) ON DELETE CASCADE,
                PRIMARY KEY (user_id, project_group_id)
            )
        """)

    conn.commit()

    # =========================================================
    # 2. ADD missing columns to users table
    # =========================================================
    user_cols = get_column_names(conn, "users")
    print(f"\n[INFO] Existing user columns: {user_cols}")

    add_cols = [
        ("google_refresh_token", "TEXT"),
        ("google_calendar_connected_at", "DATETIME"),
        ("status", "VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'"),
        ("can_book", "BOOLEAN NOT NULL DEFAULT 1"),
        ("can_attend", "BOOLEAN NOT NULL DEFAULT 1"),
        ("department_id", "INTEGER REFERENCES departments(id) ON DELETE SET NULL"),
        ("external_id", "VARCHAR(50)"),
        ("position", "VARCHAR(100)"),
    ]

    for col_name, col_def in add_cols:
        if col_name not in user_cols:
            print(f"[ADD] users.{col_name}")
            conn.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}")

    conn.commit()

    # =========================================================
    # 3. ADD missing columns to rooms table
    # =========================================================
    room_cols = get_column_names(conn, "rooms")
    print(f"\n[INFO] Existing room columns: {room_cols}")

    room_add = [
        ("amenities", "TEXT"),
        ("description", "TEXT"),
    ]
    for col_name, col_def in room_add:
        if col_name not in room_cols:
            print(f"[ADD] rooms.{col_name}")
            conn.execute(f"ALTER TABLE rooms ADD COLUMN {col_name} {col_def}")

    conn.commit()

    # =========================================================
    # 4. VERIFY
    # =========================================================
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)

    final_tables = get_tables(conn)
    print(f"\nAll tables: {final_tables}")

    final_user_cols = get_column_names(conn, "users")
    print(f"Users columns: {final_user_cols}")

    final_room_cols = get_column_names(conn, "rooms")
    print(f"Rooms columns: {final_room_cols}")

    user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    meeting_count = conn.execute("SELECT COUNT(*) FROM meetings").fetchone()[0]
    room_count = conn.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]
    print(f"\nData: {user_count} users, {meeting_count} meetings, {room_count} rooms")

    conn.execute("PRAGMA foreign_keys = ON")
    conn.close()
    print("\n✅ Full migration complete!")


if __name__ == "__main__":
    migrate()
