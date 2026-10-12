import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, PositiveInt
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.session import get_db
from app.models.restriction import UserRoomRestriction
from app.models.room import Room
from app.models.user import User

router = APIRouter(prefix="/admin/restrictions", tags=["admin-restrictions"])
logger = logging.getLogger(__name__)


class RoomRestrictionEntry(BaseModel):
    room_id: int
    reason: str | None


class UserRoomRestrictionResponse(BaseModel):
    user_id: int
    full_name: str
    email: str | None
    restrictions: list[RoomRestrictionEntry]


class UpdateUserRoomRestrictionRequest(BaseModel):
    restricted_room_ids: list[PositiveInt] = Field(alias="restrictedRoomIds")
    reason: str | None = None

    model_config = ConfigDict(populate_by_name=True)


def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy người dùng.",
        )
    return user


def _response_for_user(
    db: Session, user: User
) -> UserRoomRestrictionResponse:
    restrictions = (
        db.query(UserRoomRestriction)
        .filter(UserRoomRestriction.user_id == user.id)
        .order_by(UserRoomRestriction.room_id)
        .all()
    )
    return UserRoomRestrictionResponse(
        user_id=user.id,
        full_name=user.full_name or user.username,
        email=user.email,
        restrictions=[
            RoomRestrictionEntry(room_id=item.room_id, reason=item.reason)
            for item in restrictions
        ],
    )


@router.get("/users/{user_id}", response_model=UserRoomRestrictionResponse)
def get_user_restrictions(
    user_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
) -> UserRoomRestrictionResponse:
    user = _get_user_or_404(db, user_id)
    return _response_for_user(db, user)


@router.put("/users/{user_id}", response_model=UserRoomRestrictionResponse)
def update_user_restrictions(
    user_id: int,
    payload: UpdateUserRoomRestrictionRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
) -> UserRoomRestrictionResponse:
    user = _get_user_or_404(db, user_id)
    if user.role == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không thể giới hạn tài khoản quản trị viên.",
        )
    room_ids = sorted(set(payload.restricted_room_ids))

    if room_ids:
        existing_ids = {
            room_id
            for (room_id,) in db.query(Room.id).filter(Room.id.in_(room_ids)).all()
        }
        missing_ids = sorted(set(room_ids) - existing_ids)
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy phòng có id: {', '.join(map(str, missing_ids))}.",
            )

    reason = payload.reason.strip() if payload.reason else None
    try:
        (
            db.query(UserRoomRestriction)
            .filter(UserRoomRestriction.user_id == user.id)
            .delete(synchronize_session=False)
        )
        db.add_all(
            [
                UserRoomRestriction(user_id=user.id, room_id=room_id, reason=reason or None)
                for room_id in room_ids
            ]
        )
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Failed to update room restrictions for user_id=%s", user.id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Không thể cập nhật giới hạn phòng họp.",
        ) from exc

    return _response_for_user(db, user)
