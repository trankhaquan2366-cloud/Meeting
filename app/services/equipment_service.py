def get_equipment_availability(db, start_time, end_time, category=None, search=None):
    # This is a mock implementation of the requested logic since we don't have the real DB schema
    equipments = [
        {"code": "EQ001", "name": "Projector", "category": "AV", "total_qty": 5, "is_active": True},
        {"code": "EQ002", "name": "Whiteboard", "category": "Office", "total_qty": 2, "is_active": True},
        {"code": "EQ003", "name": "Microphone", "category": "AV", "total_qty": 10, "is_active": False},
    ]
    
    result = []
    for eq in equipments:
        if category and eq['category'] != category:
            continue
        if search and search.lower() not in eq['name'].lower():
            continue
            
        # Mock calculation: booked_qty from meeting_equipments and meetings (ignore CANCELLED).
        booked_qty = 1 if eq['code'] == 'EQ001' else (2 if eq['code'] == 'EQ002' else 0)
        available_qty = eq['total_qty'] - booked_qty
        
        if not eq['is_active']:
            status_label = "Ngừng hoạt động / Bảo trì"
        elif available_qty <= 0:
            status_label = "Đã đặt hết"
        else:
            status_label = "Có sẵn"
            
        result.append({
            "code": eq["code"],
            "name": eq["name"],
            "category": eq["category"],
            "total_qty": eq["total_qty"],
            "booked_qty": booked_qty,
            "available_qty": available_qty,
            "status_label": status_label
        })
    return result
