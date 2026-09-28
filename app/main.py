from pathlib import Path
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.routers import auth, rooms, meetings
from app.core.database import Base, engine, get_db
from app.core.security import create_access_token
from app.models.user import User
import app.models 
from app.routers import auth, meetings, rooms

# Tự động tạo các bảng CSDL nếu chưa có[cite: 6]
Base.metadata.create_all(bind=engine)

# 1. KHỞI TẠO FASTAPI[cite: 6]
app = FastAPI(
    title="Meeting Management System API",
    description="Hệ thống quản lý phòng họp và lịch họp",
    version="1.0.0",
)

# Cấu hình CORS[cite: 6]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. CẤU HÌNH FRONTEND TẬP TRUNG[cite: 6]
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
    
    assets_dir = FRONTEND_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

# 3. ĐĂNG KÝ CÁC ROUTER API[cite: 6]
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(rooms.router, prefix="/api/rooms", tags=["rooms"])    # rooms.py KHÔNG có prefix
app.include_router(meetings.router, prefix="/api", tags=["meetings"])

# 4. API ĐĂNG NHẬP TRỰC TIẾP (Khớp tuyệt đối với login.js)
class LoginSchema(BaseModel):
    username: str
    password: str

@app.post("/api/login", tags=["Authentication"])
def login(data: LoginSchema, db: Session = Depends(get_db)):
    if data.username == "admin" and data.password == "123456":
        access_token = create_access_token(data={"sub": "admin", "role": "admin"})
        return {
            "access_token": access_token,
            "role": "admin",
            "user_name": "Quản trị viên"
        }
    elif data.username == "user" and data.password == "123456":
        access_token = create_access_token(data={"sub": "user", "role": "user"})
        return {
            "access_token": access_token,
            "role": "user",
            "user_name": "Nhân viên"
        }
    
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Tài khoản hoặc mật khẩu không chính xác!"
    )

# 5. CÁC ROUTE GIAO DIỆN WEB (UI)[cite: 6]
@app.get("/", tags=["Root"])
def read_root():
    return {
        "status": "success",
        "message": "API Hệ thống Quản lý Phòng họp đang hoạt động!"
    }

@app.get("/dashboard", tags=["Web UI"], summary="Màn hình Dashboard")
def render_dashboard_page():
    dashboard_path = FRONTEND_DIR / "dashboard.html"
    if dashboard_path.exists():
        return FileResponse(dashboard_path)
    return {"error": "Không tìm thấy file frontend/dashboard.html"}

@app.get("/app", tags=["Web UI"], summary="Màn hình Quản lý chính (Đăng nhập)")
def render_index_page():
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"error": "Không tìm thấy file frontend/index.html"}