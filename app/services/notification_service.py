# app/services/notification_service.py
from datetime import datetime
from typing import List
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from app.models.meeting import Meeting
from app.models.notification import Notification

VIETNAM_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")
NOTIFICATION_CATEGORIES = ("reminder", "response", "change", "system")


class NotificationService:
    @staticmethod
    def send_notification(
        db: Session,
        user_id: int,
        title: str,
        content: str,
        meeting_id: int | None = None,
        category: str = "system",
        group_key: str | None = None,
    ) -> Notification:
        normalized_category = category.strip().lower()
        if normalized_category not in NOTIFICATION_CATEGORIES:
            normalized_category = "system"

        notification = None
        if group_key:
            notification = (
                db.query(Notification)
                .filter(
                    Notification.user_id == user_id,
                    Notification.group_key == group_key,
                )
                .with_for_update()
                .first()
            )

        if notification is None:
            notification = Notification(
                user_id=user_id,
                meeting_id=meeting_id,
                title=title,
                content=content,
                category=normalized_category,
                group_key=group_key,
            )
            db.add(notification)
        else:
            notification.meeting_id = meeting_id
            notification.title = title
            notification.content = content
            notification.category = normalized_category
            notification.created_at = datetime.utcnow()
            notification.is_read = False

        db.commit()
        db.refresh(notification)
        return notification

    @staticmethod
    def get_unread_counts(db: Session, user_id: int) -> dict:
        now = datetime.now(VIETNAM_TIMEZONE).replace(tzinfo=None)
        rows = (
            db.query(Notification.category, func.count(Notification.id))
            .outerjoin(Meeting, Notification.meeting_id == Meeting.id)
            .filter(
                Notification.user_id == user_id,
                Notification.is_read.is_(False),
                or_(
                    func.lower(Notification.category) != "reminder",
                    Meeting.id.is_(None),
                    Meeting.end_time >= now,
                ),
            )
            .group_by(Notification.category)
            .all()
        )
        by_category = {category: 0 for category in NOTIFICATION_CATEGORIES}
        for category, count in rows:
            normalized = (category or "system").lower()
            if normalized in by_category:
                by_category[normalized] = count
            else:
                by_category["system"] += count
        return {"total": sum(by_category.values()), "by_category": by_category}

    @staticmethod
    def get_user_notifications(
        db: Session,
        user_id: int,
        category: str | None = None,
        limit: int = 30,
        offset: int = 0,
    ) -> list[Notification]:
        now = datetime.now(VIETNAM_TIMEZONE).replace(tzinfo=None)
        query = (
            db.query(Notification)
            .outerjoin(Meeting, Notification.meeting_id == Meeting.id)
            .filter(
                Notification.user_id == user_id,
                or_(
                    func.lower(Notification.category) != "reminder",
                    Meeting.id.is_(None),
                    Meeting.end_time >= now,
                ),
            )
        )
        if category:
            query = query.filter(func.lower(Notification.category) == category.strip().lower())
        return (
            query.order_by(Notification.created_at.desc(), Notification.id.desc())
            .offset(max(offset, 0))
            .limit(min(max(limit, 1), 100))
            .all()
        )


def create_notification(
    db: Session,
    user_id: int,
    title: str,
    content: str,
    meeting_id: int | None = None,
    category: str = "system",
    group_key: str | None = None,
) -> Notification:
    """Compatibility wrapper for existing notification callers."""
    return NotificationService.send_notification(
        db=db,
        user_id=user_id,
        title=title,
        content=content,
        meeting_id=meeting_id,
        category=category,
        group_key=group_key,
    )


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
            category="change",
            group_key=f"invitation:{meeting_id}",
        )