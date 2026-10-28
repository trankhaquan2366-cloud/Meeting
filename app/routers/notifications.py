# app/routers/notifications.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
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


def empty_unread_counts() -> dict:
    """Số liệu an toàn dùng khi bảng notifications chưa được migrate."""
    return {
        "total": 0,
        "by_category": {"reminder": 0, "response": 0, "change": 0, "system": 0},
    }


def _normalize_unread_counts(counts) -> dict:
    normalized = empty_unread_counts()
    if not isinstance(counts, dict):
        return normalized
    by_category = counts.get("by_category") or {}
    for category in normalized["by_category"]:
        try:
            normalized["by_category"][category] = int(by_category.get(category) or 0)
        except (TypeError, ValueError):
            normalized["by_category"][category] = 0
    try:
        normalized["total"] = int(counts.get("total") or sum(normalized["by_category"].values()))
    except (TypeError, ValueError):
        normalized["total"] = sum(normalized["by_category"].values())
    return normalized


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


def _safe_notification_response(notification) -> Optional[NotificationResponse]:
    """Bỏ qua từng bản ghi hỏng thay vì làm sập toàn bộ API."""
    try:
        return _notification_response(notification)
    except Exception:
        logger.exception(
            "Skipping malformed notification id=%s",
            getattr(notification, "id", "unknown"),
        )
        return None


@router.get("/", response_model=List[NotificationResponse])
def get_user_notifications(
    category: Optional[str] = Query(None, min_length=1, max_length=20),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lấy danh sách thông báo của người dùng hiện tại (mới nhất xếp trên).

    Nếu DB chưa có cột ``category``/``group_key`` (migration chưa chạy) thì
    trả về danh sách rỗng thay vì HTTP 500 để frontend vẫn dựng được khung.
    """
    try:
        notifications = NotificationService.get_user_notifications(
            db=db,
            user_id=current_user.id,
            category=category,
            limit=limit,
            offset=offset,
        )
    except Exception:
        # Bảng/cột chưa đồng bộ hoặc DB tạm thời không sẵn sàng.
        try:
            db.rollback()
        except Exception:
            logger.exception("Rollback failed while listing notifications")
        logger.exception(
            "Falling back to empty notification list for user_id=%s", current_user.id
        )
        return []

    items: List[NotificationResponse] = []
    for notification in notifications or []:
        response = _safe_notification_response(notification)
        if response is not None:
            items.append(response)
    return items


@router.get("/unread-count")
def get_unread_notification_counts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return _normalize_unread_counts(
            NotificationService.get_unread_counts(db=db, user_id=current_user.id)
        )
    except Exception:
        try:
            db.rollback()
        except Exception:
            logger.exception("Rollback failed while counting notifications")
        logger.exception(
            "Falling back to zero notification counts for user_id=%s", current_user.id
        )
        return empty_unread_counts()


@router.put("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Đánh dấu 1 thông báo cụ thể là đã đọc"""
    try:
        notification = (
            db.query(Notification)
            .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
            .first()
        )
    except Exception as exc:
        raise _notification_database_error(db, "loading", current_user.id) from exc
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông báo"
        )

    try:
        notification.is_read = True
        db.commit()
        db.refresh(notification)
    except Exception as exc:
        raise _notification_database_error(db, "updating", current_user.id) from exc
    return _notification_response(notification)


@router.put("/read-all")
def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Đánh dấu tất cả thông báo chưa đọc của người dùng là đã đọc"""
    try:
        db.query(Notification).filter(
            Notification.user_id == current_user.id,
            Notification.is_read.is_(False)
        ).update({"is_read": True})
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            logger.exception("Rollback failed while marking notifications read")
        logger.exception(
            "Unable to mark all notifications as read for user_id=%s", current_user.id
        )
        return {"message": "Chưa thể cập nhật thông báo, vui lòng thử lại sau.", "updated": False}
    return {"message": "Đã đánh dấu tất cả thông báo là đã đọc", "updated": True}


@router.post("/reminders/trigger")
def trigger_meeting_reminders(current_user: User = Depends(get_current_user)):
    """Kích hoạt thủ công quét nhắc nhở cuộc họp ở mốc 1 ngày, 30 và 15 phút."""
    from app.services.reminder_service import check_and_send_meeting_reminders
    stats = check_and_send_meeting_reminders()
    return {"message": "Đã thực hiện quét nhắc nhở cuộc họp thành công", "stats": stats}
