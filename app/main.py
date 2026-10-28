import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Depends, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, configure_mappers
from sqlalchemy import inspect
from uuid import uuid4

# 1. DB & Models
from app.db.session import Base
from app.core.database import engine, get_db, SessionLocal
from app.models.user import User
from app.models.department import Department
from app.models.room import Room
from app.models.meeting import Meeting
from app.models.equipment import Equipment, MeetingEquipment, RoomEquipment
from app.models.google_calendar_event import GoogleCalendarEvent
from app.models.notification import Notification
from app.models.meeting_reminder import MeetingReminder
from app.models.meeting import MeetingParticipant
from app.models.chat import ChatSession, ChatMessage
from app.models.project_group import ProjectGroup

# 2. Routers & Security
from app.routers import (
    admin_analytics,
    admin_sync,
    auth,
    chatbot,
    directories,
    equipment,
    meetings,
    notifications,
    rooms,
    users,
)
from app.core.security import authenticate_user
from app.routers.auth import issue_token
from app.schemas.auth import LoginRequest
from app.routers import reports
from app.schemas.equipment import EquipmentResponse
# 3. Khởi tạo Mapper & Tạo bảng Database
try:
    configure_mappers()
except Exception as e:
    print(f"❌ Lỗi cấu hình ORM Models: {e}")

from sqlalchemy import text

Base.metadata.create_all(bind=engine)

# Tự động cập nhật các cột mới nếu các bảng đã tồn tại từ schema cũ
def _schema_log(message: str) -> None:
    """In log an toàn kể cả khi console không hỗ trợ tiếng Việt/emoji."""
    try:
        print(message)
    except UnicodeEncodeError:
        print(message.encode("ascii", "replace").decode("ascii"))


def _auto_migrate_schema():
    try:
        with engine.begin() as conn:
            if engine.dialect.name == "mysql":
                # 1. Kiểm tra bảng meetings
                cols_meetings = [row[0] for row in conn.execute(text("SHOW COLUMNS FROM meetings")).fetchall()]
                if "meeting_type" not in cols_meetings:
                    conn.execute(text("ALTER TABLE meetings ADD COLUMN meeting_type VARCHAR(20) NOT NULL DEFAULT 'offline' AFTER description"))
                    print("✅ Đã tự động thêm cột 'meeting_type' vào bảng meetings.")
                if "online_link" not in cols_meetings:
                    conn.execute(text("ALTER TABLE meetings ADD COLUMN online_link VARCHAR(500) DEFAULT NULL AFTER meeting_type"))
                    print("✅ Đã tự động thêm cột 'online_link' vào bảng meetings.")

                # Cho phép room_id nhận giá trị NULL (cho cuộc họp trực tuyến)
                room_id_col = conn.execute(text("SHOW COLUMNS FROM meetings LIKE 'room_id'")).fetchone()
                if room_id_col and room_id_col[2] == 'NO':
                    col_type = room_id_col[1]
                    conn.execute(text(f"ALTER TABLE meetings MODIFY COLUMN room_id {col_type} NULL"))
                    print("✅ Đã cập nhật cột 'room_id' cho phép NULL.")

                # 2. Kiểm tra bảng rooms
                cols_rooms = [row[0] for row in conn.execute(text("SHOW COLUMNS FROM rooms")).fetchall()]
                if "amenities" not in cols_rooms:
                    conn.execute(text("ALTER TABLE rooms ADD COLUMN amenities TEXT DEFAULT NULL AFTER description"))
                    print("✅ Đã tự động thêm cột 'amenities' vào bảng rooms.")

            if "rooms" in inspect(conn).get_table_names():
                room_columns = {
                    column["name"]
                    for column in inspect(conn).get_columns("rooms")
                }
                if "room_status" not in room_columns:
                    conn.execute(text(
                        "ALTER TABLE rooms ADD COLUMN room_status "
                        "VARCHAR(20) NOT NULL DEFAULT 'active'"
                    ))
                    conn.execute(text(
                        "UPDATE rooms SET room_status = 'maintenance' "
                        "WHERE is_active = FALSE"
                    ))
                if "room_image" not in room_columns:
                    conn.execute(text(
                        "ALTER TABLE rooms ADD COLUMN room_image VARCHAR(2048) NULL"
                    ))
                if "layout_type" not in room_columns:
                    conn.execute(text(
                        "ALTER TABLE rooms ADD COLUMN layout_type VARCHAR(30) NULL"
                    ))
                if "qr_token" not in room_columns:
                    conn.execute(text(
                        "ALTER TABLE rooms ADD COLUMN qr_token VARCHAR(64) NULL"
                    ))
                    try:
                        conn.execute(text(
                            "CREATE UNIQUE INDEX ix_rooms_qr_token ON rooms (qr_token)"
                        ))
                    except Exception:
                        # MySQL không hỗ trợ IF NOT EXISTS cho CREATE INDEX.
                        _schema_log("[schema] ix_rooms_qr_token đã tồn tại, bỏ qua.")

            if "equipments" in inspect(conn).get_table_names():
                equipment_columns = {
                    column["name"]
                    for column in inspect(conn).get_columns("equipments")
                }
                if "search_keywords" not in equipment_columns:
                    conn.execute(text(
                        "ALTER TABLE equipments ADD COLUMN search_keywords TEXT NULL"
                    ))
                if "operational_status" not in equipment_columns:
                    conn.execute(text(
                        "ALTER TABLE equipments ADD COLUMN operational_status "
                        "VARCHAR(20) NOT NULL DEFAULT 'active'"
                    ))
                    conn.execute(text(
                        "UPDATE equipments SET operational_status = 'retired' "
                        "WHERE is_active = FALSE"
                    ))

            if "meeting_participants" in inspect(conn).get_table_names():
                participant_columns = {
                    column["name"]
                    for column in inspect(conn).get_columns("meeting_participants")
                }
                if "response_status" not in participant_columns:
                    conn.execute(text(
                        "ALTER TABLE meeting_participants "
                        "ADD COLUMN response_status VARCHAR(20) NOT NULL DEFAULT 'pending'"
                    ))
                    print("✅ Đã tự động thêm cột 'response_status' vào bảng meeting_participants.")

            if "users" in inspect(conn).get_table_names():
                user_columns = {
                    column["name"]
                    for column in inspect(conn).get_columns("users")
                }
                if "daily_booking_hours_limit" not in user_columns:
                    conn.execute(text(
                        "ALTER TABLE users ADD COLUMN daily_booking_hours_limit FLOAT NULL"
                    ))
                if "can_bypass_room_approval" not in user_columns:
                    conn.execute(text(
                        "ALTER TABLE users ADD COLUMN can_bypass_room_approval "
                        "BOOLEAN NOT NULL DEFAULT FALSE"
                    ))

            if "notifications" in inspect(conn).get_table_names():
                def notification_columns_now():
                    return {
                        column["name"]
                        for column in inspect(conn).get_columns("notifications")
                    }

                def run_notification_step(label, statement):
                    """Each schema step is isolated so one failure never blocks the rest."""
                    try:
                        conn.execute(text(statement))
                        _schema_log(f"[schema] {label}")
                    except Exception as step_error:
                        _schema_log(f"[schema] skipped: {label} ({step_error})")

                notification_columns = notification_columns_now()
                # Các cột bắt buộc cho trung tâm thông báo 4 tab.
                if "category" not in notification_columns:
                    run_notification_step(
                        "Đã thêm cột notifications.category",
                        "ALTER TABLE notifications "
                        "ADD COLUMN category VARCHAR(20) NOT NULL DEFAULT 'system'",
                    )
                if "group_key" not in notification_columns:
                    run_notification_step(
                        "Đã thêm cột notifications.group_key",
                        "ALTER TABLE notifications ADD COLUMN group_key VARCHAR(80) NULL",
                    )
                if "meeting_id" not in notification_columns:
                    run_notification_step(
                        "Đã thêm cột notifications.meeting_id",
                        "ALTER TABLE notifications ADD COLUMN meeting_id INTEGER NULL",
                    )

                notification_indexes = {
                    index["name"]
                    for index in inspect(conn).get_indexes("notifications")
                }
                if "idx_notifications_group_key" not in notification_indexes:
                    run_notification_step(
                        "Đã tạo index idx_notifications_group_key",
                        "CREATE INDEX idx_notifications_group_key "
                        "ON notifications (group_key)",
                    )
                if "ix_notifications_meeting_id" not in notification_indexes:
                    run_notification_step(
                        "Đã tạo index ix_notifications_meeting_id",
                        "CREATE INDEX ix_notifications_meeting_id "
                        "ON notifications (meeting_id)",
                    )

                if engine.dialect.name == "mysql":
                    notification_foreign_keys = {
                        foreign_key["name"]
                        for foreign_key in inspect(conn).get_foreign_keys("notifications")
                    }
                    if "fk_notifications_meeting_id" not in notification_foreign_keys:
                        run_notification_step(
                            "Đã thêm khóa ngoại notifications.meeting_id",
                            "ALTER TABLE notifications "
                            "ADD CONSTRAINT fk_notifications_meeting_id "
                            "FOREIGN KEY (meeting_id) REFERENCES meetings (id) "
                            "ON DELETE SET NULL",
                        )

                # Phân loại lại các thông báo cũ để 4 tab hiển thị đúng.
                backfill_rules = (
                    ("reminder", "title LIKE '%Nhắc nhở%' OR title LIKE '%[Nhắc nhở]%'"),
                    ("response", "title LIKE '%đồng ý%' OR title LIKE '%từ chối%' "
                                 "OR title LIKE '%xác nhận%'"),
                    ("change", "title LIKE '%Lời mời%' OR title LIKE '%bị hủy%' "
                               "OR title LIKE '%thay đổi%'"),
                )
                for category, condition in backfill_rules:
                    run_notification_step(
                        f"Đã phân loại thông báo cũ vào nhóm '{category}'",
                        "UPDATE notifications SET category = "
                        f"'{category}' WHERE (category IS NULL OR category = '' "
                        f"OR category = 'system') AND ({condition})",
                    )
    except Exception as e:
        _schema_log(f"[schema] migration notice: {e}")

_auto_migrate_schema()

logger = logging.getLogger(__name__)
MEETING_SCHEDULER_INTERVAL_SECONDS = 30


def seed_initial_rooms(force: bool = False) -> None:
    """Tự động kiểm tra và chèn dữ liệu phòng họp mẫu nếu bảng rooms trống."""
    if not force and ("pytest" in sys.modules or os.getenv("TESTING")):
        return

    db: Session = SessionLocal()
    try:
        if db.query(Room).count() == 0:
            sample_rooms = [
                Room(
                    name="Phòng Hội Thảo A",
                    capacity=20,
                    location="Tầng 2",
                    description="Phòng hội thảo lớn dành cho thuyết trình và hội nghị.",
                    amenities='["Màn hình", "Wifi", "Micro", "Máy chiếu"]',
                    is_active=True,
                ),
                Room(
                    name="Phòng Họp Nhóm B",
                    capacity=8,
                    location="Tầng 1",
                    description="Phòng họp nhóm dự án linh hoạt.",
                    amenities='["Wifi", "Bảng trắng", "Ổ cắm điện"]',
                    is_active=True,
                ),
                Room(
                    name="Phòng VIP C",
                    capacity=12,
                    location="Tầng 3",
                    description="Phòng họp cấp cao với trang thiết bị cao cấp.",
                    amenities='["Màn hình", "Video", "Đồ uống", "Wifi"]',
                    is_active=True,
                ),
                Room(
                    name="Phòng Đào Tạo D",
                    capacity=25,
                    location="Tầng 4",
                    description="Phòng đào tạo và workshop nội bộ.",
                    amenities='["Máy chiếu", "Wifi", "Âm thanh", "Micro"]',
                    is_active=True,
                ),
            ]
            db.add_all(sample_rooms)
            db.commit()
            logger.info("Successfully seeded initial room data!")
            print("✅ Successfully seeded initial room data!")
    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding rooms: {e}", exc_info=True)
        print(f"❌ Error seeding rooms: {e}")
    finally:
        db.close()


def seed_initial_directories(force: bool = False) -> None:
    """Seed sample departments and project groups when their tables are empty."""
    if not force and ("pytest" in sys.modules or os.getenv("TESTING")):
        return

    db = SessionLocal()
    try:
        if db.query(Department).count() == 0:
            departments = [
                ("Phòng Công nghệ thông tin", "PHONG-CONG-NGHE-THONG-TIN"),
                ("Phòng Nhân sự", "PHONG-NHAN-SU"),
                ("Phòng Kế toán", "PHONG-KE-TOAN"),
                ("Phòng Kinh doanh", "PHONG-KINH-DOANH"),
                ("Phòng Ban Giám đốc", "PHONG-BAN-GIAM-DOC"),
            ]
            db.add_all(
                Department(name=name, code=code)
                for name, code in departments
            )
        if db.query(ProjectGroup).count() == 0:
            project_groups = [
                ("Dự án RoomSync", "DU-AN-ROOMSYNC"),
                ("Dự án AI Assistant", "DU-AN-AI-ASSISTANT"),
                ("Dự án Chuyển đổi số", "DU-AN-CHUYEN-DOI-SO"),
            ]
            db.add_all(
                ProjectGroup(name=name, code=code)
                for name, code in project_groups
            )
        db.commit()
        logger.info("Initial department and project group directories are ready.")
    except Exception:
        db.rollback()
        logger.exception("Error seeding department and project group directories.")
        raise
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    seed_initial_rooms()
    seed_initial_directories()
    from app.services.reminder_service import (
        shutdown_reminder_scheduler,
        start_reminder_scheduler,
    )
    start_reminder_scheduler(interval_seconds=MEETING_SCHEDULER_INTERVAL_SECONDS)
    try:
        yield
    finally:
        shutdown_reminder_scheduler()


# 4. Khởi tạo ứng dụng FastAPI (Phải khởi tạo TRƯỚC khi gán Middleware/Router)
app = FastAPI(title="Meeting Management System API", version="1.0.0", lifespan=lifespan)


@app.on_event("startup")
def startup_seed_rooms():
    seed_initial_rooms()



@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Log unexpected failures and return a safe JSON 500 response."""
    error_id = uuid4().hex
    logger.exception(
        "Unhandled request error id=%s method=%s path=%s",
        error_id,
        request.method,
        request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Lỗi máy chủ nội bộ. Vui lòng thử lại sau.",
            "error_id": error_id,
        },
        headers={"X-Error-ID": error_id},
    )


# 5. Cấu hình CORS Middleware (Cho phép Frontend port 3000 gọi sang Backend port 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 6. Cấu hình Static Files & Frontend
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

if FRONTEND_DIR.exists():
    js_dir = FRONTEND_DIR / "js"
    if js_dir.exists():
        app.mount("/js", StaticFiles(directory=str(js_dir)), name="js")
    css_dir = FRONTEND_DIR / "css"
    if css_dir.exists():
        app.mount("/css", StaticFiles(directory=str(css_dir)), name="css")
    images_dir = FRONTEND_DIR / "images"
    if images_dir.exists():
        app.mount("/images", StaticFiles(directory=str(images_dir)), name="images")
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
    assets_dir = FRONTEND_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

# 7. Đăng ký API Routers với Prefix chuẩn
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(auth.router, prefix="/api/v1", tags=["auth-v1"])
app.include_router(rooms.router, prefix="/api/rooms", tags=["rooms"])
app.include_router(meetings.router, prefix="/api/meetings", tags=["meetings"])
# Versioned aliases for the QR check-in API.
app.include_router(rooms.router, prefix="/api/v1/rooms", tags=["rooms-v1"])
app.include_router(meetings.router, prefix="/api/v1/meetings", tags=["meetings-v1"])
app.include_router(
    admin_analytics.router,
    prefix="/api/v1/admin/analytics",
    tags=["admin-analytics"],
)
app.include_router(
    admin_sync.router,
    prefix="/api/v1/admin",
    tags=["admin-sync"],
)
app.include_router(equipment.router, prefix="/api/equipments", tags=["equipments"])
app.include_router(
    equipment.router,
    prefix="/api/v1/equipments",
    tags=["equipments-v1"],
)
app.add_api_route(
    "/api/equipments",
    equipment.get_equipments,
    methods=["GET"],
    response_model=list[EquipmentResponse],
    include_in_schema=False,
)
app.add_api_route(
    "/api/v1/equipments",
    equipment.get_equipments,
    methods=["GET"],
    response_model=list[EquipmentResponse],
    include_in_schema=False,
)
app.include_router(notifications.router, prefix="/api", tags=["notifications"])
app.include_router(
    notifications.router,
    prefix="/api/v1",
    tags=["notifications-v1"],
)
app.include_router(users.router, prefix="/api", tags=["users"])
app.include_router(users.router, prefix="/api/v1", tags=["users-v1"])
app.include_router(directories.router, prefix="/api", tags=["directories"])
app.include_router(directories.router, prefix="/api/v1", tags=["directories-v1"])
app.include_router(reports.router, prefix="/api/v1", tags=["reports"])
app.include_router(chatbot.router, prefix="/api/v1/chatbot", tags=["chatbot"])
# 8. Endpoints Đăng nhập & Root
@app.post("/api/login", tags=["auth"])
def legacy_login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.username, payload.password)
    token_response = issue_token(user)
    return {
        **token_response.model_dump(),
        "user_name": token_response.full_name,
    }

@app.get("/", tags=["Root"])
def read_root():
    index_path = FRONTEND_DIR / "index.html"
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return {"status": "success", "message": "Meeting Management System API is running"}


@app.get("/api/health", tags=["Health"])
def health_check():
    return {"status": "success", "message": "Meeting Management System API is running"}


@app.get("/manifest.json", include_in_schema=False)
def pwa_manifest():
    return FileResponse(
        FRONTEND_DIR / "manifest.json",
        media_type="application/manifest+json",
    )


@app.get("/sw.js", include_in_schema=False)
def pwa_service_worker():
    return FileResponse(
        FRONTEND_DIR / "sw.js",
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/"},
    )


@app.get("/dashboard", tags=["Web UI"])
def render_dashboard_page():
    path = FRONTEND_DIR / "dashboard.html"
    return FileResponse(path) if path.exists() else {"error": "Dashboard page not found"}

@app.get("/app", tags=["Web UI"])
def render_index_page():
    path = FRONTEND_DIR / "index.html"
    return FileResponse(path) if path.exists() else {"error": "Application page not found"}