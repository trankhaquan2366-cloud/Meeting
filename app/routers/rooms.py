import json
from datetime import datetime
from sqlalchemy import and_, func
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError


from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.equipment import Equipment, RoomEquipment
from app.models.room import Room
from app.models.meeting import Meeting
from app.models.user import User
from app.schemas.room import RoomCreate, RoomUpdate, RoomResponse, RoomQRResponse
from app.services import room_service
# Khởi tạo APIRouter (KHÔNG thêm prefix ở đây vì đã có prefix="/api/rooms" ở main.py)
router = APIRouter()


def _resolve_room_equipment(db: Session, equipment_ids: List[int]) -> list[Equipment]:
    unique_ids = list(dict.fromkeys(equipment_ids))
    if not unique_ids:
        return []
    equipment = db.query(Equipment).filter(
        Equipment.id.in_(unique_ids),
        Equipment.is_active.is_(True),
    ).all()
    found_ids = {item.id for item in equipment}
    invalid_ids = [equipment_id for equipment_id in unique_ids if equipment_id not in found_ids]
    if invalid_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Phòng chỉ có thể liên kết thiết bị đang hoạt động.",
                "equipment_ids": invalid_ids,
            },
        )
    equipment_by_id = {item.id: item for item in equipment}
    return [equipment_by_id[equipment_id] for equipment_id in unique_ids]


def _sync_room_equipment(room: Room, equipment: List[Equipment]) -> None:
    room.default_equipments = [
        RoomEquipment(equipment=item, quantity=1)
        for item in equipment
    ]
    room.amenities = json.dumps(
        [item.name for item in equipment],
        ensure_ascii=False,
    ) if equipment else None


def _set_room_status(room: Room, room_status: str) -> None:
    room.room_status = room_status
    room.is_active = room_status == "active"


@router.get("/{room_id}/qr-code", response_model=RoomQRResponse, summary="Lấy mã QR phòng họp")
def get_room_qr_code(
    room_id: int,
    meeting_id: Optional[int] = Query(None, description="Cuộc họp do người tổ chức hiện tại chủ trì"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    role = str(current_user.role or "").strip().casefold()
    room = db.query(Room).filter(Room.id == room_id).first()
    if room is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy phòng họp")
    if role not in {"admin", "manager"}:
        if meeting_id is None:
            raise HTTPException(
                status_code=403,
                detail="Chỉ Admin, Manager hoặc chủ trì cuộc họp mới được lấy mã QR phòng.",
            )
        meeting = db.query(Meeting).filter(
            Meeting.id == meeting_id,
            Meeting.room_id == room_id,
            Meeting.organizer_id == current_user.id,
            func.upper(Meeting.status).in_(["SCHEDULED", "IN_PROGRESS"]),
        ).first()
        if meeting is None:
            raise HTTPException(
                status_code=403,
                detail="Bạn không có quyền lấy mã QR cho cuộc họp này.",
            )
    if not room.qr_token:
        room.generate_qr_token()
        db.commit()
        db.refresh(room)
    return RoomQRResponse(room_id=room.id, room_name=room.name, qr_token=room.qr_token)

# GET /api/rooms/: Lấy danh sách tất cả phòng
@router.get("/", response_model=List[RoomResponse], summary="Lấy danh sách tất cả phòng")
def get_all_rooms(db: Session = Depends(get_db)):
    return db.query(Room).filter(
        Room.is_active.is_(True),
        Room.room_status == "active",
    ).all()


@router.get(
    "/all-status/",
    response_model=List[RoomResponse],
    summary="Lấy tất cả phòng, bao gồm phòng bảo trì (Admin)",
)
def get_all_rooms_with_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    return db.query(Room).order_by(Room.name).all()


# GET /api/rooms/available: Tìm phòng trống theo khoảng thời gian
@router.get("/available", response_model=List[RoomResponse], summary="Tìm phòng trống")
def get_available_rooms(
    start_time: datetime = Query(..., description="Thời gian bắt đầu"),
    end_time: datetime = Query(..., description="Thời gian kết thúc"),
    min_capacity: Optional[int] = Query(0, description="Sức chứa tối thiểu"),
    db: Session = Depends(get_db),
):
    # 1. Kiểm tra thời gian đầu vào hợp lệ
    if start_time >= end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thời gian kết thúc phải lớn hơn thời gian bắt đầu."
        )

    return room_service.get_available_rooms(
        db=db,
        start_time=start_time,
        end_time=end_time,
        min_capacity=min_capacity or 0,
    )


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

    selected_equipment = _resolve_room_equipment(db, room_in.equipment_ids)
    room_status = room_in.room_status
    if "room_status" not in room_in.model_fields_set and "is_active" in room_in.model_fields_set:
        room_status = "active" if room_in.is_active else "maintenance"

    amenities_data = room_in.amenities
    if isinstance(amenities_data, list):
        amenities_json = json.dumps(amenities_data, ensure_ascii=False) if amenities_data else None
    elif isinstance(amenities_data, str) and amenities_data.strip():
        amenities_json = json.dumps(
            [item.strip() for item in amenities_data.split(",") if item.strip()],
            ensure_ascii=False,
        )
    else:
        amenities_json = None
    if "equipment_ids" in room_in.model_fields_set:
        amenities_json = json.dumps(
            [item.name for item in selected_equipment],
            ensure_ascii=False,
        ) if selected_equipment else None

    new_room = Room(
        name=room_in.name,
        capacity=room_in.capacity,
        location=room_in.location,
        description=room_in.description,
        amenities=amenities_json,
        is_active=room_status == "active",
        room_status=room_status,
        room_image=room_in.room_image,
        layout_type=room_in.layout_type,
    )
    if "equipment_ids" in room_in.model_fields_set:
        _sync_room_equipment(new_room, selected_equipment)
    db.add(new_room)
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
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
    selected_equipment = None
    if "equipment_ids" in update_data:
        selected_equipment = _resolve_room_equipment(db, update_data.pop("equipment_ids") or [])
    if "amenities" in update_data:
        val = update_data["amenities"]
        if isinstance(val, list):
            update_data["amenities"] = json.dumps(val, ensure_ascii=False)
        elif isinstance(val, str) and val.strip():
            update_data["amenities"] = json.dumps([s.strip() for s in val.split(',') if s.strip()], ensure_ascii=False)
        else:
            update_data["amenities"] = None

    if update_data.get("room_status") is not None:
        _set_room_status(room, update_data.pop("room_status"))
        update_data.pop("is_active", None)
    elif "is_active" in update_data:
        room.is_active = update_data.pop("is_active")
        room.room_status = "active" if room.is_active else "maintenance"

    for key, value in update_data.items():
        setattr(room, key, value)
    if selected_equipment is not None:
        _sync_room_equipment(room, selected_equipment)

    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
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
    room.room_status = "locked"
    db.commit()
    return {"status": "success", "message": f"Đã chuyển trạng thái phòng '{room.name}' thành ngưng hoạt động."}  