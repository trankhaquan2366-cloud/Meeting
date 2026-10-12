# app/routers/users.py
import secrets
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.core.security import get_current_user, hash_password, require_role
from app.models.meeting import Meeting, MeetingParticipant
from app.models.user import User
from app.schemas.users import AdminUserCreate, AdminUserCreatedResponse

router = APIRouter(prefix="/users", tags=["Users"])


class UserSimpleResponse(BaseModel):
    id: int
    full_name: Optional[str] = None
    email: Optional[str] = None
    username: str

    class Config:
        from_attributes = True


class UserUpdateProfile(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None


def _new_username(db: Session, email: str) -> str:
    """Derive a username from the email local-part and make it unique."""
    local_part = email.partition("@")[0]
    base = "".join(
        character for character in local_part if character.isalnum() or character in "._-"
    ).strip("._-")[:50] or "user"
    username = base
    suffix = 1
    while db.query(User.id).filter(func.lower(User.username) == username.lower()).first():
        suffix_text = str(suffix)
        username = f"{base[:50 - len(suffix_text)]}{suffix_text}"
        suffix += 1
    return username


@router.post(
    "/",
    response_model=AdminUserCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("admin"))],
)
def create_user(
    payload: AdminUserCreate,
    db: Session = Depends(get_db),
) -> AdminUserCreatedResponse:
    """Create an active user account; only administrators may call this endpoint."""
    existing_email = db.query(User.id).filter(
        func.lower(User.email) == payload.email.lower()
    ).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email này đã được sử dụng bởi tài khoản khác.",
        )

    if payload.username:
        existing_username = db.query(User.id).filter(
            func.lower(User.username) == payload.username.lower()
        ).first()
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tên đăng nhập này đã được sử dụng.",
            )
        username = payload.username
    else:
        username = _new_username(db, payload.email)

    password = payload.password.get_secret_value() if payload.password else secrets.token_urlsafe(24)
    user = User(
        username=username,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(password),
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email hoặc tên đăng nhập đã được sử dụng.",
        ) from exc

    db.refresh(user)
    return AdminUserCreatedResponse(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
    )


@router.get("/frequent", response_model=List[UserSimpleResponse])
def get_frequent_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    invite_counts = (
        db.query(
            MeetingParticipant.user_id.label("user_id"),
            func.count(MeetingParticipant.meeting_id).label("invite_count"),
        )
        .join(User, User.id == MeetingParticipant.user_id)
        .join(Meeting, Meeting.id == MeetingParticipant.meeting_id)
        .filter(
            User.id != current_user.id,
            User.is_active.is_(True),
            Meeting.organizer_id == current_user.id,
        )
        .group_by(MeetingParticipant.user_id)
        .order_by(func.count(MeetingParticipant.meeting_id).desc(), MeetingParticipant.user_id)
        .limit(20)
        .subquery()
    )
    return (
        db.query(User)
        .join(invite_counts, invite_counts.c.user_id == User.id)
        .order_by(invite_counts.c.invite_count.desc(), User.id)
        .all()
    )


@router.get("/", response_model=List[UserSimpleResponse])
@router.get("", response_model=List[UserSimpleResponse], include_in_schema=False)
def get_all_users(
    search: Optional[str] = Query(default=None, max_length=150),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lấy danh sách người dùng để mời tham dự cuộc họp"""
    query = db.query(User)
    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        query = query.filter(
            User.is_active.is_(True),
            or_(
                func.lower(User.full_name).like(term),
                func.lower(User.email).like(term),
                func.lower(User.username).like(term),
            ),
        )
    return query.order_by(User.full_name, User.id).all()


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