from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50, description="Tên đăng nhập")
    password: str = Field(..., min_length=1, max_length=128, description="Mật khẩu")


class UserResponse(BaseModel):
    id: int
    username: str
    email: str | None
    full_name: str | None
    role: str
    is_active: bool

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "username": "admin",
                "email": "admin@meeting.local",
                "full_name": "Quản trị viên",
                "role": "admin",
                "is_active": True,
            }
        }


class TokenResponse(BaseModel):
    """Schema phản hồi JWT Token sau khi đăng nhập thành công."""
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
    full_name: str | None = None


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