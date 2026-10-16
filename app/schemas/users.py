import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AdminUserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: str = Field(min_length=3, max_length=150)
    username: str | None = Field(default=None, min_length=1, max_length=50)
    role: Literal["admin", "employee"] = "employee"
    department_id: int | None = Field(default=None, ge=1)
    project_group_ids: list[int] = Field(default_factory=list)

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Họ tên phải có ít nhất 2 ký tự.")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("Email không đúng định dạng.")
        return value

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value or not re.fullmatch(r"[A-Za-z0-9._-]+", value):
            raise ValueError("Tên đăng nhập chỉ được chứa chữ, số, dấu chấm, gạch dưới hoặc gạch ngang.")
        return value


class AdminUserCreatedResponse(BaseModel):
    id: int
    username: str
    full_name: str | None
    email: str | None
    role: str
    is_active: bool
    status: str
    email_sent: bool

    model_config = ConfigDict(from_attributes=True)


class AdminUserUpdate(BaseModel):
    role: Literal["admin", "employee"] | None = None
    status: Literal["ACTIVE", "INACTIVE", "PENDING"] | None = None
    can_book: bool | None = None
    can_attend: bool | None = None

    @field_validator("role")
    @classmethod
    def normalize_role(cls, value: str | None) -> str | None:
        return value.lower() if value else value


class AdminUserProfileUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: str = Field(min_length=3, max_length=150)
    department_id: int | None = Field(default=None, ge=1)
    position: str | None = Field(default=None, max_length=100)
    project_group_ids: list[int] = Field(default_factory=list)
    role: Literal["admin", "manager", "employee"]
    daily_booking_hours_limit: float | None = Field(default=None, gt=0, le=24)
    can_bypass_room_approval: bool = False

    @field_validator("full_name")
    @classmethod
    def normalize_profile_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Họ tên phải có ít nhất 2 ký tự.")
        return value

    @field_validator("email")
    @classmethod
    def normalize_profile_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("Email không đúng định dạng.")
        return value

    @field_validator("position")
    @classmethod
    def normalize_position(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class AdminUserPermissionsUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    system_role: Literal["ADMIN", "NHAN_VIEN"] = Field(alias="systemRole")
    can_book: bool = Field(alias="canBook")
    can_attend: bool = Field(alias="canAttend")
