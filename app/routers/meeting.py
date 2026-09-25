from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.room import Room
from app.models.meeting import Meeting
from app.schemas.meeting import MeetingCreate

router = APIRouter(prefix="/meetings", tags=["Meetings"])

# --- NHIỆM VỤ 1: Lấy danh sách phòng họp từ kho ---
@router.get("/rooms")
def get_rooms(db: Session = Depends(get_db)):
    """Lấy danh sách toàn bộ phòng họp để hiển thị lên giao diện"""
    rooms = db.query(Room).all()
    return {
        "status": "success",
        "count": len(rooms),
        "data": rooms
    }

# --- NHIỆM VỤ 2 & 3: Đặt phòng và Chống trùng lịch ---
@router.post("/", status_code=status.HTTP_201_CREATED)
def book_meeting(meeting_data: MeetingCreate, db: Session = Depends(get_db)):
    """
    Kiểm tra logic chống trùng lịch:
    Nếu phòng đã có lịch họp trong khoảng thời gian bị đè, code sẽ chặn lại ngay lập tức!
    """
    # 1. Kiểm tra phòng có tồn tại không
    room = db.query(Room).filter(Room.id == meeting_data.room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Phòng họp không tồn tại trong hệ thống!")

    # 2. Thuật toán kiểm tra xung đột thời gian (Overlap Checking)
    # Công thức: (Existing_Start < New_End) AND (Existing_End > New_Start)
    overlapping_meeting = db.query(Meeting).filter(
        Meeting.room_id == meeting_data.room_id,
        Meeting.start_time < meeting_data.end_time,
        Meeting.end_time > meeting_data.start_time
    ).first()

    if overlapping_meeting:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Phòng '{room.name}' đã có người đặt từ "
                f"{overlapping_meeting.start_time.strftime('%H:%M %d/%m/%Y')} đến "
                f"{overlapping_meeting.end_time.strftime('%H:%M %d/%m/%Y')}. "
                "Vui lòng chọn khung giờ khác!"
            )
        )

    # 3. Tiến hành lưu lịch họp mới vào database nếu không bị trùng
    new_meeting = Meeting(
        room_id=meeting_data.room_id,
        title=meeting_data.title,
        description=meeting_data.description,
        start_time=meeting_data.start_time,
        end_time=meeting_data.end_time,
        status="scheduled"
    )
    db.add(new_meeting)
    db.commit()
    db.refresh(new_meeting)

    return {
        "message": "Đặt phòng thành công!",
        "data": new_meeting
    }