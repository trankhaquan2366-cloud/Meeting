# app/services/notification_service.py
from typing import List
from sqlalchemy.orm import Session
from app.models.notification import Notification


def create_notification(
    db: Session,
    user_id: int,
    title: str,
    content: str,
    meeting_id: int | None = None,
) -> Notification:
    """Tạo một bản ghi thông báo mới cho người dùng"""
    notification = Notification(
        user_id=user_id,
        meeting_id=meeting_id,
        title=title,
        content=content
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def send_meeting_invitation_notifications(
    db: Session,
    participant_ids: List[int],
    meeting_title: str,
    start_time_str: str,
    meeting_id: int,
):
    """
    Hàm chạy ngầm (Background Task) gửi thông báo cho danh sách người tham dự.
    """
    for user_id in participant_ids:
        title = "Lời mời tham dự cuộc họp mới"
        content = f"Bạn được mời tham gia cuộc họp '{meeting_title}' diễn ra vào lúc {start_time_str}."
        create_notification(
            db,
            user_id=user_id,
            title=title,
            content=content,
            meeting_id=meeting_id,
        )