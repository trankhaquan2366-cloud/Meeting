from sqlalchemy import Boolean, Column, DateTime, Integer, String, func

from app.core.database import Base


class User(Base):
    """Model đại diện cho bảng người dùng (tài khoản) trong hệ thống."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True, comment="Tên đăng nhập")
    email = Column(String(150), unique=True, nullable=True, comment="Địa chỉ Email")
    full_name = Column(String(150), nullable=True, comment="Họ và tên người dùng")
    hashed_password = Column(String(255), nullable=False, comment="Mật khẩu đã băm")
    role = Column(String(20), nullable=False, default="employee", comment="Vai trò: admin/employee")
    is_active = Column(Boolean, nullable=False, default=True, comment="Trạng thái tài khoản (active/inactive)")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment="Thời gian tạo")
    updated_at = Column(DateTime, nullable=True, onupdate=func.now(), comment="Thời gian cập nhật gần nhất")

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r} role={self.role!r}>"