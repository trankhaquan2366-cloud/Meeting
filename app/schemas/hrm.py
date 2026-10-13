"""Data transfer objects for HRM synchronization."""

from pydantic import BaseModel


class HRMDepartmentDTO(BaseModel):
    """Department record received from the external HRM system."""

    external_id: str
    code: str
    name: str


class HRMUserDTO(BaseModel):
    """Employee record received from the external HRM system."""

    external_id: str
    email: str
    full_name: str
    department_code: str
    is_active: bool


class HRMSyncResponse(BaseModel):
    """Summary of a completed HRM synchronization transaction."""

    total_departments_synced: int
    total_users_synced: int
    deactivated_users: int
    errors: list[str]
