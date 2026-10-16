from app.core.security import hash_password, verify_password
from app.models.user import User
from scripts.reset_default_passwords import reset_default_passwords


def test_reset_default_passwords_updates_seeded_accounts_only(db_session):
    seeded_admin = User(
        username="admin",
        email="admin@meeting.local",
        hashed_password=hash_password("custom-admin-password"),
        role="admin",
    )
    seeded_demo = User(
        username="demo.alex",
        email="demo.alex@example.test",
        hashed_password=hash_password("custom-demo-password"),
        role="employee",
    )
    custom_user = User(
        username="personal-account",
        email="personal@example.test",
        hashed_password=hash_password("personal-password"),
        role="employee",
    )
    db_session.add_all([seeded_admin, seeded_demo, custom_user])
    db_session.commit()

    assert reset_default_passwords(db_session) == 2
    assert verify_password("123456", seeded_admin.hashed_password)
    assert verify_password("123456", seeded_demo.hashed_password)
    assert verify_password("personal-password", custom_user.hashed_password)


def test_reset_default_passwords_creates_sample_admin_when_users_empty(db_session):
    assert reset_default_passwords(db_session) == 1

    admin = db_session.query(User).one()
    assert admin.email == "admin@gmail.com"
    assert admin.role == "admin"
    assert verify_password("123456", admin.hashed_password)
