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

---

## Nhắc nhở cuộc họp

Ứng dụng quét các cuộc họp mỗi 30 giây và tạo thông báo trong ứng dụng trước 24 giờ và 15 phút. Các lời nhắc bị trễ do server gián đoạn được gửi bù khi cuộc họp vẫn ở tương lai; cuộc họp đã bắt đầu sẽ không nhận lời nhắc trễ. Thông báo in-app và cờ chống gửi lặp được lưu trước khi thử gửi email, nên lỗi SMTP không chặn các người nhận hoặc cuộc họp tiếp theo. Email reminder lỗi được ghi vào `email_deliveries` và thử lại theo backoff, tối đa 6 lần tổng cộng. Trên MySQL, named lock chỉ cho phép một worker chạy lượt quét tại một thời điểm. Chạy đủ migration theo thứ tự bên dưới để tạo bảng và cờ chống gửi lặp. Với dữ liệu cũ đang lưu giờ Việt Nam, migration `007` đổi giờ sang UTC và có dấu phiên bản để tránh trừ lặp 7 giờ.

Hai form đặt lịch chuyển giờ địa phương sang UTC trước khi gửi; API diễn giải timestamp cũ không có múi giờ là giờ Việt Nam, lưu DB ở UTC và trả timestamp có múi giờ. Reminder chỉ được gửi cho cuộc họp `CONFIRMED`; cuộc họp đã hoàn tất hoặc bị hủy không nhận nhắc nhở.

Để gửi email qua Gmail/Google Workspace, bật xác minh 2 bước cho tài khoản gửi và tạo Google App Password. Không dùng mật khẩu đăng nhập thường. Điền cấu hình SMTP (STARTTLS) vào `.env`; dùng cùng địa chỉ Gmail cho username và địa chỉ gửi:

```dotenv
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-account@gmail.com
# SMTP_USER is also accepted as an alias for SMTP_USERNAME.
SMTP_PASSWORD=your-16-character-app-password
SMTP_FROM_EMAIL=your-account@gmail.com
```

Giữ app password trong `.env` (không commit và không gửi qua chat). Nếu chưa cấu hình SMTP, thông báo vẫn được lưu trong ứng dụng. Scheduler dùng MySQL named lock; nếu không phải MySQL hoặc MySQL không cấp được lock, scheduler fallback sang `filelock` ở thư mục temporary của máy. Cách fallback bảo vệ các worker trên cùng máy, không đảm bảo khóa giữa nhiều máy chủ nếu không chia sẻ cùng filesystem.

Meeting status dùng duy nhất `CONFIRMED`, `COMPLETED` và `CANCELLED`. Cuộc họp được tự chuyển sang `COMPLETED` sau thời gian kết thúc. Migration `012` chuyển các giá trị cũ (`scheduled`, `canceled`, `cancelled`) sang enum chuẩn.

### Migration cơ sở dữ liệu

Với database hiện hữu hoặc database mới, áp dụng các file SQL dưới đây **theo đúng thứ tự số**, mỗi file một lần, bằng MySQL client vào đúng database cấu hình (mặc định `meeting_db`). Khởi động ứng dụng và `Base.metadata.create_all()` không thay thế các migration này:

1. `migrations/001_add_meeting_recurring_columns.sql`
2. `migrations/002_add_meeting_participants.sql`
3. `migrations/003_add_equipment_tables.sql`
4. `migrations/004_add_room_amenities.sql`
5. `migrations/005_align_meetings_schema.sql`
6. `migrations/006_add_meeting_reminder_flags.sql`
7. `migrations/007_normalize_legacy_meeting_times_to_utc.sql`
8. `migrations/008_create_user_calendar_tokens.sql`
9. `migrations/009_create_user_calendar_events.sql`
10. `migrations/010_add_recurring_series_identity.sql`
11. `migrations/011_add_calendar_series_event_mapping.sql`
12. `migrations/012_normalize_meeting_status_enum.sql`
13. `migrations/013_create_email_delivery_retry_queue.sql`

Sao lưu database trước khi chạy migration thay đổi dữ liệu, đặc biệt là `005`, `007` và `012`. Migration `007` có kiểm tra phiên bản để tránh chuyển đổi UTC lặp lại; các migration còn lại cần được áp dụng theo môi trường triển khai và xác minh schema sau khi chạy.

Trên MySQL, có thể áp dụng riêng migration 013 và kiểm tra named lock bằng:

```powershell
.\.venv\Scripts\python.exe scripts\apply_db_migrations.py
```

Script không in thông tin kết nối; script chỉ áp dụng migration 013 nếu bảng `email_deliveries` chưa tồn tại và kiểm tra named lock `meeting_reminder_scheduler` mà scheduler thực tế sử dụng.

Thư mời họp, thông báo thay đổi và thông báo hủy được gửi qua in-app; nếu SMTP đã cấu hình, các thông báo này cũng gửi email. Khi hủy có thể nhập lý do; nếu bỏ trống, hệ thống ghi nội dung mặc định “Không cung cấp lý do.” Email hủy có lời xin lỗi. SMTP credentials không được ghi vào source hoặc gửi qua chat.

## Đồng bộ Google Calendar / Outlook

Đăng ký OAuth client ở Google Cloud Console và Microsoft Entra, bật quyền ghi Calendar, rồi khai báo `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `OUTLOOK_CLIENT_ID`, `OUTLOOK_CLIENT_SECRET` cùng redirect URI `http://localhost:8000/api/calendar/callback` trong `.env`. Tên `MICROSOFT_*` cũ vẫn được hỗ trợ cho tương thích. Có thể chỉ cấu hình provider muốn dùng. Đặt `FRONTEND_URL` thành URL trang dashboard (mặc định `http://localhost:3000/dashboard`). Tạo `CALENDAR_TOKEN_ENCRYPTION_KEY` một lần bằng lệnh:

```powershell
.\.venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Giữ nguyên khóa này sau khi lưu token; đổi hoặc mất khóa sẽ khiến token đã mã hóa không thể giải mã. Không commit `.env`, OAuth client secret hay khóa mã hóa. Các endpoint kết nối nằm dưới `/api/calendar/`; hook `sync_event_task(meeting_id, event_type, reason=None)` nhận các event `EVENT_MEETING_CREATED`, `EVENT_MEETING_UPDATED` hoặc `EVENT_MEETING_CANCELLED` qua `BackgroundTasks`. Khi cập nhật danh sách người tham dự, event của người bị gỡ sẽ được xóa khỏi lịch ngoài nếu tài khoản lịch của họ vẫn kết nối. Ngắt kết nối chỉ vô hiệu hóa quyền truy cập của ứng dụng; event hiện có trên Google/Outlook không bị xóa và mapping được giữ để có thể cập nhật/xóa đúng event khi kết nối lại.

Lịch lặp mới được lưu với một mã chuỗi dùng chung và đồng bộ thành recurring event bằng RRULE (Google) hoặc recurrence pattern (Outlook). Sửa giờ của một buổi riêng lẻ sẽ hủy occurrence cũ và tạo event đơn lẻ mới; các sửa đổi tiếp theo và thao tác hủy tác động đúng event đó, không xóa/sửa cả chuỗi. Hủy một occurrence chưa tách sẽ xóa đúng occurrence trong chuỗi. Lịch lặp cũ đã có trước migration 010 không được tự ghép theo tiêu đề/thời gian vì không thể xác định chuỗi một cách an toàn; chúng tiếp tục được coi là các event riêng.

**Release note:** Đồng bộ chuỗi lịch lặp (RRULE/recurrence pattern) chỉ áp dụng cho lịch lặp được tạo sau khi triển khai migration 010/011. Lịch lặp cũ tiếp tục đồng bộ thành các event riêng.

Trước khi dùng lịch lặp, chạy lần lượt `migrations/010_add_recurring_series_identity.sql` và `migrations/011_add_calendar_series_event_mapping.sql`. Lịch hàng tuần lặp theo cùng thứ; lịch hàng tháng lặp vào cùng ngày tháng (các tháng không có ngày đó bị bỏ qua); `until_changed` giữ chu kỳ 30 ngày, tối đa một năm như trước.

Sau khi đã cấu hình `.env`, kết nối ít nhất một tài khoản lịch cho organizer hoặc participant của cuộc họp thử nghiệm, và xác nhận SMTP recipient có thể nhận email, chạy kiểm tra live:

```powershell
.\.venv\Scripts\python.exe scripts\verify_live_services.py --email qa@example.com --meeting-id 123 --event update
```

Thay email và meeting ID bằng dữ liệu thử nghiệm của bạn. `--event update` (mặc định) cập nhật sự kiện nếu đã liên kết, hoặc tạo mới nếu chưa có mapping; `--event create` có thể tạo sự kiện mới, nên tránh chạy lặp. Script gửi một email kiểm thử thật, sau đó gọi hook đồng bộ và đo tổng thời gian cùng từng request API provider; kết quả PASS yêu cầu có ít nhất một provider request thành công và tổng thời gian nhỏ hơn 5000 ms. Chỉ chạy trên meeting/calendar thử nghiệm đã được cho phép. Không đặt secret lên command line hoặc chia sẻ output chứa thông tin cá nhân.

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
```
