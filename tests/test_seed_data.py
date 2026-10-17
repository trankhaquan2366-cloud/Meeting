from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password, verify_password
from app.models.department import Department
from app.models.meeting import Meeting
from app.models.room import Room
from app.models.user import User
from app.seed_data import DEFAULT_PASSWORD, SEED_MARKER, seed_database


def test_seed_database_is_repeatable_and_keeps_unrelated_records(db_session):
    unrelated_user = User(
        username="existing-user",
        email="existing.user@example.test",
        full_name="Existing User",
        hashed_password=hash_password("existing-password"),
        role="employee",
        status="ACTIVE",
        is_active=True,
    )
    unrelated_room = Room(
        name="Existing Room",
        capacity=5,
        location="Tầng 9",
        is_active=True,
    )
    db_session.add_all([unrelated_user, unrelated_room])
    db_session.flush()
    unrelated_meeting = Meeting(
        title="Existing meeting",
        room_id=unrelated_room.id,
        organizer_id=unrelated_user.id,
        start_time=datetime(2026, 10, 20, 10),
        end_time=datetime(2026, 10, 20, 11),
        status="SCHEDULED",
        description="Created outside the data seeder.",
    )
    db_session.add(unrelated_meeting)
    db_session.commit()
    session_factory = sessionmaker(bind=db_session.get_bind())
    fixed_now = datetime(2026, 10, 16, 12, 0)

    first_result = seed_database(session_factory, now=fixed_now)
    second_result = seed_database(session_factory, now=fixed_now)
    db_session.expire_all()

    assert first_result == {
        "users": 15,
        "rooms": 8,
        "equipments": 5,
        "meetings": 43,
    }
    assert second_result == first_result
    assert (
        db_session.scalar(
            select(Meeting.id).where(Meeting.id == unrelated_meeting.id)
        )
        == unrelated_meeting.id
    )
    assert (
        db_session.query(Meeting)
        .filter(Meeting.description == SEED_MARKER)
        .count()
        == 43
    )
    seeded_meetings = db_session.query(Meeting).filter(
        Meeting.description == SEED_MARKER
    )
    assert seeded_meetings.filter(Meeting.status == "COMPLETED").count() == 24
    assert seeded_meetings.filter(Meeting.status == "CANCELLED").count() == 6
    assert seeded_meetings.filter(Meeting.status == "IN_PROGRESS").count() == 1
    assert seeded_meetings.filter(Meeting.status == "SCHEDULED").count() == 12
    assert (
        db_session.query(User)
        .filter(User.email.like("%@roomsync.test"))
        .count()
        == 15
    )
    assert db_session.query(Room).filter(Room.name.like("SEED - %")).count() == 8
    assert db_session.query(Department).filter(Department.code.like("SEED-%")).count() == 5

    pending_user = db_session.scalar(
        select(User).where(User.email == "nghia.hoang@roomsync.test")
    )
    locked_user = db_session.scalar(
        select(User).where(User.email == "hung.phan@roomsync.test")
    )
    assert pending_user.status == "PENDING"
    assert pending_user.is_active is False
    assert locked_user.status == "LOCKED"
    assert locked_user.is_active is False
    assert verify_password(DEFAULT_PASSWORD, pending_user.hashed_password)


def test_seed_initial_rooms_when_empty(db_session, monkeypatch):
    import app.main
    from app.main import seed_initial_rooms
    from app.models.room import Room

    session_factory = sessionmaker(bind=db_session.get_bind())
    monkeypatch.setattr(app.main, "SessionLocal", session_factory)

    assert db_session.query(Room).count() == 0
    seed_initial_rooms(force=True)
    assert db_session.query(Room).count() == 4
    room_names = {r.name for r in db_session.query(Room).all()}
    assert "Phòng Hội Thảo A" in room_names
    assert "Phòng VIP C" in room_names

    # Calling it again when rooms already exist should not duplicate
    seed_initial_rooms(force=True)
    assert db_session.query(Room).count() == 4

