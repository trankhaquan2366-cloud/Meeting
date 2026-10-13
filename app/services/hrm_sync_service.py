"""Synchronize departments and employees from the HRM source."""

import secrets

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.department import Department
from app.models.user import User
from app.schemas.hrm import HRMDepartmentDTO, HRMUserDTO, HRMSyncResponse


class HRMSyncService:
    """Apply HRM data to RoomSync using an atomic upsert transaction."""

    @staticmethod
    def fetch_hrm_mock_data() -> tuple[
        list[HRMDepartmentDTO], list[HRMUserDTO]
    ]:
        """Return representative department and employee records from a mock HRM."""
        departments = [
            HRMDepartmentDTO(
                external_id="hrm-dept-001",
                code="ENG",
                name="Engineering",
            ),
            HRMDepartmentDTO(
                external_id="hrm-dept-002",
                code="HR",
                name="Human Resources",
            ),
        ]
        users = [
            HRMUserDTO(
                external_id="hrm-user-001",
                email="alex.engineer@example.test",
                full_name="Alex Engineer",
                department_code="ENG",
                is_active=True,
            ),
            HRMUserDTO(
                external_id="hrm-user-002",
                email="sam.hr@example.test",
                full_name="Sam HR",
                department_code="HR",
                is_active=True,
            ),
        ]
        return departments, users

    @staticmethod
    def _get_or_create_username(db: Session, email: str) -> str:
        """Build an available RoomSync username for a newly imported employee."""
        base_username = email.split("@", maxsplit=1)[0][:50] or "hrm-user"
        username = base_username
        suffix = 1
        while db.query(User.id).filter(User.username == username).first() is not None:
            suffix_text = str(suffix)
            username = f"{base_username[:50 - len(suffix_text)]}{suffix_text}"
            suffix += 1
        return username

    @classmethod
    def sync_hrm_data(cls, db: Session) -> HRMSyncResponse:
        """Upsert HRM departments and employees, deactivating departed employees.

        All changes are committed together. Any failure rolls back the complete
        synchronization so a partial HRM import cannot be mistaken for success.
        """
        try:
            departments, users = cls.fetch_hrm_mock_data()
            departments_by_code: dict[str, Department] = {}

            for department_data in departments:
                department = (
                    db.query(Department)
                    .filter(Department.external_id == department_data.external_id)
                    .first()
                )
                if department is None:
                    department = (
                        db.query(Department)
                        .filter(Department.code == department_data.code)
                        .first()
                    )
                if department is None:
                    department = Department()
                    db.add(department)

                department.external_id = department_data.external_id
                department.code = department_data.code
                department.name = department_data.name
                departments_by_code[department_data.code] = department

            db.flush()
            total_users_synced = 0
            for user_data in users:
                department = departments_by_code.get(user_data.department_code)
                if department is None:
                    department = (
                        db.query(Department)
                        .filter(Department.code == user_data.department_code)
                        .first()
                    )
                if department is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            "Không tìm thấy phòng ban HRM với mã "
                            f"'{user_data.department_code}'."
                        ),
                    )

                user = (
                    db.query(User)
                    .filter(User.external_id == user_data.external_id)
                    .first()
                )
                if user is None:
                    user = (
                        db.query(User)
                        .filter(User.email == user_data.email)
                        .first()
                    )
                if user is None:
                    user = User(
                        username=cls._get_or_create_username(db, user_data.email),
                        hashed_password=hash_password(secrets.token_urlsafe(32)),
                        role="employee",
                    )
                    db.add(user)

                user.external_id = user_data.external_id
                user.email = user_data.email
                user.full_name = user_data.full_name
                user.department = department
                user.is_active = user_data.is_active
                total_users_synced += 1

            active_external_ids = {
                user_data.external_id for user_data in users if user_data.is_active
            }
            deactivated_users = 0
            managed_users = (
                db.query(User)
                .filter(User.external_id.is_not(None))
                .all()
            )
            for user in managed_users:
                if user.external_id not in active_external_ids and user.is_active:
                    user.is_active = False
                    deactivated_users += 1

            db.commit()
            return HRMSyncResponse(
                total_departments_synced=len(departments),
                total_users_synced=total_users_synced,
                deactivated_users=deactivated_users,
                errors=[],
            )
        except Exception:
            db.rollback()
            raise
