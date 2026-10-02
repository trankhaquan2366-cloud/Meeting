from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from app.models.equipment import Equipment, MeetingEquipment
from app.models.meeting import Meeting
from app.schemas.equipment import EquipmentResponse, EquipmentStatusResponse, MeetingEquipmentItemInput


def get_equipment_availability(
    db: Session,
    start_time: datetime,
    end_time: datetime,
    category: Optional[str] = None,
    search: Optional[str] = None,
) -> List[EquipmentStatusResponse]:
    booked_quantities = (
        db.query(
            MeetingEquipment.equipment_id.label("equipment_id"),
            func.sum(MeetingEquipment.quantity).label("booked_qty"),
        )
        .join(Meeting, MeetingEquipment.meeting_id == Meeting.id)
        .filter(
            func.upper(Meeting.status) != "CANCELLED",
            Meeting.start_time < end_time,
            Meeting.end_time > start_time,
        )
        .group_by(MeetingEquipment.equipment_id)
        .subquery()
    )

    query = (
        db.query(Equipment, func.coalesce(booked_quantities.c.booked_qty, 0))
        .outerjoin(booked_quantities, Equipment.id == booked_quantities.c.equipment_id)
    )
    if category:
        query = query.filter(Equipment.category == category)
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            Equipment.name.ilike(search_term) | Equipment.code.ilike(search_term)
        )

    results = []
    for equipment, booked_qty in query.order_by(Equipment.name).all():
        booked_qty = int(booked_qty)
        available_qty = equipment.total_qty - booked_qty
        if not equipment.is_active:
            status_label = "Ngừng hoạt động / Bảo trì"
        elif available_qty <= 0:
            status_label = "Đã đặt hết"
        else:
            status_label = "Có sẵn"

        response_data = EquipmentResponse.model_validate(equipment).model_dump()
        response_data.update(
            {
                "booked_qty": booked_qty,
                "available_qty": available_qty,
                "status_label": status_label,
            }
        )
        results.append(EquipmentStatusResponse.model_validate(response_data))
    return results

def check_equipment_availability(
    db: Session,
    start_time: datetime,
    end_time: datetime,
    requested_items: List[MeetingEquipmentItemInput],
    exclude_meeting_id: Optional[int] = None
):

    """
    Tính toán số lượng khả dụng = Tổng tồn kho - Số lượng đã đặt trong các cuộc họp trùng khung giờ
    """
    for item in requested_items:
        # 1. Lấy thông tin thiết bị
        equip = db.query(Equipment).filter(Equipment.id == item.equipment_id, Equipment.is_active == True).first()
        if not equip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Thiết bị với ID {item.equipment_id} không tồn tại hoặc đã bị vô hiệu hóa."
            )

        # 2. Truy vấn tổng số lượng thiết bị này đã được đặt ở các cuộc họp khác trùng thời gian
        # Điều kiện trùng giờ: (Meeting.start_time < end_time) AND (Meeting.end_time > start_time)
        query = (
            db.query(func.coalesce(func.sum(MeetingEquipment.quantity), 0))
            .join(Meeting, MeetingEquipment.meeting_id == Meeting.id)
            .filter(
                MeetingEquipment.equipment_id == item.equipment_id,
                Meeting.status != "CANCELLED",  # Bỏ qua cuộc họp đã hủy
                Meeting.start_time < end_time,
                Meeting.end_time > start_time
            )
        )

        if exclude_meeting_id:
            query = query.filter(Meeting.id != exclude_meeting_id)

        booked_qty = query.scalar() or 0
        available_qty = equip.total_qty - booked_qty

        if item.quantity > available_qty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Thiết bị '{equip.name}' không đủ số lượng trong khung giờ này. "
                       f"Yêu cầu: {item.quantity}, Khả dụng: {available_qty} (Tổng: {equip.total_qty}, Đã đặt: {booked_qty})."
            )