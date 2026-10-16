from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.department import Department
from app.models.project_group import ProjectGroup
from tests.helpers import _auth_header, _create_user, _make_token


def test_participant_directory_endpoints_require_authentication(client: TestClient):
    assert client.get("/api/v1/departments").status_code == 401
    assert client.get("/api/v1/project-groups").status_code == 401
    assert client.get("/api/v1/users/search").status_code == 401


def test_participant_search_and_filter_directories(client: TestClient, db_session: Session):
    organizer = _create_user(db_session, "directory-organizer")
    department = Department(name="Finance", code="FIN")
    group = ProjectGroup(name="Mobile", code="MOBILE")
    participant = _create_user(db_session, "directory-participant")
    participant.full_name = "Mobile Manager"
    participant.external_id = "EMP-1001"
    participant.position = "Engineering Manager"
    participant.department = department
    participant.project_groups.append(group)
    db_session.add_all([department, group])
    db_session.commit()

    headers = _auth_header(_make_token(organizer))
    departments_response = client.get("/api/v1/departments", headers=headers)
    groups_response = client.get("/api/v1/project-groups", headers=headers)
    search_response = client.get(
        "/api/v1/users/search",
        params={
            "department_code": "FIN",
            "group_code": "MOBILE",
            "position": "manager",
            "keyword": "EMP-1001",
        },
        headers=headers,
    )
    next_page_response = client.get(
        "/api/v1/users/search",
        params={
            "department_code": "FIN",
            "group_code": "MOBILE",
            "position": "manager",
            "keyword": "EMP-1001",
            "limit": 500,
            "offset": 1,
        },
        headers=headers,
    )

    assert departments_response.status_code == 200
    assert departments_response.json() == [
        {"id": department.id, "name": "Finance", "code": "FIN"}
    ]
    assert groups_response.status_code == 200
    assert [item["code"] for item in groups_response.json()] == ["MOBILE"]
    assert search_response.status_code == 200
    assert len(search_response.json()) == 1
    assert search_response.json()[0]["id"] == participant.id
    assert search_response.json()[0]["position"] == "Engineering Manager"
    assert search_response.json()[0]["department"]["code"] == "FIN"
    assert search_response.json()[0]["project_groups"][0]["code"] == "MOBILE"
    assert next_page_response.status_code == 200
    assert next_page_response.json() == []
