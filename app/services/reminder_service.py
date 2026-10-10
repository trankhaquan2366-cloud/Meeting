import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.meeting import Meeting
from app.models.meeting_reminder import MeetingReminder
from app.models.notification import Notification
from app.models.user import User
from app.services.email_service import send_meeting_reminder_email

logger = logging.getLogger(__name__)

# Singleton scheduler instance
_scheduler: Optional[BackgroundScheduler] = None


def _normalize_datetime(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        local_timezone = ZoneInfo(os.getenv("APP_TIMEZONE", "Asia/Ho_Chi_Minh"))
        return value.replace(tzinfo=local_timezone).astimezone(timezone.utc)
    return value.astimezone(timezone.utc)


def check_and_send_meeting_reminders() -> Dict[str, int]:
    """
    Quét các cuộc họp sắp diễn ra và gửi thông báo nhắc nhở ở 3 mốc:
    - Trước 1 ngày (khi còn hơn 23 đến 24 giờ)
    - Trước 30 phút (khi còn hơn 15 đến 30 phút)
    - Trước 15 phút (khi còn hơn 0 đến 15 phút)

    Gửi cho organizer và người tham dự đã xác nhận (response_status = 'accepted').
    Người đang pending hoặc đã từ chối không nhận thông báo.
    Sử dụng bảng meeting_reminders để đảm bảo idempotency (không gửi trùng lặp).
    """
    stats = {"processed_meetings": 0, "reminders_sent": 0}
    db: Session = SessionLocal()

    try:
        now = datetime.now(timezone.utc)
        max_horizon = now + timedelta(hours=24)
        local_timezone = ZoneInfo(os.getenv("APP_TIMEZONE", "Asia/Ho_Chi_Minh"))
        local_now = now.astimezone(local_timezone).replace(tzinfo=None)
        meetings = (
            db.query(Meeting)
            .filter(
                func.lower(func.trim(Meeting.status)).notin_(["cancelled", "canceled"]),
                Meeting.start_time > local_now,
                Meeting.start_time <= local_now + timedelta(hours=24),
            )
            .all()
        )

        for meeting in meetings:
            meeting_start = _normalize_datetime(meeting.start_time)
            if meeting_start is None or meeting_start <= now or meeting_start > max_horizon:
                continue

            stats["processed_meetings"] += 1
            time_to_start = meeting_start - now

            applicable_reminders = []
            if timedelta(hours=23) < time_to_start <= timedelta(hours=24):
                applicable_reminders.append(("1_day", "ngày mai"))
            if timedelta(minutes=15) < time_to_start <= timedelta(minutes=30):
                applicable_reminders.append(("30_mins", "sau 30 phút nữa"))
            if timedelta(seconds=0) < time_to_start <= timedelta(minutes=15):
                applicable_reminders.append(("15_mins", "sau 15 phút nữa"))

            if not applicable_reminders:
                continue

            recipients: Dict[int, User] = {}
            if meeting.organizer and meeting.organizer.is_active:
                recipients[meeting.organizer.id] = meeting.organizer

            for participant in meeting.participants:
                status_lower = (participant.response_status or "").strip().lower()
                if status_lower == "accepted" and participant.user and participant.user.is_active:
                    recipients[participant.user.id] = participant.user

            if not recipients:
                continue

            start_str = meeting_start.astimezone(local_timezone).strftime("%H:%M ngày %d/%m/%Y")
            location_str = (
                f"Phòng {meeting.room.name}"
                if meeting.room
                else (f"Trực tuyến ({meeting.meeting_link})" if meeting.meeting_link else "Trực tuyến")
            )

            for reminder_type, time_label in applicable_reminders:
                for user_id, user in recipients.items():
                    already_sent = (
                        db.query(MeetingReminder)
                        .filter(
                            MeetingReminder.meeting_id == meeting.id,
                            MeetingReminder.user_id == user_id,
                            MeetingReminder.reminder_type == reminder_type,
                        )
                        .first()
                    )
                    if already_sent:
                        continue

                    reminder_record = MeetingReminder(
                        meeting_id=meeting.id,
                        user_id=user_id,
                        reminder_type=reminder_type,
                        sent_at=datetime.now(timezone.utc),
                    )
                    db.add(reminder_record)

                    tag = {
                        "1_day": "1 ngày",
                        "30_mins": "30 phút",
                        "15_mins": "15 phút",
                    }[reminder_type]
                    notif_title = f"[Nhắc nhở {tag}] Cuộc họp: {meeting.title}"
                    notif_content = (
                        f"Cuộc họp '{meeting.title}' sẽ diễn ra {time_label} "
                        f"(lúc {start_str}) tại {location_str}. Vui lòng chuẩn bị tham gia."
                    )
                    db.add(Notification(
                        user_id=user_id,
                        meeting_id=meeting.id,
                        title=notif_title,
                        content=notif_content,
                    ))
                    stats["reminders_sent"] += 1

                    if user.email:
                        try:
                            send_meeting_reminder_email(
                                user_email=user.email,
                                user_name=user.full_name or user.username,
                                meeting_title=meeting.title,
                                start_time_str=start_str,
                                location_str=location_str,
                                reminder_label=time_label,
                                online_link=meeting.meeting_link or meeting.online_link,
                            )
                        except Exception as email_err:
                            logger.warning("Không thể gửi email nhắc nhở cho %s: %s", user.email, email_err)

            db.commit()

    except Exception as exc:
        db.rollback()
        logger.exception("Lỗi trong quá trình quét và gửi nhắc nhở cuộc họp: %s", exc)
    finally:
        db.close()

    logger.info("Quét nhắc nhở hoàn tất: %s", stats)
    return stats


def start_reminder_scheduler(interval_seconds: int = 60) -> BackgroundScheduler:
    """Khởi động tiến trình APScheduler chạy nền định kỳ kiểm tra nhắc nhở."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        logger.info("Reminder scheduler đã chạy trước đó.")
        return _scheduler

    timezone_name = os.getenv("APP_TIMEZONE", "Asia/Ho_Chi_Minh")
    _scheduler = BackgroundScheduler(timezone=timezone_name)
    _scheduler.add_job(
        check_and_send_meeting_reminders,
        trigger="interval",
        seconds=interval_seconds,
        id="meeting_reminder_worker",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("🚀 Reminder scheduler đã khởi động (chu kỳ %s giây, timezone: %s)", interval_seconds, timezone_name)
    return _scheduler


def shutdown_reminder_scheduler() -> None:
    """Dừng tiến trình scheduler khi ứng dụng tắt."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("🛑 Reminder scheduler đã dừng an toàn.")
        _scheduler = None
