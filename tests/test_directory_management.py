from sqlalchemy.orm import Session, sessionmaker

from app.main import seed_initial_directories
from app.models.department import Department
from app.models.project_group import ProjectGroup
from app.models.user import User
from app.schemas.users import AdminUserCreate
from tests.helpers import _auth_header, _create_user, _make_token


def test_user_creation_normalizes_vietnamese_username():
    payload = AdminUserCreate(
        full_name="Nguyễn Văn An",
        email="an@example.test",
        username="  Nguyễn Văn A  ",
    )

    assert payload.username == "nguyenvana"


def test_directory_management_requires_admin_and_supports_crud(
    client,
    db_session: Session,
):
    employee = _create_user(db_session, "directory-employee")
    admin = _create_user(db_session, "directory-admin", role="admin")
    employee_headers = _auth_header(_make_token(employee))
    admin_headers = _auth_header(_make_token(admin))

    assert client.get("/api/departments").status_code == 401
    assert client.get("/api/departments", headers=employee_headers).status_code == 200
    assert client.get("/api/teams", headers=employee_headers).status_code == 200
    assert client.get("/api/directories/departments").status_code == 401
    assert client.get(
        "/api/v1/directories/departments",
        headers=employee_headers,
    ).status_code == 200
    assert client.post(
        "/api/departments",
        json={"name": "Phòng Sản phẩm"},
        headers=employee_headers,
    ).status_code == 403
    assert client.post(
        "/api/teams",
        json={"name": "Dự án Sản phẩm"},
        headers=employee_headers,
    ).status_code == 403

    department_response = client.post(
        "/api/departments",
        json={"name": "Phòng Sản phẩm"},
        headers=admin_headers,
    )
    group_response = client.post(
        "/api/teams",
        json={"name": "Dự án Sản phẩm"},
        headers=admin_headers,
    )
    assert department_response.status_code == 201
    assert group_response.status_code == 201
    department = department_response.json()
    group = group_response.json()
    assert department["name"] == "Phòng Sản phẩm"
    assert department["code"] == "PHONG-SAN-PHAM"
    assert group["code"] == "DU-AN-SAN-PHAM"
    assert client.get("/api/v1/directories/project-groups", headers=admin_headers).status_code == 200
    assert client.put(
        f"/api/departments/{department['id']}",
        json={"name": "Unauthorized department edit"},
        headers=employee_headers,
    ).status_code == 403
    assert client.delete(
        f"/api/departments/{department['id']}",
        headers=employee_headers,
    ).status_code == 403
    assert client.put(
        f"/api/teams/{group['id']}",
        json={"name": "Unauthorized team edit"},
        headers=employee_headers,
    ).status_code == 403
    assert client.delete(
        f"/api/teams/{group['id']}",
        headers=employee_headers,
    ).status_code == 403

    department_user = _create_user(db_session, "directory-department-user")
    department_user.department_id = department["id"]
    group_user = _create_user(db_session, "directory-group-user")
    group_user.project_groups.append(db_session.get(ProjectGroup, group["id"]))
    db_session.commit()

    updated_department = client.put(
        f"/api/departments/{department['id']}",
        json={"name": "Phòng Sản phẩm số"},
        headers=admin_headers,
    )
    updated_group = client.put(
        f"/api/teams/{group['id']}",
        json={"name": "Dự án Sản phẩm số"},
        headers=admin_headers,
    )
    assert updated_department.status_code == 200
    assert updated_department.json()["name"] == "Phòng Sản phẩm số"
    assert updated_group.status_code == 200
    assert updated_group.json()["name"] == "Dự án Sản phẩm số"

    assert client.delete(
        f"/api/departments/{department['id']}",
        headers=admin_headers,
    ).status_code == 204
    assert client.delete(
        f"/api/teams/{group['id']}",
        headers=admin_headers,
    ).status_code == 204
    db_session.refresh(department_user)
    db_session.refresh(group_user)
    assert department_user.department_id is None
    assert group_user.project_groups == []


def test_startup_directory_seed_is_idempotent_and_preserves_existing_data(
    db_session: Session,
    monkeypatch,
):
    import app.main

    db_session.add(Department(name="Existing department", code="EXISTING"))
    db_session.commit()
    monkeypatch.setattr(
        app.main,
        "SessionLocal",
        sessionmaker(bind=db_session.get_bind()),
    )

    seed_initial_directories(force=True)
    seed_initial_directories(force=True)

    assert db_session.query(Department).count() == 1
    assert db_session.query(ProjectGroup).count() == 3
    assert {
        group.name for group in db_session.query(ProjectGroup).all()
    } == {
        "Dự án RoomSync",
        "Dự án AI Assistant",
        "Dự án Chuyển đổi số",
    }


def test_startup_directory_seed_populates_empty_tables(db_session: Session, monkeypatch):
    import app.main

    monkeypatch.setattr(
        app.main,
        "SessionLocal",
        sessionmaker(bind=db_session.get_bind()),
    )

    seed_initial_directories(force=True)
    seed_initial_directories(force=True)

    assert {
        department.name for department in db_session.query(Department).all()
    } == {
        "Phòng Công nghệ thông tin",
        "Phòng Nhân sự",
        "Phòng Kế toán",
        "Phòng Kinh doanh",
        "Phòng Ban Giám đốc",
    }
    assert {
        group.name for group in db_session.query(ProjectGroup).all()
    } == {
        "Dự án RoomSync",
        "Dự án AI Assistant",
        "Dự án Chuyển đổi số",
    }
