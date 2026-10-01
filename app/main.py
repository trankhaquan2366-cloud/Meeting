from pathlib import Path
from fastapi import FastAPI, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, configure_mappers

# 1. Import DB Engine & Session (Chỉ dùng 1 đối tượng Base duy nhất từ app.db.session)
from app.db.session import Base
from app.core.database import engine, get_db

# 2. Import TẤT CẢ Models để đăng ký đồng bộ vào cùng một ORM Registry
from app.models.user import User
from app.models.room import Room
from app.models.meeting import Meeting
from app.models.equipment import Equipment, MeetingEquipment, RoomEquipment
import app.models

# 3. Ép SQLAlchemy liên kết tất cả Mappers trước khi tạo bảng Database
try:
    configure_mappers()
except Exception as e:
    print(f"❌ Lỗi cấu hình ORM Models: {e}")

Base.metadata.create_all(bind=engine)

# 4. Import Routers, Security và Schemas
from app.routers import auth, rooms, meetings, equipments
from app.core.security import authenticate_user
from app.routers.auth import issue_token
from app.schemas.auth import LoginRequest

# 5. Khởi tạo ứng dụng FastAPI
app = FastAPI(title="Meeting Management System API", version="1.0.0")

# 6. Cấu hình CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 7. Cấu hình Static Files & Frontend
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
    assets_dir = FRONTEND_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

# 8. Đăng ký các API Routers (Đã loại bỏ duplicate và thêm prefix chuẩn)
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(rooms.router, prefix="/api/rooms", tags=["rooms"])
app.include_router(meetings.router, prefix="/api/meetings", tags=["meetings"])
app.include_router(equipments.router, prefix="/api/equipments", tags=["equipments"])

# 9. Legacy / Compatibility Endpoints
@app.post("/api/login", tags=["auth"])
def legacy_login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Compatibility endpoint; uses the exact same database auth as /api/auth/login."""
    user = authenticate_user(db, payload.username, payload.password)
    token_response = issue_token(user)
    return {
        **token_response.model_dump(),
        "user_name": token_response.full_name,
    }

# 10. Web UI & Root Endpoints
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