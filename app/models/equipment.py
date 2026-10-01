from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base

class Equipment(Base):
    __tablename__ = "equipments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    code = Column(String(50), unique=True, nullable=True)
    category = Column(String(50), nullable=True)
    total_qty = Column(Integer, nullable=False, default=1)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    meeting_allocations = relationship("MeetingEquipment", back_populates="equipment")
    room_defaults = relationship("RoomEquipment", back_populates="equipment")


class MeetingEquipment(Base):
    __tablename__ = "meeting_equipments"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    equipment_id = Column(Integer, ForeignKey("equipments.id", ondelete="RESTRICT"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    note = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    meeting = relationship("Meeting", back_populates="equipments")
    equipment = relationship("Equipment", back_populates="meeting_allocations")

    __table_args__ = (UniqueConstraint('meeting_id', 'equipment_id', name='uq_meeting_equipment'),)


class RoomEquipment(Base):
    __tablename__ = "room_equipments"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    equipment_id = Column(Integer, ForeignKey("equipments.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)

    room = relationship("Room", back_populates="default_equipments")
    equipment = relationship("Equipment", back_populates="room_defaults")

    __table_args__ = (UniqueConstraint('room_id', 'equipment_id', name='uq_room_equipment'),)