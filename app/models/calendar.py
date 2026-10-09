from sqlalchemy import (
    Boolean,
    CheckConstraint,
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


class UserCalendarToken(Base):
    __tablename__ = "user_calendar_tokens"
    __table_args__ = (
        CheckConstraint(
            "provider IN ('google', 'outlook')",
            name="ck_user_calendar_tokens_provider",
        ),
        UniqueConstraint(
            "user_id",
            "provider",
            name="uq_user_calendar_tokens_user_provider",
        ),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider = Column(String(20), nullable=False)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())


class UserCalendarEvent(Base):
    __tablename__ = "user_calendar_events"
    __table_args__ = (
        CheckConstraint(
            "provider IN ('google', 'outlook')",
            name="ck_user_calendar_events_provider",
        ),
        UniqueConstraint(
            "meeting_id",
            "user_id",
            "provider",
            name="uq_user_calendar_events_meeting_user_provider",
        ),
    )

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
    provider = Column(String(20), nullable=False)
    external_event_id = Column(String(512), nullable=False)
    external_series_event_id = Column(String(512), nullable=True)
    external_occurrence_id = Column(String(512), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())

    meeting = relationship("Meeting")
    user = relationship("User")
