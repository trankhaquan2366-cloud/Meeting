# app/routers/meetings.py
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.meeting import Meeting, MeetingParticipant
from app.models.user import User
from app.schemas.meeting import (
    MeetingCheckInRequest,
    MeetingCheckOutRequest,
    MeetingCancelRequest,
    MeetingCreateRequest,
    MeetingParticipationResponse,
    MeetingResponse,
    SuggestTimeRequest,
    SuggestTimeResponse,
)
from app.schemas.room import RoomResponse
from app.services.meeting_service import MeetingService
from app.services.notification_service import send_meeting_invitation_notifications
from app.services.calendar_email_service import request_calendar_access_for_invitees
from app.services.google_calendar_service import (
    delete_google_events_for_meeting,
    sync_user_meetings_to_google,
)

router = APIRouter()
logger = logging.getLogger(__name__)


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

    if current_user.google_refresh_token and created_meetings:
        background_tasks.add_task(sync_user_meetings_to_google, current_user.id)

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
            background_tasks.add_task(
                request_calendar_access_for_invitees,
                user_ids=notify_ids,
                meeting_ids=[meeting.id for meeting in created_meetings],
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


@router.post("/{meeting_id}/check-in", response_model=MeetingResponse)
def check_in_meeting(
    meeting_id: int,
    payload: MeetingCheckInRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return MeetingService.check_in_meeting(db, meeting_id, payload.qr_token, current_user)


@router.post("/{meeting_id}/check-out", response_model=MeetingResponse)
def check_out_meeting(
    meeting_id: int,
    payload: MeetingCheckOutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return MeetingService.check_out_meeting(db, meeting_id, payload.qr_token, current_user)


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
    query = db.query(Meeting).filter(
        Meeting.status.notin_(["CANCELLED", "canceled", "CANCELLED_NO_SHOW"])
    )

    if room_id:
        query = query.filter(Meeting.room_id == room_id)
    if start_date:
        query = query.filter(Meeting.start_time >= start_date)
    if end_date:
        query = query.filter(Meeting.end_time <= end_date)

    try:
        return query.all()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database error while listing meetings")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Không thể tải danh sách cuộc họp do lỗi cơ sở dữ liệu. "
            "Vui lòng kiểm tra schema/migration.",
        ) from exc


@router.get(
    "/mine",
    summary="Lịch họp của người dùng hiện tại",
    description="Trả về cuộc họp do người dùng chủ trì hoặc được mời, kèm trạng thái phản hồi của từng khách mời.",
)
def get_my_meetings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        meetings = (
            db.query(Meeting)
            .outerjoin(MeetingParticipant, MeetingParticipant.meeting_id == Meeting.id)
            .filter(
                (Meeting.organizer_id == current_user.id)
                | (MeetingParticipant.user_id == current_user.id)
            )
            .filter(
                Meeting.status.notin_(
                    ["CANCELLED", "canceled", "cancelled", "CANCELLED_NO_SHOW"]
                )
            )
            .distinct()
            .order_by(Meeting.start_time)
            .all()
        )

        results = []
        for meeting in meetings:
            item = MeetingResponse.model_validate(meeting).model_dump(mode="json")
            item["is_organizer"] = meeting.organizer_id == current_user.id
            item["organizer_name"] = (
                meeting.organizer.full_name or meeting.organizer.username
                if meeting.organizer
                else "Người tổ chức"
            )
            item["room_name"] = meeting.room.name if meeting.room else None
            item["my_response_status"] = next(
                (
                    participant.response_status
                    for participant in meeting.participants
                    if participant.user_id == current_user.id
                ),
                None,
            )
            item["participants"] = [
                {
                    "user_id": participant.user_id,
                    "name": (
                        participant.user.full_name or participant.user.username
                        if participant.user
                        else "Người tham dự"
                    ),
                    "email": participant.user.email if participant.user else None,
                    "response_status": participant.response_status,
                }
                for participant in meeting.participants
            ]
            results.append(item)
        return results
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database error while loading meetings for user_id=%s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Không thể tải lịch họp do lỗi cơ sở dữ liệu. "
            "Vui lòng kiểm tra schema/migration của meeting_participants.",
        ) from exc


@router.patch(
    "/{meeting_id}/response",
    summary="Phản hồi lời mời họp",
    description="Cho phép người được mời xác nhận tham gia hoặc từ chối; không cấp quyền hủy cuộc họp.",
)
def respond_to_meeting_invitation(
    meeting_id: int,
    payload: MeetingParticipationResponse,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        participant = (
            db.query(MeetingParticipant)
            .filter(
                MeetingParticipant.meeting_id == meeting_id,
                MeetingParticipant.user_id == current_user.id,
            )
            .first()
        )
        if participant is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy lời mời họp.")
        participant.response_status = payload.response_status
        db.commit()
        return {"meeting_id": meeting_id, "response_status": participant.response_status}
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception(
            "Database error while saving RSVP for meeting_id=%s user_id=%s",
            meeting_id,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Không thể lưu phản hồi do lỗi cơ sở dữ liệu. "
            "Vui lòng kiểm tra schema/migration của meeting_participants.",
        ) from exc


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
            Meeting.status.notin_(["CANCELLED", "canceled", "CANCELLED_NO_SHOW"]),
            (
                (Meeting.organizer_id == current_user.id)
                | Meeting.id.in_(participant_meeting_ids)
            ),
        )
        .distinct()
        .order_by(Meeting.end_time.desc())
    )

    try:
        return query.all()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database error while loading meeting history for user_id=%s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Không thể tải lịch sử cuộc họp do lỗi cơ sở dữ liệu. "
            "Vui lòng kiểm tra schema/migration.",
        ) from exc


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
    payload: MeetingCancelRequest | None = Body(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    meeting = MeetingService.cancel_meeting(
        db,
        meeting_id,
        current_user,
        payload.cancellation_reason if payload else None,
    )
    background_tasks.add_task(delete_google_events_for_meeting, meeting.id)
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
    payload: MeetingCancelRequest | None = Body(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    meeting = MeetingService.cancel_meeting(
        db,
        meeting_id,
        current_user,
        payload.cancellation_reason if payload else None,
    )
    background_tasks.add_task(delete_google_events_for_meeting, meeting.id)
    return meeting