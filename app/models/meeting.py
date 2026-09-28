from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from app.core.database import Base


class Meeting(Base):
    """Model đại diện cho lịch họp trong hệ thống."""

    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(200), nullable=False, index=True, comment="Tiêu đề cuộc họp")
    description = Column(Text, nullable=True, comment="Nội dung cuộc họp")
    is_recurring = Column(Boolean, nullable=False, default=False, comment="Có phải lịch định kỳ không")
    recurring_type = Column(String(20), nullable=True, comment="Loại định kỳ: weekly, monthly...")
    room_id = Column(
        Integer,
        ForeignKey("rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Phòng họp",
    )
    organizer_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Người tổ chức",
    )
    
    start_time = Column(DateTime, nullable=False, comment="Thời gian bắt đầu")
    end_time = Column(DateTime, nullable=False, comment="Thời gian kết thúc")
    status = Column(String(20), nullable=False, default="scheduled", comment="Trạng thái")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())

    # Quan hệ nối bảng với eager loading
    room = relationship("Room", lazy="joined")
    organizer = relationship("User", lazy="joined")

    def __repr__(self) -> str:
        return f"<Meeting id={self.id} title={self.title!r}>"