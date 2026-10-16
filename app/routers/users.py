# app/routers/users.py
import os
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db.session import get_db
from app.core.security import get_current_user, hash_password, require_role
from app.models.department import Department
from app.models.meeting import Meeting, MeetingParticipant
from app.models.project_group import ProjectGroup
from app.models.user import User
from app.schemas.user import DepartmentSummary, ParticipantSearchResponse
from app.schemas.project_group import ProjectGroupResponse
from app.schemas.users import (
    AdminUserCreate,
    AdminUserCreatedResponse,
    AdminUserPermissionsUpdate,
    AdminUserProfileUpdate,
    AdminUserUpdate,
)
from app.services.user_service import (
    generate_temporary_password,
    search_participants,
    send_account_activation_email,
)

router = APIRouter(prefix="/users", tags=["Users"])


class UserSimpleResponse(BaseModel):
    id: int
    full_name: Optional[str] = None
    email: Optional[str] = None
    username: str
    role: str
    status: str
    is_active: bool
    created_at: datetime
    external_id: Optional[str] = None
    department_id: Optional[int] = None
    department: Optional[DepartmentSummary] = None
    project_groups: List[ProjectGroupResponse] = Field(default_factory=list)
    position: Optional[str] = None
    can_book: bool = True
    can_attend: bool = True
    daily_booking_hours_limit: Optional[float] = None
    can_bypass_room_approval: bool = False

    class Config:
        from_attributes = True


class UserUpdateProfile(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None


@router.get(
    "/search",
    response_model=List[ParticipantSearchResponse],
    dependencies=[Depends(get_current_user)],
)
def search_users(
    department_code: Optional[str] = Query(default=None),
    group_code: Optional[str] = Query(default=None),
    position: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None, max_length=200),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> List[User]:
    return search_participants(
        db,
        department_code=department_code,
        group_code=group_code,
        position=position,
        keyword=keyword,
        limit=limit,
        offset=offset,
    )


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
    """Create a pending account and email its one-time temporary password."""
    department = db.get(Department, payload.department_id) if payload.department_id else None
    if payload.department_id and department is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phòng ban đã chọn không tồn tại.",
        )

    project_groups = []
    if payload.project_group_ids:
        project_groups = db.query(ProjectGroup).filter(
            ProjectGroup.id.in_(payload.project_group_ids)
        ).all()
        if len(project_groups) != len(set(payload.project_group_ids)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Một hoặc nhiều nhóm dự án đã chọn không tồn tại.",
            )

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

    temporary_password = generate_temporary_password()
    user = User(
        username=username,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(temporary_password),
        role=payload.role,
        is_active=False,
        status="PENDING",
        department=department,
        project_groups=project_groups,
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
    activation_url = os.getenv(
        "FRONTEND_CHANGE_PASSWORD_URL",
        "http://localhost:8000/static/change-password.html",
    )
    email_sent = send_account_activation_email(
        user.email,
        user.full_name or user.username,
        user.username,
        temporary_password,
        activation_url,
    )
    return AdminUserCreatedResponse(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        status=user.status,
        email_sent=email_sent,
    )


@router.post(
    "/{user_id}/resend-invite",
    dependencies=[Depends(require_role("admin"))],
)
def resend_user_invitation(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy người dùng.")
    if (user.status or "").upper() != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chỉ có thể gửi lại email cho tài khoản đang chờ kích hoạt.",
        )
    _ensure_admin_target_is_editable(user, current_user)

    temporary_password = generate_temporary_password()
    activation_url = os.getenv(
        "FRONTEND_CHANGE_PASSWORD_URL",
        "http://localhost:8000/static/change-password.html",
    )
    email_sent = send_account_activation_email(
        user.email or "",
        user.full_name or user.username,
        user.username,
        temporary_password,
        activation_url,
    )
    if email_sent:
        user.hashed_password = hash_password(temporary_password)
        db.commit()
        db.refresh(user)
    return {
        "email_sent": email_sent,
        "message": (
            "Đã gửi email kích hoạt."
            if email_sent
            else "Không gửi được email. Hãy kiểm tra cấu hình Gmail/SMTP rồi thử gửi lại."
        ),
    }


def _ensure_admin_target_is_editable(target_user: User, current_user: User) -> None:
    if (
        (target_user.role or "").strip().casefold() == "admin"
        and current_user.id != target_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không được phép chỉnh sửa hoặc hạ cấp tài khoản Admin khác",
        )


@router.put("/{user_id}/permissions")
def update_user_permissions(
    user_id: int,
    payload: AdminUserPermissionsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy người dùng.")
    _ensure_admin_target_is_editable(target_user, current_user)

    target_user.role = "admin" if payload.system_role == "ADMIN" else "employee"
    target_user.can_book = payload.can_book
    target_user.can_attend = payload.can_attend
    db.commit()
    db.refresh(target_user)
    return {
        "userId": str(target_user.id),
        "systemRole": "ADMIN" if target_user.role == "admin" else "NHAN_VIEN",
        "canBook": target_user.can_book,
        "canAttend": target_user.can_attend,
    }


@router.get(
    "/{user_id}/permissions",
    dependencies=[Depends(require_role("admin"))],
)
def get_user_permissions(
    user_id: int,
    db: Session = Depends(get_db),
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy người dùng.")
    return {
        "userId": str(target_user.id),
        "systemRole": "ADMIN" if (target_user.role or "").casefold() == "admin" else "NHAN_VIEN",
        "canBook": target_user.can_book,
        "canAttend": target_user.can_attend,
    }


@router.patch("/{user_id}")
def update_user_administration(
    user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    target_user = db.query(User).filter(User.id == user_id).first()
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy người dùng.")
    _ensure_admin_target_is_editable(target_user, current_user)
    if all(
        value is None
        for value in (payload.role, payload.status, payload.can_book, payload.can_attend)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cần cung cấp ít nhất một trường để cập nhật.",
        )

    if payload.role is not None:
        target_user.role = payload.role
    if payload.status is not None:
        target_user.status = payload.status
        target_user.is_active = payload.status == "ACTIVE"
    if payload.can_book is not None:
        target_user.can_book = payload.can_book
    if payload.can_attend is not None:
        target_user.can_attend = payload.can_attend
    db.commit()
    db.refresh(target_user)
    return {
        "id": target_user.id,
        "role": target_user.role,
        "status": target_user.status,
        "is_active": target_user.is_active,
    }


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
    role: Optional[str] = Query(default=None, max_length=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Return admin-visible account records or active users for regular users."""
    query = db.query(User)
    if (current_user.role or "").strip().casefold() != "admin":
        query = query.filter(User.is_active.is_(True))
    if role and role.strip():
        normalized_role = role.strip().casefold()
        if normalized_role not in {"admin", "employee"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vai trò tìm kiếm không hợp lệ.",
            )
        query = query.filter(func.lower(User.role) == normalized_role)
    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        query = query.filter(
            or_(
                func.lower(User.full_name).like(term),
                func.lower(User.email).like(term),
                func.lower(User.username).like(term),
            ),
        )
    return query.order_by(User.created_at.desc(), User.id.desc()).all()


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


@router.get(
    "/{user_id}",
    response_model=UserSimpleResponse,
    dependencies=[Depends(require_role("admin"))],
)
def get_user_profile(
    user_id: int,
    db: Session = Depends(get_db),
) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy người dùng.")
    return user


@router.put(
    "/{user_id}",
    response_model=UserSimpleResponse,
    dependencies=[Depends(require_role("admin"))],
)
def update_user_profile(
    user_id: int,
    payload: AdminUserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
) -> User:
    target_user = db.query(User).filter(User.id == user_id).first()
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy người dùng.")
    _ensure_admin_target_is_editable(target_user, current_user)

    existing_email = db.query(User.id).filter(
        func.lower(User.email) == payload.email,
        User.id != target_user.id,
    ).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email này đã được sử dụng bởi tài khoản khác.",
        )

    department = db.get(Department, payload.department_id) if payload.department_id else None
    if payload.department_id and department is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phòng ban đã chọn không tồn tại.")

    project_group_ids = set(payload.project_group_ids)
    project_groups = db.query(ProjectGroup).filter(
        ProjectGroup.id.in_(project_group_ids)
    ).all() if project_group_ids else []
    if len(project_groups) != len(project_group_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Một hoặc nhiều nhóm dự án đã chọn không tồn tại.",
        )

    target_user.full_name = payload.full_name
    target_user.email = payload.email
    target_user.department = department
    target_user.position = payload.position
    target_user.project_groups = project_groups
    target_user.role = payload.role
    target_user.daily_booking_hours_limit = payload.daily_booking_hours_limit
    target_user.can_bypass_room_approval = payload.can_bypass_room_approval
    db.commit()
    db.refresh(target_user)
    return target_user