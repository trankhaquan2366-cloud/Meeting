from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from app.models.department import Department
from app.models.project_group import ProjectGroup
from app.services.user_service import search_participants
from tests.helpers import _create_user


def test_project_group_migration_preserves_existing_user_data(
    tmp_path: Path,
    monkeypatch,
):
    database_url = f"sqlite:///{(tmp_path / 'project-groups.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    project_root = Path(__file__).resolve().parents[1]
    config = Config(str(project_root / "alembic.ini"))
    command.upgrade(config, "d2e5f8a1c930")

    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO departments (name, code) "
                    "VALUES ('Engineering', 'ENG')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO users "
                    "(username, hashed_password, role, is_active, department_id) "
                    "VALUES ('existing-user', 'hashed-password', 'employee', 1, 1)"
                )
            )

        command.upgrade(config, "head")

        inspector = inspect(engine)
        assert "position" in {
            column["name"] for column in inspector.get_columns("users")
        }
        assert {"project_groups", "user_project_groups"} <= set(
            inspector.get_table_names()
        )
        with engine.connect() as connection:
            user = connection.execute(
                text(
                    "SELECT username, department_id FROM users "
                    "WHERE username = 'existing-user'"
                )
            ).one()
        assert tuple(user) == ("existing-user", 1)
    finally:
        engine.dispose()


def _create_department(db: Session, name: str, code: str) -> Department:
    department = Department(name=name, code=code)
    db.add(department)
    db.commit()
    db.refresh(department)
    return department


def _create_project_group(db: Session, name: str, code: str) -> ProjectGroup:
    group = ProjectGroup(name=name, code=code)
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


def test_search_participants_filters_by_department_code(db_session: Session):
    engineering = _create_department(db_session, "Engineering", "ENG")
    hr = _create_department(db_session, "Human Resources", "HR")
    engineer = _create_user(db_session, "department-engineer")
    hr_user = _create_user(db_session, "department-hr")
    engineer.department = engineering
    hr_user.department = hr
    db_session.commit()

    result = search_participants(db_session, department_code="ENG")

    assert [user.id for user in result] == [engineer.id]


def test_search_participants_filters_by_project_group(db_session: Session):
    backend = _create_project_group(db_session, "Backend", "BACKEND")
    design = _create_project_group(db_session, "Design", "DESIGN")
    backend_user = _create_user(db_session, "group-backend")
    design_user = _create_user(db_session, "group-design")
    backend_user.project_groups.append(backend)
    design_user.project_groups.append(design)
    db_session.commit()

    result = search_participants(db_session, group_code="BACKEND")

    assert [user.id for user in result] == [backend_user.id]


def test_search_participants_filters_by_position(db_session: Session):
    manager = _create_user(db_session, "position-manager")
    employee = _create_user(db_session, "position-employee")
    manager.position = "Engineering Manager"
    employee.position = "Software Engineer"
    db_session.commit()

    result = search_participants(db_session, position="manager")

    assert [user.id for user in result] == [manager.id]


def test_search_participants_filters_by_specialist_category(db_session: Session):
    specialist = _create_user(db_session, "position-specialist")
    manager = _create_user(db_session, "position-category-manager")
    specialist.position = "Chuyên viên Kế toán"
    manager.position = "Trưởng phòng Kế toán"
    db_session.commit()

    result = search_participants(db_session, position="specialist")

    assert [user.id for user in result] == [specialist.id]


def test_search_participants_removes_duplicates_from_keyword_joins(
    db_session: Session,
):
    group_one = _create_project_group(db_session, "Platform Operations", "OPS-1")
    group_two = _create_project_group(db_session, "Operations Support", "OPS-2")
    user = _create_user(db_session, "keyword-multiple-groups")
    user.project_groups.extend([group_one, group_two])
    inactive_user = _create_user(db_session, "keyword-inactive")
    inactive_user.is_active = False
    inactive_user.project_groups.extend([group_one, group_two])
    db_session.commit()

    result = search_participants(db_session, keyword="operations")

    assert [item.id for item in result] == [user.id]
