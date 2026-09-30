from datetime import datetime
from sqlalchemy.orm import Session
from app.models.meeting import Meeting
from app.models.room import Room


def get_available_rooms(
    db: Session,
    start_time: datetime,
    end_time: datetime,
    min_capacity: int = 0,
):
    # 1. Tìm các room_id đã bị đặt trong khoảng thời gian này
    occupied_room_ids = (
        db.query(Meeting.room_id)
        .filter(
            Meeting.status != "CANCELLED",
            Meeting.start_time < end_time,
            Meeting.end_time > start_time,
        )
        .subquery()
    )

    # 2. Lấy danh sách các phòng trống và đủ sức chứa
    available_rooms = (
        db.query(Room)
        .filter(
            Room.is_active == True,
            Room.capacity >= min_capacity,
            ~Room.id.in_(occupied_room_ids),
        )
        .all()
    )

    return available_rooms