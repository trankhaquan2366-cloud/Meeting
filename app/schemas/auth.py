from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.user import UserResponse


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50, description="Tên đăng nhập")
    password: str = Field(..., min_length=1, max_length=128, description="Mật khẩu")


class TokenResponse(BaseModel):
    """Schema phản hồi JWT Token sau khi đăng nhập thành công."""
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
    full_name: str | None = None
    user_id: int


class ChangePasswordRequest(BaseModel):
    email: str = Field(min_length=3, max_length=150)
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)
    confirm_password: str = Field(min_length=6, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()

    @model_validator(mode="after")
    def passwords_must_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("Mật khẩu mới và xác nhận mật khẩu không khớp.")
        if self.new_password == self.current_password:
            raise ValueError("Mật khẩu mới phải khác mật khẩu tạm hiện tại.")
        return self


class LoginResponse(BaseModel):
    status: str = "success"
    message: str = "Đăng nhập thành công"
    user: UserResponse

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Đăng nhập thành công",
                "user": {
                    "id": 1,
                    "username": "admin",
                    "email": "admin@meeting.local",
                    "full_name": "Quản trị viên",
                    "role": "admin",
                    "is_active": True,
                },
            }
        }