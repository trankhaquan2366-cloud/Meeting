from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Equipment(Base):
    __tablename__ = "equipments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    # Expected values include available and maintenance.
    status = Column(String(30), nullable=False, default="available", server_default="available")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())

    meeting_links = relationship(
        "MeetingEquipment",
        back_populates="equipment",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Equipment id={self.id} name={self.name!r}>"


class MeetingEquipment(Base):
    __tablename__ = "meeting_equipments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    meeting_id = Column(
        Integer,
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    equipment_id = Column(
        Integer,
        ForeignKey("equipments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    meeting = relationship("Meeting", back_populates="equipment_links")
    equipment = relationship("Equipment", back_populates="meeting_links")

    __table_args__ = (
        UniqueConstraint("meeting_id", "equipment_id", name="uq_meeting_equipment"),
    )

    def __repr__(self) -> str:
        return f"<MeetingEquipment meeting_id={self.meeting_id} equipment_id={self.equipment_id}>"
