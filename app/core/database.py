import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

# Lấy chuỗi kết nối từ .env
DATABASE_URL = os.getenv("DATABASE_URL")

# Nếu chưa tạo file .env thì báo lỗi rõ ràng
if not DATABASE_URL:
    raise ValueError("Chưa tìm thấy DATABASE_URL! Vui lòng tạo file .env từ .env.example")


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Tự kiểm tra kết nối sống[cite: 8]
    pool_size=10,         # Tối đa 10 kết nối thường trực
    max_overflow=20,      # Cho phép mở rộng tối đa thêm 20 kết nối khi quá tải
    pool_recycle=1800     # Tự động làm mới kết nối sau mỗi 30 phút để tránh bị treo
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()