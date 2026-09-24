from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine, Base

# Khởi tạo các bảng DB nếu chưa tồn tại
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Meeting Management System API",
    description="Hệ thống quản lý phòng họp và lịch họp",
    version="1.0.0"
)

# Cấu hình CORS để cho phép Frontend truy cập
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["Root"])
def read_root():
    return {
        "status": "success",
        "message": "API Hệ thống Quản lý Phòng họp đang hoạt động!"
    }