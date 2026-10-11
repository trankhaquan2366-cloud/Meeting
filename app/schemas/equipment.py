from pydantic import BaseModel
from typing import Optional

class EquipmentStatusResponse(BaseModel):
    code: str
    name: str
    category: str
    total_qty: int
    booked_qty: int
    available_qty: int
    status_label: str
