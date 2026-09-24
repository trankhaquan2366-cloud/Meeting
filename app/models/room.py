from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func

from app.core.database import Base


class Room(Base):
    """Model đại diện cho phòng họp trong hệ thống."""

    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True, comment="Tên phòng họp")
    capacity = Column(Integer, nullable=False, default=10, comment="Sức chứa tối đa")
    location = Column(String(255), nullable=True, comment="Vị trí/Tầng")
    description = Column(Text, nullable=True, comment="Mô tả/Trang thiết bị phòng họp")
    is_active = Column(Boolean, nullable=False, default=True, comment="Trạng thái phòng")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Room id={self.id} name={self.name!r}>"