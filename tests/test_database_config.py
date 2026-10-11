from sqlalchemy.engine import make_url

from app.core.database import _resolve_database_url


def test_database_url_falls_back_to_local_mysql(monkeypatch):
    for name in (
        "DATABASE_URL",
        "DATABASE_HOST",
        "DATABASE_PORT",
        "MYSQL_USER",
        "MYSQL_PASSWORD",
        "MYSQL_DATABASE",
    ):
        monkeypatch.delenv(name, raising=False)

    url = make_url(_resolve_database_url())

    assert url.host == "127.0.0.1"
    assert url.port == 3307
    assert url.database == "meeting_db"


def test_docker_hostname_is_mapped_to_local_host_outside_compose(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "mysql+pymysql://roomsync_user:roomsync_pass@roomsync_db:3306/meeting_db",
    )
    monkeypatch.delenv("DATABASE_HOST", raising=False)
    monkeypatch.delenv("DATABASE_PORT", raising=False)

    url = make_url(_resolve_database_url())

    assert url.host == "127.0.0.1"
    assert url.port == 3307


def test_compose_can_keep_internal_database_hostname(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "mysql+pymysql://roomsync_user:roomsync_pass@roomsync_db:3306/meeting_db",
    )
    monkeypatch.setenv("DATABASE_HOST", "roomsync_db")
    monkeypatch.setenv("DATABASE_PORT", "3306")

    url = make_url(_resolve_database_url())

    assert url.host == "roomsync_db"
    assert url.port == 3306


def test_non_mysql_database_url_is_not_modified_by_mysql_host_settings(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("DATABASE_HOST", "127.0.0.1")
    monkeypatch.setenv("DATABASE_PORT", "3307")

    assert _resolve_database_url() == "sqlite:///test.db"
