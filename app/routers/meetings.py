# app/routers/meetings.py
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.core.time import VIETNAM_TZ, as_utc_aware, normalize_to_utc_naive
from app.core.meeting_events import (
    EVENT_MEETING_CANCELLED,
    EVENT_MEETING_CREATED,
    EVENT_MEETING_UPDATED,
)
from app.db.session import get_db
from app.models.meeting import Meeting, MeetingParticipant
from app.models.room import Room
from app.models.user import User
from app.schemas.meeting import (
    MeetingCreateRequest,
    MeetingResponse,
    MeetingUpdateRequest,
    SuggestTimeRequest,
    SuggestTimeResponse,
)
from app.schemas.room import RoomResponse
from app.services.meeting_service import MeetingService
from app.services.notification_service import send_meeting_notification_task
from app.services.calendar_sync_service import sync_event_task

router = APIRouter()


def _queue_meeting_cancellation_tasks(
    meeting: Meeting,
    reason: str,
    background_tasks: BackgroundTasks,
    db: Session,
) -> None:
    background_tasks.add_task(
        sync_event_task,
        meeting.id,
        EVENT_MEETING_CANCELLED,
        reason,
    )
    recipient_ids = {
        user_id
        for (user_id,) in db.query(MeetingParticipant.user_id)
        .filter(MeetingParticipant.meeting_id == meeting.id)
        .all()
    }
    if meeting.organizer_id is not None:
        recipient_ids.add(meeting.organizer_id)
    background_tasks.add_task(
        send_meeting_notification_task,
        sorted(recipient_ids),
        "Cuộc họp đã bị hủy",
        f"Cuộc họp '{meeting.title}' đã bị hủy. "
        f"Lý do: {reason}.\nChúng tôi xin lỗi vì sự bất tiện này.",
        meeting.id,
    )


@router.get(
    "",
    response_model=List[RoomResponse],
    summary="Lấy danh sách phòng họp",
    description="Trả về danh sách các phòng họp đang sẵn sàng cho người dùng chọn.",
)
def list_rooms(db: Session = Depends(get_db)):
    return MeetingService.get_all_active_rooms(db)


@router.post(
    "/book",
    response_model=List[MeetingResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Đặt lịch họp mới (Đơn & Định kỳ)",
    description="Tạo cuộc họp mới hoặc chuỗi lịch định kỳ (bao gồm mượn thiết bị). Hệ thống tự động kiểm tra trùng lịch, tồn kho thiết bị và rollback toàn bộ nếu có xung đột.",
)
def create_meeting(
    payload: MeetingCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. Gọi Service tạo cuộc họp
    created_meetings = MeetingService.create_meeting(
        db=db,
        payload=payload,
        organizer_id=current_user.id,
    )
    for meeting in created_meetings:
        background_tasks.add_task(
            sync_event_task,
            meeting.id,
            EVENT_MEETING_CREATED,
        )

    # 2. Gửi thông báo ngầm cho những người được mời tham dự
    # Filter organizer khỏi danh sách — organizer không nhận invitation notification
    if payload.participant_ids and created_meetings:
        first_meeting = created_meetings[0]
        start_str = as_utc_aware(first_meeting.start_time).astimezone(
            VIETNAM_TZ
        ).strftime("%H:%M %d/%m/%Y")
        notify_ids = [pid for pid in payload.participant_ids if pid != current_user.id]
        if notify_ids:
            background_tasks.add_task(
                send_meeting_notification_task,
                notify_ids,
                "Lời mời tham dự cuộc họp mới",
                f"Bạn được mời tham gia cuộc họp '{first_meeting.title}' "
                f"diễn ra vào lúc {start_str}.",
                first_meeting.id,
            )

    return created_meetings


@router.post(
    "/suggest-time",
    response_model=SuggestTimeResponse,
    summary="Gợi ý khung giờ họp khả dụng",
    description="Tìm kiếm khung giờ họp phù hợp dựa trên danh sách người tham gia và phòng họp.",
)
def suggest_time(
    payload: SuggestTimeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return MeetingService.suggest_time(db=db, payload=payload)


@router.get(
    "/",
    response_model=List[MeetingResponse],
    summary="Lấy danh sách các cuộc họp",
    description="Lấy danh sách cuộc họp có hỗ trợ lọc theo phòng họp và khoảng thời gian.",
)
def get_meetings(
    room_id: Optional[int] = Query(None, description="Lọc theo phòng"),
    start_date: Optional[datetime] = Query(None, description="Lọc từ ngày"),
    end_date: Optional[datetime] = Query(None, description="Lọc đến ngày"),
    db: Session = Depends(get_db),
):
    query = db.query(Meeting).filter(Meeting.status != "CANCELLED")

    if room_id:
        query = query.filter(Meeting.room_id == room_id)
    if start_date:
        query = query.filter(Meeting.start_time >= normalize_to_utc_naive(start_date))
    if end_date:
        query = query.filter(Meeting.end_time <= normalize_to_utc_naive(end_date))

    return query.all()


@router.get(
    "/history",
    response_model=List[MeetingResponse],
    summary="Lịch sử cuộc họp",
    description="Chỉ trả về cuộc họp đã kết thúc mà người dùng tham gia (organizer hoặc participant), sắp xếp end_time giảm dần.",
)
def get_meeting_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    participant_meeting_ids = (
        db.query(MeetingParticipant.meeting_id)
        .filter(MeetingParticipant.user_id == current_user.id)
        .subquery()
    )

    query = (
        db.query(Meeting)
        .filter(
            Meeting.end_time < now,
            Meeting.status != "CANCELLED",
            (
                (Meeting.organizer_id == current_user.id)
                | Meeting.id.in_(participant_meeting_ids)
            ),
        )
        .distinct()
        .order_by(Meeting.end_time.desc())
    )

    return query.all()


@router.get(
    "/{meeting_id}",
    response_model=MeetingResponse,
    summary="Chi tiết cuộc họp",
)
def get_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).one_or_none()
    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy cuộc họp",
        )

    is_participant = (
        db.query(MeetingParticipant.id)
        .filter(
            MeetingParticipant.meeting_id == meeting_id,
            MeetingParticipant.user_id == current_user.id,
        )
        .first()
        is not None
    )
    if (
        meeting.organizer_id != current_user.id
        and current_user.role != "admin"
        and not is_participant
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền xem cuộc họp này",
        )
    return meeting


@router.patch(
    "/{meeting_id}",
    response_model=MeetingResponse,
    summary="Cập nhật cuộc họp",
)
def update_meeting(
    meeting_id: int,
    payload: MeetingUpdateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cần cung cấp ít nhất một trường để cập nhật",
        )

    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy cuộc họp",
        )
    if meeting.organizer_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền cập nhật cuộc họp này",
        )
    if meeting.status in ("CANCELLED", "COMPLETED"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể cập nhật cuộc họp đã hủy hoặc hoàn tất",
        )

    start_time = updates.get("start_time", meeting.start_time)
    end_time = updates.get("end_time", meeting.end_time)
    if start_time >= end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thời gian kết thúc phải sau thời gian bắt đầu",
        )
    if (
        ("start_time" in updates or "end_time" in updates)
        and start_time < datetime.now(timezone.utc).replace(tzinfo=None)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể chuyển cuộc họp sang thời gian đã qua",
        )

    meeting_type = updates.get("meeting_type", meeting.meeting_type)
    room_id = updates.get("room_id", meeting.room_id)
    online_link = updates.get("online_link", meeting.online_link)
    schedule_changed = any(
        field in updates
        for field in ("meeting_type", "room_id", "start_time", "end_time")
    )
    start_time_changed = (
        "start_time" in updates and start_time != meeting.start_time
    )
    moved_recurring_occurrence = (
        meeting.recurring_series_id is not None
        and (
            start_time != meeting.start_time
            or end_time != meeting.end_time
        )
    )
    if schedule_changed and meeting_type == "online":
        if room_id is not None or not online_link or not online_link.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cuộc họp online cần online_link và không được gán phòng",
            )
    elif schedule_changed:
        if not room_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cuộc họp offline cần có phòng họp",
            )
        room = (
            db.query(Room)
            .filter(Room.id == room_id, Room.is_active.is_(True))
            .one_or_none()
        )
        if room is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phòng họp không tồn tại hoặc đã ngưng hoạt động",
            )
        conflicting_meeting = (
            db.query(Meeting)
            .filter(
                Meeting.id != meeting.id,
                Meeting.room_id == room_id,
                Meeting.status != "CANCELLED",
                and_(
                    Meeting.start_time < end_time,
                    Meeting.end_time > start_time,
                ),
            )
            .first()
        )
        if conflicting_meeting is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Phòng họp đã có cuộc họp trong khung giờ này",
            )

    participant_ids = updates.pop("participant_ids", None)
    for field in (
        "title",
        "description",
        "meeting_type",
        "online_link",
        "room_id",
        "start_time",
        "end_time",
    ):
        if field in updates:
            setattr(meeting, field, updates[field])

    if start_time_changed:
        time_until_start = start_time - datetime.now(timezone.utc).replace(
            tzinfo=None
        )
        if time_until_start > timedelta(hours=24):
            meeting.is_reminded_24h = False
            meeting.is_reminded_15m = False
        else:
            meeting.is_reminded_24h = True
            meeting.is_reminded_15m = False

    if participant_ids is not None:
        unique_participant_ids = set(participant_ids) - {current_user.id}
        existing_ids = {
            user_id
            for (user_id,) in db.query(User.id)
            .filter(User.id.in_(unique_participant_ids))
            .all()
        }
        if existing_ids != unique_participant_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Danh sách người tham dự chứa tài khoản không tồn tại",
            )
        meeting.participants = [
            MeetingParticipant(user_id=user_id)
            for user_id in unique_participant_ids
        ]
    if moved_recurring_occurrence:
        meeting.recurrence_is_detached = True

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể lưu cập nhật cuộc họp",
        ) from exc

    db.refresh(meeting)
    background_tasks.add_task(
        sync_event_task,
        meeting.id,
        EVENT_MEETING_UPDATED,
    )
    if updates:
        notify_ids = {
            user_id
            for (user_id,) in db.query(MeetingParticipant.user_id)
            .filter(MeetingParticipant.meeting_id == meeting.id)
            .all()
        }
        if meeting.organizer_id is not None:
            notify_ids.add(meeting.organizer_id)
        start_str = as_utc_aware(meeting.start_time).astimezone(
            VIETNAM_TZ
        ).strftime("%H:%M %d/%m/%Y")
        background_tasks.add_task(
            send_meeting_notification_task,
            sorted(notify_ids),
            "Cuộc họp đã được cập nhật",
            f"Lịch cuộc họp '{meeting.title}' đã thay đổi. "
            f"Thời gian hiện tại: {start_str}.",
            meeting.id,
        )
    return meeting


@router.patch(
    "/{meeting_id}/cancel",
    response_model=MeetingResponse,
    status_code=status.HTTP_200_OK,
    summary="Hủy cuộc họp",
    description="Hủy cuộc họp theo ID. Chỉ người tổ chức (organizer) hoặc admin mới có quyền hủy.",
)
def cancel_meeting(
    meeting_id: int,
    background_tasks: BackgroundTasks,
    reason: str | None = Query(None, max_length=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    was_cancelled = (
        db.query(Meeting.status)
        .filter(Meeting.id == meeting_id)
        .scalar()
        == "CANCELLED"
    )
    meeting = MeetingService.cancel_meeting(db, meeting_id, current_user)
    reason = reason.strip() if reason and reason.strip() else "Không cung cấp lý do."
    if not was_cancelled:
        _queue_meeting_cancellation_tasks(meeting, reason, background_tasks, db)
    return meeting


@router.delete(
    "/{meeting_id}",
    response_model=MeetingResponse,
    status_code=status.HTTP_200_OK,
    summary="Hủy cuộc họp (Endpoint tương thích)",
    description="Endpoint tương thích ngược hỗ trợ hủy cuộc họp qua phương thức DELETE.",
)
def cancel_meeting_legacy(
    meeting_id: int,
    background_tasks: BackgroundTasks,
    reason: str | None = Query(None, max_length=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    was_cancelled = (
        db.query(Meeting.status)
        .filter(Meeting.id == meeting_id)
        .scalar()
        == "CANCELLED"
    )
    meeting = MeetingService.cancel_meeting(db, meeting_id, current_user)
    reason = reason.strip() if reason and reason.strip() else "Không cung cấp lý do."
    if not was_cancelled:
        _queue_meeting_cancellation_tasks(meeting, reason, background_tasks, db)
    return meeting