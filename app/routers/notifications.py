# app/routers/notifications.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
import logging

from app.core.database import get_db
from app.models.notification import Notification
from app.models.user import User
from app.routers.auth import get_current_user  # Kiểm tra lại đường dẫn import hàm get_current_user của bạn
from app.schemas.meeting import NotificationResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])
logger = logging.getLogger(__name__)


def _notification_database_error(db: Session, operation: str, user_id: int) -> HTTPException:
    db.rollback()
    logger.exception(
        "Database error while %s notifications for user_id=%s",
        operation,
        user_id,
    )
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Không thể tải thông báo do lỗi cơ sở dữ liệu. Vui lòng kiểm tra migration.",
    )


def _notification_response(notification: Notification) -> NotificationResponse:
    response = NotificationResponse.model_validate(notification)
    return response.model_copy(
        update={
            "meeting_title": notification.meeting.title if notification.meeting else None,
            "meeting_status": notification.meeting.status if notification.meeting else None,
            "meeting_link": (
                notification.meeting.meeting_link if notification.meeting else None
            ),
        }
    )


@router.get("/", response_model=List[NotificationResponse])
def get_user_notifications(
    category: Optional[str] = Query(None, min_length=1, max_length=20),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lấy danh sách thông báo của người dùng hiện tại (mới nhất xếp trên)"""
    try:
        notifications = NotificationService.get_user_notifications(
            db=db,
            user_id=current_user.id,
            category=category,
            limit=limit,
            offset=offset,
        )
        return [_notification_response(notification) for notification in notifications]
    except SQLAlchemyError as exc:
        raise _notification_database_error(db, "listing", current_user.id) from exc


@router.get("/unread-count")
def get_unread_notification_counts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return NotificationService.get_unread_counts(db=db, user_id=current_user.id)
    except SQLAlchemyError as exc:
        raise _notification_database_error(db, "counting unread", current_user.id) from exc


@router.put("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Đánh dấu 1 thông báo cụ thể là đã đọc"""
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông báo"
        )

    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return _notification_response(notification)


@router.put("/read-all")
def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Đánh dấu tất cả thông báo chưa đọc của người dùng là đã đọc"""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read.is_(False)
    ).update({"is_read": True})
    db.commit()
    return {"message": "Đã đánh dấu tất cả thông báo là đã đọc"}


@router.post("/reminders/trigger")
def trigger_meeting_reminders(current_user: User = Depends(get_current_user)):
    """Kích hoạt thủ công quét nhắc nhở cuộc họp ở mốc 1 ngày, 30 và 15 phút."""
    from app.services.reminder_service import check_and_send_meeting_reminders
    stats = check_and_send_meeting_reminders()
    return {"message": "Đã thực hiện quét nhắc nhở cuộc họp thành công", "stats": stats}
