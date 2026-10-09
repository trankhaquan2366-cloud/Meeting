from pathlib import Path
from fastapi import FastAPI, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, configure_mappers

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

# 3. Khởi tạo Mapper & Tạo bảng Database
try:
    configure_mappers()
except Exception as e:
    print(f"❌ Lỗi cấu hình ORM Models: {e}")

Base.metadata.create_all(bind=engine)

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