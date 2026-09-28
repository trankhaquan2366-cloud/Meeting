from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.database import get_db
from app.core.security import get_current_user  # Hoặc hàm lấy user hiện tại từ token
from app.models.meeting import Meeting
from app.models.room import Room
from app.schemas.meeting import MeetingCreateRequest, MeetingResponse

router = APIRouter(prefix="/api/meetings", tags=["Meetings Management"])


# ----------------------------------------------------
# 1. ĐẶT LỊCH HỌP MỚI
# ----------------------------------------------------
@router.post(
    "/",
    response_model=MeetingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Đặt lịch họp mới"
)
def create_meeting(
    meeting_in: MeetingCreateRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    # 1. Kiểm tra phòng họp có tồn tại và đang hoạt động không
    room = db.query(Room).filter(Room.id == meeting_in.room_id, Room.is_active == True).first()
    if not room:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Phòng họp không tồn tại hoặc đã ngừng hoạt động."
        )

    # 2. Kiểm tra xung đột lịch họp (Overlapping check)
    overlapping_meeting = db.query(Meeting).filter(
        Meeting.room_id == meeting_in.room_id,
        Meeting.status != "cancelled",  # Bỏ qua lịch đã hủy
        and_(
            Meeting.start_time < meeting_in.end_time,
            Meeting.end_time > meeting_in.start_time
        )
    ).first()

    if overlapping_meeting:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phòng họp đã bị trùng lịch trong khoảng thời gian này!"
        )

    # 3. Tạo cuộc họp mới
    new_meeting = Meeting(
        title=meeting_in.title,
        description=meeting_in.description,
        room_id=meeting_in.room_id,
        organizer_id=current_user.id,  # Lấy ID người tạo từ Token đăng nhập
        start_time=meeting_in.start_time,
        end_time=meeting_in.end_time,
        status="scheduled"
    )

    db.add(new_meeting)
    db.commit()
    db.refresh(new_meeting)
    return new_meeting


# ----------------------------------------------------
# 2. LẤY DANH SÁCH CUỘC HỌP (Có bộ lọc)
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
    query = db.query(Meeting).filter(Meeting.status != "cancelled")

    if room_id:
        query = query.filter(Meeting.room_id == room_id)
    if start_date:
        query = query.filter(Meeting.start_time >= start_date)
    if end_date:
        query = query.filter(Meeting.end_time <= end_date)

    return query.all()


# ----------------------------------------------------
# 3. HỦY CUỘC HỌP
# ----------------------------------------------------
@router.delete(
    "/{meeting_id}",
    status_code=status.HTTP_200_OK,
    summary="Hủy cuộc họp"
)
def cancel_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
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

    meeting.status = "cancelled"
    db.commit()

    return {"status": "success", "message": f"Đã hủy cuộc họp '{meeting.title}' thành công."}