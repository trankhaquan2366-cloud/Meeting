import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.routers import auth, rooms
from app.core.database import Base, engine
import app.models 
from app.routers import auth, meetings

# Tự động tạo các bảng CSDL nếu chưa có
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Meeting Management System API",
    description="Hệ thống quản lý phòng họp và lịch họp",
    version="1.0.0",
)

# Cấu hình CORS để giao diện Web gọi API không bị chặn
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký các Router API
app.include_router(auth.router)
app.include_router(meetings.router)
app.include_router(rooms.router)
# Phục vụ file tĩnh từ thư mục static
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/login", tags=["Web UI"], summary="Màn hình Đăng nhập Web")
def render_login_page():
    """Trả về Giao diện Web Đăng nhập"""
    login_path = os.path.join("static", "login.html")
    if os.path.exists(login_path):
        return FileResponse(login_path)
    return {"error": "Không tìm thấy file static/login.html"}


@app.get("/", tags=["Root"])
def read_root():
    return {
        "status": "success",
        "message": "API Hệ thống Quản lý Phòng họp đang hoạt động!",
        "login_url": "http://127.0.0.1:8000/login"
    }