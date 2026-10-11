# app/routers/notifications.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.notification import Notification
from app.models.user import User
from app.routers.auth import get_current_user  # Kiểm tra lại đường dẫn import hàm get_current_user của bạn
from app.schemas.meeting import NotificationResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def _notification_response(notification: Notification) -> NotificationResponse:
    response = NotificationResponse.model_validate(notification)
    return response.model_copy(
        update={
            "meeting_title": notification.meeting.title if notification.meeting else None,
            "meeting_status": notification.meeting.status if notification.meeting else None,
        }
    )


@router.get("/", response_model=List[NotificationResponse])
def get_user_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lấy danh sách thông báo của người dùng hiện tại (mới nhất xếp trên)"""
    notifications = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )
    return [_notification_response(notification) for notification in notifications]


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
        Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"message": "Đã đánh dấu tất cả thông báo là đã đọc"}


@router.post("/reminders/trigger")
def trigger_meeting_reminders(current_user: User = Depends(get_current_user)):
    """Kích hoạt thủ công quét nhắc nhở cuộc họp ở mốc 1 ngày, 30 và 15 phút."""
    from app.services.reminder_service import check_and_send_meeting_reminders
    stats = check_and_send_meeting_reminders()
    return {"message": "Đã thực hiện quét nhắc nhở cuộc họp thành công", "stats": stats}