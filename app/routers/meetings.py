from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.meeting import Meeting
from app.models.user import User
from app.schemas.room import RoomResponse
from app.schemas.meeting import MeetingCreateRequest, MeetingResponse
from app.services.meeting_service import MeetingService

router = APIRouter(prefix="/meetings", tags=["Meetings Management"])


# ----------------------------------------------------
# 1. LẤY DANH SÁCH PHÒNG HỌP ĐANG HOẠT ĐỘNG
# ----------------------------------------------------
@router.get(
    "/rooms",
    response_model=List[RoomResponse],
    summary="Lấy danh sách phòng họp",
    description="Trả về danh sách các phòng họp đang sẵn sàng cho người dùng chọn."
)
def list_rooms(db: Session = Depends(get_db)):
    return MeetingService.get_all_active_rooms(db)


# ----------------------------------------------------
# 2. ĐẶT LỊCH HỌP MỚI (HỖ TRỢ ĐƠN & ĐỊNH KỲ)
# ----------------------------------------------------
@router.post(
    "/book",
    response_model=List[MeetingResponse],  # Trả về danh sách (chứa 1 hoặc nhiều cuộc họp nếu lặp lịch)
    status_code=status.HTTP_201_CREATED,
    summary="Đặt lịch họp mới (Đơn & Định kỳ)",
    description="Tạo cuộc họp mới hoặc chuỗi lịch định kỳ. Hệ thống tự động kiểm tra trùng lịch và rollback toàn bộ nếu có xung đột."
)
def create_meeting(
    payload: MeetingCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Sử dụng MeetingService để xử lý nghiệp vụ:
    - Chặn đặt lịch trong quá khứ
    - Kiểm tra phòng họp tồn tại & active
    - Tự động tạo chuỗi cuộc họp nếu đặt lịch định kỳ (weekly/monthly)
    - Kiểm tra chống trùng phòng họp & Rollback nếu phát hiện xung đột
    """
    return MeetingService.create_meeting(
        db=db,
        payload=payload,
        organizer_id=current_user.id
    )


# ----------------------------------------------------
# 3. LẤY DANH SÁCH CUỘC HỌP (Có bộ lọc)
# ----------------------------------------------------
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


# ----------------------------------------------------
# 4. HỦY CUỘC HỌP
# ----------------------------------------------------
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

    # Chỉ người tạo (organizer) hoặc Admin mới có quyền hủy
    is_admin = getattr(current_user, "role", "") == "admin"
    if meeting.organizer_id != current_user.id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền hủy cuộc họp này."
        )

    meeting.status = "canceled"
    db.commit()

    return {"status": "success", "message": f"Đã hủy cuộc họp '{meeting.title}' thành công."}