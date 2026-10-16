"""Health checks for frontend API paths and unexpected exception responses."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.department import Department
from app.models.project_group import ProjectGroup
from tests.helpers import _auth_header, _create_user, _make_token


def test_frontend_api_paths_work_with_authenticated_user(
    client: TestClient,
    db_session: Session,
) -> None:
    """Legacy and versioned profile/resource endpoints remain reachable."""
    user = _create_user(db_session, "api-compatibility-user")
    headers = _auth_header(_make_token(user))

    responses = {
        "legacy auth profile": client.get("/api/auth/me", headers=headers),
        "versioned auth profile": client.get("/api/v1/auth/me", headers=headers),
        "legacy user profile": client.get("/api/users/me", headers=headers),
        "versioned user profile": client.get("/api/v1/users/me", headers=headers),
        "versioned rooms": client.get("/api/v1/rooms/", headers=headers),
        "versioned equipment without trailing slash": client.get(
            "/api/v1/equipments",
            headers=headers,
        ),
        "versioned equipment with trailing slash": client.get(
            "/api/v1/equipments/",
            headers=headers,
        ),
        "versioned notifications": client.get(
            "/api/v1/notifications/",
            headers=headers,
        ),
        "versioned meetings": client.get("/api/v1/meetings/mine", headers=headers),
    }

    assert {name: response.status_code for name, response in responses.items()} == {
        name: 200 for name in responses
    }
    assert responses["versioned auth profile"].json()["id"] == user.id
    assert responses["versioned user profile"].json()["id"] == user.id


def test_current_user_profile_includes_department_and_project_groups(
    client: TestClient,
    db_session: Session,
) -> None:
    user = _create_user(db_session, "quick-invite-profile-user")
    department = Department(name="Quick Invite Department", code="QID")
    project_group = ProjectGroup(name="Quick Invite Project", code="QIP")
    user.department = department
    user.project_groups.append(project_group)
    db_session.commit()

    response = client.get(
        "/api/v1/users/me",
        headers=_auth_header(_make_token(user)),
    )

    assert response.status_code == 200
    assert response.json()["department"]["code"] == "QID"
    assert response.json()["project_groups"][0]["code"] == "QIP"


def test_unhandled_exception_returns_json_500_and_error_id() -> None:
    """Unexpected route failures get a JSON response without exposing exception text."""
    def raise_unhandled_error() -> None:
        raise RuntimeError("private database connection detail")

    app.add_api_route(
        "/__test__/unhandled-error",
        raise_unhandled_error,
        methods=["GET"],
        include_in_schema=False,
    )
    test_route = app.router.routes[-1]
    try:
        with TestClient(app, raise_server_exceptions=False) as test_client:
            response = test_client.get("/__test__/unhandled-error")
    finally:
        app.router.routes.remove(test_route)

    assert response.status_code == 500
    assert response.headers["x-error-id"] == response.json()["error_id"]
    assert "private database connection detail" not in response.text
    assert response.json()["detail"]
