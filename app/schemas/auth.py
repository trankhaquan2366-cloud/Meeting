from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50, description="Ten dang nhap")
    password: str = Field(..., min_length=1, max_length=128, description="Mat khau")


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
            "example": {"id": 1, "username": "admin", "email": "admin@meeting.local", "full_name": "Quan tri vien", "role": "admin", "is_active": True}
        }


class LoginResponse(BaseModel):
    status: str = "success"
    message: str = "Dang nhap thanh cong"
    user: UserResponse

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Dang nhap thanh cong",
                "user": {"id": 1, "username": "admin", "email": "admin@meeting.local", "full_name": "Quan tri vien", "role": "admin", "is_active": True},
            }
        }