from pathlib import Path
from fastapi import FastAPI, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, configure_mappers
from sqlalchemy import inspect

# 1. DB & Models
from app.db.session import Base
from app.core.database import engine, get_db
from app.models.user import User
from app.models.room import Room
from app.models.meeting import Meeting
from app.models.equipment import Equipment, MeetingEquipment, RoomEquipment
from app.models.google_calendar_event import GoogleCalendarEvent

# 2. Routers & Security
from app.routers import auth, equipment, meetings, notifications, rooms, users
from app.core.security import authenticate_user
from app.routers.auth import issue_token
from app.schemas.auth import LoginRequest
from app.routers import auth, equipment, meetings, notifications, rooms, users
from app.routers import reports
# 3. Khởi tạo Mapper & Tạo bảng Database
try:
    configure_mappers()
except Exception as e:
    print(f"❌ Lỗi cấu hình ORM Models: {e}")

from sqlalchemy import text

Base.metadata.create_all(bind=engine)

# Tự động cập nhật các cột mới nếu các bảng đã tồn tại từ schema cũ
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
    except Exception as e:
        print(f"⚠️ Thông báo cập nhật schema: {e}")

_auto_migrate_schema()

# 4. Khởi tạo ứng dụng FastAPI (Phải khởi tạo TRƯỚC khi gán Middleware/Router)
app = FastAPI(title="Meeting Management System API", version="1.0.0")

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
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
    assets_dir = FRONTEND_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

# 7. Đăng ký API Routers với Prefix chuẩn
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(rooms.router, prefix="/api/rooms", tags=["rooms"])
app.include_router(meetings.router, prefix="/api/meetings", tags=["meetings"])
app.include_router(equipment.router, prefix="/api/equipments", tags=["equipments"])
app.include_router(notifications.router, prefix="/api", tags=["notifications"])
app.include_router(users.router, prefix="/api", tags=["users"])
app.include_router(reports.router, prefix="/api/v1", tags=["reports"])
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
    return {"status": "success", "message": "Meeting Management System API is running"}

@app.get("/dashboard", tags=["Web UI"])
def render_dashboard_page():
    path = FRONTEND_DIR / "dashboard.html"
    return FileResponse(path) if path.exists() else {"error": "Dashboard page not found"}

@app.get("/app", tags=["Web UI"])
def render_index_page():
    path = FRONTEND_DIR / "index.html"
    return FileResponse(path) if path.exists() else {"error": "Application page not found"}