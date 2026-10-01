from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session


from app.core.database import get_db
from app.core.security import require_role
from app.models.room import Room
from app.models.meeting import Meeting
from app.schemas.room import RoomCreate, RoomUpdate, RoomResponse
from app.services import room_service
# Khởi tạo APIRouter (KHÔNG thêm prefix ở đây vì đã có prefix="/api/rooms" ở main.py)
router = APIRouter()

# GET /api/rooms/: Lấy danh sách tất cả phòng
@router.get("/", response_model=List[RoomResponse], summary="Lấy danh sách tất cả phòng")
def get_all_rooms(db: Session = Depends(get_db)):
    # THÊM FILTER is_active == True
    return db.query(Room).filter(Room.is_active == True).all()


# GET /api/rooms/available: Tìm phòng trống theo khoảng thời gian
@router.get("/available", response_model=List[RoomResponse], summary="Tìm phòng trống")
def get_available_rooms(
    start_time: datetime,
    end_time: datetime,
    db: Session = Depends(get_db)
):
    # 1. Kiểm tra thời gian đầu vào hợp lệ
    if start_time >= end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thời gian kết thúc phải lớn hơn thời gian bắt đầu."
        )

    # 2. Tìm danh sách ID các phòng BỊ TRÙNG LỊCH
    busy_rooms_query = db.query(Meeting.room_id).filter(
        Meeting.status != "canceled",  # Bỏ qua các cuộc họp đã hủy
        and_(
            Meeting.start_time < end_time,
            Meeting.end_time > start_time
        )
    ).subquery()

    # 3. Lấy danh sách phòng ĐANG HOẠT ĐỘNG và KHÔNG BỊ TRÙNG LỊCH
    available_rooms = db.query(Room).filter(
        Room.is_active == True,
        Room.id.notin_(busy_rooms_query)
    ).all()

    return available_rooms


# POST /api/rooms/: Thêm phòng mới (Chỉ Admin)
@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED, summary="Thêm phòng mới (Admin)")
def create_room(
    room_in: RoomCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin"))
):
    # Kiểm tra xem tên phòng đã tồn tại chưa
    existing_room = db.query(Room).filter(Room.name == room_in.name).first()
    if existing_room:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tên phòng họp đã tồn tại!"
        )

    # Tạo phòng mới
    new_room = Room(
        name=room_in.name,
        capacity=room_in.capacity,
        location=room_in.location,
        description=room_in.description,
        is_active=room_in.is_active
    )
    db.add(new_room)
    db.commit()
    db.refresh(new_room)
    return new_room


# PUT /api/rooms/{room_id}: Cập nhật thông tin phòng (Chỉ Admin)
@router.put("/{room_id}", response_model=RoomResponse, status_code=status.HTTP_200_OK, summary="Cập nhật phòng (Admin)")
def update_room(
    room_id: int,
    room_in: RoomUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin"))
):
    # Tìm phòng
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Không tìm thấy phòng họp")

    # Cập nhật các trường có gửi lên
    update_data = room_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(room, key, value)

    db.commit()
    db.refresh(room)
    return room


# DELETE /api/rooms/{room_id}: Xóa (ẩn - soft delete) phòng (Chỉ Admin)
@router.delete("/{room_id}", status_code=status.HTTP_200_OK, summary="Xóa/Ẩn phòng (Admin)")
def delete_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin"))
):
    # Tìm phòng
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Không tìm thấy phòng họp")

    # Soft delete: Cập nhật trạng thái thành False thay vì xóa hẳn khỏi DB
    room.is_active = False
    db.commit()
    return {"status": "success", "message": f"Đã chuyển trạng thái phòng '{room.name}' thành ngưng hoạt động."}
@router.get("/available/", response_model=List[RoomResponse])
def read_available_rooms(
    start_time: datetime = Query(..., description="Thời gian bắt đầu"),
    end_time: datetime = Query(..., description="Thời gian kết thúc"),
    min_capacity: Optional[int] = Query(0, description="Sức chứa tối thiểu"),
    db: Session = Depends(get_db),
):
    if start_time >= end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thời gian bắt đầu phải nhỏ hơn thời gian kết thúc!",
        )

    rooms = room_service.get_available_rooms(
        db=db,
        start_time=start_time,
        end_time=end_time,
        min_capacity=min_capacity,
    )

    return rooms