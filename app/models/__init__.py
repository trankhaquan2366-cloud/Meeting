# app/models/__init__.py

from app.core.database import Base
from app.models.user import User
from app.models.department import Department
from app.models.room import Room
from app.models.meeting import Meeting
from app.models.equipment import Equipment, MeetingEquipment, RoomEquipment

__all__ = [
    "Base",
    "User",
    "Department",
    "Room",
    "Meeting",
    "Equipment",
    "MeetingEquipment",
    "RoomEquipment",
]