"""Shared test helpers."""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.room import Room
from app.models.meeting import Meeting, MeetingParticipant
from app.core.security import hash_password, create_access_token


def _create_user(db: Session, username: str, role: str = "employee", password: str = "password123") -> User:
    user = User(
        username=username,
        email=f"{username}@test.local",
        full_name=f"Test {username}",
        hashed_password=hash_password(password),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_room(db: Session, name: str = "Room A") -> Room:
    room = Room(name=name, capacity=10, location="Floor 1", is_active=True)
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


def _create_meeting(
    db: Session,
    room: Room,
    organizer: User,
    start: datetime,
    end: datetime,
    status: str = "scheduled",
) -> Meeting:
    m = Meeting(
        title="Test meeting",
        description="desc",
        room_id=room.id,
        organizer_id=organizer.id,
        start_time=start,
        end_time=end,
        status=status,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def _add_participant(db: Session, meeting: Meeting, user: User) -> MeetingParticipant:
    mp = MeetingParticipant(meeting_id=meeting.id, user_id=user.id)
    db.add(mp)
    db.commit()
    db.refresh(mp)
    return mp


def _make_token(user: User) -> str:
    return create_access_token(
        data={"sub": user.username, "user_id": user.id, "role": user.role}
    )


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}