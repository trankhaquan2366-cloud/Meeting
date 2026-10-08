# app/routers/meetings.py
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.meeting import Meeting, MeetingParticipant
from app.models.user import User
from app.schemas.meeting import (
    MeetingCreateRequest,
    MeetingResponse,
    SuggestTimeRequest,
    SuggestTimeResponse,
)
from app.schemas.room import RoomResponse
from app.services.meeting_service import MeetingService
from app.services.notification_service import send_meeting_invitation_notifications

router = APIRouter()


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

    # 2. Gửi thông báo ngầm cho những người được mời tham dự
    # Filter organizer khỏi danh sách — organizer không nhận invitation notification
    if payload.participant_ids and created_meetings:
        first_meeting = created_meetings[0] if isinstance(created_meetings, list) else created_meetings
        start_str = first_meeting.start_time.strftime("%H:%M %d/%m/%Y")
        notify_ids = [pid for pid in payload.participant_ids if pid != current_user.id]
        if notify_ids:
            background_tasks.add_task(
                send_meeting_invitation_notifications,
                db=db,
                participant_ids=notify_ids,
                meeting_title=first_meeting.title,
                start_time_str=start_str,
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
    query = db.query(Meeting).filter(Meeting.status.notin_(["CANCELLED", "canceled"]))

    if room_id:
        query = query.filter(Meeting.room_id == room_id)
    if start_date:
        query = query.filter(Meeting.start_time >= start_date)
    if end_date:
        query = query.filter(Meeting.end_time <= end_date)

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
    now = datetime.utcnow()

    participant_meeting_ids = (
        db.query(MeetingParticipant.meeting_id)
        .filter(MeetingParticipant.user_id == current_user.id)
        .subquery()
    )

    query = (
        db.query(Meeting)
        .filter(
            Meeting.end_time < now,
            Meeting.status.notin_(["CANCELLED", "canceled"]),
            (
                (Meeting.organizer_id == current_user.id)
                | Meeting.id.in_(participant_meeting_ids)
            ),
        )
        .distinct()
        .order_by(Meeting.end_time.desc())
    )

    return query.all()


@router.patch(
    "/{meeting_id}/cancel",
    response_model=MeetingResponse,
    status_code=status.HTTP_200_OK,
    summary="Hủy cuộc họp",
    description="Hủy cuộc họp theo ID. Chỉ người tổ chức (organizer) hoặc admin mới có quyền hủy.",
)
def cancel_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return MeetingService.cancel_meeting(db, meeting_id, current_user)


@router.delete(
    "/{meeting_id}",
    response_model=MeetingResponse,
    status_code=status.HTTP_200_OK,
    summary="Hủy cuộc họp (Endpoint tương thích)",
    description="Endpoint tương thích ngược hỗ trợ hủy cuộc họp qua phương thức DELETE.",
)
def cancel_meeting_legacy(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return MeetingService.cancel_meeting(db, meeting_id, current_user)