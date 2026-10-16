from pydantic import BaseModel, ConfigDict, Field

from app.schemas.project_group import ProjectGroupResponse


class DepartmentSummary(BaseModel):
    id: int
    name: str
    code: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ParticipantSearchResponse(BaseModel):
    id: int
    username: str
    external_id: str | None = None
    email: str | None = None
    full_name: str | None = None
    position: str | None = None
    department: DepartmentSummary | None = None
    project_groups: list[ProjectGroupResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    id: int
    username: str
    email: str | None
    full_name: str | None
    role: str
    is_active: bool
    position: str | None = None
    project_groups: list[ProjectGroupResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
