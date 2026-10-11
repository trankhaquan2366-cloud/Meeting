from fastapi import APIRouter, Query
from typing import List, Optional
from app.schemas.equipment import EquipmentStatusResponse
from app.services import equipment_service

router = APIRouter(prefix="/api/equipments", tags=["Equipments"])

@router.get("/availability", response_model=List[EquipmentStatusResponse])
def get_availability(
    start_time: str = Query(...),
    end_time: str = Query(...),
    category: Optional[str] = None,
    search: Optional[str] = None
):
    # Assuming db dependency is passed, here we mock it
    db = None 
    return equipment_service.get_equipment_availability(db, start_time, end_time, category, search)
