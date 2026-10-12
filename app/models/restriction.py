from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text, UniqueConstraint, func

from app.core.database import Base


class UserRoomRestriction(Base):
    """A room that a user is not allowed to book."""

    __tablename__ = "user_room_restrictions"
    __table_args__ = (
        UniqueConstraint("user_id", "room_id", name="uq_user_room_restriction"),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    room_id = Column(
        Integer,
        ForeignKey("rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
