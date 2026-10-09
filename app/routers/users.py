# app/routers/users.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter(prefix="/users", tags=["Users"])


class UserSimpleResponse(BaseModel):
    id: int
    full_name: Optional[str] = None
    email: str

    class Config:
        from_attributes = True


class UserUpdateProfile(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None


@router.get("/", response_model=List[UserSimpleResponse])
def get_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lấy danh sách người dùng để mời tham dự cuộc họp"""
    return db.query(User).all()


@router.get("/me", response_model=UserSimpleResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    """Lấy thông tin chi tiết của tài khoản đang đăng nhập"""
    return current_user


@router.put("/me", response_model=UserSimpleResponse)
def update_my_profile(
    payload: UserUpdateProfile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cập nhật thông tin cá nhân (Tên, Email) của người dùng hiện tại xuống DB"""
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.email is not None:
        # Kiểm tra xem email mới có bị trùng với tài khoản khác không
        existing_user = db.query(User).filter(User.email == payload.email, User.id != current_user.id).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email này đã được sử dụng bởi tài khoản khác."
            )
        current_user.email = payload.email

    db.commit()
    db.refresh(current_user)
    return current_user