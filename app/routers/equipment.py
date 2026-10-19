from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.models.equipment import Equipment
from app.schemas.equipment import EquipmentCreate, EquipmentUpdate, EquipmentResponse, EquipmentStatusResponse
from app.services.equipment_service import get_equipment_availability
from app.core.security import require_role

router = APIRouter()
EQUIPMENT_CATEGORIES = ("Visual", "Audio", "Cable", "Network", "Accessory")
EQUIPMENT_STATUSES = ("active", "maintenance", "retired")


def _apply_operational_status(equipment: Equipment, operational_status: str) -> None:
    equipment.operational_status = operational_status
    equipment.is_active = operational_status == "active"


def _apply_legacy_active_flag(equipment: Equipment, is_active: bool) -> None:
    _apply_operational_status(equipment, "active" if is_active else "retired")


def _filter_equipment_query(query, category, operational_status, search):
    if category:
        if category == "other":
            query = query.filter(
                Equipment.category.notin_(EQUIPMENT_CATEGORIES)
                | Equipment.category.is_(None)
            )
        else:
            query = query.filter(Equipment.category == category)
    if operational_status:
        query = query.filter(Equipment.operational_status == operational_status)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            Equipment.name.ilike(term)
            | Equipment.code.ilike(term)
            | Equipment.category.ilike(term)
            | Equipment.search_keywords.ilike(term)
        )
    return query

# 🟢 Dấu "/" ở cuối để khớp với yêu cầu GET /api/equipments/?include_inactive=true từ Frontend
@router.get("/", response_model=List[EquipmentResponse])
def get_equipments(
    skip: int = 0,
    limit: int = 100,
    include_inactive: bool = Query(False, description="Nếu True, trả về cả các thiết bị đã ngưng hoạt động/vô hiệu hóa"),
    category: str | None = Query(None),
    operational_status: str | None = Query(None),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Equipment)
    if not include_inactive:
        query = query.filter(Equipment.is_active == True)
    if operational_status and operational_status not in EQUIPMENT_STATUSES:
        raise HTTPException(status_code=422, detail="Trạng thái thiết bị không hợp lệ.")
    query = _filter_equipment_query(query, category, operational_status, search)
    return query.offset(skip).limit(limit).all()


@router.get("/availability", response_model=List[EquipmentStatusResponse])
def get_equipment_availability_list(
    start_time: datetime = Query(..., description="Thời gian bắt đầu"),
    end_time: datetime = Query(..., description="Thời gian kết thúc"),
    category: str | None = Query(None),
    operational_status: str | None = Query(None),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
):
    if end_time <= start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thời gian kết thúc phải sau thời gian bắt đầu.",
        )

    if operational_status and operational_status not in EQUIPMENT_STATUSES:
        raise HTTPException(status_code=422, detail="Trạng thái thiết bị không hợp lệ.")
    return get_equipment_availability(
        db=db,
        start_time=start_time,
        end_time=end_time,
        category=category,
        operational_status_filter=operational_status,
        search=search,
        active_only=False,
    )


@router.post("/", response_model=EquipmentResponse, status_code=status.HTTP_201_CREATED)
def create_equipment(
    payload: EquipmentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin")),
):
    equipment_data = payload.model_dump()
    operational_status = equipment_data.pop("operational_status")
    is_active = equipment_data.pop("is_active")
    equip = Equipment(**equipment_data)
    if "operational_status" in payload.model_fields_set:
        _apply_operational_status(equip, operational_status)
    else:
        _apply_legacy_active_flag(equip, is_active)
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

    update_data = payload.model_dump(exclude_unset=True)
    if "operational_status" in update_data:
        _apply_operational_status(equip, update_data.pop("operational_status"))
        update_data.pop("is_active", None)
    elif "is_active" in update_data:
        _apply_legacy_active_flag(equip, update_data.pop("is_active"))
    for field, value in update_data.items():
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
    equip.operational_status = "retired"
    db.commit()
    return {"status": "success", "message": f"Đã chuyển trạng thái thiết bị '{equip.name}' thành ngừng hoạt động."}
