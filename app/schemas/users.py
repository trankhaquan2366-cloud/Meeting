import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class AdminUserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: str = Field(min_length=3, max_length=150)
    username: str | None = Field(default=None, min_length=1, max_length=50)
    password: SecretStr | None = Field(default=None, min_length=8, max_length=128)
    role: Literal["admin", "employee"] = "employee"

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

    model_config = ConfigDict(from_attributes=True)
