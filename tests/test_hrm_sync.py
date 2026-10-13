"""Tests for HRM department and employee synchronization."""

from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from app.models.department import Department
from app.models.user import User
from app.schemas.hrm import HRMDepartmentDTO, HRMUserDTO
from app.services.hrm_sync_service import HRMSyncService
from tests.helpers import _auth_header, _create_user, _make_token


def test_hrm_migration_adds_indexed_external_identifiers_on_sqlite(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """The migration creates the HRM columns and indexes on SQLite."""
    database_url = f"sqlite:///{(tmp_path / 'hrm-migration.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    project_root = Path(__file__).resolve().parents[1]
    config = Config(str(project_root / "alembic.ini"))

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        assert {
            "external_id",
        } <= {
            column["name"] for column in inspector.get_columns("users")
        }
        assert {
            "code",
            "external_id",
        } <= {
            column["name"] for column in inspector.get_columns("departments")
        }
        user_indexes = {
            index["name"] for index in inspector.get_indexes("users")
        }
        department_indexes = {
            index["name"] for index in inspector.get_indexes("departments")
        }
        assert "ix_users_external_id" in user_indexes
        assert {
            "ix_departments_code",
            "ix_departments_external_id",
        } <= department_indexes
    finally:
        engine.dispose()


def _set_hrm_data(
    monkeypatch,
    departments: list[HRMDepartmentDTO],
    users: list[HRMUserDTO],
) -> None:
    """Replace mock HRM records for one isolated synchronization test."""
    monkeypatch.setattr(
        HRMSyncService,
        "fetch_hrm_mock_data",
        staticmethod(lambda: (departments, users)),
    )


def test_hrm_sync_creates_departments_and_users(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    """New HRM records are created and linked by department code."""
    _set_hrm_data(
        monkeypatch,
        [HRMDepartmentDTO(external_id="dep-1", code="ENG", name="Engineering")],
        [
            HRMUserDTO(
                external_id="user-1",
                email="new.engineer@example.test",
                full_name="New Engineer",
                department_code="ENG",
                is_active=True,
            )
        ],
    )
    admin = _create_user(db_session, "hrm-sync-admin", role="admin")

    response = client.post(
        "/api/v1/admin/sync/hrm",
        headers=_auth_header(_make_token(admin)),
    )

    assert response.status_code == 200
    assert response.json() == {
        "total_departments_synced": 1,
        "total_users_synced": 1,
        "deactivated_users": 0,
        "errors": [],
    }
    department = db_session.query(Department).filter_by(code="ENG").one()
    user = db_session.query(User).filter_by(external_id="user-1").one()
    assert department.external_id == "dep-1"
    assert user.email == "new.engineer@example.test"
    assert user.full_name == "New Engineer"
    assert user.department_id == department.id
    assert user.role == "employee"
    assert user.is_active is True


def test_hrm_sync_updates_existing_user_and_preserves_admin_role(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    """Existing employee details and department are updated without demoting admins."""
    admin_department = Department(
        name="Legacy Admin Department",
        code="OLD",
        external_id="legacy-dep",
    )
    db_session.add(admin_department)
    db_session.flush()
    existing_admin = _create_user(
        db_session,
        "hrm-existing-admin",
        role="admin",
    )
    existing_admin.email = "admin@example.test"
    existing_admin.external_id = "user-admin"
    existing_admin.department_id = admin_department.id
    db_session.commit()

    _set_hrm_data(
        monkeypatch,
        [HRMDepartmentDTO(external_id="dep-new", code="NEW", name="New Department")],
        [
            HRMUserDTO(
                external_id="user-admin",
                email="admin@example.test",
                full_name="Admin Renamed",
                department_code="NEW",
                is_active=True,
            )
        ],
    )

    response = client.post(
        "/api/v1/admin/sync/hrm",
        headers=_auth_header(_make_token(existing_admin)),
    )

    assert response.status_code == 200
    db_session.refresh(existing_admin)
    new_department = db_session.query(Department).filter_by(code="NEW").one()
    assert existing_admin.full_name == "Admin Renamed"
    assert existing_admin.department_id == new_department.id
    assert existing_admin.role == "admin"


def test_hrm_sync_falls_back_to_department_code_and_user_email(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    """Legacy records without external IDs are matched by code and email."""
    department = Department(name="Old Engineering", code="ENG")
    db_session.add(department)
    db_session.flush()
    existing_user = _create_user(db_session, "hrm-email-fallback")
    existing_user.email = "fallback.engineer@example.test"
    existing_user.department_id = department.id
    db_session.commit()
    _set_hrm_data(
        monkeypatch,
        [
            HRMDepartmentDTO(
                external_id="dep-eng",
                code="ENG",
                name="Engineering",
            )
        ],
        [
            HRMUserDTO(
                external_id="user-fallback",
                email="fallback.engineer@example.test",
                full_name="Updated Engineer",
                department_code="ENG",
                is_active=True,
            )
        ],
    )
    admin = _create_user(db_session, "hrm-fallback-admin", role="admin")

    response = client.post(
        "/api/v1/admin/sync/hrm",
        headers=_auth_header(_make_token(admin)),
    )

    assert response.status_code == 200
    assert db_session.query(Department).filter_by(code="ENG").count() == 1
    assert db_session.query(User).filter_by(email="fallback.engineer@example.test").count() == 1
    db_session.refresh(department)
    db_session.refresh(existing_user)
    assert department.name == "Engineering"
    assert department.external_id == "dep-eng"
    assert existing_user.external_id == "user-fallback"
    assert existing_user.full_name == "Updated Engineer"
    assert existing_user.department_id == department.id


def test_hrm_sync_deactivates_departed_employee(
    client: TestClient,
    db_session: Session,
    monkeypatch,
) -> None:
    """Managed employees absent from active HRM records are soft-deactivated."""
    departed = _create_user(db_session, "hrm-departed-employee")
    departed.external_id = "departed-1"
    db_session.commit()
    _set_hrm_data(monkeypatch, [], [])
    admin = _create_user(db_session, "hrm-deactivation-admin", role="admin")

    response = client.post(
        "/api/v1/admin/sync/hrm",
        headers=_auth_header(_make_token(admin)),
    )

    assert response.status_code == 200
    assert response.json()["deactivated_users"] == 1
    db_session.refresh(departed)
    assert departed.is_active is False
    assert db_session.query(User).filter_by(id=departed.id).count() == 1


def test_hrm_sync_requires_admin(
    client: TestClient,
    db_session: Session,
) -> None:
    """A regular employee cannot trigger HRM synchronization."""
    employee = _create_user(db_session, "hrm-sync-employee")

    response = client.post(
        "/api/v1/admin/sync/hrm",
        headers=_auth_header(_make_token(employee)),
    )

    assert response.status_code == 403
