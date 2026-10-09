# app/models/meeting.py
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    # meeting_type: 'online' | 'offline' — online meetings do not require a room
    meeting_type = Column(String(20), nullable=False, default="offline", server_default="offline")
    # online_link: used when meeting_type == 'online'
    online_link = Column(String(500), nullable=True)
    is_recurring = Column(Boolean, nullable=False, default=False, server_default="0")
    recurring_type = Column(String(20), nullable=True)
    recurring_series_id = Column(String(36), nullable=True, index=True)
    recurrence_original_start = Column(DateTime, nullable=True)
    recurrence_is_detached = Column(Boolean, nullable=False, default=False, server_default="0")
    # room_id is nullable: online meetings have no room
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True, index=True)
    organizer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(
        String(20),
        nullable=False,
        default="CONFIRMED",
        server_default="CONFIRMED",
    )
    is_reminded_24h = Column(Boolean, nullable=False, default=False, server_default="0")
    is_reminded_15m = Column(Boolean, nullable=False, default=False, server_default="0")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())

    # Relationships
    equipments = relationship("MeetingEquipment", back_populates="meeting", cascade="all, delete-orphan")
    room = relationship("Room", lazy="joined")
    organizer = relationship("User", lazy="joined")
    participants = relationship(
        "MeetingParticipant",
        back_populates="meeting",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Meeting id={self.id} title={self.title!r}>"


class MeetingParticipant(Base):
    __tablename__ = "meeting_participants"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    meeting_id = Column(
        Integer,
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    meeting = relationship("Meeting", back_populates="participants")
    user = relationship("User", lazy="joined")

    __table_args__ = (
        UniqueConstraint("meeting_id", "user_id", name="uq_meeting_participant"),
    )

    def __repr__(self) -> str:
        return f"<MeetingParticipant meeting_id={self.meeting_id} user_id={self.user_id}>"