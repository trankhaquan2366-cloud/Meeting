from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.department import Department
from app.models.project_group import ProjectGroup
from app.models.user import User
from tests.helpers import _auth_header, _create_user, _make_token


def test_admin_can_read_and_update_complete_user_profile(
    client: TestClient,
    db_session: Session,
):
    admin = _create_user(db_session, "profile-admin", role="admin")
    user = _create_user(db_session, "profile-target")
    department = Department(name="Profile department", code="PROFILE")
    group = ProjectGroup(name="Profile project", code="PROFILE-P")
    db_session.add_all([department, group])
    db_session.commit()
    headers = _auth_header(_make_token(admin))

    profile = client.get(f"/api/v1/users/{user.id}", headers=headers)

    assert profile.status_code == 200
    assert profile.json()["username"] == user.username
    assert profile.json()["department_id"] is None
    assert profile.json()["daily_booking_hours_limit"] is None

    updated = client.put(
        f"/api/v1/users/{user.id}",
        headers=headers,
        json={
            "full_name": "Updated Profile Name",
            "email": "updated.profile@example.test",
            "department_id": department.id,
            "position": "Senior Developer",
            "project_group_ids": [group.id],
            "role": "manager",
            "daily_booking_hours_limit": 3.5,
            "can_bypass_room_approval": True,
        },
    )

    assert updated.status_code == 200
    response_data = updated.json()
    assert response_data["full_name"] == "Updated Profile Name"
    assert response_data["email"] == "updated.profile@example.test"
    assert response_data["department_id"] == department.id
    assert response_data["position"] == "Senior Developer"
    assert [item["id"] for item in response_data["project_groups"]] == [group.id]
    assert response_data["role"] == "manager"
    assert response_data["daily_booking_hours_limit"] == 3.5
    assert response_data["can_bypass_room_approval"] is True


def test_user_profile_routes_require_admin_and_preserve_me_route(
    client: TestClient,
    db_session: Session,
):
    employee = _create_user(db_session, "profile-employee")
    target = _create_user(db_session, "profile-protected-target")
    headers = _auth_header(_make_token(employee))

    forbidden = client.get(f"/api/v1/users/{target.id}", headers=headers)
    own_profile = client.get("/api/v1/users/me", headers=headers)

    assert forbidden.status_code == 403
    assert own_profile.status_code == 200
    assert own_profile.json()["id"] == employee.id


def test_user_profile_rejects_unknown_department_and_project_group(
    client: TestClient,
    db_session: Session,
):
    admin = _create_user(db_session, "profile-validation-admin", role="admin")
    user = _create_user(db_session, "profile-validation-target")
    headers = _auth_header(_make_token(admin))
    payload = {
        "full_name": "Valid Profile Name",
        "email": "valid.profile@example.test",
        "department_id": 987654,
        "project_group_ids": [],
        "role": "employee",
    }

    unknown_department = client.put(
        f"/api/v1/users/{user.id}",
        headers=headers,
        json=payload,
    )
    unknown_group = client.put(
        f"/api/v1/users/{user.id}",
        headers=headers,
        json={**payload, "department_id": None, "project_group_ids": [987654]},
    )

    assert unknown_department.status_code == 400
    assert unknown_group.status_code == 400
    assert db_session.query(User).filter_by(id=user.id).one().email == user.email
