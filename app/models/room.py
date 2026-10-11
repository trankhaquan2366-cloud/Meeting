from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, event, func
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Mapper, relationship
from app.db.session import Base


class Room(Base):
    """Phòng họp."""

    __tablename__ = "rooms"
    default_equipments = relationship("RoomEquipment", back_populates="room", cascade="all, delete-orphan")
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True, comment="Tên phòng")
    location = Column(String(255), nullable=True, comment="Vị trí phòng")
    capacity = Column(Integer, nullable=False, default=1, comment="Sức chứa")
    description = Column(Text, nullable=True, comment="Mô tả")
    amenities = Column(Text, nullable=True, comment="Tiện ích phòng họp (JSON list)")
    is_active = Column(Boolean, nullable=False, default=True, comment="Trạng thái phòng")
    qr_token = Column(String(64), nullable=True, unique=True, index=True, default=lambda: str(uuid4()))
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())

    def generate_qr_token(self) -> str:
        """Generate a stable QR token for this room when it does not have one."""
        if not self.qr_token:
            self.qr_token = str(uuid4())
        return self.qr_token

    def __repr__(self) -> str:
        return f"<Room id={self.id} name={self.name!r}>"


@event.listens_for(Room, "before_insert")
def _ensure_room_qr_token(mapper: Mapper[Room], connection: Connection, room: Room) -> None:
    room.generate_qr_token()