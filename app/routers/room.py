from fastapi import APIRouter, HTTPException, Depends, Header
from typing import List, Optional
from app.schemas.room import RoomResponse, RoomCreate, RoomUpdate

router = APIRouter(prefix="/api/rooms", tags=["Rooms"])

FAKE_ROOMS = [
    {
        "id": 1,
        "name": "Phòng Họp Hội Đồng",
        "location": "Tầng 5",
        "capacity": "18-20 người",
        "amenities": ["Màn hình", "Wifi", "Video"],
        "image_url": "https://images.unsplash.com/photo-1497366216548-37526070297c",
        "is_available": True
    },
    {
        "id": 2,
        "name": "Phòng Họp Sáng Tạo",
        "location": "Tầng 3",
        "capacity": "6-8 người",
        "amenities": ["Màn hình", "Wifi", "Đồ uống"],
        "image_url": "https://images.unsplash.com/photo-1517502884422-41eaead166d4",
        "is_available": False
    },
    {
        "id": 3,
        "name": "Phòng Hội Nghị A",
        "location": "Tầng 2",
        "capacity": "10-12 người",
        "amenities": ["Màn hình", "Wifi"],
        "image_url": "https://images.unsplash.com/photo-1431540015161-0bf868a2d407",
        "is_available": True
    }
]

def verify_admin(authorization: Optional[str] = Header(None)):
    if not authorization or "admin" not in authorization.lower():
        raise HTTPException(status_code=403, detail="Yêu cầu quyền Quản trị viên (Admin).")
    return True

@router.get("", response_model=List[RoomResponse])
def get_rooms():
    return FAKE_ROOMS

@router.post("", response_model=RoomResponse, status_code=201)
def create_room(room: RoomCreate, is_admin: bool = Depends(verify_admin)):
    new_id = max([r["id"] for r in FAKE_ROOMS], default=0) + 1
    new_room = room.model_dump()
    new_room["id"] = new_id
    FAKE_ROOMS.append(new_room)
    return new_room

@router.put("/{room_id}", response_model=RoomResponse)
def update_room(room_id: int, room_data: RoomUpdate, is_admin: bool = Depends(verify_admin)):
    for r in FAKE_ROOMS:
        if r["id"] == room_id:
            r.update(room_data.model_dump(exclude_unset=True))
            return r
    raise HTTPException(status_code=404, detail="Không tìm thấy phòng họp.")

@router.delete("/{room_id}")
def delete_room(room_id: int, is_admin: bool = Depends(verify_admin)):
    global FAKE_ROOMS
    initial_count = len(FAKE_ROOMS)
    FAKE_ROOMS = [r for r in FAKE_ROOMS if r["id"] != room_id]
    if len(FAKE_ROOMS) == initial_count:
        raise HTTPException(status_code=404, detail="Không tìm thấy phòng họp.")
    return {"message": "Đã xóa phòng thành công."}