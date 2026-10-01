from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func
from sqlalchemy.orm import relationship
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
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Room id={self.id} name={self.name!r}>"