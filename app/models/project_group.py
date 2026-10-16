from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, func
from sqlalchemy.orm import relationship

from app.core.database import Base


user_project_groups = Table(
    "user_project_groups",
    Base.metadata,
    Column(
        "user_id",
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "project_group_id",
        Integer,
        ForeignKey("project_groups.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class ProjectGroup(Base):
    __tablename__ = "project_groups"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(120), nullable=False)
    code = Column(String(50), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    users = relationship(
        "User",
        secondary=user_project_groups,
        back_populates="project_groups",
    )

    def __repr__(self) -> str:
        return f"<ProjectGroup id={self.id} code={self.code!r}>"
