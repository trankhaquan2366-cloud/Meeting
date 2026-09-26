from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.room import RoomResponse
from app.schemas.meeting import MeetingCreateRequest, MeetingResponse
from app.services.meeting_service import MeetingService

router = APIRouter(prefix="/meetings", tags=["Meeting Management"])


@router.get(
    "/rooms",
    response_model=List[RoomResponse],
    summary="Việc 1: Lấy danh sách phòng họp",
    description="Trả về danh sách các phòng họp đang sẵn sàng cho người dùng chọn."
)
def list_rooms(db: Session = Depends(get_db)):
    return MeetingService.get_all_active_rooms(db)


@router.post(
    "/book",
    response_model=List[MeetingResponse],  # <--- Đổi thành List[MeetingResponse]
    status_code=status.HTTP_201_CREATED,
    summary="Việc 2 & 3: Đặt phòng họp (Hỗ trợ đơn & định kỳ)",
    description="Tạo cuộc họp mới hoặc chuỗi lịch định kỳ. Hệ thống sẽ tự động chặn và rollback toàn bộ nếu bị trùng khung giờ bất kỳ ngày nào."
)
def book_room(payload: MeetingCreateRequest, db: Session = Depends(get_db)):
    # Tạm thời chưa bắt buộc JWT token, để organizer_id=1 (Admin) thử nghiệm
    return MeetingService.create_meeting(db=db, payload=payload, organizer_id=1)