from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Dang nhap",
    description="Xac thuc nguoi dung bang username va password. Mat khau duoc kiem tra voi hash PBKDF2-SHA256.",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user: User | None = db.query(User).filter(User.username == payload.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Sai ten dang nhap hoac mat khau")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Tai khoan da bi khoa")

    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Sai ten dang nhap hoac mat khau")

    return LoginResponse(
        status="success",
        message="Dang nhap thanh cong",
        user=UserResponse.model_validate(user),
    )