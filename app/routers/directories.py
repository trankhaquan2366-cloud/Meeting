from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.department import Department
from app.models.project_group import ProjectGroup
from app.schemas.project_group import ProjectGroupResponse
from app.schemas.user import DepartmentSummary

router = APIRouter(tags=["Directories"])


@router.get(
    "/departments",
    response_model=list[DepartmentSummary],
    dependencies=[Depends(get_current_user)],
)
def list_departments(db: Session = Depends(get_db)) -> list[Department]:
    return db.query(Department).order_by(Department.name, Department.id).all()


@router.get(
    "/project-groups",
    response_model=list[ProjectGroupResponse],
    dependencies=[Depends(get_current_user)],
)
def list_project_groups(db: Session = Depends(get_db)) -> list[ProjectGroup]:
    return db.query(ProjectGroup).order_by(ProjectGroup.name, ProjectGroup.id).all()
