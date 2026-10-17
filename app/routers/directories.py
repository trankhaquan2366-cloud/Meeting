import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_role
from app.db.session import get_db
from app.models.department import Department
from app.models.project_group import ProjectGroup
from app.models.user import User
from app.schemas.directories import DirectoryCreate, DirectoryUpdate
from app.schemas.project_group import ProjectGroupResponse
from app.schemas.user import DepartmentSummary

router = APIRouter(tags=["Directories"])


def _slug_code(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name.lower())
    normalized = "".join(
        character for character in normalized if not unicodedata.combining(character)
    ).replace("đ", "d")
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-").upper()[:50] or "GROUP"


def _unique_group_code(db: Session, name: str, current_id: int | None = None) -> str:
    base = _slug_code(name)
    candidate = base
    suffix = 2
    while db.query(ProjectGroup.id).filter(
        ProjectGroup.code == candidate,
        ProjectGroup.id != current_id if current_id is not None else True,
    ).first():
        suffix_text = f"-{suffix}"
        candidate = f"{base[:50 - len(suffix_text)]}{suffix_text}"
        suffix += 1
    return candidate


def _unique_department_code(
    db: Session,
    name: str,
    current_id: int | None = None,
) -> str:
    base = _slug_code(name)
    candidate = base
    suffix = 2
    while db.query(Department.id).filter(
        Department.code == candidate,
        Department.id != current_id if current_id is not None else True,
    ).first():
        suffix_text = f"-{suffix}"
        candidate = f"{base[:50 - len(suffix_text)]}{suffix_text}"
        suffix += 1
    return candidate


@router.get(
    "/departments",
    response_model=list[DepartmentSummary],
    dependencies=[Depends(get_current_user)],
)
@router.get(
    "/directories/departments",
    response_model=list[DepartmentSummary],
    dependencies=[Depends(get_current_user)],
    include_in_schema=False,
)
def list_departments(db: Session = Depends(get_db)) -> list[Department]:
    return db.query(Department).order_by(Department.name, Department.id).all()


@router.post(
    "/departments",
    response_model=DepartmentSummary,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("admin"))],
)
def create_department(
    payload: DirectoryCreate,
    db: Session = Depends(get_db),
) -> Department:
    if db.query(Department.id).filter(
        func.lower(Department.name) == payload.name.lower()
    ).first():
        raise HTTPException(status_code=409, detail="Phòng ban này đã tồn tại.")
    department = Department(
        name=payload.name,
        code=_unique_department_code(db, payload.name),
    )
    db.add(department)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Mã phòng ban này đã được sử dụng.") from exc
    db.refresh(department)
    return department


@router.put(
    "/departments/{department_id}",
    response_model=DepartmentSummary,
    dependencies=[Depends(require_role("admin"))],
)
@router.patch(
    "/departments/{department_id}",
    response_model=DepartmentSummary,
    dependencies=[Depends(require_role("admin"))],
    include_in_schema=False,
)
def update_department(
    department_id: int,
    payload: DirectoryUpdate,
    db: Session = Depends(get_db),
) -> Department:
    department = db.get(Department, department_id)
    if department is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy phòng ban.")
    if db.query(Department.id).filter(
        func.lower(Department.name) == payload.name.lower(),
        Department.id != department_id,
    ).first():
        raise HTTPException(status_code=409, detail="Phòng ban này đã tồn tại.")
    department.name = payload.name
    department.code = _unique_department_code(db, payload.name, current_id=department_id)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Mã phòng ban này đã được sử dụng.") from exc
    db.refresh(department)
    return department


@router.delete(
    "/departments/{department_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role("admin"))],
)
def delete_department(department_id: int, db: Session = Depends(get_db)) -> Response:
    department = db.get(Department, department_id)
    if department is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy phòng ban.")
    db.query(User).filter(User.department_id == department_id).update(
        {User.department_id: None}, synchronize_session=False
    )
    db.delete(department)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/project-groups",
    response_model=list[ProjectGroupResponse],
    dependencies=[Depends(get_current_user)],
)
@router.get(
    "/teams",
    response_model=list[ProjectGroupResponse],
    dependencies=[Depends(get_current_user)],
    include_in_schema=False,
)
@router.get(
    "/project-teams",
    response_model=list[ProjectGroupResponse],
    dependencies=[Depends(get_current_user)],
    include_in_schema=False,
)
@router.get(
    "/directories/project-groups",
    response_model=list[ProjectGroupResponse],
    dependencies=[Depends(get_current_user)],
    include_in_schema=False,
)
def list_project_groups(db: Session = Depends(get_db)) -> list[ProjectGroup]:
    return db.query(ProjectGroup).order_by(ProjectGroup.name, ProjectGroup.id).all()


@router.post(
    "/teams",
    response_model=ProjectGroupResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("admin"))],
)
@router.post(
    "/project-teams",
    response_model=ProjectGroupResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("admin"))],
    include_in_schema=False,
)
def create_project_group(
    payload: DirectoryCreate,
    db: Session = Depends(get_db),
) -> ProjectGroup:
    if db.query(ProjectGroup.id).filter(
        func.lower(ProjectGroup.name) == payload.name.lower()
    ).first():
        raise HTTPException(status_code=409, detail="Nhóm dự án này đã tồn tại.")
    group = ProjectGroup(
        name=payload.name,
        code=_unique_group_code(db, payload.name),
    )
    db.add(group)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Mã nhóm dự án này đã được sử dụng.") from exc
    db.refresh(group)
    return group


@router.put(
    "/teams/{group_id}",
    response_model=ProjectGroupResponse,
    dependencies=[Depends(require_role("admin"))],
)
@router.put(
    "/project-teams/{group_id}",
    response_model=ProjectGroupResponse,
    dependencies=[Depends(require_role("admin"))],
    include_in_schema=False,
)
@router.patch(
    "/teams/{group_id}",
    response_model=ProjectGroupResponse,
    dependencies=[Depends(require_role("admin"))],
    include_in_schema=False,
)
def update_project_group(
    group_id: int,
    payload: DirectoryUpdate,
    db: Session = Depends(get_db),
) -> ProjectGroup:
    group = db.get(ProjectGroup, group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhóm dự án.")
    if db.query(ProjectGroup.id).filter(
        func.lower(ProjectGroup.name) == payload.name.lower(),
        ProjectGroup.id != group_id,
    ).first():
        raise HTTPException(status_code=409, detail="Nhóm dự án này đã tồn tại.")
    group.name = payload.name
    group.code = _unique_group_code(db, payload.name, current_id=group_id)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Mã nhóm dự án này đã được sử dụng.") from exc
    db.refresh(group)
    return group


@router.delete(
    "/teams/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role("admin"))],
)
@router.delete(
    "/project-teams/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role("admin"))],
    include_in_schema=False,
)
def delete_project_group(group_id: int, db: Session = Depends(get_db)) -> Response:
    group = db.get(ProjectGroup, group_id)
    if group is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhóm dự án.")
    group.users.clear()
    db.delete(group)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
