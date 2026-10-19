from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from fastapi import HTTPException, status
from sqlalchemy import func

from app.models.equipment import Equipment, MeetingEquipment
from app.models.meeting import Meeting


def _coerce_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if value is None:
        return datetime.utcnow()
    if isinstance(value, str):
        value = value.strip()
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    raise TypeError(f"Unsupported datetime value: {type(value)!r}")


def _mock_equipment_catalog():
    return [
        {"id": 1, "code": "EQ001", "name": "Projector", "category": "Visual", "search_keywords": "projector, máy chiếu", "operational_status": "active", "total_qty": 5, "is_active": True},
        {"id": 2, "code": "EQ002", "name": "Whiteboard", "category": "Accessory", "search_keywords": "whiteboard, bảng trắng", "operational_status": "active", "total_qty": 2, "is_active": True},
        {"id": 3, "code": "EQ003", "name": "Microphone", "category": "Audio", "search_keywords": "mic, microphone", "operational_status": "maintenance", "total_qty": 10, "is_active": False},
    ]


def _mock_booked_qty(eq_name: str) -> int:
    if eq_name == "Projector":
        return 1
    if eq_name == "Whiteboard":
        return 2
    return 0


def _normalize_requested_equipments(requested_equipments: Iterable[Any] | None) -> dict[int, int]:
    normalized: dict[int, int] = {}
    if not requested_equipments:
        return normalized

    for item in requested_equipments:
        if isinstance(item, dict):
            equipment_id = item.get("equipment_id")
            quantity = item.get("quantity", 0)
        else:
            equipment_id = getattr(item, "equipment_id", None)
            quantity = getattr(item, "quantity", 0)

        if equipment_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Thiết bị mượn thiếu equipment_id.",
            )
        try:
            equipment_id = int(equipment_id)
            quantity = int(quantity)
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Số lượng và mã thiết bị mượn phải là số nguyên hợp lệ.",
            ) from exc

        if equipment_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mã thiết bị mượn không hợp lệ.",
            )
        if quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Số lượng thiết bị mượn không được âm.",
            )
        if quantity == 0:
            continue
        normalized[equipment_id] = normalized.get(equipment_id, 0) + quantity
    return normalized


def _booked_equipment_quantity(db, equipment_id: int, start_time: datetime, end_time: datetime) -> int:
    if db is None:
        return _mock_booked_qty(next(
            (item["name"] for item in _mock_equipment_catalog() if item["code"] == str(equipment_id) or item["name"] == str(equipment_id)),
            "",
        ))

    overlap = (
        db.query(func.coalesce(func.sum(MeetingEquipment.quantity), 0))
        .join(Meeting, Meeting.id == MeetingEquipment.meeting_id)
        .filter(
            MeetingEquipment.equipment_id == equipment_id,
            func.upper(Meeting.status).notin_(
                ["CANCELLED", "CANCELED", "CANCELLED_NO_SHOW", "COMPLETED"]
            ),
            Meeting.start_time < end_time,
            Meeting.end_time > start_time,
        )
        .scalar()
    )
    return int(overlap or 0)


def get_equipment_availability(
    db,
    start_time,
    end_time,
    category=None,
    search=None,
    active_only=False,
    operational_status_filter=None,
):
    if db is None:
        equipments = _mock_equipment_catalog()
    else:
        start_time = _coerce_datetime(start_time)
        end_time = _coerce_datetime(end_time)
        query = db.query(Equipment)
        if active_only:
            query = query.filter(Equipment.is_active.is_(True))
        if category and category != "other":
            query = query.filter(Equipment.category == category)
        elif category == "other":
            query = query.filter(
                Equipment.category.notin_(["Visual", "Audio", "Cable", "Network", "Accessory"])
                | Equipment.category.is_(None)
            )
        if operational_status_filter:
            query = query.filter(Equipment.operational_status == operational_status_filter)
        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                Equipment.name.ilike(term)
                | Equipment.code.ilike(term)
                | Equipment.category.ilike(term)
                | Equipment.search_keywords.ilike(term)
            )
        equipments = query.all()

    result = []
    for eq in equipments:
        if isinstance(eq, dict):
            equipment_id = eq.get("id")
            code = eq.get("code")
            name = eq.get("name")
            category_name = eq.get("category")
            search_keywords = eq.get("search_keywords")
            operational_status = eq.get("operational_status", "active" if eq.get("is_active", True) else "retired")
            total_qty = int(eq.get("total_qty") or 0)
            is_active = bool(eq.get("is_active", True))
        else:
            equipment_id = eq.id
            code = eq.code
            name = eq.name
            category_name = eq.category
            search_keywords = eq.search_keywords
            operational_status = eq.operational_status
            total_qty = int(eq.total_qty or 0)
            is_active = bool(eq.is_active)

        if category and category != "other" and category != category_name:
            continue
        if category == "other" and category_name in {"Visual", "Audio", "Cable", "Network", "Accessory"}:
            continue
        if operational_status_filter and operational_status_filter != operational_status:
            continue
        searchable_text = " ".join(
            str(value or "")
            for value in (name, code, category_name, search_keywords)
        ).casefold()
        if search and search.strip().casefold() not in searchable_text:
            continue

        if db is None:
            booked_qty = _mock_booked_qty(name)
        else:
            booked_qty = _booked_equipment_quantity(db, eq.id, _coerce_datetime(start_time), _coerce_datetime(end_time))
        available_qty = max(total_qty - booked_qty, 0)

        if operational_status == "maintenance":
            status_label = "Đang bảo trì"
        elif operational_status == "retired" or not is_active:
            status_label = "Ngưng sử dụng"
        elif available_qty <= 0:
            status_label = "Đã đặt hết"
        else:
            status_label = "Có sẵn"

        result.append({
            "id": equipment_id,
            "code": code,
            "name": name,
            "category": category_name,
            "search_keywords": search_keywords,
            "operational_status": operational_status,
            "total_qty": total_qty,
            "booked_qty": booked_qty,
            "available_qty": available_qty,
            "total_quantity": total_qty,
            "allocated_quantity": booked_qty,
            "available_quantity": available_qty,
            "is_active": is_active,
            "status_label": status_label,
        })
    return result


def check_equipment_availability(
    db,
    equipment_id: int,
    start_time: datetime,
    end_time: datetime,
    requested_qty: int,
) -> int:
    start_time = _coerce_datetime(start_time)
    end_time = _coerce_datetime(end_time)
    if end_time <= start_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thời gian kết thúc phải sau thời gian bắt đầu.",
        )
    try:
        equipment_id = int(equipment_id)
        requested_qty = int(requested_qty)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Số lượng và mã thiết bị phải là số nguyên hợp lệ.",
        ) from exc
    if equipment_id <= 0 or requested_qty < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã thiết bị hoặc số lượng thiết bị không hợp lệ.",
        )

    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if equipment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Thiết bị ID {equipment_id} không tồn tại.",
        )
    if not equipment.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Thiết bị '{equipment.name}' hiện đã ngừng hoạt động và không thể mượn.",
        )

    allocated_qty = _booked_equipment_quantity(
        db, equipment_id, start_time, end_time
    )
    return max(int(equipment.total_qty or 0) - allocated_qty, 0)


def validate_requested_equipments(db, start_time, end_time, requested_equipments):
    if not requested_equipments:
        return []

    start_time = _coerce_datetime(start_time)
    end_time = _coerce_datetime(end_time)
    if start_time > end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thời gian bắt đầu phải nhỏ hơn hoặc bằng thời gian kết thúc.",
        )

    normalized = _normalize_requested_equipments(requested_equipments)
    for equipment_id, requested_qty in sorted(normalized.items()):
        equipment = (
            db.query(Equipment)
            .filter(Equipment.id == equipment_id)
            .with_for_update()
            .first()
        )
        if equipment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Thiết bị ID {equipment_id} không tồn tại.",
            )
        if not equipment.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Thiết bị '{equipment.name}' hiện đã ngừng hoạt động và không thể mượn.",
            )

        available_qty = check_equipment_availability(
            db, equipment_id, start_time, end_time, requested_qty
        )
        if requested_qty > available_qty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Thiết bị '{equipment.name}' chỉ còn {available_qty} chiếc khả dụng "
                    f"trong khung thời gian này. Bạn yêu cầu {requested_qty}."
                ),
            )

    return []
