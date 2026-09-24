from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine

# Import models de create_all nhan biet cac bang (users/rooms/meetings)
import app.models  # noqa: F401

# Tao cac bang DB neu chua ton tai (schema cu the trong schema.sql)
Base.metadata.create_all(bind=engine)

from app.routers import auth  # noqa: E402

app = FastAPI(
    title="Meeting Management System API",
    description="Hệ thống quản lý phòng họp và lịch họp",
    version="1.0.0",
)

# Cau hinh CORS de cho phép Frontend truy cap
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)


@app.get("/", tags=["Root"])
def read_root():
    return {
        "status": "success",
        "message": "API Hệ thống Quản lý Phòng họp đang hoạt động!",
    }