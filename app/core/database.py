import os
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, make_url
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()


def _resolve_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    configured_host = os.getenv("DATABASE_HOST")
    configured_port = os.getenv("DATABASE_PORT")

    if database_url:
        url = make_url(database_url)
        if url.get_backend_name() == "mysql":
            if configured_host:
                url = url.set(
                    host=configured_host,
                    port=int(configured_port) if configured_port else (url.port or 3306),
                )
            elif url.host == "roomsync_db":
                url = url.set(
                    host="127.0.0.1",
                    port=int(configured_port or "3307"),
                )
        return url.render_as_string(hide_password=False)

    url = URL.create(
        "mysql+pymysql",
        username=os.getenv("MYSQL_USER", "roomsync_user"),
        password=os.getenv("MYSQL_PASSWORD", "roomsync_pass"),
        host=configured_host or "127.0.0.1",
        port=int(configured_port or "3307"),
        database=os.getenv("MYSQL_DATABASE", "meeting_db"),
    )
    return url.render_as_string(hide_password=False)


DATABASE_URL = _resolve_database_url()

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