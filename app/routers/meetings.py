from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.meeting import Meeting, MeetingParticipant
from app.models.user import User
from app.schemas.room import RoomResponse
from app.schemas.meeting import MeetingCreateRequest, MeetingResponse
from app.services.meeting_service import MeetingService

router = APIRouter(prefix="/meetings", tags=["Meetings Management"])


@router.get(
    "/rooms",
    response_model=List[RoomResponse],
    summary="Lấy danh sách phòng họp",
    description="Trả về danh sách các phòng họp đang sẵn sàng cho người dùng chọn."
)
def list_rooms(db: Session = Depends(get_db)):
    return MeetingService.get_all_active_rooms(db)


@router.post(
    "/book",
    response_model=List[MeetingResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Đặt lịch họp mới (Đơn & Định kỳ)",
    description="Tạo cuộc họp mới hoặc chuỗi lịch định kỳ. Hệ thống tự động kiểm tra trùng lịch và rollback toàn bộ nếu có xung đột."
)
def create_meeting(
    payload: MeetingCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return MeetingService.create_meeting(
        db=db,
        payload=payload,
        organizer_id=current_user.id
    )


@router.get(
    "/",
    response_model=List[MeetingResponse],
    summary="Lấy danh sách các cuộc họp"
)
def get_meetings(
    room_id: Optional[int] = Query(None, description="Lọc theo phòng"),
    start_date: Optional[datetime] = Query(None, description="Lọc từ ngày"),
    end_date: Optional[datetime] = Query(None, description="Lọc đến ngày"),
    db: Session = Depends(get_db)
):
    query = db.query(Meeting).filter(Meeting.status != "canceled")

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
            Meeting.status != "canceled",
            (
                (Meeting.organizer_id == current_user.id)
                | Meeting.id.in_(participant_meeting_ids)
            ),
        )
        .distinct()
        .order_by(Meeting.end_time.desc())
    )

    return query.all()


@router.delete(
    "/{meeting_id}",
    status_code=status.HTTP_200_OK,
    summary="Hủy cuộc họp"
)
def cancel_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy cuộc họp."
        )

    is_admin = getattr(current_user, "role", "") == "admin"
    if meeting.organizer_id != current_user.id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền hủy cuộc họp này."
        )

    meeting.status = "canceled"
    db.commit()

    return {"status": "success", "message": f"Đã hủy cuộc họp '{meeting.title}' thành công."}