import secrets
import string
from html import escape

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.department import Department
from app.models.project_group import ProjectGroup
from app.models.user import User

from app.services.email_service import send_email


MANAGEMENT_POSITION_TERMS = (
    "manager", "management", "head", "director", "chief", "lead",
    "trưởng", "phó", "quản lý", "giám đốc",
)

ACCOUNT_ACTIVATION_SUBJECT = "[RoomSync] Thông tin tài khoản & Hướng dẫn kích hoạt"
TEMP_PASSWORD_ALPHABET = string.ascii_letters + string.digits


def generate_temporary_password(length: int = 12) -> str:
    if length < 10 or length > 12:
        raise ValueError("Temporary passwords must be 10 to 12 characters long.")
    return "".join(secrets.choice(TEMP_PASSWORD_ALPHABET) for _ in range(length))


def send_account_activation_email(
    email: str,
    full_name: str,
    username: str,
    temporary_password: str,
    change_password_url: str,
) -> bool:
    safe_name = escape(full_name)
    safe_email = escape(email)
    safe_username = escape(username)
    safe_password = escape(temporary_password)
    safe_url = escape(change_password_url, quote=True)
    body_text = (
        f"Xin chào {full_name},\n\n"
        "Tài khoản RoomSync của bạn đã được tạo.\n"
        f"Gmail đăng ký: {email}\n"
        f"Tên đăng nhập: {username}\n"
        f"Mật khẩu tạm thời: {temporary_password}\n\n"
        f"Đổi mật khẩu và kích hoạt tài khoản tại: {change_password_url}\n"
    )
    body_html = f"""<!DOCTYPE html>
<html><body style="font-family:Arial,sans-serif;color:#0f172a;line-height:1.6">
  <div style="max-width:560px;margin:auto;padding:24px;border:1px solid #e2e8f0;border-radius:12px">
    <h2>Thông tin tài khoản RoomSync</h2>
    <p>Xin chào <strong>{safe_name}</strong>, tài khoản của bạn đã được tạo.</p>
    <p><strong>Gmail đăng ký:</strong> {safe_email}<br>
       <strong>Tên đăng nhập:</strong> {safe_username}<br>
       <strong>Mật khẩu tạm thời:</strong> {safe_password}</p>
    <p>Vui lòng đổi mật khẩu để kích hoạt tài khoản:</p>
    <p><a href="{safe_url}" style="display:inline-block;padding:12px 18px;background:#2563eb;color:#fff;text-decoration:none;border-radius:8px">Đổi mật khẩu &amp; kích hoạt</a></p>
    <p>Nếu nút không hoạt động, mở liên kết: <a href="{safe_url}">{safe_url}</a></p>
  </div>
</body></html>"""
    return send_email(
        email,
        ACCOUNT_ACTIVATION_SUBJECT,
        body_text,
        body_html,
    )


def search_participants(
    db: Session,
    department_code: str | None = None,
    group_code: str | None = None,
    position: str | None = None,
    keyword: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[User]:
    query = db.query(User).filter(User.is_active.is_(True))

    if department_code and department_code.strip():
        query = query.filter(
            User.department.has(Department.code == department_code.strip())
        )
    if group_code and group_code.strip():
        query = query.filter(
            User.project_groups.any(ProjectGroup.code == group_code.strip())
        )
    if position and position.strip():
        normalized_position = position.strip().lower()
        if normalized_position == "manager":
            query = query.filter(or_(*(
                func.lower(User.position).like(f"%{term}%")
                for term in MANAGEMENT_POSITION_TERMS
            )))
        elif normalized_position == "specialist":
            query = query.filter(
                func.lower(User.position).like("%chuyên viên%")
                | func.lower(User.position).like("%specialist%")
            )
        else:
            query = query.filter(
                func.lower(User.position).like(f"%{normalized_position}%")
            )
    if keyword and keyword.strip():
        term = f"%{keyword.strip().lower()}%"
        query = query.outerjoin(User.department).outerjoin(User.project_groups).filter(
            or_(
                func.lower(User.username).like(term),
                func.lower(User.full_name).like(term),
                func.lower(User.email).like(term),
                func.lower(User.external_id).like(term),
                func.lower(User.position).like(term),
                func.lower(Department.name).like(term),
                func.lower(Department.code).like(term),
                func.lower(ProjectGroup.name).like(term),
                func.lower(ProjectGroup.code).like(term),
            )
        )

    query = query.distinct().order_by(User.full_name, User.id)
    if offset:
        query = query.offset(offset)
    if limit is not None:
        query = query.limit(limit)
    return query.all()
