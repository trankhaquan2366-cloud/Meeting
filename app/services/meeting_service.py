from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi import HTTPException, status

from app.models.room import Room
from app.models.meeting import Meeting
from app.schemas.meeting import MeetingCreateRequest

class MeetingService:

    @staticmethod
    def get_all_active_rooms(db: Session):
        """VIỆC 1: Lấy danh sách tất cả phòng họp đang hoạt động"""
        return db.query(Room).filter(Room.is_active == True).all()

    @staticmethod
    def create_meeting(db: Session, payload: MeetingCreateRequest, organizer_id: int | None = None):
        """VIỆC 2 & 3: Đặt phòng + Kiểm tra chống trùng lịch"""

        # 1. Kiểm tra phòng họp có tồn tại và active không
        room = db.query(Room).filter(Room.id == payload.room_id, Room.is_active == True).first()
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Phòng họp không tồn tại hoặc đã bị khóa!"
            )

        # 2. VIỆC 3: LOGIC CHỐNG TRÙNG LỊCH HỌP (OVERLAPPING CHECK)
        # Tìm cuộc họp nào thuộc phòng này, chưa bị hủy (status != 'canceled')
        # và có khoảng thời gian đè đan xen với khoảng thời gian mới đăng ký.
        overlapping_meeting = db.query(Meeting).filter(
            Meeting.room_id == payload.room_id,
            Meeting.status != "canceled",
            and_(
                Meeting.start_time < payload.end_time,
                Meeting.end_time > payload.start_time
            )
        ).first()

        # Nếu tìm thấy dù chỉ 1 cuộc họp bị trùng -> Chặn lại ngay!
        if overlapping_meeting:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Phòng họp '{room.name}' đã bị trùng lịch! "
                       f"Đã có cuộc họp '{overlapping_meeting.title}' "
                       f"từ {overlapping_meeting.start_time.strftime('%H:%M')} "
                       f"đến {overlapping_meeting.end_time.strftime('%H:%M')}."
            )

        # 3. Tạo bản ghi đặt phòng mới nếu thỏa mãn điều kiện
        new_meeting = Meeting(
            title=payload.title,
            description=payload.description,
            room_id=payload.room_id,
            organizer_id=organizer_id,
            start_time=payload.start_time,
            end_time=payload.end_time,
            status="scheduled"
        )

        db.add(new_meeting)
        db.commit()
        db.refresh(new_meeting)
        return new_meeting