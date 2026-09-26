from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

class UserLogin(BaseModel):
    email: EmailStr
    password: str

# Tài khoản mẫu
USERS_DB = {
    "admin@congty.com": {"password": "123456", "fullName": "Nguyễn Minh Tuấn", "role": "admin"},
    "user@congty.com": {"password": "123456", "fullName": "Trần Văn B", "role": "user"}
}

@router.post("/login")
def login(user: UserLogin):
    account = USERS_DB.get(user.email)
    if not account or account["password"] != user.password:
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không chính xác.")
    
    token = f"bearer-token-{account['role']}-{user.email}"
    return {
        "token": token,
        "user_name": account["fullName"],
        "role": account["role"]
    }