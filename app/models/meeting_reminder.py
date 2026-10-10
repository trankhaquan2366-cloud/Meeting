from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class MeetingReminder(Base):
    __tablename__ = "meeting_reminders"

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
    reminder_type = Column(String(50), nullable=False)  # '1_day' | '30_mins' | '15_mins'
    sent_at = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())

    meeting = relationship("Meeting")
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint("meeting_id", "user_id", "reminder_type", name="uq_meeting_user_reminder"),
    )

    def __repr__(self) -> str:
        return f"<MeetingReminder meeting_id={self.meeting_id} user_id={self.user_id} type={self.reminder_type}>"
