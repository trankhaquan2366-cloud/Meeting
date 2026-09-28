from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import authenticate_user, create_access_token, get_current_user, require_role
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth")


def issue_token(user: User) -> TokenResponse:
    token = create_access_token(data={"sub": user.username, "user_id": user.id, "role": user.role})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role,
        username=user.username,
        full_name=user.full_name or user.username,
    )


@router.post("/login", response_model=TokenResponse, summary="Đăng nhập")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    return issue_token(authenticate_user(db, payload.username, payload.password))


@router.get("/me", response_model=UserResponse, summary="Lấy thông tin cá nhân")
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/admin-only", summary="Kiểm tra quyền Admin")
def admin_only_route(current_user: User = Depends(require_role("admin"))):
    return {"status": "success", "message": f"Xin chào Admin {current_user.full_name}! Bạn có toàn quyền quản trị."}
