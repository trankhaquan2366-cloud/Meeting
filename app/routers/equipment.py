from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.models.equipment import Equipment
from app.schemas.equipment import EquipmentCreate, EquipmentUpdate, EquipmentResponse, EquipmentStatusResponse
from app.services.equipment_service import get_equipment_availability
from app.core.security import require_role
from app.core.time import normalize_to_utc_naive

router = APIRouter()

# 🟢 Dấu "/" ở cuối để khớp với yêu cầu GET /api/equipments/?include_inactive=true từ Frontend
@router.get("/", response_model=List[EquipmentResponse])
def get_equipments(
    skip: int = 0,
    limit: int = 100,
    include_inactive: bool = Query(False, description="Nếu True, trả về cả các thiết bị đã ngưng hoạt động/vô hiệu hóa"),
    db: Session = Depends(get_db),
):
    query = db.query(Equipment)
    if not include_inactive:
        query = query.filter(Equipment.is_active == True)
    return query.offset(skip).limit(limit).all()


@router.get("/availability", response_model=List[EquipmentStatusResponse])
def get_equipment_availability_list(
    start_time: datetime | None = Query(None, description="Thời gian bắt đầu"),
    end_time: datetime | None = Query(None, description="Thời gian kết thúc"),
    category: str | None = Query(None),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
):
    if start_time is None and end_time is None:
        start_time = end_time = datetime.now(timezone.utc)
    elif start_time is None:
        start_time = end_time
    elif end_time is None:
        end_time = start_time

    start_time = normalize_to_utc_naive(start_time)
    end_time = normalize_to_utc_naive(end_time)
    if start_time > end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thời gian bắt đầu phải nhỏ hơn hoặc bằng thời gian kết thúc.",
        )

    return get_equipment_availability(
        db=db,
        start_time=start_time,
        end_time=end_time,
        category=category,
        search=search,
    )


@router.post("/", response_model=EquipmentResponse, status_code=status.HTTP_201_CREATED)
def create_equipment(
    payload: EquipmentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin")),
):
    equip = Equipment(**payload.model_dump())
    db.add(equip)
    db.commit()
    db.refresh(equip)
    return equip


@router.put("/{equipment_id}", response_model=EquipmentResponse)
def update_equipment(
    equipment_id: int,
    payload: EquipmentUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin")),
):
    equip = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equip:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(equip, field, value)

    db.commit()
    db.refresh(equip)
    return equip


@router.delete("/{equipment_id}", status_code=status.HTTP_200_OK)
def delete_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin")),
):
    equip = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equip:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị")

    equip.is_active = False
    db.commit()
    return {"status": "success", "message": f"Đã chuyển trạng thái thiết bị '{equip.name}' thành ngừng hoạt động."}