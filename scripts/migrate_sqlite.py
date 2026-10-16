"""
migrate_sqlite.py — Vá cấu trúc bảng meetings & meeting_participants cho SQLite.

Thay đổi:
1. meetings: thêm meeting_type, meeting_link, cancellation_reason, cancelled_at,
   check_in_time, check_out_time, reminder_sent.
   Sửa room_id → NULLABLE, FK ON DELETE SET NULL (thay vì CASCADE).
2. meeting_participants: thêm response_status.

An toàn: dùng transaction, tạo bảng mới → copy data → đổi tên.
"""
import sqlite3
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "meeting.db")

def get_column_names(conn, table):
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cursor.fetchall()]

def migrate():
    print(f"[INFO] Mở database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = OFF")

    try:
        # =============================================
        # 1. MIGRATE bảng meetings
        # =============================================
        meeting_cols = get_column_names(conn, "meetings")
        print(f"[INFO] Cột hiện tại của meetings: {meeting_cols}")

        missing_cols = []
        need_room_id_fix = False

        # Kiểm tra cột thiếu
        needed = ["meeting_type", "meeting_link", "cancellation_reason",
                  "cancelled_at", "check_in_time", "check_out_time", "reminder_sent"]
        for col in needed:
            if col not in meeting_cols:
                missing_cols.append(col)

        # Kiểm tra room_id nullable & FK
        room_info = conn.execute("PRAGMA table_info(meetings)").fetchall()
        for row in room_info:
            if row[1] == "room_id" and row[3] == 1:  # notnull = 1
                need_room_id_fix = True

        fk_info = conn.execute("PRAGMA foreign_key_list(meetings)").fetchall()
        for fk in fk_info:
            if fk[3] == "room_id" and fk[5] != "SET NULL":
                need_room_id_fix = True

        if not missing_cols and not need_room_id_fix:
            print("[OK] Bảng meetings đã có đầy đủ cột và cấu hình FK đúng.")
        else:
            print(f"[FIX] Cột thiếu: {missing_cols}")
            if need_room_id_fix:
                print("[FIX] room_id cần sửa: NULLABLE + ON DELETE SET NULL")

            # Tạo bảng mới với schema đầy đủ
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS meetings_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title VARCHAR(200) NOT NULL,
                    description TEXT,
                    cancellation_reason TEXT,
                    cancelled_at DATETIME,
                    meeting_type VARCHAR(20) NOT NULL DEFAULT 'offline',
                    meeting_link VARCHAR(255),
                    is_recurring BOOLEAN NOT NULL DEFAULT 0,
                    recurring_type VARCHAR(20),
                    room_id INTEGER REFERENCES rooms(id) ON DELETE SET NULL,
                    organizer_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'scheduled',
                    check_in_time DATETIME,
                    check_out_time DATETIME,
                    reminder_sent BOOLEAN NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME
                );
            """)

            # Copy dữ liệu cũ sang bảng mới
            old_cols_for_copy = [c for c in meeting_cols if c in [
                "id", "title", "description", "is_recurring", "recurring_type",
                "room_id", "organizer_id", "start_time", "end_time", "status",
                "created_at", "updated_at",
                # Nếu đã có sẵn col nào thì cũng copy
                "meeting_type", "meeting_link", "cancellation_reason", "cancelled_at",
                "check_in_time", "check_out_time", "reminder_sent"
            ]]
            cols_str = ", ".join(old_cols_for_copy)
            print(f"[INFO] Copy dữ liệu: {cols_str}")
            conn.execute(f"INSERT INTO meetings_new ({cols_str}) SELECT {cols_str} FROM meetings")

            # Đổi tên
            conn.execute("DROP TABLE meetings")
            conn.execute("ALTER TABLE meetings_new RENAME TO meetings")

            # Tạo lại index
            conn.execute("CREATE INDEX IF NOT EXISTS ix_meetings_id ON meetings(id)")
            conn.execute("CREATE INDEX IF NOT EXISTS ix_meetings_title ON meetings(title)")
            conn.execute("CREATE INDEX IF NOT EXISTS ix_meetings_room_id ON meetings(room_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS ix_meetings_organizer_id ON meetings(organizer_id)")

            conn.commit()
            print("[OK] Đã migrate bảng meetings thành công!")

        # =============================================
        # 2. MIGRATE bảng meeting_participants
        # =============================================
        participant_cols = get_column_names(conn, "meeting_participants")
        print(f"\n[INFO] Cột hiện tại của meeting_participants: {participant_cols}")

        if "response_status" not in participant_cols:
            print("[FIX] Thêm cột response_status vào meeting_participants")
            # SQLite hỗ trợ ALTER TABLE ADD COLUMN
            conn.execute("""
                ALTER TABLE meeting_participants
                ADD COLUMN response_status VARCHAR(20) NOT NULL DEFAULT 'pending'
            """)
            conn.commit()
            print("[OK] Đã thêm response_status!")
        else:
            print("[OK] Bảng meeting_participants đã có cột response_status.")

        # =============================================
        # 3. XÁC MINH KẾT QUẢ
        # =============================================
        print("\n" + "=" * 60)
        print("XÁC MINH KẾT QUẢ MIGRATION")
        print("=" * 60)

        final_cols = get_column_names(conn, "meetings")
        print(f"\n[VERIFY] Cột meetings: {final_cols}")

        final_part_cols = get_column_names(conn, "meeting_participants")
        print(f"[VERIFY] Cột meeting_participants: {final_part_cols}")

        # Kiểm tra FK
        fk_final = conn.execute("PRAGMA foreign_key_list(meetings)").fetchall()
        print(f"[VERIFY] FK meetings: {fk_final}")

        # Kiểm tra room_id nullable
        for row in conn.execute("PRAGMA table_info(meetings)").fetchall():
            if row[1] == "room_id":
                nullable = "NULLABLE" if row[3] == 0 else "NOT NULL"
                print(f"[VERIFY] room_id: {nullable}")

        # Đếm records
        count = conn.execute("SELECT COUNT(*) FROM meetings").fetchone()[0]
        print(f"[VERIFY] Số meeting records: {count}")

        count_p = conn.execute("SELECT COUNT(*) FROM meeting_participants").fetchone()[0]
        print(f"[VERIFY] Số meeting_participant records: {count_p}")

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Migration thất bại: {e}")
        sys.exit(1)
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()

    print("\n✅ Migration hoàn tất!")

if __name__ == "__main__":
    migrate()
