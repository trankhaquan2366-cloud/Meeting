from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_password, create_access_token, get_current_user, require_role
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Đăng nhập",
    description="Xác thực người dùng bằng username và password (băm PBKDF2-SHA256), cấp JWT Token.",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    # 1. Tìm user theo username
    user: User | None = db.query(User).filter(User.username == payload.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sai tên đăng nhập hoặc mật khẩu"
        )

    # 2. Kiểm tra trạng thái tài khoản
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị khóa"
        )

    # 3. Đối soát mật khẩu với hash PBKDF2-SHA256
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sai tên đăng nhập hoặc mật khẩu"
        )

    # 4. Tạo JWT Access Token chứa thông tin vai trò (role)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role, "user_id": user.id}
    )

    # 5. Trả về Response theo đúng chuẩn TokenResponse cho Frontend
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        username=user.username,
        full_name=user.full_name or user.username
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Lấy thông tin cá nhân",
    description="Lấy thông tin tài khoản đang đăng nhập từ JWT Token."
)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get(
    "/admin-only",
    summary="Kiểm tra quyền Admin",
    description="Endpoint chỉ dành riêng cho tài khoản có vai trò 'admin'."
)
def admin_only_route(current_user: User = Depends(require_role("admin"))):
    return {
        "status": "success",
        "message": f"Xin chào Admin {current_user.full_name}! Bạn có toàn quyền quản trị."
    }