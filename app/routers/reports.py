from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional

from app.core.database import get_db
from app.models.meeting import Meeting
from app.models.room import Room

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/room-usage")
def get_room_usage_report(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    room_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    # Thiết lập thời gian mặc định (30 ngày gần nhất)
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thời gian bắt đầu (start_date) không được lớn hơn thời gian kết thúc (end_date)."
        )

    delta_days = (end_date - start_date).days or 1

    # CHỈ LẤY CÁC PHÒNG CÒN TỒN TẠI VÀ ĐANG HOẠT ĐỘNG TRONG HỆ THỐNG
    room_query = db.query(Room).filter(Room.is_active == True) if hasattr(Room, 'is_active') else db.query(Room)
    
    if room_id:
        room_query = room_query.filter(Room.id == room_id)
    
    rooms = room_query.all()
    valid_room_ids = {room.id for room in rooms}
    total_rooms_count = len(rooms)

    room_details = []
    total_meetings_all = 0
    total_hours_all = 0.0

    for room in rooms:
        # Chỉ quét các cuộc họp thuộc đúng phòng hiện có và có trạng thái hợp lệ
        meetings = db.query(Meeting).filter(
            Meeting.room_id == room.id,
            Meeting.status.in_(["CONFIRMED", "COMPLETED", "scheduled"]),
            Meeting.start_time >= start_date,
            Meeting.end_time <= end_date
        ).all()

        room_meeting_count = len(meetings)
        room_total_hours = 0.0

        for m in meetings:
            if m.start_time and m.end_time:
                duration = (m.end_time - m.start_time).total_seconds() / 3600.0
                room_total_hours += max(0.0, duration)

        max_possible_hours = delta_days * 8.0
        occupancy_rate = (room_total_hours / max_possible_hours * 100.0) if max_possible_hours > 0 else 0.0
        occupancy_rate = min(100.0, occupancy_rate)

        total_meetings_all += room_meeting_count
        total_hours_all += room_total_hours

        room_details.append({
            "room_id": room.id,
            "room_name": room.name,
            "total_meetings": room_meeting_count,
            "total_hours": round(room_total_hours, 2),
            "occupancy_rate": round(occupancy_rate, 2)
        })

    avg_occupancy = (sum(r["occupancy_rate"] for r in room_details) / total_rooms_count) if total_rooms_count > 0 else 0.0

    return {
        "summary": {
            "total_rooms": total_rooms_count,
            "total_meetings": total_meetings_all,
            "total_hours": round(total_hours_all, 2),
            "average_occupancy_rate": round(avg_occupancy, 2)
        },
        "room_details": room_details
    }