from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine
import app.models  # Đảm bảo tất cả models (User, Room, Meeting) được đăng ký trước khi tạo bảng
from app.routers import auth, meeting

# Tự động tạo các bảng trong MySQL nếu chưa tồn tại
Base.metadata.create_all(bind=engine)

# Khởi tạo ứng dụng FastAPI
app = FastAPI(
    title="Meeting Management System API",
    description="Hệ thống quản lý phòng họp và lịch họp",
    version="1.0.0",
)

# Cấu hình CORS cho phép kết nối từ Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Kết nối các Router API
app.include_router(auth.router)
app.include_router(meeting.router)

@app.get("/", tags=["Root"])
def read_root():
    return {
        "status": "success",
        "message": "API Hệ thống Quản lý Phòng họp đang hoạt động!",
    }