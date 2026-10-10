# 🏢 Meeting Management System (Hệ thống Quản lý Phòng họp)

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-00000F?style=for-the-badge&logo=mysql&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71105?style=for-the-badge&logo=sqlalchemy&logoColor=white)

Hệ thống Quản lý và Đặt lịch Phòng họp trực tuyến dành cho doanh nghiệp và tổ chức. Dự án được phát triển bằng **FastAPI** (Python) và **MySQL**, hỗ trợ tối ưu hóa việc quản lý phòng, đăng ký lịch họp và phân quyền người dùng.

---

## 📌 1. Bảng Công nghệ (Tech Stack)

* **Backend Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Python 3.10+)
* **Database:** MySQL
* **ORM:** [SQLAlchemy 2.0](https://www.sqlalchemy.org/) & [PyMySQL](https://pymysql.readthedocs.io/)
* **Security & Auth:** PBKDF2-HMAC-SHA256 Password Hashing, JWT Token Authentication
* **Validation & Schemas:** Pydantic v2
* **Server Runner:** Uvicorn ASGI Server

## Docker (local development)

Set `MYSQL_ROOT_PASSWORD` in `.env` if you want to override the local default, then start the stack and apply database migrations:

```sh
docker compose up --build -d
docker compose exec web alembic upgrade head
```

Compose configures the backend to connect to the `roomsync_db` service and the `meeting_db` database; do not use `localhost` as the database host from inside the backend container. Check service health with `docker compose ps` and backend output with `docker compose logs web`.

## QR meeting check-in

Apply the Alembic migration with `alembic upgrade head` to add room QR tokens and meeting check-in fields. Admins and managers can retrieve the room QR payload from `GET /api/v1/rooms/{room_id}/qr-code`; display its `qr_token` value as the room's QR code. Organizers and accepted invitees can scan that code during the 15-minute check-in window using the dashboard's booking list. Check-in and check-out are available at `/api/v1/meetings/{meeting_id}/check-in` and `/api/v1/meetings/{meeting_id}/check-out`. The API process runs reminder, no-show cancellation, and automatic check-out jobs every minute. Configure the existing SMTP environment variables to send no-show emails.

## 🔐 Google OAuth 2.0

The project uses the existing `httpx` dependency for Google OAuth and Calendar API requests. Create a Google OAuth 2.0 Web client, enable Google Calendar API, and register `http://localhost:8000/api/auth/google/callback` as an authorized redirect URI. Set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `FRONTEND_LOGIN_URL`, and `BACKEND_PUBLIC_URL` in `.env` (see `.env.example`).

Users can connect or disconnect their own Google Calendar from the dashboard Settings page. Once connected, newly created meetings are added to the organizer's calendar and Google sends invitations to meeting invitees; connecting also syncs the user's existing meetings. Invitees may still receive a Calendar consent email so their own calendar can be synchronized. Configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and `SMTP_FROM_EMAIL` to send those emails. Generate a Fernet key for `GOOGLE_TOKEN_ENCRYPTION_KEY`; refresh tokens are encrypted at rest. Apply `migrations/007_google_calendar_invitees.sql` and `migrations/008_add_meeting_participant_response_status.sql` before deploying. Set `FRONTEND_DASHBOARD_URL` to the dashboard's public URL (defaults to `/static/dashboard.html`). For production, use HTTPS and the exact public callback/frontend URLs.

---

## 📁 2. Cấu trúc Dự án (Project Structure)

```text
MeetingManagement/
├── app/
│   ├── core/                  # Cấu hình kết nối Database và Bảo mật
│   │   ├── database.py        # Kết nối SQLAlchemy Engine & Session
│   │   └── security.py        # Hash mật khẩu & Xác thực bảo mật
│   ├── models/                # SQLAlchemy Models (ORM Mapping)
│   │   ├── user.py            # Bảng người dùng
│   │   ├── room.py            # Bảng phòng họp
│   │   └── meeting.py         # Bảng lịch họp
│   ├── routers/               # API Endpoints (Controllers)
│   │   └── auth.py            # API Đăng nhập / Xác thực
│   └── schemas/               # Pydantic Schemas (Request/Response Validation)
│       └── auth.py
│   └── main.py                # File khởi chạy chính của ứng dụng FastAPI
├── scripts/
│   └── seed.py                # Script khởi tạo dữ liệu mẫu (Admin, Rooms)
├── .env.example               # Mẫu cấu hình biến môi trường
├── .gitignore                 # Bỏ qua các file rác và tài nguyên nhạy cảm
├── README.md                  # Tài liệu hướng dẫn sử dụng
├── requirements.txt           # Thư viện phụ thuộc của dự án
└── schema.sql                 # Sơ đồ Cơ sở dữ liệu DDL