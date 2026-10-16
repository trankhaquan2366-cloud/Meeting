from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProjectGroupResponse(BaseModel):
    id: int
    name: str
    code: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
