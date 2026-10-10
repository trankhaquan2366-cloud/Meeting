This file is a merged representation of a subset of the codebase, containing files not matching ignore patterns, combined into a single document by Repomix.

# File Summary

## Purpose
This file contains a packed representation of a subset of the repository's contents that is considered the most important context.
It is designed to be easily consumable by AI systems for analysis, code review,
or other automated processes.

## File Format
The content is organized as follows:
1. This summary section
2. Repository information
3. Directory structure
4. Repository files (if enabled)
5. Multiple file entries, each consisting of:
  a. A header with the file path (## File: path/to/file)
  b. The full contents of the file in a code block

## Usage Guidelines
- This file should be treated as read-only. Any changes should be made to the
  original repository files, not this packed version.
- When processing this file, use the file path to distinguish
  between different files in the repository.
- Be aware that this file may contain sensitive information. Handle it with
  the same level of security as you would the original repository.

## Notes
- Some files may have been excluded based on .gitignore rules and Repomix's configuration
- Binary files are not included in this packed representation. Please refer to the Repository Structure section for a complete list of file paths, including binary files
- Files matching these patterns are excluded: **/node_modules/**, **/.next/**, **/venv/**, **/.venv/**, **/*.db, **/__pycache__/**, **/.git/**, **/.env*, **/*.pem, **/secrets.json, **/config.local.json
- Files matching patterns in .gitignore are excluded
- Files matching default ignore patterns are excluded
- Files are sorted by Git change count (files with more changes are at the bottom)

# Directory Structure
````
.agents/
  tasks/
    plan.md
alembic/
  versions/
    33c26788d6a2_fix_missing_meeting_link_column.py
    6b1d9f4a2c70_add_room_qr_and_meeting_checkin.py
    cf70acc36382_add_google_refresh_token_to_users.py
  env.py
  README
  script.py.mako
app/
  core/
    config.py
    database.py
    security.py
  db/
    session.py
  models/
    __init__.py
    equipment.py
    google_calendar_event.py
    meeting.py
    notification.py
    room.py
    user.py
  routers/
    __init__.py
    auth.py
    equipment.py
    meetings.py
    notifications.py
    reports.py
    rooms.py
    users.py
  schemas/
    __init__.py
    auth.py
    equipment.py
    meeting.py
    reports.py
    room.py
  services/
    calendar_email_service.py
    equipment_service.py
    google_calendar_service.py
    meeting_service.py
    notification_service.py
    reports.py
    room_service.py
    scheduler.py
  main.py
frontend/
  assets/
    index-DDntIe9W.css
    index-DPhpmZ5j.js
  css/
    booking.css
    create-meeting.css
    style.css
  js/
    app.js
    auth.js
    create-meeting.js
    login.js
  dashboard.html
  index.html
  login.html
  robots.txt
migrations/
  001_add_meeting_recurring_columns.sql
  002_add_meeting_participants.sql
  003_add_equipment_tables.sql
  004_add_room_amenities.sql
  005_add_meeting_type_and_link.sql
  005_align_meetings_schema.sql
  006_reconcile_live_room_meeting_schema.sql
  007_add_google_calendar_connection.sql
  007_google_calendar_invitees.sql
  008_add_meeting_participant_response_status.sql
scripts/
  patch_db.py
  seed.py
tests/
  __init__.py
  conftest.py
  helpers.py
  test_calendar_email.py
  test_equipment_admin.py
  test_equipment_availability.py
  test_google_auth.py
  test_google_calendar_delete.py
  test_google_calendar_service.py
  test_live_checkin_checkout.py
  test_meeting_cancel.py
  test_meeting_create.py
  test_meetings_history.py
  test_meetings_mine.py
  test_meetings.py
  test_room_create.py
.dockerignore
.env.example
.gitignore
alembic.ini
docker-compose.yml
Dockerfile
FETCH_HEAD
package.json
README.md
requirements-dev.txt
requirements.txt
schema.sql
````

# Files

## File: alembic/versions/6b1d9f4a2c70_add_room_qr_and_meeting_checkin.py
````python
"""Add room QR tokens and meeting check-in lifecycle fields.

Revision ID: 6b1d9f4a2c70
Revises: 33c26788d6a2
Create Date: 2026-10-10
"""
from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision: str = "6b1d9f4a2c70"
down_revision: Union[str, Sequence[str], None] = "33c26788d6a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "rooms" not in tables or "meetings" not in tables:
        raise RuntimeError("The rooms and meetings tables must exist before this migration.")

    room_columns = {column["name"] for column in inspector.get_columns("rooms")}
    if "qr_token" not in room_columns:
        op.add_column("rooms", sa.Column("qr_token", sa.String(length=64), nullable=True))

    meeting_columns = {column["name"] for column in inspector.get_columns("meetings")}
    if "check_in_time" not in meeting_columns:
        op.add_column("meetings", sa.Column("check_in_time", sa.DateTime(), nullable=True))
    if "check_out_time" not in meeting_columns:
        op.add_column("meetings", sa.Column("check_out_time", sa.DateTime(), nullable=True))
    if "reminder_sent" not in meeting_columns:
        op.add_column(
            "meetings",
            sa.Column(
                "reminder_sent",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )

    room_table = sa.table(
        "rooms",
        sa.column("id", sa.Integer()),
        sa.column("qr_token", sa.String(length=64)),
    )
    for room_id, in bind.execute(
        sa.select(room_table.c.id).where(room_table.c.qr_token.is_(None))
    ):
        bind.execute(
            room_table.update()
            .where(room_table.c.id == room_id)
            .values(qr_token=str(uuid4()))
        )

    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes("rooms")}
    unique_constraints = {
        constraint["name"] for constraint in inspector.get_unique_constraints("rooms")
    }
    if "ix_rooms_qr_token" not in indexes and "uq_rooms_qr_token" not in unique_constraints:
        op.create_index("ix_rooms_qr_token", "rooms", ["qr_token"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "rooms" in inspector.get_table_names():
        indexes = {index["name"] for index in inspector.get_indexes("rooms")}
        if "ix_rooms_qr_token" in indexes:
            op.drop_index("ix_rooms_qr_token", table_name="rooms")
        columns = {column["name"] for column in inspector.get_columns("rooms")}
        if "qr_token" in columns:
            op.drop_column("rooms", "qr_token")

    if "meetings" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("meetings")}
        for column_name in ("reminder_sent", "check_out_time", "check_in_time"):
            if column_name in columns:
                op.drop_column("meetings", column_name)
````

## File: app/services/scheduler.py
````python
"""Periodic meeting lifecycle jobs."""

import logging
import os
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.meeting import Meeting, MeetingParticipant
from app.models.notification import Notification
from app.models.user import User

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _meeting_recipients(db: Session, meeting: Meeting, accepted_only: bool) -> list[User]:
    users: dict[int, User] = {}
    if meeting.organizer is not None:
        users[meeting.organizer.id] = meeting.organizer
    participants = db.query(MeetingParticipant).filter(
        MeetingParticipant.meeting_id == meeting.id
    ).all()
    for participant in participants:
        if accepted_only and (participant.response_status or "").casefold() != "accepted":
            continue
        if participant.user is not None:
            users[participant.user.id] = participant.user
    return list(users.values())


def _send_meeting_email(recipients: list[User], subject: str, body: str) -> None:
    host = os.getenv("SMTP_HOST")
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("SMTP_FROM_EMAIL") or username
    if not all((host, username, password, from_email)):
        logger.warning("Meeting lifecycle email skipped: SMTP settings are incomplete")
        return

    port = int(os.getenv("SMTP_PORT", "587"))
    use_starttls = os.getenv("SMTP_STARTTLS", "true").strip().casefold() in {
        "1", "true", "yes",
    }
    for user in recipients:
        if not user.email:
            logger.warning("Meeting lifecycle email skipped: user_id=%s has no email", user.id)
            continue
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = from_email
        message["To"] = user.email
        message.set_content(f"Chào {user.full_name or user.username},\n\n{body}")
        try:
            with smtplib.SMTP(host, port, timeout=20) as smtp:
                smtp.ehlo()
                if use_starttls:
                    smtp.starttls(context=ssl.create_default_context())
                    smtp.ehlo()
                smtp.login(username, password)
                smtp.send_message(message)
        except (OSError, smtplib.SMTPException):
            logger.exception("Meeting lifecycle email failed for user_id=%s", user.id)


def process_meeting_reminders(db: Session, now: datetime | None = None) -> int:
    """Notify organizers and confirmed attendees during the check-in window."""
    current_time = now or _utc_now()
    meetings = (
        db.query(Meeting)
        .filter(
            func.upper(Meeting.status) == "SCHEDULED",
            Meeting.reminder_sent.is_(False),
            Meeting.start_time <= current_time,
            Meeting.start_time > current_time - timedelta(minutes=15),
        )
        .all()
    )
    for meeting in meetings:
        recipients = _meeting_recipients(db, meeting, accepted_only=True)
        for user in recipients:
            db.add(
                Notification(
                    user_id=user.id,
                    title="Nhắc check-in cuộc họp",
                    content=(
                        f"Cuộc họp '{meeting.title}' đã bắt đầu. "
                        "Vui lòng quét mã QR của phòng để check-in."
                    ),
                )
            )
        meeting.reminder_sent = True

    if meetings:
        try:
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Failed to process meeting reminders")
            raise
    return len(meetings)


def process_no_show_meetings(db: Session, now: datetime | None = None) -> int:
    """Cancel meetings that have not been checked in within the grace period."""
    current_time = now or _utc_now()
    meetings = (
        db.query(Meeting)
        .filter(
            func.upper(Meeting.status) == "SCHEDULED",
            Meeting.check_in_time.is_(None),
            Meeting.start_time <= current_time - timedelta(minutes=15),
        )
        .all()
    )
    recipients_by_meeting: list[tuple[Meeting, list[User]]] = []
    for meeting in meetings:
        recipients_by_meeting.append(
            (meeting, _meeting_recipients(db, meeting, accepted_only=False))
        )
        meeting.status = "CANCELLED_NO_SHOW"

    if meetings:
        try:
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Failed to cancel no-show meetings")
            raise

    for meeting, recipients in recipients_by_meeting:
        _send_meeting_email(
            recipients,
            "Cuộc họp đã bị hủy do không check-in",
            (
                f"Cuộc họp '{meeting.title}' đã bị hủy vì không có check-in "
                "trong vòng 15 phút kể từ giờ bắt đầu."
            ),
        )
    return len(meetings)


def process_auto_checkouts(db: Session, now: datetime | None = None) -> int:
    """Complete in-progress meetings after their scheduled end time."""
    current_time = now or _utc_now()
    meetings = (
        db.query(Meeting)
        .filter(
            func.upper(Meeting.status) == "IN_PROGRESS",
            Meeting.end_time <= current_time,
        )
        .all()
    )
    for meeting in meetings:
        meeting.status = "COMPLETED"
        meeting.check_out_time = meeting.end_time

    if meetings:
        try:
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Failed to process automatic meeting check-outs")
            raise
    return len(meetings)
````

## File: tests/test_live_checkin_checkout.py
````python
"""Real-time API smoke test for the QR check-in/check-out flow."""

from datetime import datetime, timedelta, timezone
import sys
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.equipment import Equipment, MeetingEquipment
from app.models.meeting import Meeting
from app.models.notification import Notification
from tests.helpers import _auth_header, _create_room, _create_user, _make_token


def test_live_checkin_notification_and_checkout(
    client: TestClient,
    db_session: Session,
) -> None:
    """Run both authenticated endpoints using the current UTC time."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    suffix = uuid4().hex
    organizer_user = _create_user(db_session, f"live-checkin-{suffix}")
    room = _create_room(db_session, f"Phòng Test 22h {suffix}")
    assert room.qr_token, "Test room did not receive a QR token"

    equipment = Equipment(
        name=f"Live check-in equipment {suffix}",
        code=f"LIVE-{suffix[:12]}",
        total_qty=1,
        is_active=True,
    )
    db_session.add(equipment)
    db_session.flush()

    start_time = datetime.now(timezone.utc).replace(tzinfo=None)
    end_time = start_time + timedelta(hours=1)
    meeting = Meeting(
        title=f"Live QR check-in test {suffix}",
        room_id=room.id,
        organizer_id=organizer_user.id,
        start_time=start_time,
        end_time=end_time,
        status="SCHEDULED",
    )
    db_session.add(meeting)
    db_session.flush()
    db_session.add(
        MeetingEquipment(
            meeting_id=meeting.id,
            equipment_id=equipment.id,
            quantity=1,
        )
    )
    db_session.commit()
    db_session.refresh(meeting)

    auth_headers = _auth_header(_make_token(organizer_user))
    failures: list[str] = []

    print(f"[STEP] Tạo cuộc họp '{meeting.title}' trong phòng '{room.name}'")
    print(
        f"[INFO] Bắt đầu UTC: {start_time.isoformat()} | "
        f"Kết thúc UTC: {end_time.isoformat()}"
    )

    check_in_response = client.post(
        f"/api/v1/meetings/{meeting.id}/check-in",
        json={"qr_token": room.qr_token},
        headers=auth_headers,
    )
    check_in_data = (
        check_in_response.json() if check_in_response.status_code == 200 else {}
    )
    check_in_time = check_in_data.get("check_in_time")
    if (
        check_in_response.status_code == 200
        and check_in_data.get("status", "").upper() == "IN_PROGRESS"
        and check_in_time
    ):
        print(f"[SUCCESS] Check-in thành công lúc: {check_in_time}")
    else:
        print(
            "[FAIL] Check-in không thành công: "
            f"HTTP {check_in_response.status_code} {check_in_response.text}"
        )
        failures.append("Check-in response/status/timestamp invalid")

    db_session.expire_all()
    organizer_notifications = (
        db_session.query(Notification)
        .filter(Notification.user_id == organizer_user.id)
        .all()
    )
    check_in_notification = next(
        (
            notification
            for notification in organizer_notifications
            if any(
                term in f"{notification.title} {notification.content}".casefold()
                for term in ("check-in", "check in", "đã bắt đầu")
            )
        ),
        None,
    )
    if check_in_notification is not None:
        print(
            "[NOTIFICATION] Đã gửi phản hồi tới Chủ trì: "
            f"{organizer_user.full_name} — {check_in_notification.title}"
        )
    else:
        print(
            "[FAIL] Chưa tìm thấy notification check-in/đã bắt đầu "
            f"cho Chủ trì: {organizer_user.full_name}"
        )
        failures.append("No check-in notification was created for the organizer")

    check_out_response = client.post(
        f"/api/v1/meetings/{meeting.id}/check-out",
        json={"qr_token": room.qr_token},
        headers=auth_headers,
    )
    check_out_data = (
        check_out_response.json() if check_out_response.status_code == 200 else {}
    )
    check_out_time = check_out_data.get("check_out_time")
    if (
        check_out_response.status_code == 200
        and check_out_data.get("status", "").upper() == "COMPLETED"
        and check_out_time
    ):
        print(f"[SUCCESS] Check-out thành công lúc: {check_out_time}")
    else:
        print(
            "[FAIL] Check-out không thành công: "
            f"HTTP {check_out_response.status_code} {check_out_response.text}"
        )
        failures.append("Check-out response/status/timestamp invalid")

    availability_start = datetime.now(timezone.utc).replace(tzinfo=None)
    availability_end = availability_start + timedelta(minutes=1)
    params = {
        "start_time": availability_start.isoformat(),
        "end_time": availability_end.isoformat(),
    }
    room_availability_response = client.get(
        "/api/rooms/available",
        params=params,
    )
    if room_availability_response.status_code == 200:
        room_is_available = any(
            available_room["id"] == room.id
            for available_room in room_availability_response.json()
        )
    else:
        room_is_available = False
        failures.append(
            "Could not verify room availability: "
            f"HTTP {room_availability_response.status_code}"
        )

    equipment_availability_response = client.get(
        "/api/equipments/availability",
        params={**params, "search": equipment.code},
    )
    if equipment_availability_response.status_code == 200:
        equipment_status = next(
            (
                item
                for item in equipment_availability_response.json()
                if item["id"] == equipment.id
            ),
            None,
        )
        equipment_is_available = (
            equipment_status is not None
            and equipment_status["available_qty"] == equipment.total_qty
        )
    else:
        equipment_is_available = False
        failures.append(
            "Could not verify equipment availability: "
            f"HTTP {equipment_availability_response.status_code}"
        )

    if not room_is_available:
        failures.append("Room is still reported unavailable after check-out")
    if not equipment_is_available:
        failures.append("Equipment is still reported unavailable after check-out")
    if room_is_available and equipment_is_available:
        print("[SUCCESS] Check-out thành công, đã giải phóng phòng và thiết bị!")
    else:
        print(
            "[FAIL] Tài nguyên sau check-out: "
            f"phòng khả dụng={room_is_available}, "
            f"thiết bị khả dụng={equipment_is_available}"
        )

    assert not failures, "Live QR flow failures:\n- " + "\n- ".join(failures)
````

## File: tests/test_meetings.py
````python
from datetime import datetime, timedelta, timezone, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.equipment import Equipment, MeetingEquipment
from app.models.notification import Notification
from app.services.meeting_service import MeetingService
from app.services.scheduler import (
    process_auto_checkouts,
    process_meeting_reminders,
    process_no_show_meetings,
)
from tests.helpers import (
    _add_participant,
    _auth_header,
    _create_meeting,
    _create_room,
    _create_user,
    _make_token,
)


def _meeting_at(
    db_session: Session,
    start_time: datetime,
    status: str = "scheduled",
):
    identifier = uuid4().hex
    organizer = _create_user(db_session, f"qr-organizer-{identifier}")
    room = _create_room(db_session, f"QR Room {identifier}")
    meeting = _create_meeting(
        db_session,
        room,
        organizer,
        start_time,
        start_time + timedelta(hours=1),
        status=status,
    )
    return meeting, room, organizer


def test_check_in_succeeds_within_fifteen_minute_window(db_session: Session):
    now = datetime(2026, 10, 10, 10, 0)
    meeting, room, organizer = _meeting_at(db_session, now + timedelta(minutes=15))

    checked_in = MeetingService.check_in_meeting(
        db_session, meeting.id, room.qr_token, organizer, now=now
    )

    assert checked_in.status == "IN_PROGRESS"
    assert checked_in.check_in_time == now
    notification = (
        db_session.query(Notification)
        .filter(Notification.user_id == organizer.id)
        .one()
    )
    assert "Test meeting" in notification.content
    assert "check-in thành công và bắt đầu" in notification.content


@pytest.mark.parametrize("failure", ["wrong_qr", "not_accepted"])
def test_check_in_rejects_wrong_qr_or_unaccepted_participant(
    db_session: Session,
    failure: str,
):
    now = datetime(2026, 10, 10, 10, 0)
    meeting, room, organizer = _meeting_at(db_session, now)
    participant = _create_user(db_session, f"qr-participant-{failure}")
    participant_row = _add_participant(db_session, meeting, participant)

    qr_token = room.qr_token
    if failure == "wrong_qr":
        participant_row.response_status = "accepted"
        db_session.commit()
        qr_token = "invalid-token"

    with pytest.raises(HTTPException) as error:
        MeetingService.check_in_meeting(
            db_session, meeting.id, qr_token, participant, now=now
        )

    assert error.value.status_code == (400 if failure == "wrong_qr" else 403)


@pytest.mark.parametrize(
    ("offset_minutes", "message"),
    [
        (-16, "Chưa đến thời gian check-in (cho phép trước 15 phút)"),
        (16, "Đã quá thời gian check-in"),
    ],
)
def test_check_in_rejects_outside_allowed_time_window(
    db_session: Session,
    offset_minutes: int,
    message: str,
):
    start_time = datetime(2026, 10, 10, 10, 0)
    now = start_time + timedelta(minutes=offset_minutes)
    meeting, room, organizer = _meeting_at(db_session, start_time)

    with pytest.raises(HTTPException) as error:
        MeetingService.check_in_meeting(
            db_session, meeting.id, room.qr_token, organizer, now=now
        )

    assert error.value.status_code == 400
    assert error.value.detail == message


@pytest.mark.parametrize("offset_minutes", [-15, 15])
def test_check_in_accepts_exact_window_boundaries(
    db_session: Session,
    offset_minutes: int,
):
    start_time = datetime(2026, 10, 10, 10, 0)
    meeting, room, organizer = _meeting_at(db_session, start_time)

    checked_in = MeetingService.check_in_meeting(
        db_session,
        meeting.id,
        room.qr_token,
        organizer,
        now=start_time + timedelta(minutes=offset_minutes),
    )
    assert checked_in.status == "IN_PROGRESS"


def test_check_out_completes_meeting_with_room_qr(db_session: Session):
    now = datetime(2026, 10, 10, 10, 0)
    meeting, room, organizer = _meeting_at(db_session, now, status="IN_PROGRESS")
    equipment = Equipment(
        name=f"Early checkout equipment {uuid4().hex}",
        total_qty=1,
        is_active=True,
    )
    db_session.add(equipment)
    db_session.flush()
    db_session.add(
        MeetingEquipment(meeting_id=meeting.id, equipment_id=equipment.id, quantity=1)
    )
    db_session.commit()

    checked_out = MeetingService.check_out_meeting(
        db_session,
        meeting.id,
        room.qr_token,
        organizer,
        now=now + timedelta(minutes=20),
    )

    assert checked_out.status == "COMPLETED"
    assert checked_out.check_out_time == now + timedelta(minutes=20)
    from app.services.equipment_service import get_equipment_availability
    from app.services.room_service import get_available_rooms

    available_rooms = get_available_rooms(
        db_session,
        start_time=now + timedelta(minutes=21),
        end_time=now + timedelta(minutes=30),
    )
    assert room.id in {available_room.id for available_room in available_rooms}

    equipment_availability = get_equipment_availability(
        db_session,
        start_time=now + timedelta(minutes=21),
        end_time=now + timedelta(minutes=30),
    )
    equipment_status = next(item for item in equipment_availability if item.id == equipment.id)
    assert equipment_status.booked_qty == 0
    assert equipment_status.available_qty == equipment.total_qty


def test_versioned_check_in_endpoint(client: TestClient, db_session: Session):
    organizer = _create_user(db_session, f"api-organizer-{uuid4().hex}")
    room = _create_room(db_session, f"API QR Room {uuid4().hex}")
    start_time = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=5)
    meeting = _create_meeting(
        db_session,
        room,
        organizer,
        start_time,
        start_time + timedelta(hours=1),
    )

    response = client.post(
        f"/api/v1/meetings/{meeting.id}/check-in",
        json={"qr_token": room.qr_token},
        headers=_auth_header(_make_token(organizer)),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "IN_PROGRESS"
    assert response.json()["check_in_time"] is not None


def test_manager_can_retrieve_room_qr_code(client: TestClient, db_session: Session):
    manager = _create_user(db_session, f"qr-manager-{uuid4().hex}", role="manager")
    room = _create_room(db_session, f"Manager QR Room {uuid4().hex}")

    response = client.get(
        f"/api/v1/rooms/{room.id}/qr-code",
        headers=_auth_header(_make_token(manager)),
    )

    assert response.status_code == 200
    assert response.json() == {
        "room_id": room.id,
        "room_name": room.name,
        "qr_token": room.qr_token,
    }


def test_meeting_organizer_can_retrieve_qr_for_their_scheduled_meeting(
    client: TestClient,
    db_session: Session,
):
    organizer = _create_user(db_session, f"qr-owner-{uuid4().hex}")
    outsider = _create_user(db_session, f"qr-outsider-{uuid4().hex}")
    room = _create_room(db_session, f"Organizer QR Room {uuid4().hex}")
    start_time = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=5)
    meeting = _create_meeting(
        db_session, room, organizer, start_time, start_time + timedelta(hours=1)
    )

    owner_response = client.get(
        f"/api/v1/rooms/{room.id}/qr-code",
        params={"meeting_id": meeting.id},
        headers=_auth_header(_make_token(organizer)),
    )
    outsider_response = client.get(
        f"/api/v1/rooms/{room.id}/qr-code",
        params={"meeting_id": meeting.id},
        headers=_auth_header(_make_token(outsider)),
    )

    assert owner_response.status_code == 200
    assert owner_response.json()["qr_token"] == room.qr_token
    assert outsider_response.status_code == 403


def test_no_show_scheduler_cancels_meeting_after_grace_period(db_session: Session):
    now = datetime(2026, 10, 10, 10, 16)
    meeting, _, _ = _meeting_at(
        db_session,
        now - timedelta(minutes=16),
    )

    processed = process_no_show_meetings(db_session, now=now)

    db_session.refresh(meeting)
    assert processed == 1
    assert meeting.status == "CANCELLED_NO_SHOW"


def test_no_show_meeting_releases_equipment_inventory(db_session: Session):
    now = datetime(2026, 10, 10, 10, 16)
    meeting, _, _ = _meeting_at(db_session, now - timedelta(minutes=16))
    equipment = Equipment(
        name=f"QR scheduler equipment {uuid4().hex}",
        total_qty=1,
        is_active=True,
    )
    db_session.add(equipment)
    db_session.flush()
    db_session.add(
        MeetingEquipment(meeting_id=meeting.id, equipment_id=equipment.id, quantity=1)
    )
    db_session.commit()

    process_no_show_meetings(db_session, now=now)

    from app.services.equipment_service import get_equipment_availability

    availability = get_equipment_availability(
        db_session,
        now - timedelta(minutes=1),
        now + timedelta(minutes=1),
    )
    equipment_status = next(item for item in availability if item.id == equipment.id)
    assert equipment_status.booked_qty == 0
    assert equipment_status.available_qty == 1


def test_no_show_scheduler_does_not_cancel_before_grace_period(db_session: Session):
    now = datetime(2026, 10, 10, 10, 14)
    meeting, _, _ = _meeting_at(
        db_session,
        now - timedelta(minutes=14),
    )

    processed = process_no_show_meetings(db_session, now=now)

    db_session.refresh(meeting)
    assert processed == 0
    assert meeting.status == "scheduled"


def test_reminder_scheduler_notifies_organizer_and_accepted_attendees(db_session: Session):
    now = datetime(2026, 10, 10, 10, 5)
    meeting, _, organizer = _meeting_at(db_session, now - timedelta(minutes=5))
    accepted = _create_user(db_session, f"reminder-accepted-{uuid4().hex}")
    pending = _create_user(db_session, f"reminder-pending-{uuid4().hex}")
    accepted_invitation = _add_participant(db_session, meeting, accepted)
    accepted_invitation.response_status = "accepted"
    _add_participant(db_session, meeting, pending)
    db_session.commit()

    processed = process_meeting_reminders(db_session, now=now)

    assert processed == 1
    assert meeting.reminder_sent is True
    notifications = db_session.query(Notification).all()
    assert {notification.user_id for notification in notifications} == {
        organizer.id,
        accepted.id,
    }


def test_auto_checkout_uses_scheduled_end_time(db_session: Session):
    now = datetime(2026, 10, 10, 11, 0)
    meeting, _, _ = _meeting_at(
        db_session,
        now - timedelta(hours=2),
        status="IN_PROGRESS",
    )

    processed = process_auto_checkouts(db_session, now=now)

    db_session.refresh(meeting)
    assert processed == 1
    assert meeting.status == "COMPLETED"
    assert meeting.check_out_time == meeting.end_time
````

## File: .agents/tasks/plan.md
````markdown
# Implementation Plan — Tạo cuộc họp hoàn chỉnh

> Dựa trên: đọc trực tiếp source code hiện tại (tất cả file liên quan)
> Ghi chú: `python-dateutil` **KHÔNG có** trong `requirements.txt` → dùng `calendar` stdlib để xử lý monthly recurrence.

---

## Tổng quan các vấn đề phát hiện khi đọc code

| File | Vấn đề |
|---|---|
| `models/meeting.py` | `room_id` nullable=False + ondelete='CASCADE' — cần đổi cho phép NULL với SET NULL |
| `schemas/meeting.py` | Thiếu `meeting_type`, `meeting_link`; `MeetingCreateResponse` chưa có; `room_id` bắt buộc |
| `services/meeting_service.py` | Monthly dùng `timedelta(days=30)` sai; conflict → reject toàn bộ thay vì skip; không lưu participants; không có alias `suggest_time`; không check `meeting_type` |
| `routers/meetings.py` | GET `""` trả `RoomResponse` thay vì meetings; gọi `suggest_time` nhưng service có method `calculate_suggested_times`; response_model POST `/book` là `List[MeetingResponse]` thay vì `MeetingCreateResponse` |
| `routers/rooms.py` | Có 2 endpoint trùng: `/available` và `/available/`; endpoint `/available/` có `min_capacity` nhưng `/available` thì không |
| `create-meeting.js` | Online meeting → early return trước khi gọi API; mockIds filter loại bỏ IDs hợp lệ; `meeting_type`/`meeting_link` không có trong payload; không auto-search khi switch offline; không hiển thị skipped; không validate min 15 phút |
| `create-meeting.css` | Thiếu style `.cm-skipped-notice` |

---

## STEP 1 — Database Migration + Model Update

- [ ] 1. Tạo file SQL migration `005_add_meeting_type_and_link.sql`.

  Tạo file mới tại `c:\Users\ADMIN\Desktop\Meeting\migrations\005_add_meeting_type_and_link.sql` với nội dung:

  ```sql
  USE meeting_db;
  ALTER TABLE meetings ADD COLUMN IF NOT EXISTS meeting_type VARCHAR(10) NOT NULL DEFAULT 'offline' AFTER description;
  ALTER TABLE meetings ADD COLUMN IF NOT EXISTS meeting_link VARCHAR(500) NULL AFTER meeting_type;
  ALTER TABLE meetings DROP FOREIGN KEY IF EXISTS fk_meetings_room;
  ALTER TABLE meetings MODIFY COLUMN room_id INT NULL;
  ALTER TABLE meetings ADD CONSTRAINT fk_meetings_room FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE SET NULL ON UPDATE CASCADE;
  ```

  **Files:** `c:\Users\ADMIN\Desktop\Meeting\migrations\005_add_meeting_type_and_link.sql`

- [ ] 2. Cập nhật `app/models/meeting.py` để phản ánh schema mới.

  **Các thay đổi cụ thể trong file (giữ nguyên phần còn lại):**

  - Dòng hiện tại (~line 22): `room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True)`
    → Đổi thành: `room_id = Column(Integer, ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True, index=True)`

  - Sau field `description` (line 20), thêm 2 field mới:
    ```python
    meeting_type = Column(String(10), nullable=False, default='offline')
    meeting_link = Column(String(500), nullable=True)
    ```

  **Giữ nguyên:** Tất cả relationships, `__tablename__`, `MeetingParticipant`, các field khác.

  **Files:** `c:\Users\ADMIN\Desktop\Meeting\app\models\meeting.py`

  **Verify:** `python -c "from app.models.meeting import Meeting; print(Meeting.meeting_type, Meeting.meeting_link, Meeting.room_id)"` không raise ImportError. Nếu có DB kết nối: chạy migration SQL và kiểm tra `DESCRIBE meetings;` thấy 2 cột mới + room_id nullable.

---

## STEP 2 — Schemas + Service Logic

- [ ] 3. Cập nhật `app/schemas/meeting.py` — thêm fields và schema mới.

  **Thay đổi tại `MeetingCreateRequest` (hiện tại dòng 10–18):**
  - Đổi `room_id: int` → `room_id: Optional[int] = None` (bỏ required, vì online meeting không cần)
  - Thêm 2 field sau `description`:
    ```python
    meeting_type: str = 'offline'
    meeting_link: Optional[str] = None
    ```
  - Thêm validator cho `meeting_type`:
    ```python
    @field_validator('meeting_type')
    @classmethod
    def validate_meeting_type(cls, v):
        if v not in ('online', 'offline'):
            raise ValueError("meeting_type phải là 'online' hoặc 'offline'")
        return v
    ```

  **Thay đổi tại `MeetingResponse` (hiện tại dòng 22–35):**
  - Đổi `room_id: int` → `room_id: Optional[int] = None`
  - Thêm 2 field mới:
    ```python
    meeting_type: str = 'offline'
    meeting_link: Optional[str] = None
    ```

  **Thêm class mới `MeetingCreateResponse` sau `MeetingResponse`:**
  ```python
  class MeetingCreateResponse(BaseModel):
      created: List[MeetingResponse]
      skipped: List[dict]
  ```

  **Giữ nguyên:** `FrequentUserResponse`, `NotificationResponse`, `SuggestTimeRequest`, `TimeSlot`, `SuggestTimeResponse`, validator `parse_equipments`.

  **Files:** `c:\Users\ADMIN\Desktop\Meeting\app\schemas\meeting.py`

- [ ] 4. Cập nhật `app/services/meeting_service.py` — 7 fix quan trọng.

  **Import cần thêm ở đầu file:**
  ```python
  import calendar
  from app.models.meeting import MeetingParticipant
  ```

  **Fix A — Validate meeting_type (thêm vào đầu method `create_meeting`, sau kiểm tra `start_time < now`):**
  ```python
  meeting_type = getattr(payload, 'meeting_type', 'offline') or 'offline'
  meeting_link = getattr(payload, 'meeting_link', None)

  if meeting_type == 'online':
      if not meeting_link:
          raise HTTPException(status_code=400, detail="Cuộc họp online cần có meeting_link!")
      room = None  # online không cần phòng
  else:  # offline
      if not payload.room_id:
          raise HTTPException(status_code=400, detail="Cuộc họp offline cần chọn phòng họp!")
      room = db.query(Room).filter(Room.id == payload.room_id, Room.is_active == True).first()
      if not room:
          raise HTTPException(status_code=400, detail="Phòng họp không tồn tại hoặc đã bị ngưng hoạt động!")
  ```
  → **Xóa block kiểm tra phòng hiện tại** (lines ~40–46 kiểm tra room cứng nhắc) vì đã được xử lý trong Fix A.

  **Fix B — Monthly recurrence dùng calendar (thay `timedelta(days=30)` trong vòng lặp):**
  ```python
  elif recurrence_type in ("monthly", "until_changed"):
      # Tính đúng ngày tháng tiếp theo bằng calendar arithmetic
      year = current_start.year
      month = current_start.month + 1
      if month > 12:
          month = 1
          year += 1
      day = min(current_start.day, calendar.monthrange(year, month)[1])
      delta = current_start.replace(year=year, month=month, day=day) - current_start
      current_start += delta
      current_end += delta
  ```

  **Fix C — Skip conflict thay vì reject toàn bộ (thay block `if overlapping_meeting`):**
  - Khai báo `skipped = []` trước vòng lặp `for s_time, e_time in meeting_dates`.
  - Thay đoạn raise HTTPException khi conflict bằng:
    ```python
    if overlapping_meeting:
        date_str = s_time.strftime("%d/%m/%Y lúc %H:%M")
        skipped.append({
            "date": date_str,
            "reason": f"Phòng đã có lịch vào {date_str}"
        })
        continue  # bỏ qua occurrence này, tiếp tục tạo những cái khác
    ```
  - Sau vòng lặp, thêm guard:
    ```python
    if not created_meetings:
        db.rollback()
        raise HTTPException(status_code=400, detail="Tất cả các mốc thời gian đều bị xung đột lịch phòng!")
    ```

  **Fix D — Lưu participants sau `db.flush()` (thêm ngay sau block lưu equipments):**
  ```python
  participant_ids = getattr(payload, 'participant_ids', []) or []
  for pid in participant_ids:
      if pid == organizer_id:
          continue  # không thêm organizer vào participants
      participant = MeetingParticipant(
          meeting_id=new_meeting.id,
          user_id=pid
      )
      db.add(participant)
  ```

  **Fix E — Không check room conflict khi online (trong vòng lặp `for s_time, e_time`):**
  ```python
  # Chỉ kiểm tra conflict phòng khi offline
  if meeting_type == 'offline':
      overlapping_meeting = db.query(Meeting).filter(
          Meeting.room_id == payload.room_id,
          ...
      ).first()
      if overlapping_meeting:
          ...  # skip logic từ Fix C
  ```

  **Fix F — Truyền `meeting_type` và `meeting_link` vào `Meeting(...)` constructor:**
  ```python
  new_meeting = Meeting(
      title=payload.title,
      description=payload.description,
      room_id=payload.room_id if meeting_type == 'offline' else None,
      meeting_type=meeting_type,
      meeting_link=meeting_link,
      organizer_id=organizer_id,
      start_time=s_time,
      end_time=e_time,
      is_recurring=recurrence_type not in (None, "none"),
      recurring_type=recurrence_type if recurrence_type != "none" else None,
      status="scheduled"
  )
  ```

  **Fix G — Return dict thay vì list + thêm alias `suggest_time`:**
  - Đổi `return created_meetings` cuối method thành:
    ```python
    return {'created': created_meetings, 'skipped': skipped}
    ```
  - Thêm alias method sau `calculate_suggested_times`:
    ```python
    @staticmethod
    def suggest_time(db: Session, payload):
        return MeetingService.calculate_suggested_times(
            db=db,
            participant_ids=payload.participant_ids,
            date_str=payload.date,
            duration_minutes=payload.duration_minutes
        )
    ```

  **Files:** `c:\Users\ADMIN\Desktop\Meeting\app\services\meeting_service.py`

  **Verify:** `python -c "from app.services.meeting_service import MeetingService; print('OK')"` không raise ImportError.

---

## STEP 3 — Router Update

- [ ] 5. Cập nhật `app/routers/meetings.py` — 3 fix.

  **Fix A — Import `MeetingCreateResponse`:**
  Thêm `MeetingCreateResponse` vào import block từ `app.schemas.meeting`:
  ```python
  from app.schemas.meeting import (
      MeetingCreateRequest,
      MeetingCreateResponse,
      MeetingResponse,
      SuggestTimeRequest,
      SuggestTimeResponse,
  )
  ```

  **Fix B — Endpoint GET `""` (dòng ~20–29) trả sai kiểu:**
  Hiện tại: `response_model=List[RoomResponse]` và gọi `MeetingService.get_all_active_rooms(db)`.
  → Đổi thành trả meetings, hoặc xóa endpoint này vì đã có GET `/` bên dưới. **Quyết định: xóa endpoint GET `""` vì GET `/` đã cover đúng chức năng.**
  
  Xóa toàn bộ block:
  ```python
  @router.get(
      "",
      response_model=List[RoomResponse],
      ...
  )
  def list_rooms(db: Session = Depends(get_db)):
      return MeetingService.get_all_active_rooms(db)
  ```
  Đồng thời xóa import `RoomResponse` từ `app.schemas.room` nếu không dùng ở đâu khác.

  **Fix C — Endpoint POST `/book` đổi response_model:**
  ```python
  @router.post(
      "/book",
      response_model=MeetingCreateResponse,   # ← đổi từ List[MeetingResponse]
      status_code=status.HTTP_201_CREATED,
      ...
  )
  def create_meeting(...):
      result = MeetingService.create_meeting(...)   # giờ trả dict
      
      # Gửi notification dùng result['created'] thay vì created_meetings
      if payload.participant_ids and result['created']:
          first_meeting = result['created'][0]
          start_str = first_meeting.start_time.strftime("%H:%M %d/%m/%Y")
          background_tasks.add_task(
              send_meeting_invitation_notifications,
              db=db,
              participant_ids=payload.participant_ids,
              meeting_title=first_meeting.title,
              start_time_str=start_str,
          )
      
      return result   # dict {'created': [...], 'skipped': [...]}
  ```

  **Giữ nguyên:** Tất cả endpoint khác (`/suggest-time`, `/`, `/history`, `/{meeting_id}/cancel`, `/{meeting_id}`).

  **Files:** `c:\Users\ADMIN\Desktop\Meeting\app\routers\meetings.py`

- [ ] 6. Cập nhật `app/routers/rooms.py` — gộp 2 endpoint `/available`.

  **Vấn đề:** Có 2 endpoint:
  - `GET /available` (line ~25) — không có `min_capacity`
  - `GET /available/` (line ~120) — có `min_capacity`, dùng `room_service.get_available_rooms()`

  **Quyết định:** Gộp thành 1 endpoint duy nhất `GET /available`, dùng logic từ `room_service.get_available_rooms()` (đầy đủ hơn).

  Xóa endpoint `GET /available` cũ (không có min_capacity) và **đổi tên** endpoint `GET /available/` (trailing slash) thành `GET /available`:
  ```python
  @router.get("/available", response_model=List[RoomResponse], summary="Tìm phòng trống")
  def read_available_rooms(
      start_time: datetime = Query(...),
      end_time: datetime = Query(...),
      min_capacity: Optional[int] = Query(0),
      db: Session = Depends(get_db),
  ):
      if start_time >= end_time:
          raise HTTPException(status_code=400, detail="Thời gian bắt đầu phải nhỏ hơn thời gian kết thúc!")
      return room_service.get_available_rooms(db=db, start_time=start_time, end_time=end_time, min_capacity=min_capacity)
  ```

  **Giữ nguyên:** Tất cả endpoint khác (`GET /`, `POST /`, `PUT /{room_id}`, `DELETE /{room_id}`).

  **Files:** `c:\Users\ADMIN\Desktop\Meeting\app\routers\rooms.py`

  **Verify:** `python -c "from app.routers.meetings import router; from app.routers.rooms import router as rr; print('Routers OK')"` không raise ImportError.

---

## STEP 4 — Frontend JS Fix

- [ ] 7. Sửa `frontend/js/create-meeting.js` — 7 fix.

  **Fix 1 — Thêm `meeting_type` và `meeting_link` vào payload** (trong `handleCreateMeetingSubmit`, khu vực build `payload` object, hiện tại từ line ~764):

  Sau dòng `room_id: ...`, thêm:
  ```js
  meeting_type: cmState.mode,  // 'online' hoặc 'offline'
  meeting_link: cmState.mode === 'online' ? (cmEl('cmMeetingLink')?.value.trim() || null) : null,
  ```

  **Fix 2 — Xóa early return cho online meeting** (lines ~779–783):
  Xóa block:
  ```js
  if (cmState.mode === 'online') {
      payload.equipments = [];
      rememberAttendees(realParticipantIds);
      showCreateMeetingSuccess();
      return;
  }
  ```
  → Online meeting phải gọi API thật như offline. Giữ `payload.equipments = []` nếu mode === 'online' bằng cách thay vào logic build equipments:
  ```js
  equipments: cmState.mode === 'online' ? [] : Object.entries(cmState.borrowQty)
      .filter(([, qty]) => qty > 0)
      .map(([equipment_id, quantity]) => ({ equipment_id: parseInt(equipment_id, 10), quantity })),
  ```

  **Fix 3 — Xóa `mockIds` filter** (lines ~771–774), gửi tất cả integer IDs:
  Xóa:
  ```js
  const mockIds = new Set(CM_MOCK_USERS.map(u => u.id));
  const realParticipantIds = cmState.attendees
      .map(a => a.id)
      .filter(id => Number.isInteger(id) && !mockIds.has(id));
  ```
  Thay bằng:
  ```js
  const realParticipantIds = cmState.attendees
      .map(a => a.id)
      .filter(id => Number.isInteger(id));
  ```

  **Fix 4 — Auto-search phòng khi `setCreateMeetingMode('offline')`:**
  Trong function `setCreateMeetingMode(mode)`, sau dòng `updateCreateMeetingSummary()`, thêm:
  ```js
  if (mode === 'offline') {
      const { date, start, end } = cmGetTimes();
      if (date && start && end) {
          searchMatchingRooms();
      }
  }
  ```

  **Fix 5 — Room search thêm `min_capacity` vào query params** (trong `searchMatchingRooms()`, khu vực build `params`):
  ```js
  const params = new URLSearchParams({
      start_time: `${date}T${start}:00`,
      end_time: `${date}T${end}:00`,
      min_capacity: String(cmNeededSeats()),   // ← thêm dòng này
  });
  ```

  **Fix 6 — Hiển thị `skipped` occurrences sau tạo thành công** (trong `handleCreateMeetingSubmit`, sau `if (!res.ok)` block, trong try block):
  Thay:
  ```js
  rememberAttendees(realParticipantIds);
  showCreateMeetingSuccess();
  ```
  Bằng:
  ```js
  const result = await res.json();
  rememberAttendees(realParticipantIds);
  showCreateMeetingSuccess();

  // Hiển thị skipped nếu có
  if (result.skipped && result.skipped.length > 0) {
      const skipDates = result.skipped.map(s => s.date || s.reason || JSON.stringify(s)).join(', ');
      const noticeEl = document.createElement('div');
      noticeEl.className = 'cm-skipped-notice';
      noticeEl.textContent = `⚠ ${result.skipped.length} khung giờ bị bỏ qua do xung đột: ${skipDates}`;
      cmEl('cmDialog')?.appendChild(noticeEl);
  }
  ```

  **Fix 7 — Validate min 15 phút duration** (trong `validateCreateMeeting()`):
  Sau block kiểm tra `end <= start`, thêm:
  ```js
  if (date && start && end) {
      const startMs = new Date(`${date}T${start}:00`).getTime();
      const endMs = new Date(`${date}T${end}:00`).getTime();
      if (endMs - startMs < 15 * 60 * 1000) {
          showFormError('Cuộc họp phải có thời lượng tối thiểu 15 phút.');
          ok = false;
      }
  }
  ```

  **Files:** `c:\Users\ADMIN\Desktop\Meeting\frontend\js\create-meeting.js`

  **Verify:** Mở browser console, gọi `openCreateMeeting()`, kiểm tra không có JS errors. Test flow: chọn mode online → không early return → gọi API. Test validate duration < 15 phút → hiển thị error.

---

## STEP 5 — CSS Minor Update

- [ ] 8. Thêm style `.cm-skipped-notice` vào `frontend/css/create-meeting.css`.

  Append vào cuối file (sau CSS rule cuối cùng):
  ```css
  /* Thông báo các lịch bị bỏ qua (skipped occurrences) */
  .cm-skipped-notice {
      background: var(--cm-warning-soft);
      border: 1px solid #fde68a;
      border-radius: var(--cm-radius);
      padding: 12px 16px;
      font-size: 13px;
      color: var(--cm-warning);
      margin-top: 12px;
  }
  ```

  CSS sử dụng các biến đã khai báo trong `:root` (`--cm-warning-soft: #fffbeb`, `--cm-warning: #b45309`, `--cm-radius: 10px`) — không cần thêm biến mới.

  **Files:** `c:\Users\ADMIN\Desktop\Meeting\frontend\css\create-meeting.css`

  **Verify:** Mở file HTML của create-meeting trong browser, tạo element `<div class="cm-skipped-notice">Test</div>` qua DevTools console, kiểm tra style áp dụng đúng (nền vàng nhạt, chữ vàng đậm, border vàng).

---

## Ghi chú thứ tự dependency

- STEP 1 phải hoàn thành trước STEP 2 (model phải có field mới trước khi service dùng chúng).
- STEP 2 phải hoàn thành trước STEP 3 (schema `MeetingCreateResponse` phải tồn tại trước khi router import).
- STEP 3 và STEP 4 có thể làm song song (backend router độc lập với frontend JS).
- STEP 5 độc lập hoàn toàn, có thể làm bất kỳ lúc nào.
- Không cần cài thêm dependency: `calendar` là stdlib Python, `python-dateutil` không có trong `requirements.txt` và không cần thiết.
````

## File: alembic/README
````
Generic single-database configuration.
````

## File: alembic/script.py.mako
````
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, Sequence[str], None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """Upgrade schema."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Downgrade schema."""
    ${downgrades if downgrades else "pass"}
````

## File: app/core/config.py
````python
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


def load_environment() -> None:
    """Load project environment variables without overriding process settings."""
    load_dotenv(dotenv_path=ENV_FILE, override=False)


def get_google_oauth_credentials() -> tuple[str, str] | None:
    load_environment()
    credentials = {
        "GOOGLE_CLIENT_ID": os.getenv("GOOGLE_CLIENT_ID"),
        "GOOGLE_CLIENT_SECRET": os.getenv("GOOGLE_CLIENT_SECRET"),
    }
    invalid_variables = [
        name
        for name, value in credentials.items()
        if (
            not value
            or not value.strip()
            or value.strip().lower().startswith(("your_", "your-", "replace_", "replace-"))
            or "placeholder" in value.strip().lower()
        )
    ]
    if invalid_variables:
        logger.error(
            "Google OAuth is not configured; missing or placeholder environment variable(s): %s",
            ", ".join(invalid_variables),
        )
        return None

    client_id = credentials["GOOGLE_CLIENT_ID"]
    client_secret = credentials["GOOGLE_CLIENT_SECRET"]
    assert client_id is not None and client_secret is not None
    return client_id, client_secret


load_environment()
````

## File: app/db/session.py
````python
# app/db/session.py
from app.core.database import Base, engine, SessionLocal, get_db

__all__ = ["Base", "engine", "SessionLocal", "get_db"]
````

## File: app/models/equipment.py
````python
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base

class Equipment(Base):
    __tablename__ = "equipments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    code = Column(String(50), unique=True, nullable=True)
    category = Column(String(50), nullable=True)
    total_qty = Column(Integer, nullable=False, default=1)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    meeting_allocations = relationship("MeetingEquipment", back_populates="equipment")
    room_defaults = relationship("RoomEquipment", back_populates="equipment")


class MeetingEquipment(Base):
    __tablename__ = "meeting_equipments"

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    equipment_id = Column(Integer, ForeignKey("equipments.id", ondelete="RESTRICT"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    note = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    meeting = relationship("Meeting", back_populates="equipments")
    equipment = relationship("Equipment", back_populates="meeting_allocations")

    __table_args__ = (UniqueConstraint('meeting_id', 'equipment_id', name='uq_meeting_equipment'),)


class RoomEquipment(Base):
    __tablename__ = "room_equipments"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    equipment_id = Column(Integer, ForeignKey("equipments.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)

    room = relationship("Room", back_populates="default_equipments")
    equipment = relationship("Equipment", back_populates="room_defaults")

    __table_args__ = (UniqueConstraint('room_id', 'equipment_id', name='uq_room_equipment'),)
````

## File: app/models/google_calendar_event.py
````python
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func

from app.core.database import Base


class GoogleCalendarEvent(Base):
    __tablename__ = "google_calendar_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    meeting_id = Column(Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    google_event_id = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "meeting_id", name="uq_google_event_user_meeting"),
        UniqueConstraint("user_id", "google_event_id", name="uq_google_event_user_event"),
    )
````

## File: app/routers/__init__.py
````python

````

## File: app/routers/notifications.py
````python
# app/routers/notifications.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.notification import Notification
from app.models.user import User
from app.routers.auth import get_current_user  # Kiểm tra lại đường dẫn import hàm get_current_user của bạn
from app.schemas.meeting import NotificationResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/", response_model=List[NotificationResponse])
def get_user_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lấy danh sách thông báo của người dùng hiện tại (mới nhất xếp trên)"""
    return (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )


@router.put("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Đánh dấu 1 thông báo cụ thể là đã đọc"""
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông báo"
        )

    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


@router.put("/read-all")
def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Đánh dấu tất cả thông báo chưa đọc của người dùng là đã đọc"""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"message": "Đã đánh dấu tất cả thông báo là đã đọc"}
````

## File: app/routers/reports.py
````python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional

from app.core.database import get_db
from app.models.meeting import Meeting
from app.models.room import Room

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("/room-usage")
def get_room_usage_report(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    room_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    # Thiết lập thời gian mặc định (30 ngày gần nhất)
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thời gian bắt đầu (start_date) không được lớn hơn thời gian kết thúc (end_date)."
        )

    delta_days = (end_date - start_date).days or 1

    # CHỈ LẤY CÁC PHÒNG CÒN TỒN TẠI VÀ ĐANG HOẠT ĐỘNG TRONG HỆ THỐNG
    room_query = db.query(Room).filter(Room.is_active == True) if hasattr(Room, 'is_active') else db.query(Room)
    
    if room_id:
        room_query = room_query.filter(Room.id == room_id)
    
    rooms = room_query.all()
    valid_room_ids = {room.id for room in rooms}
    total_rooms_count = len(rooms)

    room_details = []
    total_meetings_all = 0
    total_hours_all = 0.0

    for room in rooms:
        # Chỉ quét các cuộc họp thuộc đúng phòng hiện có và có trạng thái hợp lệ
        meetings = db.query(Meeting).filter(
            Meeting.room_id == room.id,
            Meeting.status.in_(["CONFIRMED", "COMPLETED", "scheduled"]),
            Meeting.start_time >= start_date,
            Meeting.end_time <= end_date
        ).all()

        room_meeting_count = len(meetings)
        room_total_hours = 0.0

        for m in meetings:
            if m.start_time and m.end_time:
                duration = (m.end_time - m.start_time).total_seconds() / 3600.0
                room_total_hours += max(0.0, duration)

        max_possible_hours = delta_days * 8.0
        occupancy_rate = (room_total_hours / max_possible_hours * 100.0) if max_possible_hours > 0 else 0.0
        occupancy_rate = min(100.0, occupancy_rate)

        total_meetings_all += room_meeting_count
        total_hours_all += room_total_hours

        room_details.append({
            "room_id": room.id,
            "room_name": room.name,
            "total_meetings": room_meeting_count,
            "total_hours": round(room_total_hours, 2),
            "occupancy_rate": round(occupancy_rate, 2)
        })

    avg_occupancy = (sum(r["occupancy_rate"] for r in room_details) / total_rooms_count) if total_rooms_count > 0 else 0.0

    return {
        "summary": {
            "total_rooms": total_rooms_count,
            "total_meetings": total_meetings_all,
            "total_hours": round(total_hours_all, 2),
            "average_occupancy_rate": round(avg_occupancy, 2)
        },
        "room_details": room_details
    }
````

## File: app/schemas/__init__.py
````python

````

## File: app/schemas/reports.py
````python
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class RoomReportDetail(BaseModel):
    room_id: int = Field(..., description="ID của phòng họp")
    room_name: str = Field(..., description="Tên phòng họp")
    total_meetings: int = Field(..., description="Tổng số cuộc họp hợp lệ")
    total_hours: float = Field(..., description="Tổng số giờ họp (đã làm tròn 1 chữ số thập phân)")
    occupancy_rate: float = Field(..., description="Tỷ lệ lấp đầy (%) (đã làm tròn 1 chữ số thập phân)")

    model_config = ConfigDict(from_attributes=True)


class RoomReportSummary(BaseModel):
    total_rooms: int = Field(..., description="Tổng số phòng họp trong báo cáo")
    total_meetings: int = Field(..., description="Tổng số cuộc họp toàn hệ thống")
    total_hours: float = Field(..., description="Tổng số giờ họp toàn hệ thống")
    average_occupancy_rate: float = Field(..., description="Trung bình occupancy_rate các phòng")


class RoomUsageReportResponse(BaseModel):
    summary: RoomReportSummary
    room_details: List[RoomReportDetail]
````

## File: app/services/calendar_email_service.py
````python
import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.meeting import Meeting, MeetingParticipant
from app.models.user import User
from app.services.google_calendar_service import make_calendar_consent_url, sync_user_meetings_to_google

logger = logging.getLogger(__name__)


def _send_calendar_consent_email(user: User, meetings: list[Meeting]) -> None:
    host = os.getenv("SMTP_HOST")
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("SMTP_FROM_EMAIL") or username
    if not all((host, username, password, from_email)):
        logger.warning("Calendar permission email skipped: SMTP settings are incomplete")
        return

    try:
        consent_url = make_calendar_consent_url(user)
    except ValueError:
        logger.warning("Calendar permission email skipped: user_id=%s has no email", user.id)
        return

    meeting_lines = []
    for meeting in meetings:
        start_time = meeting.start_time.strftime("%d/%m/%Y %H:%M")
        meeting_lines.append(f"- {meeting.title} — {start_time}")

    message = EmailMessage()
    message["Subject"] = "Kết nối Google Calendar với RoomSync"
    message["From"] = from_email
    message["To"] = user.email
    message.set_content(
        f"Chào {user.full_name or user.username},\n\n"
        "Bạn được mời tham dự các cuộc họp sau trong RoomSync:\n"
        f"{chr(10).join(meeting_lines)}\n\n"
        "Để các cuộc họp được tự động thêm vào Google Calendar của bạn, hãy mở liên kết dưới đây "
        "và cấp quyền Calendar cho RoomSync. Google sẽ yêu cầu bạn xác nhận tài khoản trước khi cấp quyền.\n\n"
        f"{consent_url}\n\n"
        "Liên kết có hiệu lực trong 7 ngày và chỉ dùng để kết nối tài khoản có email đăng ký trong RoomSync.\n"
        "Nếu bạn không mong đợi email này, có thể bỏ qua."
    )

    port = int(os.getenv("SMTP_PORT", "587"))
    use_starttls = os.getenv("SMTP_STARTTLS", "true").strip().lower() in {"1", "true", "yes"}
    try:
        with smtplib.SMTP(host, port, timeout=20) as smtp:
            smtp.ehlo()
            if use_starttls:
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
            smtp.login(username, password)
            smtp.send_message(message)
        logger.info("Calendar permission email sent to user_id=%s", user.id)
    except (OSError, smtplib.SMTPException):
        logger.exception("Calendar permission email failed for user_id=%s", user.id)


def request_calendar_access_for_invitees(user_ids: list[int], meeting_ids: list[int]) -> None:
    """Email unconnected invitees or sync their existing invited meetings."""
    unique_user_ids = list(dict.fromkeys(user_ids))
    unique_meeting_ids = list(dict.fromkeys(meeting_ids))
    if not unique_user_ids or not unique_meeting_ids:
        return

    db: Session = SessionLocal()
    try:
        meetings_by_user = {}
        for user_id in unique_user_ids:
            user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
            if not user:
                continue
            meetings = (
                db.query(Meeting)
                .join(MeetingParticipant, MeetingParticipant.meeting_id == Meeting.id)
                .filter(
                    MeetingParticipant.user_id == user_id,
                    Meeting.id.in_(unique_meeting_ids),
                    Meeting.status.notin_(["CANCELLED", "canceled", "CANCELLED_NO_SHOW"]),
                )
                .order_by(Meeting.start_time)
                .all()
            )
            if meetings:
                meetings_by_user[user_id] = (user, meetings)
    finally:
        db.close()

    for user, meetings in meetings_by_user.values():
        if user.google_refresh_token:
            sync_user_meetings_to_google(user.id)
        else:
            _send_calendar_consent_email(user, meetings)
````

## File: app/services/notification_service.py
````python
# app/services/notification_service.py
from typing import List
from sqlalchemy.orm import Session
from app.models.notification import Notification


def create_notification(db: Session, user_id: int, title: str, content: str) -> Notification:
    """Tạo một bản ghi thông báo mới cho người dùng"""
    notification = Notification(
        user_id=user_id,
        title=title,
        content=content
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def send_meeting_invitation_notifications(
    db: Session,
    participant_ids: List[int],
    meeting_title: str,
    start_time_str: str
):
    """
    Hàm chạy ngầm (Background Task) gửi thông báo cho danh sách người tham dự.
    """
    for user_id in participant_ids:
        title = "Lời mời tham dự cuộc họp mới"
        content = f"Bạn được mời tham gia cuộc họp '{meeting_title}' diễn ra vào lúc {start_time_str}."
        create_notification(db, user_id=user_id, title=title, content=content)
````

## File: app/services/reports.py
````python
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case

from app.models.room import Room
from app.models.meeting import Meeting


class ReportRoomService:
    @staticmethod
    async def get_room_usage_report(
        db: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        room_id: Optional[int] = None
    ) -> Dict[str, Any]:
        # 1. Thiết lập giá trị thời gian mặc định nếu không được cung cấp
        now = datetime.now()
        if not end_date:
            end_date = now
        if not start_date:
            start_date = end_date - timedelta(days=30)

        # 2. Tính toán tham số days: days = max((end_date - start_date).total_seconds()/86400, 1/24)
        total_seconds = (end_date - start_date).total_seconds()
        days = max(total_seconds / 86400.0, 1.0 / 24.0)

        # 3. Điều kiện lọc cuộc họp (chỉ CONFIRMED hoặc COMPLETED và thuộc khoảng thời gian)
        meeting_filter = and_(
            Meeting.status.in_(["CONFIRMED", "COMPLETED"]),
            Meeting.start_time >= start_date,
            Meeting.end_time <= end_date
        )

        # Tính thời lượng cuộc họp bằng giây qua TIMESTAMPDIFF (tối ưu cho MySQL)
        meeting_duration_hours = func.timestampdiff(func.SECOND, Meeting.start_time, Meeting.end_time) / 3600.0

        # 4. Truy vấn cơ sở dữ liệu tối ưu với LEFT JOIN và GROUP BY
        query = (
            select(
                Room.id.label("room_id"),
                Room.name.label("room_name"),
                func.count(case((meeting_filter, Meeting.id), else_=None)).label("total_meetings"),
                func.coalesce(
                    func.sum(case((meeting_filter, meeting_duration_hours), else_=0.0)),
                    0.0
                ).label("total_hours")
            )
            .select_from(Room)
            .outerjoin(Meeting, Room.id == Meeting.room_id)
            .group_by(Room.id, Room.name)
        )

        if room_id is not None:
            query = query.where(Room.id == room_id)

        result = await db.execute(query)
        rows = result.all()

        # 5. Duyệt và tính toán các chỉ số cho từng phòng
        room_details: List[Dict[str, Any]] = []
        sum_occupancy_rate = 0.0
        total_system_meetings = 0
        total_system_hours = 0.0

        for row in rows:
            r_id = row.room_id
            r_name = row.room_name
            t_meetings = int(row.total_meetings)
            t_hours = round(float(row.total_hours), 1)

            # Công thức: occupancy_rate = (total_hours / (days * 8)) * 100
            raw_occupancy = (t_hours / (days * 8.0)) * 100.0
            occ_rate = round(raw_occupancy, 1)

            room_details.append({
                "room_id": r_id,
                "room_name": r_name,
                "total_meetings": t_meetings,
                "total_hours": t_hours,
                "occupancy_rate": occ_rate
            })

            total_system_meetings += t_meetings
            total_system_hours += t_hours
            sum_occupancy_rate += occ_rate

        # 6. Tổng hợp dữ liệu summary toàn hệ thống
        total_rooms = len(room_details)
        avg_occupancy_rate = round(sum_occupancy_rate / total_rooms, 1) if total_rooms > 0 else 0.0
        total_system_hours = round(total_system_hours, 1)

        return {
            "summary": {
                "total_rooms": total_rooms,
                "total_meetings": total_system_meetings,
                "total_hours": total_system_hours,
                "average_occupancy_rate": avg_occupancy_rate
            },
            "room_details": room_details
        }
````

## File: app/services/room_service.py
````python
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.meeting import Meeting
from app.models.room import Room


def get_available_rooms(
    db: Session,
    start_time: datetime,
    end_time: datetime,
    min_capacity: int = 0,
):
    # 1. Tìm các room_id đã bị đặt trong khoảng thời gian này
    occupied_room_ids = (
        db.query(Meeting.room_id)
        .filter(
            func.upper(Meeting.status).notin_(
                ["CANCELLED", "CANCELLED_NO_SHOW", "COMPLETED"]
            ),
            Meeting.check_out_time.is_(None),
            Meeting.start_time < end_time,
            Meeting.end_time > start_time,
        )
        .subquery()
    )

    # 2. Lấy danh sách các phòng trống và đủ sức chứa
    available_rooms = (
        db.query(Room)
        .filter(
            Room.is_active == True,
            Room.capacity >= min_capacity,
            ~Room.id.in_(occupied_room_ids),
        )
        .all()
    )

    return available_rooms
````

## File: frontend/css/create-meeting.css
````css
/* Create Meeting — enterprise form (not a room-search dashboard) */

:root {
    --cm-primary: #2563eb;
    --cm-primary-dark: #1d4ed8;
    --cm-primary-soft: #eff6ff;
    --cm-success: #15803d;
    --cm-success-soft: #f0fdf4;
    --cm-warning: #b45309;
    --cm-warning-soft: #fffbeb;
    --cm-error: #b91c1c;
    --cm-error-soft: #fef2f2;
    --cm-neutral-950: #0f172a;
    --cm-neutral-700: #334155;
    --cm-neutral-500: #64748b;
    --cm-neutral-400: #94a3b8;
    --cm-neutral-300: #cbd5e1;
    --cm-neutral-200: #e2e8f0;
    --cm-neutral-100: #f1f5f9;
    --cm-neutral-50: #f8fafc;
    --cm-white: #ffffff;
    --cm-radius: 10px;
    --cm-radius-lg: 16px;
    --cm-shadow: 0 24px 48px rgba(15, 23, 42, 0.2);
    --cm-focus: 0 0 0 3px rgba(37, 99, 235, 0.18);
}

.cm-overlay {
    position: fixed;
    inset: 0;
    z-index: 240;
    display: none;
    align-items: center;
    justify-content: center;
    padding: 20px;
    background: rgba(15, 23, 42, 0.55);
    backdrop-filter: blur(4px);
}

.cm-overlay.is-open {
    display: flex;
}

.cm-dialog {
    width: min(1120px, 100%);
    max-height: min(92vh, 860px);
    display: flex;
    flex-direction: column;
    background: var(--cm-white);
    border: 1px solid var(--cm-neutral-200);
    border-radius: var(--cm-radius-lg);
    box-shadow: var(--cm-shadow);
    overflow: hidden;
}

.cm-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    padding: 16px 22px;
    border-bottom: 1px solid var(--cm-neutral-200);
    flex-shrink: 0;
}

.cm-kicker {
    margin: 0 0 2px;
    color: var(--cm-primary);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.cm-header h1 {
    margin: 0;
    color: var(--cm-neutral-950);
    font-size: 18px;
    line-height: 24px;
    font-weight: 700;
}

.cm-icon-btn {
    width: 36px;
    height: 36px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: var(--cm-neutral-500);
    background: var(--cm-neutral-50);
    border: 1px solid var(--cm-neutral-200);
    border-radius: 999px;
}

.cm-icon-btn:hover,
.cm-icon-btn:focus-visible {
    color: var(--cm-error);
    background: var(--cm-error-soft);
    outline: none;
    box-shadow: var(--cm-focus);
}

.cm-layout {
    display: grid;
    grid-template-columns: minmax(0, 1.45fr) minmax(280px, 0.7fr);
    min-height: 0;
    flex: 1;
}

#createMeetingForm.cm-layout {
    min-height: 0;
}

.cm-form-pane {
    min-height: 0;
    overflow-y: auto;
    padding: 20px 22px 28px;
    display: flex;
    flex-direction: column;
    gap: 18px;
}

.cm-summary-pane {
    min-height: 0;
    overflow-y: auto;
    padding: 18px 18px 20px;
    background: var(--cm-neutral-50);
    border-left: 1px solid var(--cm-neutral-200);
    display: flex;
    flex-direction: column;
    gap: 14px;
}

.cm-section {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.cm-section[hidden] {
    display: none !important;
}

.cm-section-title {
    margin: 0;
    color: var(--cm-neutral-950);
    font-size: 13px;
    font-weight: 700;
}

.cm-section-head {
    display: flex;
    flex-direction: column;
    gap: 2px;
}

.cm-help {
    margin: 0;
    color: var(--cm-neutral-500);
    font-size: 12px;
    line-height: 18px;
}

.cm-label {
    color: var(--cm-neutral-700);
    font-size: 12.5px;
    font-weight: 600;
}

.cm-title-input {
    width: 100%;
    min-height: 52px;
    padding: 12px 14px;
    color: var(--cm-neutral-950);
    font-size: 17px;
    font-weight: 650;
    line-height: 1.35;
    background: var(--cm-white);
    border: 1px solid var(--cm-neutral-300);
    border-radius: 12px;
}

.cm-title-input::placeholder {
    color: var(--cm-neutral-400);
    font-weight: 500;
}

.cm-input,
.cm-select,
.cm-textarea {
    width: 100%;
    min-height: 40px;
    padding: 8px 12px;
    color: var(--cm-neutral-950);
    background: var(--cm-white);
    border: 1px solid var(--cm-neutral-300);
    border-radius: 8px;
    font-size: 13px;
}

.cm-textarea {
    min-height: 72px;
    resize: vertical;
    line-height: 1.45;
}

.cm-title-input:focus,
.cm-input:focus,
.cm-select:focus,
.cm-textarea:focus,
.cm-search:focus {
    outline: none;
    border-color: var(--cm-primary);
    box-shadow: var(--cm-focus);
}

.cm-title-input.is-invalid,
.cm-input.is-invalid,
.cm-select.is-invalid,
.cm-textarea.is-invalid {
    border-color: var(--cm-error);
    box-shadow: 0 0 0 3px rgba(185, 28, 28, 0.12);
}

.cm-field-error {
    display: none;
    color: var(--cm-error);
    font-size: 12px;
    font-weight: 600;
}

.cm-field-error.is-visible {
    display: block;
}

.cm-time-grid {
    display: grid;
    grid-template-columns: 1.15fr 1fr 1fr;
    gap: 10px;
}

.cm-mini-label {
    display: block;
    margin-bottom: 5px;
    color: var(--cm-neutral-500);
    font-size: 11px;
    font-weight: 600;
}

.cm-seg {
    display: flex;
    gap: 6px;
    padding: 4px;
    background: var(--cm-neutral-100);
    border-radius: 10px;
    width: fit-content;
}

.cm-seg button {
    min-height: 34px;
    padding: 0 12px;
    color: var(--cm-neutral-700);
    background: transparent;
    border: 0;
    border-radius: 8px;
    font-size: 12.5px;
    font-weight: 600;
}

.cm-seg button[aria-pressed="true"] {
    color: var(--cm-primary-dark);
    background: var(--cm-white);
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
}

.cm-seg button:focus-visible {
    outline: none;
    box-shadow: var(--cm-focus);
}

.cm-recurring-extra {
    display: none;
    gap: 10px;
    padding: 12px;
    background: var(--cm-white);
    border: 1px solid var(--cm-neutral-200);
    border-radius: var(--cm-radius);
}

.cm-recurring-extra.is-open {
    display: grid;
    grid-template-columns: 1fr 1fr;
}

.cm-attendee-search {
    position: relative;
}

.cm-search {
    width: 100%;
    min-height: 42px;
    padding: 8px 12px 8px 38px;
    border: 1px solid var(--cm-neutral-300);
    border-radius: 8px;
    background: var(--cm-white) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='none' stroke='%2394a3b8' stroke-width='2'%3E%3Ccircle cx='7' cy='7' r='5'/%3E%3Cpath d='M11 11l3 3'/%3E%3C/svg%3E") 12px 50% no-repeat;
}

.cm-suggest {
    position: absolute;
    z-index: 6;
    top: calc(100% + 4px);
    left: 0;
    right: 0;
    display: none;
    max-height: 240px;
    overflow-y: auto;
    margin: 0;
    padding: 6px;
    list-style: none;
    background: var(--cm-white);
    border: 1px solid var(--cm-neutral-200);
    border-radius: 10px;
    box-shadow: 0 12px 28px rgba(15, 23, 42, 0.12);
}

.cm-suggest.is-open {
    display: block;
}

.cm-suggest button {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 10px;
    text-align: left;
    background: transparent;
    border: 0;
    border-radius: 8px;
}

.cm-suggest button:hover,
.cm-suggest button.is-active,
.cm-suggest button:focus-visible {
    background: var(--cm-primary-soft);
    outline: none;
}

.cm-avatar {
    width: 28px;
    height: 28px;
    flex: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: var(--cm-white);
    background: var(--cm-primary);
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
}

.cm-suggest-meta {
    display: flex;
    flex-direction: column;
    min-width: 0;
}

.cm-suggest-meta strong {
    font-size: 13px;
    color: var(--cm-neutral-950);
}

.cm-suggest-meta span {
    font-size: 11.5px;
    color: var(--cm-neutral-500);
}

.cm-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
}

.cm-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 8px 4px 4px;
    background: var(--cm-primary-soft);
    border: 1px solid #bfdbfe;
    border-radius: 999px;
    color: var(--cm-primary-dark);
    font-size: 12px;
    font-weight: 600;
}

.cm-chip button {
    width: 18px;
    height: 18px;
    padding: 0;
    color: var(--cm-neutral-500);
    background: transparent;
    border: 0;
    border-radius: 999px;
    font-size: 13px;
    line-height: 1;
}

.cm-chip button:hover,
.cm-chip button:focus-visible {
    color: var(--cm-error);
    outline: none;
}

.cm-inline-actions {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
}

.cm-link-btn {
    padding: 0;
    color: var(--cm-primary);
    background: transparent;
    border: 0;
    font-size: 12.5px;
    font-weight: 600;
}

.cm-link-btn:hover,
.cm-link-btn:focus-visible {
    color: var(--cm-primary-dark);
    outline: none;
    text-decoration: underline;
}

.cm-mode {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
}

.cm-mode button {
    min-height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 8px 12px;
    color: var(--cm-neutral-700);
    background: var(--cm-white);
    border: 1px solid var(--cm-neutral-300);
    border-radius: 10px;
    font-size: 13px;
    font-weight: 600;
}

.cm-mode button[aria-pressed="true"] {
    color: var(--cm-primary-dark);
    background: var(--cm-primary-soft);
    border-color: var(--cm-primary);
}

.cm-mode button:focus-visible {
    outline: none;
    box-shadow: var(--cm-focus);
}

.cm-online-box,
.cm-resources {
    display: none;
    gap: 10px;
    padding: 14px;
    background: var(--cm-white);
    border: 1px solid var(--cm-neutral-200);
    border-radius: 12px;
}

.cm-online-box.is-open,
.cm-resources.is-open {
    display: flex;
    flex-direction: column;
}

.cm-section .cm-resources {
    margin-top: 8px;
}

.cm-capacity {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 12px 14px;
    background: var(--cm-neutral-50);
    border: 1px solid var(--cm-neutral-200);
    border-radius: 10px;
}

.cm-capacity strong {
    display: block;
    font-size: 14px;
}

.cm-fixed-requirements {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.cm-amenity-options {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 8px;
}

.cm-amenity-choice {
    display: flex;
    align-items: center;
    gap: 8px;
    min-height: 38px;
    padding: 8px 10px;
    color: var(--cm-neutral-700);
    background: var(--cm-neutral-50);
    border: 1px solid var(--cm-neutral-200);
    border-radius: 8px;
    font-size: 12.5px;
    cursor: pointer;
}

.cm-amenity-choice:has(input:checked) {
    color: var(--cm-primary-dark);
    background: var(--cm-primary-soft);
    border-color: #93c5fd;
}

.cm-amenity-choice input {
    width: 15px;
    height: 15px;
    margin: 0;
    accent-color: var(--cm-primary);
}

.cm-btn {
    min-height: 40px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 0 14px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 650;
    border: 1px solid transparent;
}

.cm-btn:focus-visible {
    outline: none;
    box-shadow: var(--cm-focus);
}

.cm-btn:disabled {
    cursor: not-allowed;
    opacity: 0.55;
}

.cm-btn-primary {
    color: var(--cm-white);
    background: var(--cm-primary);
    border-color: var(--cm-primary);
}

.cm-btn-primary:hover:not(:disabled) {
    background: var(--cm-primary-dark);
}

.cm-btn-secondary {
    color: var(--cm-neutral-700);
    background: var(--cm-white);
    border-color: var(--cm-neutral-300);
}

.cm-btn-ghost {
    color: var(--cm-primary);
    background: var(--cm-primary-soft);
    border-color: #bfdbfe;
}

.cm-room-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.cm-room-card {
    padding: 12px 14px;
    background: var(--cm-white);
    border: 1px solid var(--cm-neutral-200);
    border-radius: 12px;
}

.cm-room-card.is-selected {
    border-color: var(--cm-primary);
    background: var(--cm-primary-soft);
}

.cm-room-selected {
    border-color: var(--cm-success);
    background: var(--cm-success-soft);
}

.cm-room-card.is-busy {
    opacity: 0.78;
    background: var(--cm-neutral-50);
}

.cm-room-top {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 8px;
}

.cm-room-top h3 {
    margin: 0;
    font-size: 14px;
}

.cm-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 8px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 700;
}

.cm-badge::before {
    content: "";
    width: 7px;
    height: 7px;
    border-radius: 999px;
    background: currentColor;
}

.cm-badge-ok {
    color: var(--cm-success);
    background: var(--cm-success-soft);
}

.cm-badge-busy {
    color: var(--cm-error);
    background: var(--cm-error-soft);
}

.cm-room-meta,
.cm-room-amenities {
    margin: 6px 0 0;
    color: var(--cm-neutral-500);
    font-size: 12px;
    line-height: 18px;
}

.cm-room-actions {
    margin-top: 10px;
}

.cm-fixed-eq,
.cm-borrow-eq {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.cm-fixed-item {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--cm-success);
    font-size: 13px;
    font-weight: 600;
}

.cm-eq-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 10px 12px;
    border: 1px solid var(--cm-neutral-200);
    border-radius: 10px;
}

.cm-eq-row.is-empty {
    background: var(--cm-error-soft);
}

.cm-stepper {
    display: inline-flex;
    align-items: center;
    gap: 4px;
}

.cm-stepper button {
    width: 28px;
    height: 28px;
    color: var(--cm-neutral-700);
    background: var(--cm-white);
    border: 1px solid var(--cm-neutral-300);
    border-radius: 6px;
    font-weight: 700;
}

.cm-stepper button:focus-visible {
    outline: none;
    box-shadow: var(--cm-focus);
}

.cm-stepper span {
    min-width: 22px;
    text-align: center;
    font-weight: 700;
}

.cm-alert {
    display: none;
    gap: 8px;
    padding: 10px 12px;
    border-radius: 10px;
    font-size: 12.5px;
    line-height: 18px;
}

.cm-alert.is-open {
    display: flex;
    flex-direction: column;
}

.cm-alert-warn {
    color: #92400e;
    background: var(--cm-warning-soft);
    border: 1px solid #fde68a;
}

.cm-alert-error {
    color: var(--cm-error);
    background: var(--cm-error-soft);
    border: 1px solid #fecaca;
}

.cm-alert-ok {
    color: var(--cm-success);
    background: var(--cm-success-soft);
    border: 1px solid #bbf7d0;
}

.cm-summary-card {
    padding: 12px;
    background: var(--cm-white);
    border: 1px solid var(--cm-neutral-200);
    border-radius: 12px;
}

.cm-summary-card h2 {
    margin: 0 0 10px;
    font-size: 14px;
}

.cm-summary-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin: 0;
    padding: 0;
    list-style: none;
    font-size: 13px;
    color: var(--cm-neutral-700);
}

.cm-summary-list li {
    display: flex;
    gap: 8px;
    line-height: 1.4;
}

.cm-status {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 10px 12px;
    border-radius: 10px;
    font-size: 12.5px;
    font-weight: 650;
}

.cm-status.is-ok {
    color: var(--cm-success);
    background: var(--cm-success-soft);
}

.cm-status.is-warn {
    color: var(--cm-warning);
    background: var(--cm-warning-soft);
}

.cm-summary-actions {
    margin-top: auto;
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.cm-empty,
.cm-loading {
    padding: 16px 8px;
    color: var(--cm-neutral-500);
    font-size: 13px;
    text-align: center;
}

.cm-skeleton {
    height: 72px;
    border-radius: 12px;
    background: linear-gradient(90deg, #f1f5f9, #e2e8f0, #f1f5f9);
    background-size: 200% 100%;
    animation: cmPulse 1.1s ease-in-out infinite;
}

@keyframes cmPulse {
    0% { background-position: 0 0; }
    100% { background-position: -200% 0; }
}

.cm-success {
    display: none;
    flex: 1;
    align-items: center;
    justify-content: center;
    padding: 48px 24px;
    text-align: center;
}

.cm-dialog.is-success .cm-layout {
    display: none;
}

.cm-dialog.is-success .cm-success {
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.cm-success-icon {
    width: 52px;
    height: 52px;
    margin: 0 auto 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--cm-success);
    background: var(--cm-success-soft);
    border-radius: 14px;
    font-size: 24px;
}

.cm-top-create {
    min-height: 36px;
    padding: 0 14px;
    color: var(--cm-white);
    background: var(--cm-primary);
    border: 0;
    border-radius: 8px;
    font-size: 12.5px;
    font-weight: 650;
}

.cm-top-create:hover {
    background: var(--cm-primary-dark);
}

@media (max-width: 860px) {
    .cm-layout {
        grid-template-columns: 1fr;
    }

    .cm-summary-pane {
        border-left: 0;
        border-top: 1px solid var(--cm-neutral-200);
    }

    .cm-time-grid,
    .cm-recurring-extra.is-open,
    .cm-mode {
        grid-template-columns: 1fr;
    }
}

@media (prefers-reduced-motion: reduce) {
    .cm-skeleton {
        animation: none;
    }
}
````

## File: migrations/001_add_meeting_recurring_columns.sql
````sql
-- Additive migration for existing MySQL databases. Run while using meeting_db.
-- Safe to re-run: each column is only added if it does not already exist.

USE meeting_db;

-- Check and add is_recurring
SET @has_is_recurring = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME   = 'meetings'
      AND COLUMN_NAME  = 'is_recurring'
);

SET @add_is_recurring = IF(
    @has_is_recurring = 0,
    'ALTER TABLE meetings ADD COLUMN is_recurring TINYINT(1) NOT NULL DEFAULT 0 AFTER description',
    'SELECT 1'
);
PREPARE stmt FROM @add_is_recurring;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Check and add recurring_type
SET @has_recurring_type = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME   = 'meetings'
      AND COLUMN_NAME  = 'recurring_type'
);

SET @add_recurring_type = IF(
    @has_recurring_type = 0,
    'ALTER TABLE meetings ADD COLUMN recurring_type VARCHAR(20) NULL AFTER is_recurring',
    'SELECT 1'
);
PREPARE stmt FROM @add_recurring_type;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
````

## File: migrations/002_add_meeting_participants.sql
````sql
-- Additive migration: meeting_participants . Does not drop any database or data.
USE meeting_db;

CREATE TABLE IF NOT EXISTS meeting_participants (
    id         INT UNSIGNED NOT NULL AUTO_INCREMENT,
    meeting_id INT UNSIGNED NOT NULL,
    user_id    INT UNSIGNED NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_meeting_participant (meeting_id, user_id),
    CONSTRAINT fk_meeting_participants_meeting FOREIGN KEY (meeting_id) REFERENCES meetings (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_meeting_participants_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
````

## File: migrations/003_add_equipment_tables.sql
````sql
-- 1. Bảng danh mục thiết bị trong kho
CREATE TABLE IF NOT EXISTS equipments (
    id          INT UNSIGNED NOT NULL AUTO_INCREMENT,
    name        VARCHAR(150) NOT NULL,
    code        VARCHAR(50) DEFAULT NULL,
    category    VARCHAR(50) DEFAULT NULL,
    total_qty   INT NOT NULL DEFAULT 1,
    description TEXT DEFAULT NULL,
    is_active   TINYINT(1) NOT NULL DEFAULT 1,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_equipments_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Bảng đăng ký mượn thiết bị theo cuộc họp
CREATE TABLE IF NOT EXISTS meeting_equipments (
    id           INT UNSIGNED NOT NULL AUTO_INCREMENT,
    meeting_id   INT UNSIGNED NOT NULL,
    equipment_id INT UNSIGNED NOT NULL,
    quantity     INT NOT NULL DEFAULT 1,
    note         VARCHAR(255) DEFAULT NULL,
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_meeting_equipment (meeting_id, equipment_id),
    KEY idx_meeting_equipments_meeting (meeting_id),
    KEY idx_meeting_equipments_equipment (equipment_id),
    CONSTRAINT fk_me_meeting FOREIGN KEY (meeting_id) REFERENCES meetings (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_me_equipment FOREIGN KEY (equipment_id) REFERENCES equipments (id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Bảng thiết bị cố định đi kèm phòng
CREATE TABLE IF NOT EXISTS room_equipments (
    id           INT UNSIGNED NOT NULL AUTO_INCREMENT,
    room_id      INT UNSIGNED NOT NULL,
    equipment_id INT UNSIGNED NOT NULL,
    quantity     INT NOT NULL DEFAULT 1,
    PRIMARY KEY (id),
    UNIQUE KEY uq_room_equipment (room_id, equipment_id),
    CONSTRAINT fk_re_room FOREIGN KEY (room_id) REFERENCES rooms (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_re_equipment FOREIGN KEY (equipment_id) REFERENCES equipments (id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
````

## File: migrations/004_add_room_amenities.sql
````sql
ALTER TABLE rooms
    ADD COLUMN amenities TEXT DEFAULT NULL AFTER description;
````

## File: migrations/005_add_meeting_type_and_link.sql
````sql
-- Add meeting mode/link fields and allow room deletion without deleting meetings.
-- Safe to re-run against databases where some or all changes already exist.

USE meeting_db;

-- Add meeting_type when it is not already present.
SET @has_meeting_type = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'meetings'
      AND COLUMN_NAME = 'meeting_type'
);

SET @add_meeting_type = IF(
    @has_meeting_type = 0,
    'ALTER TABLE meetings ADD COLUMN meeting_type VARCHAR(20) NOT NULL DEFAULT ''offline''',
    'SELECT 1'
);
PREPARE stmt FROM @add_meeting_type;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Add meeting_link when it is not already present.
SET @has_meeting_link = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'meetings'
      AND COLUMN_NAME = 'meeting_link'
);

SET @add_meeting_link = IF(
    @has_meeting_link = 0,
    'ALTER TABLE meetings ADD COLUMN meeting_link VARCHAR(255) NULL',
    'SELECT 1'
);
PREPARE stmt FROM @add_meeting_link;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Replace the current room foreign key, regardless of its constraint name.
SET @room_fk = (
    SELECT CONSTRAINT_NAME
    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'meetings'
      AND COLUMN_NAME = 'room_id'
      AND REFERENCED_TABLE_NAME = 'rooms'
    LIMIT 1
);

SET @drop_room_fk = IF(
    @room_fk IS NULL,
    'SELECT 1',
    CONCAT('ALTER TABLE meetings DROP FOREIGN KEY `', @room_fk, '`')
);
PREPARE stmt FROM @drop_room_fk;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

ALTER TABLE meetings MODIFY COLUMN room_id INT UNSIGNED NULL;
ALTER TABLE meetings
    ADD CONSTRAINT fk_meetings_room
    FOREIGN KEY (room_id) REFERENCES rooms (id)
    ON DELETE SET NULL ON UPDATE CASCADE;
````

## File: migrations/005_align_meetings_schema.sql
````sql
-- ============================================================
-- Migration 005: Align meetings table với model thực tế
-- Safe: chỉ modify room_id nullable + update default meeting_type
-- Không DROP cột nào, không mất dữ liệu
-- ============================================================
USE meeting_db;

-- 1. Chuẩn hóa meeting_type: đổi default về lowercase 'offline'
--    Các row cũ đang có giá trị 'OFFLINE' — cập nhật về lowercase để nhất quán
UPDATE meetings SET meeting_type = 'offline' WHERE meeting_type = 'OFFLINE';
UPDATE meetings SET meeting_type = 'online'  WHERE meeting_type = 'ONLINE';

ALTER TABLE meetings
    MODIFY COLUMN meeting_type VARCHAR(20) NOT NULL DEFAULT 'offline';

-- 2. Nullable room_id: drop FK cũ, alter column, re-add FK với SET NULL
ALTER TABLE meetings DROP FOREIGN KEY meetings_ibfk_1;
ALTER TABLE meetings MODIFY COLUMN room_id INT NULL;
ALTER TABLE meetings
    ADD CONSTRAINT fk_meetings_room
    FOREIGN KEY (room_id) REFERENCES rooms(id)
    ON DELETE SET NULL ON UPDATE CASCADE;

-- Verify: DESCRIBE meetings;
````

## File: migrations/006_reconcile_live_room_meeting_schema.sql
````sql
-- Reconcile an existing MySQL database with the current room/meeting models.
-- Additive and repeatable: existing row values are retained.

SET @has_amenities = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'rooms'
      AND COLUMN_NAME = 'amenities'
);
SET @add_amenities = IF(
    @has_amenities = 0,
    'ALTER TABLE rooms ADD COLUMN amenities TEXT NULL',
    'SELECT 1'
);
PREPARE stmt FROM @add_amenities;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_meeting_type = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'meetings'
      AND COLUMN_NAME = 'meeting_type'
);
SET @add_meeting_type = IF(
    @has_meeting_type = 0,
    'ALTER TABLE meetings ADD COLUMN meeting_type VARCHAR(20) NOT NULL DEFAULT ''offline''',
    'SELECT 1'
);
PREPARE stmt FROM @add_meeting_type;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_meeting_link = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'meetings'
      AND COLUMN_NAME = 'meeting_link'
);
SET @add_meeting_link = IF(
    @has_meeting_link = 0,
    'ALTER TABLE meetings ADD COLUMN meeting_link VARCHAR(255) NULL',
    'SELECT 1'
);
PREPARE stmt FROM @add_meeting_link;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @room_fk = (
    SELECT CONSTRAINT_NAME
    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'meetings'
      AND COLUMN_NAME = 'room_id'
      AND REFERENCED_TABLE_NAME = 'rooms'
    LIMIT 1
);
SET @drop_room_fk = IF(
    @room_fk IS NULL,
    'SELECT 1',
    CONCAT('ALTER TABLE meetings DROP FOREIGN KEY `', @room_fk, '`')
);
PREPARE stmt FROM @drop_room_fk;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

ALTER TABLE meetings
    MODIFY COLUMN room_id INT NULL COMMENT 'Phòng họp';

ALTER TABLE meetings
    ADD CONSTRAINT fk_meetings_room
    FOREIGN KEY (room_id) REFERENCES rooms (id)
    ON DELETE SET NULL ON UPDATE CASCADE;
````

## File: migrations/007_add_google_calendar_connection.sql
````sql
-- Store encrypted Google Calendar refresh tokens for opted-in users.
-- Run against the application's configured database.

SET @has_google_refresh_token = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'users'
      AND COLUMN_NAME = 'google_refresh_token'
);
SET @add_google_refresh_token = IF(
    @has_google_refresh_token = 0,
    'ALTER TABLE users ADD COLUMN google_refresh_token TEXT NULL',
    'SELECT 1'
);
PREPARE stmt FROM @add_google_refresh_token;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_google_calendar_connected_at = (
    SELECT COUNT(*)
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'users'
      AND COLUMN_NAME = 'google_calendar_connected_at'
);
SET @add_google_calendar_connected_at = IF(
    @has_google_calendar_connected_at = 0,
    'ALTER TABLE users ADD COLUMN google_calendar_connected_at DATETIME NULL',
    'SELECT 1'
);
PREPARE stmt FROM @add_google_calendar_connected_at;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
````

## File: migrations/007_google_calendar_invitees.sql
````sql
-- Calendar refresh tokens are stored encrypted by the application.
-- Apply this migration to the configured MySQL database before deploying.

SET @has_google_refresh_token = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'users'
      AND COLUMN_NAME = 'google_refresh_token'
);
SET @add_google_refresh_token = IF(
    @has_google_refresh_token = 0,
    'ALTER TABLE users ADD COLUMN google_refresh_token TEXT NULL',
    'SELECT 1'
);
PREPARE stmt FROM @add_google_refresh_token;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @has_google_calendar_connected_at = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'users'
      AND COLUMN_NAME = 'google_calendar_connected_at'
);
SET @add_google_calendar_connected_at = IF(
    @has_google_calendar_connected_at = 0,
    'ALTER TABLE users ADD COLUMN google_calendar_connected_at DATETIME NULL',
    'SELECT 1'
);
PREPARE stmt FROM @add_google_calendar_connected_at;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

CREATE TABLE IF NOT EXISTS google_calendar_events (
    id INT NOT NULL AUTO_INCREMENT,
    user_id INT NOT NULL,
    meeting_id INT NOT NULL,
    google_event_id VARCHAR(255) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_google_event_user_meeting (user_id, meeting_id),
    UNIQUE KEY uq_google_event_user_event (user_id, google_event_id),
    CONSTRAINT fk_google_calendar_event_user
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_google_calendar_event_meeting
        FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
````

## File: migrations/008_add_meeting_participant_response_status.sql
````sql
-- Track invitee RSVP state for the dashboard and meeting organizers.
SET @has_response_status = (
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'meeting_participants'
      AND COLUMN_NAME = 'response_status'
);
SET @add_response_status = IF(
    @has_response_status = 0,
    'ALTER TABLE meeting_participants ADD COLUMN response_status VARCHAR(20) NOT NULL DEFAULT ''pending''',
    'SELECT 1'
);
PREPARE stmt FROM @add_response_status;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
````

## File: tests/__init__.py
````python

````

## File: tests/conftest.py
````python
"""Pytest configuration: in-memory SQLite, fixtures, and app setup."""

import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# Ensure project root is importable and force SQLite BEFORE any app import.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DATABASE_URL"] = "sqlite:///test.db"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"

from app.core.database import Base, get_db, engine as app_engine
from app.main import app

# Release connections opened by create_all at import time.
app_engine.dispose()

# Test engine with SQLite-friendly settings.
test_engine = create_engine(
    "sqlite:///test.db",
    connect_args={"check_same_thread": False},
)


@event.listens_for(test_engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def _override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def _recreate_tables():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db_session():
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
````

## File: tests/helpers.py
````python
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
````

## File: tests/test_calendar_email.py
````python
from datetime import datetime, timedelta

from app.models.meeting import MeetingParticipant
from app.services import calendar_email_service
from tests.helpers import _create_meeting, _create_room, _create_user


class FakeSMTP:
    sent_messages = []

    def __init__(self, host, port, timeout):
        self.host = host
        self.port = port
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def ehlo(self):
        return None

    def starttls(self, context):
        return None

    def login(self, username, password):
        return None

    def send_message(self, message):
        self.sent_messages.append(message)


def test_unconnected_invitee_receives_calendar_consent_email(
    db_session, monkeypatch
):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "calendar@example.test")
    monkeypatch.setenv("SMTP_PASSWORD", "test-smtp-password")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "calendar@example.test")
    monkeypatch.setenv("SMTP_STARTTLS", "false")
    monkeypatch.setenv("BACKEND_PUBLIC_URL", "https://roomsync.example.test")
    FakeSMTP.sent_messages = []
    monkeypatch.setattr(calendar_email_service.smtplib, "SMTP", FakeSMTP)

    organizer = _create_user(db_session, "email-organizer")
    invitee = _create_user(db_session, "email-invitee")
    invitee.email = "invitee@example.test"
    db_session.commit()
    room = _create_room(db_session, "Calendar Email Room")
    start = datetime.now() + timedelta(days=2)
    meeting = _create_meeting(db_session, room, organizer, start, start + timedelta(hours=1))
    db_session.add(MeetingParticipant(meeting_id=meeting.id, user_id=invitee.id))
    db_session.commit()

    calendar_email_service.request_calendar_access_for_invitees([invitee.id], [meeting.id])

    assert len(FakeSMTP.sent_messages) == 1
    sent = FakeSMTP.sent_messages[0]
    assert sent["To"] == "invitee@example.test"
    assert "Kết nối Google Calendar" in sent["Subject"]
    assert "/api/auth/google/calendar/connect?" in sent.get_content()
    assert "Calendar Email Room" not in sent.get_content()
    assert meeting.title in sent.get_content()
````

## File: tests/test_equipment_availability.py
````python
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.equipment import Equipment, MeetingEquipment
from tests.helpers import _create_meeting, _create_room, _create_user


def _create_equipment(db: Session, total_qty: int = 5) -> Equipment:
    equipment = Equipment(
        name="Conference microphone",
        code="MIC-01",
        category="Audio",
        total_qty=total_qty,
        is_active=True,
    )
    db.add(equipment)
    db.commit()
    db.refresh(equipment)
    return equipment


def _attach_equipment(db: Session, meeting_id: int, equipment_id: int, quantity: int):
    allocation = MeetingEquipment(
        meeting_id=meeting_id,
        equipment_id=equipment_id,
        quantity=quantity,
    )
    db.add(allocation)
    db.commit()
    return allocation


def test_availability_tracks_overlapping_bookings_and_inactive_status(
    client: TestClient, db_session: Session
):
    organizer = _create_user(db_session, "equipment-organizer")
    room = _create_room(db_session, "Equipment Room")
    equipment = _create_equipment(db_session)

    first_meeting = _create_meeting(
        db_session,
        room,
        organizer,
        datetime(2026, 10, 5, 9, 0),
        datetime(2026, 10, 5, 10, 0),
    )
    _attach_equipment(db_session, first_meeting.id, equipment.id, 2)

    params = {
        "start_time": "2026-10-05T09:30:00",
        "end_time": "2026-10-05T10:30:00",
    }
    response = client.get("/api/equipments/availability", params=params)
    assert response.status_code == 200
    item = response.json()[0]
    assert item["booked_qty"] == 2
    assert item["available_qty"] == 3
    assert item["status_label"] == "Có sẵn"

    second_meeting = _create_meeting(
        db_session,
        room,
        organizer,
        datetime(2026, 10, 5, 9, 45),
        datetime(2026, 10, 5, 10, 15),
    )
    _attach_equipment(db_session, second_meeting.id, equipment.id, 3)

    response = client.get("/api/equipments/availability", params=params)
    assert response.status_code == 200
    item = response.json()[0]
    assert item["booked_qty"] == 5
    assert item["available_qty"] == 0
    assert item["status_label"] == "Đã đặt hết"

    equipment.is_active = False
    db_session.commit()
    response = client.get("/api/equipments/availability", params=params)
    assert response.status_code == 200
    item = response.json()[0]
    assert item["status_label"] == "Ngừng hoạt động / Bảo trì"


def test_availability_ignores_canceled_meetings_and_supports_filters(
    client: TestClient, db_session: Session
):
    organizer = _create_user(db_session, "equipment-canceled-organizer")
    room = _create_room(db_session, "Equipment Canceled Room")
    equipment = _create_equipment(db_session)
    canceled_meeting = _create_meeting(
        db_session,
        room,
        organizer,
        datetime(2026, 10, 5, 9, 0),
        datetime(2026, 10, 5, 10, 0),
        status="CANCELLED",
    )
    _attach_equipment(db_session, canceled_meeting.id, equipment.id, 5)

    response = client.get(
        "/api/equipments/availability",
        params={
            "start_time": "2026-10-05T09:30:00",
            "end_time": "2026-10-05T10:30:00",
            "category": "Audio",
            "search": "MIC-01",
        },
    )
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["booked_qty"] == 0


def test_availability_defaults_to_current_time(client: TestClient, db_session: Session):
    _create_equipment(db_session)

    response = client.get("/api/equipments/availability")

    assert response.status_code == 200
    assert response.json()[0]["available_qty"] == 5
````

## File: tests/test_google_calendar_delete.py
````python
from datetime import datetime, timedelta
from types import SimpleNamespace

import httplib2
import pytest
from cryptography.fernet import Fernet
from googleapiclient.errors import HttpError
from sqlalchemy.orm import sessionmaker

from app.models.google_calendar_event import GoogleCalendarEvent
from app.services import google_calendar_service
from app.services.google_calendar_service import encrypt_refresh_token
from app.models.user import User
from tests.conftest import test_engine
from tests.helpers import _create_user


class FakeDeleteRequest:
    def __init__(self, error=None):
        self.error = error

    def execute(self):
        if self.error:
            raise self.error
        return None


class FakeCalendarEvents:
    def __init__(self, error=None):
        self.error = error
        self.arguments = None

    def delete(self, **kwargs):
        self.arguments = kwargs
        return FakeDeleteRequest(self.error)


class FakeCalendarService:
    def __init__(self, events):
        self._events = events

    def events(self):
        return self._events


def _http_error(status_code):
    response = httplib2.Response({"status": str(status_code), "reason": "test"})
    return HttpError(response, b'{"error":{"message":"test"}}')


@pytest.mark.parametrize("status_code", [404, 410])
def test_delete_calendar_event_treats_missing_google_event_as_success(
    monkeypatch, status_code
):
    monkeypatch.setenv("GOOGLE_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    user = User(id=42, google_refresh_token=encrypt_refresh_token("refresh-token"))
    events = FakeCalendarEvents(_http_error(status_code))
    monkeypatch.setattr(google_calendar_service.Credentials, "refresh", lambda self, request: None)
    monkeypatch.setattr(
        google_calendar_service,
        "build",
        lambda *args, **kwargs: FakeCalendarService(events),
    )

    assert google_calendar_service.delete_google_calendar_event(user, "event-42") is True
    assert events.arguments == {"calendarId": "primary", "eventId": "event-42"}


def test_delete_calendar_event_returns_false_for_other_google_errors(monkeypatch):
    monkeypatch.setenv("GOOGLE_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    user = User(id=43, google_refresh_token=encrypt_refresh_token("refresh-token"))
    events = FakeCalendarEvents(_http_error(500))
    monkeypatch.setattr(google_calendar_service.Credentials, "refresh", lambda self, request: None)
    monkeypatch.setattr(
        google_calendar_service,
        "build",
        lambda *args, **kwargs: FakeCalendarService(events),
    )

    assert google_calendar_service.delete_google_calendar_event(user, "event-43") is False


def test_cancel_worker_removes_mapping_only_after_success(db_session, monkeypatch):
    monkeypatch.setenv("GOOGLE_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    user = _create_user(db_session, "calendar-delete-user")
    user.google_refresh_token = encrypt_refresh_token("refresh-token")
    db_session.commit()

    from app.models.meeting import Meeting

    meeting = Meeting(
        title="Delete calendar event",
        room_id=None,
        organizer_id=user.id,
        start_time=datetime.now() + timedelta(days=2),
        end_time=datetime.now() + timedelta(days=2, hours=1),
        status="CANCELLED",
    )
    db_session.add(meeting)
    db_session.commit()
    db_session.add(
        GoogleCalendarEvent(
            user_id=user.id,
            meeting_id=meeting.id,
            google_event_id="event-to-delete",
        )
    )
    db_session.commit()

    session_factory = sessionmaker(bind=test_engine)
    monkeypatch.setattr(google_calendar_service, "SessionLocal", session_factory)
    deleted = []
    monkeypatch.setattr(
        google_calendar_service,
        "delete_google_calendar_event",
        lambda event_user, event_id: deleted.append((event_user.id, event_id)) or True,
    )

    google_calendar_service.delete_google_events_for_meeting(meeting.id)

    assert deleted == [(user.id, "event-to-delete")]
    assert db_session.query(GoogleCalendarEvent).filter_by(meeting_id=meeting.id).count() == 0
````

## File: tests/test_room_create.py
````python
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import _auth_header, _create_user, _make_token


def test_admin_can_create_room_with_amenities(client: TestClient, db_session: Session):
    admin = _create_user(db_session, "room-create-admin", role="admin")

    response = client.post(
        "/api/rooms/",
        json={
            "name": "API-created room",
            "location": "Floor 3",
            "capacity": 10,
            "amenities": ["Screen", "Wi-Fi"],
            "is_active": True,
        },
        headers=_auth_header(_make_token(admin)),
    )

    assert response.status_code == 201
    assert response.json()["name"] == "API-created room"
    assert response.json()["amenities"] == ["Screen", "Wi-Fi"]
````

## File: alembic.ini
````ini
# A generic, single database configuration.

[alembic]
# path to migration scripts.
# this is typically a path given in POSIX (e.g. forward slashes)
# format, relative to the token %(here)s which refers to the location of this
# ini file
script_location = %(here)s/alembic

# template used to generate migration file names; The default value is %%(rev)s_%%(slug)s
# Uncomment the line below if you want the files to be prepended with date and time
# see https://alembic.sqlalchemy.org/en/latest/tutorial.html#editing-the-ini-file
# for all available tokens
# file_template = %%(year)d_%%(month).2d_%%(day).2d_%%(hour).2d%%(minute).2d-%%(rev)s_%%(slug)s
# Or organize into date-based subdirectories (requires recursive_version_locations = true)
# file_template = %%(year)d/%%(month).2d/%%(day).2d_%%(hour).2d%%(minute).2d_%%(second).2d_%%(rev)s_%%(slug)s

# sys.path path, will be prepended to sys.path if present.
# defaults to the current working directory.  for multiple paths, the path separator
# is defined by "path_separator" below.
prepend_sys_path = .


# timezone to use when rendering the date within the migration file
# as well as the filename.
# If specified, requires the tzdata library which can be installed by adding
# `alembic[tz]` to the pip requirements.
# string value is passed to ZoneInfo()
# leave blank for localtime
# timezone =

# max length of characters to apply to the "slug" field
# truncate_slug_length = 40

# set to 'true' to run the environment during
# the 'revision' command, regardless of autogenerate
# revision_environment = false

# set to 'true' to allow .pyc and .pyo files without
# a source .py file to be detected as revisions in the
# versions/ directory
# sourceless = false

# version location specification; This defaults
# to <script_location>/versions.  When using multiple version
# directories, initial revisions must be specified with --version-path.
# The path separator used here should be the separator specified by "path_separator"
# below.
# version_locations = %(here)s/bar:%(here)s/bat:%(here)s/alembic/versions

# path_separator; This indicates what character is used to split lists of file
# paths, including version_locations and prepend_sys_path within configparser
# files such as alembic.ini.
# The default rendered in new alembic.ini files is "os", which uses os.pathsep
# to provide os-dependent path splitting.
#
# Note that in order to support legacy alembic.ini files, this default does NOT
# take place if path_separator is not present in alembic.ini.  If this
# option is omitted entirely, fallback logic is as follows:
#
# 1. Parsing of the version_locations option falls back to using the legacy
#    "version_path_separator" key, which if absent then falls back to the legacy
#    behavior of splitting on spaces and/or commas.
# 2. Parsing of the prepend_sys_path option falls back to the legacy
#    behavior of splitting on spaces, commas, or colons.
#
# Valid values for path_separator are:
#
# path_separator = :
# path_separator = ;
# path_separator = space
# path_separator = newline
#
# Use os.pathsep. Default configuration used for new projects.
path_separator = os

# set to 'true' to search source files recursively
# in each "version_locations" directory
# new in Alembic version 1.10
# recursive_version_locations = false

# the output encoding used when revision files
# are written from script.py.mako
# output_encoding = utf-8

# database URL.  This is consumed by the user-maintained env.py script only.
# other means of configuring database URLs may be customized within the env.py
# file.
sqlalchemy.url = driver://user:pass@localhost/dbname


[post_write_hooks]
# post_write_hooks defines scripts or Python functions that are run
# on newly generated revision scripts.  See the documentation for further
# detail and examples

# format using "black" - use the console_scripts runner, against the "black" entrypoint
# hooks = black
# black.type = console_scripts
# black.entrypoint = black
# black.options = -l 79 REVISION_SCRIPT_FILENAME

# lint with attempts to fix using "ruff" - use the module runner, against the "ruff" module
# hooks = ruff
# ruff.type = module
# ruff.module = ruff
# ruff.options = check --fix REVISION_SCRIPT_FILENAME

# Alternatively, use the exec runner to execute a binary found on your PATH
# hooks = ruff
# ruff.type = exec
# ruff.executable = ruff
# ruff.options = check --fix REVISION_SCRIPT_FILENAME

# Logging configuration.  This is also consumed by the user-maintained
# env.py script only.
[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARNING
handlers = console
qualname =

[logger_sqlalchemy]
level = WARNING
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
````

## File: FETCH_HEAD
````

````

## File: requirements-dev.txt
````
-r requirements.txt
pytest
httpx
````

## File: alembic/versions/33c26788d6a2_fix_missing_meeting_link_column.py
````python
"""Add the missing meeting_link column to meetings.

Revision ID: 33c26788d6a2
Revises: cf70acc36382
Create Date: 2026-10-09 19:15:47.700439
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "33c26788d6a2"
down_revision: Union[str, Sequence[str], None] = "cf70acc36382"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add meeting_link if the existing database does not already have it."""
    inspector = sa.inspect(op.get_bind())
    if "meetings" not in inspector.get_table_names():
        raise RuntimeError("The meetings table must exist before applying this migration.")

    columns = {column["name"] for column in inspector.get_columns("meetings")}
    if "meeting_link" not in columns:
        op.add_column("meetings", sa.Column("meeting_link", sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Remove meeting_link if present."""
    inspector = sa.inspect(op.get_bind())
    if "meetings" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("meetings")}
    if "meeting_link" in columns:
        op.drop_column("meetings", "meeting_link")
````

## File: alembic/versions/cf70acc36382_add_google_refresh_token_to_users.py
````python
"""Add google_refresh_token to users

Revision ID: cf70acc36382
Revises: 
Create Date: 2026-10-09 17:49:57.088496

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cf70acc36382'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Google Calendar OAuth columns to users when they are missing."""
    inspector = sa.inspect(op.get_bind())
    if "users" not in inspector.get_table_names():
        raise RuntimeError("The users table must exist before applying this migration.")

    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    if "google_refresh_token" not in existing_columns:
        op.add_column("users", sa.Column("google_refresh_token", sa.Text(), nullable=True))
    if "google_calendar_connected_at" not in existing_columns:
        op.add_column("users", sa.Column("google_calendar_connected_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Remove the Google Calendar OAuth columns when present."""
    inspector = sa.inspect(op.get_bind())
    if "users" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    if "google_calendar_connected_at" in existing_columns:
        op.drop_column("users", "google_calendar_connected_at")
    if "google_refresh_token" in existing_columns:
        op.drop_column("users", "google_refresh_token")
````

## File: app/models/notification.py
````python
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from datetime import datetime
from app.core.database import Base

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
````

## File: app/routers/equipment.py
````python
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.models.equipment import Equipment
from app.schemas.equipment import EquipmentCreate, EquipmentUpdate, EquipmentResponse, EquipmentStatusResponse
from app.services.equipment_service import get_equipment_availability
from app.core.security import require_role

router = APIRouter()

# 🟢 Dấu "/" ở cuối để khớp với yêu cầu GET /api/equipments/?include_inactive=true từ Frontend
@router.get("/", response_model=List[EquipmentResponse])
def get_equipments(
    skip: int = 0,
    limit: int = 100,
    include_inactive: bool = Query(False, description="Nếu True, trả về cả các thiết bị đã ngưng hoạt động/vô hiệu hóa"),
    db: Session = Depends(get_db),
):
    query = db.query(Equipment)
    if not include_inactive:
        query = query.filter(Equipment.is_active == True)
    return query.offset(skip).limit(limit).all()


@router.get("/availability", response_model=List[EquipmentStatusResponse])
def get_equipment_availability_list(
    start_time: datetime | None = Query(None, description="Thời gian bắt đầu"),
    end_time: datetime | None = Query(None, description="Thời gian kết thúc"),
    category: str | None = Query(None),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
):
    if start_time is None and end_time is None:
        start_time = end_time = datetime.now()
    elif start_time is None:
        start_time = end_time
    elif end_time is None:
        end_time = start_time

    if start_time > end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thời gian bắt đầu phải nhỏ hơn hoặc bằng thời gian kết thúc.",
        )

    return get_equipment_availability(
        db=db,
        start_time=start_time,
        end_time=end_time,
        category=category,
        search=search,
    )


@router.post("/", response_model=EquipmentResponse, status_code=status.HTTP_201_CREATED)
def create_equipment(
    payload: EquipmentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin")),
):
    equip = Equipment(**payload.model_dump())
    db.add(equip)
    db.commit()
    db.refresh(equip)
    return equip


@router.put("/{equipment_id}", response_model=EquipmentResponse)
def update_equipment(
    equipment_id: int,
    payload: EquipmentUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin")),
):
    equip = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equip:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(equip, field, value)

    db.commit()
    db.refresh(equip)
    return equip


@router.delete("/{equipment_id}", status_code=status.HTTP_200_OK)
def delete_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin")),
):
    equip = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equip:
        raise HTTPException(status_code=404, detail="Không tìm thấy thiết bị")

    equip.is_active = False
    db.commit()
    return {"status": "success", "message": f"Đã chuyển trạng thái thiết bị '{equip.name}' thành ngừng hoạt động."}
````

## File: app/routers/users.py
````python
# app/routers/users.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter(prefix="/users", tags=["Users"])


class UserSimpleResponse(BaseModel):
    id: int
    full_name: Optional[str] = None
    email: str

    class Config:
        from_attributes = True


class UserUpdateProfile(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None


@router.get("/", response_model=List[UserSimpleResponse])
def get_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lấy danh sách người dùng để mời tham dự cuộc họp"""
    return db.query(User).all()


@router.get("/me", response_model=UserSimpleResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    """Lấy thông tin chi tiết của tài khoản đang đăng nhập"""
    return current_user


@router.put("/me", response_model=UserSimpleResponse)
def update_my_profile(
    payload: UserUpdateProfile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cập nhật thông tin cá nhân (Tên, Email) của người dùng hiện tại xuống DB"""
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.email is not None:
        # Kiểm tra xem email mới có bị trùng với tài khoản khác không
        existing_user = db.query(User).filter(User.email == payload.email, User.id != current_user.id).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email này đã được sử dụng bởi tài khoản khác."
            )
        current_user.email = payload.email

    db.commit()
    db.refresh(current_user)
    return current_user
````

## File: app/schemas/auth.py
````python
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50, description="Tên đăng nhập")
    password: str = Field(..., min_length=1, max_length=128, description="Mật khẩu")


class UserResponse(BaseModel):
    id: int
    username: str
    email: str | None
    full_name: str | None
    role: str
    is_active: bool

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "username": "admin",
                "email": "admin@meeting.local",
                "full_name": "Quản trị viên",
                "role": "admin",
                "is_active": True,
            }
        }


class TokenResponse(BaseModel):
    """Schema phản hồi JWT Token sau khi đăng nhập thành công."""
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
    full_name: str | None = None


class LoginResponse(BaseModel):
    status: str = "success"
    message: str = "Đăng nhập thành công"
    user: UserResponse

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Đăng nhập thành công",
                "user": {
                    "id": 1,
                    "username": "admin",
                    "email": "admin@meeting.local",
                    "full_name": "Quản trị viên",
                    "role": "admin",
                    "is_active": True,
                },
            }
        }
````

## File: app/schemas/equipment.py
````python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# --- Equipment Base & CRUD ---
class EquipmentBase(BaseModel):
    name: str = Field(..., max_length=150)
    code: Optional[str] = Field(None, max_length=50)
    category: Optional[str] = Field(None, max_length=50)
    total_qty: int = Field(1, ge=1)
    description: Optional[str] = None
    is_active: bool = True

class EquipmentCreate(EquipmentBase):
    pass

class EquipmentUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    category: Optional[str] = None
    total_qty: Optional[int] = Field(None, ge=1)
    description: Optional[str] = None
    is_active: Optional[bool] = None

class EquipmentResponse(EquipmentBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class EquipmentStatusResponse(EquipmentResponse):
    booked_qty: int
    available_qty: int
    status_label: str

# --- Meeting Equipment Request/Response ---
class MeetingEquipmentItemInput(BaseModel):
    equipment_id: int
    quantity: int = Field(1, ge=1)
    note: Optional[str] = None

class MeetingEquipmentItemOutput(BaseModel):
    equipment_id: int
    equipment_name: str
    quantity: int
    note: Optional[str] = None

    class Config:
        from_attributes = True
````

## File: app/services/equipment_service.py
````python
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from app.models.equipment import Equipment, MeetingEquipment
from app.models.meeting import Meeting
from app.schemas.equipment import EquipmentResponse, EquipmentStatusResponse, MeetingEquipmentItemInput


def get_equipment_availability(
    db: Session,
    start_time: datetime,
    end_time: datetime,
    category: Optional[str] = None,
    search: Optional[str] = None,
) -> List[EquipmentStatusResponse]:
    booked_quantities = (
        db.query(
            MeetingEquipment.equipment_id.label("equipment_id"),
            func.sum(MeetingEquipment.quantity).label("booked_qty"),
        )
        .join(Meeting, MeetingEquipment.meeting_id == Meeting.id)
        .filter(
            func.upper(Meeting.status).notin_(
                ["CANCELLED", "CANCELLED_NO_SHOW", "COMPLETED"]
            ),
            Meeting.start_time < end_time,
            Meeting.end_time > start_time,
        )
        .group_by(MeetingEquipment.equipment_id)
        .subquery()
    )

    query = (
        db.query(Equipment, func.coalesce(booked_quantities.c.booked_qty, 0))
        .outerjoin(booked_quantities, Equipment.id == booked_quantities.c.equipment_id)
    )
    if category:
        query = query.filter(Equipment.category == category)
    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            Equipment.name.ilike(search_term) | Equipment.code.ilike(search_term)
        )

    results = []
    for equipment, booked_qty in query.order_by(Equipment.name).all():
        booked_qty = int(booked_qty)
        available_qty = equipment.total_qty - booked_qty
        if not equipment.is_active:
            status_label = "Ngừng hoạt động / Bảo trì"
        elif available_qty <= 0:
            status_label = "Đã đặt hết"
        else:
            status_label = "Có sẵn"

        response_data = EquipmentResponse.model_validate(equipment).model_dump()
        response_data.update(
            {
                "booked_qty": booked_qty,
                "available_qty": available_qty,
                "status_label": status_label,
            }
        )
        results.append(EquipmentStatusResponse.model_validate(response_data))
    return results

def check_equipment_availability(
    db: Session,
    start_time: datetime,
    end_time: datetime,
    requested_items: List[MeetingEquipmentItemInput],
    exclude_meeting_id: Optional[int] = None
):

    """
    Tính toán số lượng khả dụng = Tổng tồn kho - Số lượng đã đặt trong các cuộc họp trùng khung giờ
    """
    for item in requested_items:
        # 1. Lấy thông tin thiết bị
        equip = db.query(Equipment).filter(Equipment.id == item.equipment_id, Equipment.is_active == True).first()
        if not equip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Thiết bị với ID {item.equipment_id} không tồn tại hoặc đã bị vô hiệu hóa."
            )

        # 2. Truy vấn tổng số lượng thiết bị này đã được đặt ở các cuộc họp khác trùng thời gian
        # Điều kiện trùng giờ: (Meeting.start_time < end_time) AND (Meeting.end_time > start_time)
        query = (
            db.query(func.coalesce(func.sum(MeetingEquipment.quantity), 0))
            .join(Meeting, MeetingEquipment.meeting_id == Meeting.id)
            .filter(
                MeetingEquipment.equipment_id == item.equipment_id,
                func.upper(Meeting.status).notin_(
                    ["CANCELLED", "CANCELLED_NO_SHOW", "COMPLETED"]
                ),
                Meeting.start_time < end_time,
                Meeting.end_time > start_time
            )
        )

        if exclude_meeting_id:
            query = query.filter(Meeting.id != exclude_meeting_id)

        booked_qty = query.scalar() or 0
        available_qty = equip.total_qty - booked_qty

        if item.quantity > available_qty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Thiết bị '{equip.name}' không đủ số lượng trong khung giờ này. "
                       f"Yêu cầu: {item.quantity}, Khả dụng: {available_qty} (Tổng: {equip.total_qty}, Đã đặt: {booked_qty})."
            )
````

## File: app/services/google_calendar_service.py
````python
import base64
import hashlib
import hmac
import logging
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import SECRET_KEY
from app.models.google_calendar_event import GoogleCalendarEvent
from app.models.meeting import Meeting, MeetingParticipant
from app.models.user import User

logger = logging.getLogger(__name__)
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_TOKEN_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
GOOGLE_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
GOOGLE_CALENDAR_EVENTS_SCOPE = "https://www.googleapis.com/auth/calendar.events"


def _fernet() -> Fernet:
    key = os.getenv("GOOGLE_TOKEN_ENCRYPTION_KEY")
    if not key:
        raise RuntimeError("GOOGLE_TOKEN_ENCRYPTION_KEY is not configured")
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise RuntimeError("GOOGLE_TOKEN_ENCRYPTION_KEY must be a valid Fernet key") from exc


def encrypt_refresh_token(refresh_token: str) -> str:
    return _fernet().encrypt(refresh_token.encode("utf-8")).decode("ascii")


def decrypt_refresh_token(encrypted_token: str) -> str:
    try:
        return _fernet().decrypt(encrypted_token.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeEncodeError) as exc:
        raise RuntimeError("Stored Google refresh token cannot be decrypted") from exc


def make_calendar_consent_url(user: User) -> str:
    if not user.email:
        raise ValueError("Calendar consent requires a user email")
    expires = int(datetime.now(timezone.utc).timestamp()) + 7 * 24 * 60 * 60
    message = f"{user.id}:{user.email.strip().lower()}:{expires}"
    signature = hmac.new(
        SECRET_KEY.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    backend_url = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000").rstrip("/")
    query = urlencode({"user_id": user.id, "expires": expires, "signature": signature})
    return f"{backend_url}/api/auth/google/calendar/connect?{query}"


def verify_calendar_consent_signature(user: User, expires: int, signature: str) -> bool:
    import time

    if expires < int(time.time()) or not user.email:
        return False
    message = f"{user.id}:{user.email.strip().lower()}:{expires}"
    expected = hmac.new(
        SECRET_KEY.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def _google_config() -> tuple[str, str]:
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("Google OAuth client credentials are not configured")
    return client_id, client_secret


def _access_token(refresh_token: str) -> str:
    client_id, client_secret = _google_config()
    response = httpx.post(
        GOOGLE_TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=15,
    )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        try:
            error_data = response.json()
        except ValueError:
            error_data = {}
        oauth_error = error_data.get("error") if isinstance(error_data, dict) else None
        error_description = (
            error_data.get("error_description")
            if isinstance(error_data, dict)
            else None
        )
        logger.error(
            "Google OAuth refresh-token request failed (HTTP %s, error=%s): %s",
            response.status_code,
            oauth_error or "unknown",
            error_description or response.text[:500] or str(exc),
        )
        raise
    access_token = response.json().get("access_token")
    if not access_token:
        raise RuntimeError("Google did not return an access token")
    return access_token


def revoke_google_refresh_token(encrypted_refresh_token: str) -> None:
    """Revoke a stored Google refresh token after the local account is disconnected."""
    try:
        refresh_token = decrypt_refresh_token(encrypted_refresh_token)
        response = httpx.post(
            GOOGLE_TOKEN_REVOKE_URL,
            params={"token": refresh_token},
            timeout=15,
        )
        response.raise_for_status()
    except (RuntimeError, httpx.HTTPError):
        logger.exception("Could not revoke the disconnected Google Calendar token")


def _local_datetime(value: datetime) -> datetime:
    timezone_name = os.getenv("APP_TIMEZONE", "Asia/Ho_Chi_Minh")
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        zone = timezone(timedelta(hours=7))
    if value.tzinfo is None:
        return value.replace(tzinfo=zone)
    return value.astimezone(zone)


def _timezone_name() -> str:
    timezone_name = os.getenv("APP_TIMEZONE", "Asia/Ho_Chi_Minh")
    try:
        ZoneInfo(timezone_name)
        return timezone_name
    except ZoneInfoNotFoundError:
        return "Asia/Ho_Chi_Minh"


def _google_event_id(user_id: int, meeting_id: int) -> str:
    digest = hashlib.sha256(f"{user_id}:{meeting_id}".encode("ascii")).digest()
    return base64.b32hexencode(digest).decode("ascii").rstrip("=").lower()


def _event_payload(user_id: int, meeting: Meeting) -> dict:
    room = meeting.room
    if meeting.meeting_type == "online":
        location = meeting.meeting_link or ""
    elif room:
        location = " - ".join(part for part in (room.name, room.location) if part)
    else:
        location = ""

    details = [meeting.description or ""]
    if meeting.meeting_type == "online" and meeting.meeting_link:
        details.append(f"Meeting link: {meeting.meeting_link}")
    description = "\n".join(part for part in details if part)
    start = _local_datetime(meeting.start_time)
    end = _local_datetime(meeting.end_time)
    payload = {
        "id": _google_event_id(user_id, meeting.id),
        "summary": meeting.title,
        "description": description,
        "location": location,
        "start": {"dateTime": start.isoformat(), "timeZone": _timezone_name()},
        "end": {"dateTime": end.isoformat(), "timeZone": _timezone_name()},
    }
    if meeting.organizer_id == user_id:
        attendees = [
            {"email": participant.user.email}
            for participant in meeting.participants
            if participant.user and participant.user.email
        ]
        if attendees:
            payload["attendees"] = attendees
    return payload


def _log_calendar_sync_http_error(
    exc: httpx.HTTPStatusError,
    *,
    meeting_id: int,
    user_id: int,
) -> None:
    response = exc.response
    try:
        error_data = response.json()
    except ValueError:
        error_data = {}

    google_error = error_data.get("error", {}) if isinstance(error_data, dict) else {}
    errors = google_error.get("errors", []) if isinstance(google_error, dict) else []
    reason = errors[0].get("reason") if errors and isinstance(errors[0], dict) else None
    message = google_error.get("message") if isinstance(google_error, dict) else None
    message = message or response.text[:500] or str(exc)

    if response.status_code == 403:
        logger.error(
            "Google Calendar denied sync for meeting_id=%s user_id=%s "
            "(reason=%s): %s. If this is an insufficientPermissions error, "
            "disconnect Google Calendar in Settings and connect again to grant "
            "the calendar.events scope. Also verify Calendar API access and "
            "the Google account's calendar sharing policy.",
            meeting_id,
            user_id,
            reason or "unknown",
            message,
        )
        return

    logger.exception(
        "Could not sync meeting_id=%s to Google Calendar for user_id=%s (HTTP %s)",
        meeting_id,
        user_id,
        response.status_code,
    )


def sync_user_meetings_to_google(user_id: int) -> None:
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
        if not user or not user.google_refresh_token:
            return
        try:
            refresh_token = decrypt_refresh_token(user.google_refresh_token)
            access_token = _access_token(refresh_token)
        except (RuntimeError, httpx.HTTPError) as exc:
            logger.warning("Google Calendar authorization unavailable for user_id=%s: %s", user_id, exc)
            return

        meetings = (
            db.query(Meeting)
            .outerjoin(MeetingParticipant, MeetingParticipant.meeting_id == Meeting.id)
            .filter(
                (Meeting.organizer_id == user_id)
                | (MeetingParticipant.user_id == user_id),
                Meeting.status.notin_(["CANCELLED", "canceled", "CANCELLED_NO_SHOW"]),
            )
            .distinct()
            .order_by(Meeting.start_time)
            .all()
        )
        existing_meeting_ids = {
            row[0]
            for row in db.query(GoogleCalendarEvent.meeting_id)
            .filter(GoogleCalendarEvent.user_id == user_id)
            .all()
        }
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        for meeting in meetings:
            if meeting.id in existing_meeting_ids:
                continue
            google_event_id = _google_event_id(user_id, meeting.id)
            try:
                response = httpx.post(
                    GOOGLE_EVENTS_URL,
                    headers=headers,
                    json=_event_payload(user_id, meeting),
                    params={"sendUpdates": "all"} if meeting.organizer_id == user_id else None,
                    timeout=15,
                )
                if response.status_code == 409:
                    pass
                else:
                    response.raise_for_status()
                db.add(
                    GoogleCalendarEvent(
                        user_id=user_id,
                        meeting_id=meeting.id,
                        google_event_id=google_event_id,
                    )
                )
                db.commit()
                existing_meeting_ids.add(meeting.id)
            except httpx.HTTPStatusError as exc:
                db.rollback()
                _log_calendar_sync_http_error(
                    exc,
                    meeting_id=meeting.id,
                    user_id=user_id,
                )
            except (httpx.HTTPError, RuntimeError):
                db.rollback()
                logger.exception(
                    "Could not sync meeting_id=%s to Google Calendar for user_id=%s",
                    meeting.id,
                    user_id,
                )
    finally:
        db.close()


def delete_google_calendar_event(user: User, google_event_id: str) -> bool:
    """Delete one event from the connected user's primary Google Calendar."""
    if not user.google_refresh_token:
        logger.warning(
            "Cannot delete Google event %s: user_id=%s has no refresh token",
            google_event_id,
            user.id,
        )
        return False

    try:
        refresh_token = decrypt_refresh_token(user.google_refresh_token)
        client_id, client_secret = _google_config()
        credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri=GOOGLE_TOKEN_URL,
            client_id=client_id,
            client_secret=client_secret,
            scopes=[GOOGLE_CALENDAR_EVENTS_SCOPE],
        )
        credentials.refresh(GoogleAuthRequest())
        service = build("calendar", "v3", credentials=credentials, cache_discovery=False)
        service.events().delete(
            calendarId="primary",
            eventId=google_event_id,
        ).execute()
        return True
    except HttpError as exc:
        response_status = getattr(getattr(exc, "resp", None), "status", None)
        if response_status in {404, 410}:
            logger.warning(
                "Google event %s is already deleted (HTTP %s) for user_id=%s",
                google_event_id,
                response_status,
                user.id,
            )
            return True
        logger.exception(
            "Failed to delete Google event %s for user_id=%s (HTTP %s)",
            google_event_id,
            user.id,
            response_status,
        )
        return False
    except Exception:
        logger.exception(
            "Failed to delete Google event %s for user_id=%s",
            google_event_id,
            user.id,
        )
        return False


def delete_google_events_for_meeting(meeting_id: int) -> None:
    """Delete tracked attendee events and retain mappings if Google is unavailable."""
    db: Session = SessionLocal()
    try:
        event_records = (
            db.query(GoogleCalendarEvent)
            .filter(GoogleCalendarEvent.meeting_id == meeting_id)
            .all()
        )
        for event_record in event_records:
            user = db.query(User).filter(User.id == event_record.user_id).first()
            if user is None:
                db.delete(event_record)
                continue
            if delete_google_calendar_event(user, event_record.google_event_id):
                db.delete(event_record)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Could not process Google events for meeting_id=%s", meeting_id)
    finally:
        db.close()
````

## File: frontend/js/auth.js
````javascript
const AUTH_API_BASE = window.AUTH_API_BASE || window.API_URL || 'http://localhost:8000/api';

function handleGoogleAuthCallback() {
    const callbackValues = new URLSearchParams(window.location.hash.slice(1));
    const accessToken = callbackValues.get('access_token');

    if (accessToken) {
        localStorage.setItem('token', accessToken);
        localStorage.setItem('access_token', accessToken);

        const valuesToStore = {
            role: callbackValues.get('role'),
            user_name: callbackValues.get('full_name'),
            user_email: callbackValues.get('email'),
            user_id: callbackValues.get('user_id'),
            user_picture: callbackValues.get('picture'),
        };
        Object.entries(valuesToStore).forEach(([key, value]) => {
            if (value) localStorage.setItem(key, value);
        });

        const dashboardUrl = new URL('dashboard.html', window.location.href);
        window.location.replace(dashboardUrl.href);
        return;
    }

    const query = new URLSearchParams(window.location.search);
    if (query.get('calendar_connected') === '1') {
        const successAlert = document.getElementById('errorAlert');
        if (successAlert) {
            successAlert.textContent = 'Đã kết nối Google Calendar. Các cuộc họp được mời sẽ được đồng bộ.';
            successAlert.classList.remove('hidden', 'bg-red-50', 'border-red-200', 'text-red-600');
            successAlert.classList.add('bg-green-50', 'border-green-200', 'text-green-700');
        }
        window.history.replaceState({}, document.title, window.location.pathname);
        return;
    }
    const oauthError = query.get('google_error');
    if (!oauthError) return;

    const errorAlert = document.getElementById('errorAlert');
    const messages = {
        access_denied: 'Bạn đã hủy đăng nhập bằng Google.',
        calendar_permission_denied: 'Bạn chưa cấp quyền Google Calendar cho RoomSync.',
        oauth_failed: 'Không thể đăng nhập bằng Google. Vui lòng thử lại.',
    };
    if (errorAlert) {
        errorAlert.textContent = messages[oauthError] || messages.oauth_failed;
        errorAlert.classList.remove('hidden');
    }
    window.history.replaceState({}, document.title, window.location.pathname);
}

document.addEventListener('DOMContentLoaded', () => {
    const googleButton = document.getElementById('googleLoginButton');
    googleButton?.addEventListener('click', () => {
        window.location.assign(`${AUTH_API_BASE}/auth/google/login`);
    });

    handleGoogleAuthCallback();
});
````

## File: frontend/js/create-meeting.js
````javascript
/* Create Meeting flow — meeting-first, resources second */

const CM_WEEKDAYS = ['Chủ nhật', 'Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy'];
const CM_PREVIEW = new URLSearchParams(location.search).get('preview') === 'meeting';

const cmState = {
    mode: 'offline',
    attendees: [],
    selectedRoom: null,
    roomsResult: [],
    requiredAmenities: [],
    roomSelectionExpanded: false,
    roomSearchVersion: 0,
    hasRoomSearch: false,
    searching: false,
    borrowQty: {},
    equipment: [],
    users: [],
    suggestIndex: -1,
    submitting: false,
    apiError: '',
    suggestedRooms: [],
    roomSearchTimer: null,
};

const CM_MOCK_USERS = [
    { id: 101, full_name: 'Nguyễn Văn A', email: 'a.nguyen@congty.com', title: 'Product Owner' },
    { id: 102, full_name: 'Trần Văn B', email: 'b.tran@congty.com', title: 'Tech Lead' },
    { id: 103, full_name: 'Lê Thị C', email: 'c.le@congty.com', title: 'Designer' },
    { id: 104, full_name: 'Phạm Minh D', email: 'd.pham@congty.com', title: 'QA' },
    { id: 105, full_name: 'Hoàng E', email: 'e.hoang@congty.com', title: 'Backend' },
    { id: 106, full_name: 'Đỗ F', email: 'f.do@congty.com', title: 'Frontend' },
    { id: 107, full_name: 'Vũ G', email: 'g.vu@congty.com', title: 'Scrum Master' },
    { id: 108, full_name: 'Bùi H', email: 'h.bui@congty.com', title: 'BA' },
];

const CM_MOCK_EQUIPMENT = [
    { id: 1, name: 'Laptop', available_qty: 5, total_qty: 10, is_active: true },
    { id: 2, name: 'Micro không dây', available_qty: 2, total_qty: 4, is_active: true },
    { id: 3, name: 'Webcam', available_qty: 0, total_qty: 3, is_active: true },
];

function cmEl(id) {
    return document.getElementById(id);
}

function cmInitials(name) {
    const parts = String(name || '?').trim().split(/\s+/);
    return ((parts[0] || '?')[0] + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase();
}

function cmParseAmenities(room) {
    let list = room?.amenities || [];
    if (typeof list === 'string') {
        try { list = JSON.parse(list); }
        catch (e) { list = list.split(',').map(s => s.trim()).filter(Boolean); }
    }
    return Array.isArray(list) ? list : [];
}

function cmNormalizeAmenity(value) {
    return String(value || '').trim().replace(/\s+/g, ' ').toLocaleLowerCase();
}

function cmCapacityNumber(room) {
    const n = parseInt(room?.capacity, 10);
    return Number.isFinite(n) ? n : 8;
}

function cmNormalizeUserKey(user) {
    if (!user) return '';
    const id = user.id ?? user.user_id;
    const email = String(user.email || '').trim().toLowerCase();
    const name = String(user.full_name || user.name || '').trim().toLowerCase();
    if (id !== undefined && id !== null && id !== '') return `id:${String(id)}`;
    if (email) return `email:${email}`;
    if (name) return `name:${name}`;
    return '';
}

function cmCurrentOrganizer() {
    const storedName = String(localStorage.getItem('user_name') || '').trim();
    const storedEmail = String(localStorage.getItem('user_email') || '').trim().toLowerCase();
    const storedId = String(localStorage.getItem('user_id') || '').trim();
    const users = Array.isArray(cmState.users) ? cmState.users : [];

    const match = users.find(user => {
        const email = String(user.email || '').trim().toLowerCase();
        const fullName = String(user.full_name || user.name || '').trim().toLowerCase();
        const id = String(user.id ?? user.user_id ?? '').trim();
        return (storedId && id && id === storedId)
            || (storedEmail && email && email === storedEmail)
            || (storedName && fullName && fullName === storedName.trim().toLowerCase());
    });

    if (match) return match;
    if (storedName || storedEmail || storedId) {
        return {
            id: storedId || 'current-user',
            user_id: storedId || 'current-user',
            full_name: storedName || 'Current User',
            email: storedEmail || '',
            name: storedName || 'Current User',
        };
    }

    return null;
}

function cmIsOrganizerUser(user) {
    if (!user) return false;
    const organizer = cmCurrentOrganizer();
    if (!organizer) return false;
    const userId = String(user.id ?? user.user_id ?? '');
    const organizerId = String(organizer.id ?? organizer.user_id ?? '');
    if (userId && organizerId && userId === organizerId) return true;

    const userName = String(user.full_name || user.name || '').trim().toLowerCase();
    const organizerName = String(organizer.full_name || organizer.name || '').trim().toLowerCase();
    const userEmail = String(user.email || '').trim().toLowerCase();
    const organizerEmail = String(organizer.email || '').trim().toLowerCase();
    return (!!userName && !!organizerName && userName === organizerName)
        || (!!userEmail && !!organizerEmail && userEmail === organizerEmail);
}

function cmUniqueValidParticipants() {
    const organizer = cmCurrentOrganizer();
    const seen = new Map();
    const normalized = cmState.attendees.filter(user => {
        const candidateKey = cmNormalizeUserKey(user);
        if (!candidateKey) return false;
        if (organizer && cmIsOrganizerUser(user)) return false;
        if (seen.has(candidateKey)) return false;
        seen.set(candidateKey, true);
        return true;
    });
    cmState.attendees = normalized;
    return normalized;
}

function cmAttendeeCount() {
    return cmUniqueValidParticipants().length;
}

function cmNeededSeats() {
    return 1 + cmAttendeeCount();
}

function cmGetTimes() {
    const date = cmEl('cmDate')?.value;
    const start = cmEl('cmStart')?.value;
    const end = cmEl('cmEnd')?.value;
    return { date, start, end };
}

function cmFormatViDate(iso) {
    if (!iso) return 'Chưa chọn ngày';
    const [y, m, d] = iso.split('-');
    return `${d}/${m}/${y}`;
}

function cmRecurrenceLabel() {
    const type = cmEl('cmRecurrence')?.value || 'none';
    if (type === 'none') return 'Không lặp';
    const extra = cmEl('cmRecurrenceNote')?.textContent || '';
    return extra || (type === 'weekly' ? 'Hàng tuần' : 'Hàng tháng');
}

function frequentIds() {
    try {
        return JSON.parse(localStorage.getItem('cm_frequent_ids') || '[]');
    } catch (e) {
        return [];
    }
}

function rememberAttendees(ids) {
    const prev = frequentIds();
    const next = [...ids, ...prev.filter(id => !ids.includes(id))].slice(0, 20);
    localStorage.setItem('cm_frequent_ids', JSON.stringify(next));
}

function rankUsers(users, query) {
    const q = query.trim().toLowerCase();
    const freq = new Set(frequentIds());
    return users
        .filter(u => {
            if (!q) return true;
            const blob = `${u.full_name || ''} ${u.email || ''} ${u.title || ''}`.toLowerCase();
            return blob.includes(q);
        })
        .sort((a, b) => {
            const aRel = q && String(a.full_name || '').toLowerCase().startsWith(q) ? 0 : 1;
            const bRel = q && String(b.full_name || '').toLowerCase().startsWith(q) ? 0 : 1;
            if (aRel !== bRel) return aRel - bRel;
            const aF = freq.has(a.id) ? 0 : 1;
            const bF = freq.has(b.id) ? 0 : 1;
            return aF - bF;
        })
        .slice(0, 8);
}

function openCreateMeeting(options = {}) {
    const overlay = cmEl('createMeetingModal');
    if (!overlay) return;

    resetCreateMeeting();
    cmEl('cmDialog')?.classList.remove('is-success');
    overlay.classList.add('is-open');
    overlay.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';

    const title = cmEl('cmTitle');
    if (title) setTimeout(() => title.focus(), 30);

    loadCreateMeetingData().then(async () => {
        if (options.roomId) {
            await searchMatchingRooms();
            const match = cmState.roomsResult.find(item => String(item.room.id) === String(options.roomId));
            if (match) selectCreateMeetingRoom(match.room, { silent: true });
        }
        updateCreateMeetingSummary();
    });
}

function closeCreateMeeting() {
    const overlay = cmEl('createMeetingModal');
    if (!overlay) return;
    overlay.classList.remove('is-open');
    overlay.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    const dialog = cmEl('cmDialog');
    if (dialog) dialog.classList.remove('is-success');
}

function resetCreateMeeting() {
    cmState.mode = 'offline';
    cmState.attendees = [];
    cmState.selectedRoom = null;
    cmState.roomsResult = [];
    cmState.requiredAmenities = [];
    cmState.roomSelectionExpanded = false;
    cmState.roomSearchVersion += 1;
    cmState.hasRoomSearch = false;
    cmState.searching = false;
    cmState.borrowQty = {};
    cmState.suggestIndex = -1;
    cmState.submitting = false;
    cmState.apiError = '';
    cmState.suggestedRooms = [];
    if (cmState.roomSearchTimer) clearTimeout(cmState.roomSearchTimer);
    cmState.roomSearchTimer = null;

    const formIds = ['cmTitle', 'cmDescription', 'cmMeetingLink', 'cmAttendeeSearch'];
    formIds.forEach(id => {
        const el = cmEl(id);
        if (el) {
            el.value = '';
            el.classList.remove('is-invalid');
        }
    });
    setCreateMeetingMode('offline');
    setRecurrence('none');
    setDefaultCreateMeetingTimes();
    renderAttendeeChips();
    renderFixedAmenityOptions();
    renderRoomResults();
    renderEquipment();
    updateEquipmentSectionVisibility();
    hideCmAlerts();
    updateCreateMeetingSummary();
}

function setDefaultCreateMeetingTimes() {
    const now = new Date();
    let startHour = now.getHours();
    let startMin = now.getMinutes() < 30 ? '30' : '00';
    if (now.getMinutes() >= 30) startHour += 1;
    if (startHour < 7) startHour = 9;
    if (startHour > 20) startHour = 9;
    const endHour = Math.min(startHour + 1, 21);
    const dateVal = typeof formatDateInput === 'function' ? formatDateInput(now) : now.toISOString().slice(0, 10);
    const startVal = `${String(startHour).padStart(2, '0')}:${startMin}`;
    const endVal = `${String(endHour).padStart(2, '0')}:${startMin}`;

    const dateEl = cmEl('cmDate');
    const startEl = cmEl('cmStart');
    const endEl = cmEl('cmEnd');
    if (dateEl) dateEl.value = dateVal;
    if (typeof buildViTimeOptions === 'function') {
        buildViTimeOptions(startEl, startVal);
        buildViTimeOptions(endEl, endVal);
    } else {
        if (startEl) startEl.value = startVal;
        if (endEl) endEl.value = endVal;
    }
}

async function loadCreateMeetingData() {
    const token = typeof getAuthToken === 'function' ? getAuthToken() : '';
    try {
        if (typeof _allUsers !== 'undefined' && _allUsers.length) {
            cmState.users = _allUsers;
        } else if (token) {
            const res = await fetch(`${API_BASE}/users/`, { headers: { Authorization: `Bearer ${token}` } });
            if (res.ok) cmState.users = await res.json();
        }
    } catch (e) {
        console.warn('Không tải được người dùng', e);
    }
    if (!cmState.users.length) cmState.users = CM_MOCK_USERS;

    try {
        if (typeof allRooms !== 'undefined' && !allRooms.length) {
            const res = await fetch(`${API_BASE}/rooms/`);
            if (!res.ok) throw new Error(`Không tải được phòng (${res.status}).`);
            allRooms = await res.json();
        }
        renderFixedAmenityOptions();
    } catch (e) {
        console.warn('Không tải được tiện nghi phòng', e);
        const options = cmEl('cmFixedAmenityOptions');
        if (options) options.innerHTML = '<p class="cm-help">Không tải được tiện nghi phòng. Vui lòng thử tải lại.</p>';
    }

    try {
        const { date, start, end } = cmGetTimes();
        const params = new URLSearchParams();
        if (date && start && end) {
            params.set('start_time', `${date}T${start}:00`);
            params.set('end_time', `${date}T${end}:00`);
        }
        if (token) {
            const res = await fetch(`${API_BASE}/equipments/availability?${params}`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            if (res.ok) cmState.equipment = (await res.json()).filter(eq => eq.is_active !== false);
        }
    } catch (e) {
        console.warn('Không tải được thiết bị', e);
    }
    if (!cmState.equipment.length) cmState.equipment = CM_MOCK_EQUIPMENT;
    renderEquipment();
    updateCapacityHint();
}

function canSearchRoomsForMeeting() {
    if (cmState.mode !== 'offline') return false;
    const { date, start, end } = cmGetTimes();
    if (!date || !start || !end) return false;
    if (end <= start) return false;
    if (cmTimeIsInPast(date, start)) return false;
    return cmNeededSeats() > 0;
}

function invalidateRoomResults() {
    cmState.roomSearchVersion += 1;
    cmState.selectedRoom = null;
    cmState.roomSelectionExpanded = false;
    if (cmState.roomSearchTimer) clearTimeout(cmState.roomSearchTimer);
    cmState.roomSearchTimer = null;
    cmState.searching = false;
    cmState.roomsResult = [];
    cmState.hasRoomSearch = false;
    cmState.suggestedRooms = [];
    renderRoomResults();
    updateEquipmentSectionVisibility();
    updateCreateMeetingSummary();
}

function setCreateMeetingMode(mode) {
    cmState.mode = mode;
    invalidateRoomResults();
    if (mode === 'online') {
        cmState.requiredAmenities = [];
        renderFixedAmenityOptions();
    }

    const onlineBtn = cmEl('cmModeOnline');
    const offlineBtn = cmEl('cmModeOffline');
    if (onlineBtn) onlineBtn.setAttribute('aria-pressed', String(mode === 'online'));
    if (offlineBtn) offlineBtn.setAttribute('aria-pressed', String(mode === 'offline'));

    const onlineBox = cmEl('cmOnlineBox');
    const roomSection = cmEl('cmResources');
    if (onlineBox) onlineBox.classList.toggle('is-open', mode === 'online');
    if (roomSection) roomSection.classList.toggle('is-open', mode === 'offline');
    onlineBox?.setAttribute('aria-hidden', String(mode !== 'online'));
    roomSection?.setAttribute('aria-hidden', String(mode !== 'offline'));

    const roomSearchBtn = document.getElementById('cmSearchRoomsBtn');
    if (roomSearchBtn) roomSearchBtn.disabled = mode !== 'offline';

    const onlineLink = cmEl('cmMeetingLink');
    if (mode === 'online') {
        if (onlineLink) onlineLink.required = true;
    } else if (onlineLink) {
        onlineLink.value = '';
        onlineLink.required = false;
        onlineLink.classList.remove('is-invalid');
    }

    renderRoomResults();
    updateEquipmentSectionVisibility();
    updateCreateMeetingSummary();
}

function renderFixedAmenityOptions() {
    const box = cmEl('cmFixedAmenityOptions');
    if (!box) return;

    const amenities = new Map();
    (typeof allRooms !== 'undefined' ? allRooms : [])
        .filter(room => room.is_active !== false)
        .forEach(room => cmParseAmenities(room).forEach(amenity => {
            const value = String(amenity || '').trim();
            const key = cmNormalizeAmenity(value);
            if (key && !amenities.has(key)) amenities.set(key, value);
        }));

    if (!amenities.size) {
        box.innerHTML = '<p class="cm-help">Chưa có tiện nghi cố định được khai báo cho phòng.</p>';
        return;
    }

    box.innerHTML = [...amenities.values()].sort((a, b) => a.localeCompare(b, 'vi')).map(amenity => `
        <label class="cm-amenity-choice">
            <input type="checkbox" value="${escapeHtml(amenity)}" ${cmState.requiredAmenities.some(item => cmNormalizeAmenity(item) === cmNormalizeAmenity(amenity)) ? 'checked' : ''}>
            <span>${escapeHtml(amenity)}</span>
        </label>
    `).join('');
}

function updateEquipmentSectionVisibility() {
    const section = cmEl('cmEquipmentSection');
    if (section) section.hidden = cmState.mode !== 'offline' || !cmState.selectedRoom;
}

function setRecurrence(type) {
    const select = cmEl('cmRecurrence');
    if (select && type) select.value = type;
    const value = select?.value || 'none';
    const extra = cmEl('cmRecurringExtra');
    extra?.classList.toggle('is-open', value !== 'none');
    cmEl('cmRecNone')?.setAttribute('aria-pressed', String(value === 'none'));
    cmEl('cmRecWeekly')?.setAttribute('aria-pressed', String(value === 'weekly'));
    cmEl('cmRecMonthly')?.setAttribute('aria-pressed', String(value === 'monthly'));
    updateRecurrenceNote();
    updateCreateMeetingSummary();
    scheduleRoomSearchRefresh();
}

function updateRecurrenceNote() {
    const type = cmEl('cmRecurrence')?.value || 'none';
    const note = cmEl('cmRecurrenceNote');
    const until = cmEl('cmRecurrenceUntil')?.value;
    const { date } = cmGetTimes();
    if (!note) return;
    if (type === 'none') {
        note.textContent = '';
        return;
    }
    const dt = date ? new Date(`${date}T00:00:00`) : new Date();
    const weekday = CM_WEEKDAYS[dt.getDay()];
    const day = dt.getDate();
    const untilText = until ? `, kết thúc ${cmFormatViDate(until)}` : '';
    note.textContent = type === 'weekly'
        ? `Lặp vào ${weekday} hàng tuần${untilText}`
        : `Lặp hàng tháng vào ngày ${day}${untilText}`;
}

function renderAttendeeChips() {
    const normalized = cmUniqueValidParticipants();
    const wrap = cmEl('cmAttendeeChips');
    const count = cmEl('cmAttendeeCount');
    if (count) count.textContent = `${normalized.length} người tham dự`;
    if (!wrap) return;
    if (!normalized.length) {
        wrap.innerHTML = '<p class="cm-help">Chưa có người tham dự. Bạn vẫn có thể tạo cuộc họp với tư cách người tổ chức.</p>';
        updateCapacityHint();
        updateCreateMeetingSummary();
        return;
    }
    wrap.innerHTML = normalized.map(u => `
        <span class="cm-chip">
            <span class="cm-avatar" aria-hidden="true">${escapeHtml(cmInitials(u.full_name || u.email))}</span>
            ${escapeHtml(u.full_name || u.email)}
            <button type="button" aria-label="Xóa ${escapeHtml(u.full_name || u.email)}" onclick="removeCreateMeetingAttendee(${u.id})">×</button>
        </span>
    `).join('');
    updateCapacityHint();
    updateCreateMeetingSummary();
}

function scheduleRoomSearchRefresh() {
    invalidateRoomResults();
    if (!canSearchRoomsForMeeting()) {
        return;
    }

    cmState.roomSearchTimer = setTimeout(() => {
        cmState.roomSearchTimer = null;
        if (canSearchRoomsForMeeting()) {
            searchMatchingRooms();
        }
    }, 250);
}

function onFixedAmenityChange(event) {
    if (!event.target.matches('#cmFixedAmenityOptions input[type="checkbox"]')) return;
    cmState.requiredAmenities = [...cmEl('cmFixedAmenityOptions').querySelectorAll('input:checked')]
        .map(input => input.value);
    scheduleRoomSearchRefresh();
}

function addCreateMeetingAttendee(user) {
    if (!user || cmIsOrganizerUser(user)) return;
    const key = cmNormalizeUserKey(user);
    if (!key || cmState.attendees.some(a => cmNormalizeUserKey(a) === key)) return;
    cmState.attendees.push(user);
    renderAttendeeChips();
    scheduleRoomSearchRefresh();
}

function removeCreateMeetingAttendee(id) {
    cmState.attendees = cmState.attendees.filter(a => String(a.id) !== String(id));
    renderAttendeeChips();
    scheduleRoomSearchRefresh();
}

function addAllTeamMembers() {
    const organizer = cmCurrentOrganizer();
    const domain = (localStorage.getItem('user_email') || organizer?.email || cmState.users[0]?.email || '').split('@')[1];
    cmState.users
        .filter(u => {
            if (organizer && cmIsOrganizerUser(u)) return false;
            if (!domain) return true;
            return String(u.email || '').endsWith(`@${domain}`);
        })
        .forEach(addCreateMeetingAttendee);
    closeAttendeeSuggest();
}

function onAttendeeSearchInput() {
    const input = cmEl('cmAttendeeSearch');
    const list = cmEl('cmAttendeeSuggest');
    if (!input || !list) return;
    const query = input.value;
    const organizer = cmCurrentOrganizer();
    const selected = new Set(cmState.attendees.map(a => cmNormalizeUserKey(a)));
    const matches = rankUsers(
        cmState.users.filter(u => {
            if (organizer && cmIsOrganizerUser(u)) return false;
            return !selected.has(cmNormalizeUserKey(u));
        }),
        query
    );
    if (!query.trim() || !matches.length) {
        closeAttendeeSuggest();
        return;
    }
    cmState.suggestIndex = -1;
    list.innerHTML = matches.map((u, i) => `
        <li>
            <button type="button" data-index="${i}" onclick="pickCreateMeetingAttendee(${u.id})">
                <span class="cm-avatar">${escapeHtml(cmInitials(u.full_name || u.email))}</span>
                <span class="cm-suggest-meta">
                    <strong>${escapeHtml(u.full_name || 'Người dùng')}</strong>
                    <span>${escapeHtml(u.email || '')}${u.title ? ' · ' + escapeHtml(u.title) : ''}</span>
                </span>
            </button>
        </li>
    `).join('');
    list.classList.add('is-open');
    list.dataset.ids = matches.map(u => u.id).join(',');
}

function pickCreateMeetingAttendee(id) {
    const user = cmState.users.find(u => String(u.id) === String(id));
    if (user) addCreateMeetingAttendee(user);
    const input = cmEl('cmAttendeeSearch');
    if (input) input.value = '';
    closeAttendeeSuggest();
}

function closeAttendeeSuggest() {
    cmEl('cmAttendeeSuggest')?.classList.remove('is-open');
    cmState.suggestIndex = -1;
}

function handleAttendeeKeydown(event) {
    const list = cmEl('cmAttendeeSuggest');
    if (!list?.classList.contains('is-open')) return;
    const buttons = [...list.querySelectorAll('button')];
    if (event.key === 'ArrowDown') {
        event.preventDefault();
        cmState.suggestIndex = Math.min(cmState.suggestIndex + 1, buttons.length - 1);
    } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        cmState.suggestIndex = Math.max(cmState.suggestIndex - 1, 0);
    } else if (event.key === 'Enter' && cmState.suggestIndex >= 0) {
        event.preventDefault();
        buttons[cmState.suggestIndex]?.click();
        return;
    } else if (event.key === 'Escape') {
        closeAttendeeSuggest();
        return;
    }
    buttons.forEach((btn, i) => btn.classList.toggle('is-active', i === cmState.suggestIndex));
}

function updateCapacityHint() {
    const needed = cmNeededSeats();
    const label = cmEl('cmCapacityValue');
    if (label) label.textContent = `${needed} người`;
    const min = cmEl('cmCapacityMin');
    if (min) min.textContent = `Phòng tối thiểu: ${needed} chỗ`;
}

function hideCmAlerts() {
    ['cmRoomConflict', 'cmEquipConflict', 'cmFormError', 'cmApiError'].forEach(id => {
        cmEl(id)?.classList.remove('is-open');
    });
}

async function searchMatchingRooms() {
    if (cmState.mode !== 'offline') return;

    const results = cmEl('cmRoomResults');
    const { date, start, end } = cmGetTimes();
    if (!canSearchRoomsForMeeting()) {
        showFormError('Chọn ngày và khung giờ hợp lệ trước khi tìm phòng.');
        return;
    }
    const searchVersion = ++cmState.roomSearchVersion;
    const requiredAmenities = cmState.requiredAmenities.map(cmNormalizeAmenity);
    cmState.selectedRoom = null;
    cmState.roomSelectionExpanded = false;
    cmState.roomsResult = [];
    cmState.hasRoomSearch = true;
    cmState.searching = true;
    updateEquipmentSectionVisibility();
    if (results) {
        results.innerHTML = '<div class="cm-skeleton"></div><div class="cm-skeleton"></div>';
    }
    hideCmAlerts();

    const token = typeof getAuthToken === 'function' ? getAuthToken() : '';
    let availableRooms = [];
    try {
        const params = new URLSearchParams({
            start_time: `${date}T${start}:00`,
            end_time: `${date}T${end}:00`,
        });
        const res = await fetch(`${API_BASE}/rooms/available?${params}`, {
            headers: token ? { Authorization: `Bearer ${token}` } : {}
        });
        if (!res.ok) throw new Error(`Room availability returned ${res.status}.`);
        availableRooms = await res.json();
    } catch (e) {
        console.warn('Không kiểm tra được phòng trống', e);
        showFormError('Không thể kiểm tra phòng trống lúc này. Vui lòng thử lại.');
    }
    if (searchVersion !== cmState.roomSearchVersion) return;

    const needed = cmNeededSeats();
    const mapped = availableRooms
        .filter(r => r.is_active !== false)
        .map(room => {
            const capacity = cmCapacityNumber(room);
            const available = room.is_available !== false;
            const fit = capacity >= needed;
            return { room, capacity, available, fit, score: available && fit ? capacity - needed : 999 };
        })
        .sort((a, b) => {
            if (a.available !== b.available) return a.available ? -1 : 1;
            if (a.fit !== b.fit) return a.fit ? -1 : 1;
            return a.score - b.score;
        });

    cmState.roomsResult = mapped.filter(item => {
        if (!item.available || !item.fit) return false;
        const roomAmenities = new Set(cmParseAmenities(item.room).map(cmNormalizeAmenity));
        return requiredAmenities.every(amenity => roomAmenities.has(amenity));
    });

    cmState.searching = false;
    renderRoomResults();
    updateCreateMeetingSummary();
}

function renderRoomResults() {
    const results = cmEl('cmRoomResults');
    if (!results) return;
    if (cmState.mode === 'online') {
        results.innerHTML = '<div class="cm-empty">Cuộc họp online không cần chọn phòng.</div>';
        return;
    }
    if (cmState.searching) return;
    if (!cmState.roomsResult.length) {
        results.innerHTML = `<div class="cm-empty">${cmState.hasRoomSearch ? 'Không tìm thấy phòng phù hợp với thời gian, sức chứa và tiện nghi đã chọn.' : 'Chọn điều kiện phòng rồi bấm “Tìm phòng phù hợp”.'}</div>`;
        return;
    }

    const selected = cmState.selectedRoom
        ? cmState.roomsResult.find(item => String(item.room.id) === String(cmState.selectedRoom.id))
        : null;
    if (selected && !cmState.roomSelectionExpanded) {
        const amenities = cmParseAmenities(selected.room);
        results.innerHTML = `
            <article class="cm-room-card cm-room-selected">
                <div class="cm-room-top">
                    <h3>✓ ${escapeHtml(selected.room.name)}</h3>
                    <span class="cm-badge cm-badge-ok">Đã chọn · Trống</span>
                </div>
                <p class="cm-room-meta">${escapeHtml(selected.room.location || 'Chưa có vị trí')} · ${selected.capacity} chỗ · ${escapeHtml(cmGetTimes().start || '')}–${escapeHtml(cmGetTimes().end || '')}</p>
                <p class="cm-room-amenities">${amenities.length ? amenities.map(item => `✓ ${escapeHtml(item)}`).join(' · ') : 'Chưa khai báo tiện nghi cố định'}</p>
                <div class="cm-room-actions"><button type="button" class="cm-btn cm-btn-secondary" onclick="changeCreateMeetingRoom()">Đổi phòng</button></div>
            </article>
        `;
        return;
    }

    results.innerHTML = cmState.roomsResult.map(item => {
        const room = item.room;
        const isSelected = cmState.selectedRoom && String(cmState.selectedRoom.id) === String(room.id);
        const amenities = cmParseAmenities(room);
        const displayedAmenities = cmState.requiredAmenities.length
            ? cmState.requiredAmenities.map(item => `✓ ${escapeHtml(item)}`)
            : amenities.map(item => `✓ ${escapeHtml(item)}`);
        const action = isSelected
            ? '<button type="button" class="cm-btn cm-btn-ghost" disabled>Đã chọn</button>'
            : `<button type="button" class="cm-btn cm-btn-ghost" onclick="selectCreateMeetingRoomById('${room.id}')">Chọn phòng</button>`;
        return `
            <article class="cm-room-card ${isSelected ? 'is-selected' : ''}">
                <div class="cm-room-top">
                    <h3>${escapeHtml(room.name)}</h3>
                    <span class="cm-badge cm-badge-ok">Trống</span>
                </div>
                <p class="cm-room-meta">${escapeHtml(room.location || 'Chưa có vị trí')} · ${item.capacity} chỗ</p>
                <p class="cm-room-amenities">${displayedAmenities.length ? displayedAmenities.join(' · ') : 'Không yêu cầu tiện nghi cố định'}</p>
                <div class="cm-room-actions">${action}</div>
            </article>
        `;
    }).join('');
}

function selectCreateMeetingRoomById(id) {
    const found = cmState.roomsResult.find(item => String(item.room.id) === String(id));
    if (found) selectCreateMeetingRoom(found.room);
}

function selectCreateMeetingRoom(room, { silent } = {}) {
    if (!room) return;
    const match = cmState.roomsResult.find(item =>
        String(item.room.id) === String(room.id) && item.available && item.fit
    );
    if (!match) return;
    cmState.selectedRoom = match.room;
    cmState.roomSelectionExpanded = false;
    renderRoomResults();
    updateEquipmentSectionVisibility();
    if (!silent) updateCreateMeetingSummary();
}

function changeCreateMeetingRoom() {
    if (!cmState.selectedRoom) return;
    cmState.roomSelectionExpanded = true;
    renderRoomResults();
}

function renderEquipment() {
    const box = cmEl('cmBorrowEquipment');
    if (!box) return;
    if (!cmState.equipment.length) {
        box.innerHTML = '<p class="cm-help">Không có thiết bị để mượn thêm.</p>';
        return;
    }
    box.innerHTML = cmState.equipment.map(eq => {
        const qty = cmState.borrowQty[eq.id] || 0;
        const available = eq.available_qty ?? eq.total_qty ?? 0;
        const empty = available <= 0;
        return `
            <div class="cm-eq-row ${empty ? 'is-empty' : ''}">
                <div>
                    <strong>${escapeHtml(eq.name)}</strong>
                    <div class="cm-help">Available: ${available} / ${eq.total_qty ?? available}</div>
                </div>
                ${empty
                    ? '<span class="cm-badge cm-badge-busy">Hết thiết bị</span>'
                    : `<div class="cm-stepper">
                        <button type="button" aria-label="Giảm ${escapeHtml(eq.name)}" onclick="changeBorrowQty(${eq.id}, -1)">−</button>
                        <span>${qty}</span>
                        <button type="button" aria-label="Tăng ${escapeHtml(eq.name)}" onclick="changeBorrowQty(${eq.id}, 1)">+</button>
                       </div>`}
            </div>
        `;
    }).join('');
    updateEquipmentConflict();
}

function changeBorrowQty(id, delta) {
    const eq = cmState.equipment.find(item => item.id === id);
    if (!eq) return;
    const available = eq.available_qty ?? eq.total_qty ?? 0;
    const next = Math.max(0, (cmState.borrowQty[id] || 0) + delta);
    cmState.borrowQty[id] = Math.min(next, available);
    renderEquipment();
    updateCreateMeetingSummary();
}

function reduceEquipmentToAvailable(id) {
    const eq = cmState.equipment.find(item => item.id === id);
    if (!eq) return;
    cmState.borrowQty[id] = eq.available_qty ?? 0;
    renderEquipment();
    updateCreateMeetingSummary();
}

function clearBorrowQty(id) {
    cmState.borrowQty[id] = 0;
    renderEquipment();
    updateCreateMeetingSummary();
}

function updateEquipmentConflict() {
    const alert = cmEl('cmEquipConflict');
    if (!alert) return;
    const issues = cmState.equipment.filter(eq => (cmState.borrowQty[eq.id] || 0) > (eq.available_qty ?? eq.total_qty ?? 0));
    if (!issues.length) {
        alert.classList.remove('is-open');
        alert.innerHTML = '';
        return;
    }
    const eq = issues[0];
    alert.classList.add('is-open');
    alert.innerHTML = `
        <strong>⚠ ${escapeHtml(eq.name)} không đủ số lượng</strong>
        <span>Available: ${eq.available_qty} · Yêu cầu: ${cmState.borrowQty[eq.id]}</span>
        <span>
            <button type="button" class="cm-link-btn" onclick="reduceEquipmentToAvailable(${eq.id})">Giảm số lượng</button>
            ·
            <button type="button" class="cm-link-btn" onclick="clearBorrowQty(${eq.id})">Chọn thiết bị khác</button>
        </span>
    `;
}

function generateMeetingLink() {
    const input = cmEl('cmMeetingLink');
    if (!input) return;
    const slug = Math.random().toString(36).slice(2, 8);
    input.value = `https://meet.roomsync.vn/${slug}`;
    updateCreateMeetingSummary();
}

function collectConflicts() {
    const conflicts = [];
    if (cmState.mode === 'offline' && cmState.selectedRoom) {
        const match = cmState.roomsResult.find(item => String(item.room.id) === String(cmState.selectedRoom.id));
        if (match && match.available === false) {
            conflicts.push(`Phòng ${cmState.selectedRoom.name} không khả dụng trong khung giờ đã chọn.`);
            cmState.suggestedRooms = cmState.roomsResult.filter(item => item.available).slice(0, 2).map(item => item.room);
        }
    }
    cmState.equipment.forEach(eq => {
        const qty = cmState.borrowQty[eq.id] || 0;
        const available = eq.available_qty ?? 0;
        if (qty > available) conflicts.push(`${eq.name} không đủ số lượng.`);
    });
    return conflicts;
}

function updateCreateMeetingSummary() {
    const title = cmEl('cmTitle')?.value.trim() || 'Chưa đặt tên cuộc họp';
    const { date, start, end } = cmGetTimes();
    const borrowed = cmState.equipment.filter(eq => (cmState.borrowQty[eq.id] || 0) > 0);
    const conflicts = collectConflicts();
    const roomConflict = cmEl('cmRoomConflict');
    if (roomConflict) {
        if (conflicts.some(c => c.startsWith('Phòng'))) {
            const suggestions = cmState.suggestedRooms.map(r => escapeHtml(r.name)).join(', ');
            roomConflict.classList.add('is-open');
            roomConflict.innerHTML = `
                <strong>⚠ Phòng ${escapeHtml(cmState.selectedRoom.name)} không khả dụng</strong>
                <span>${escapeHtml(start || '')} – ${escapeHtml(end || '')} đã có cuộc họp.</span>
                ${suggestions ? `<span>Đề xuất: ${suggestions}</span>` : ''}
            `;
        } else {
            roomConflict.classList.remove('is-open');
        }
    }

    const list = cmEl('cmSummaryList');
    if (list) {
        const items = [
            `📌 ${title}`,
            `📅 ${cmFormatViDate(date)}`,
            `🕐 ${start || '--:--'} – ${end || '--:--'}`,
            `👥 ${cmAttendeeCount()} người`,
            cmState.mode === 'online' ? '🌐 Online' : `🏢 ${cmState.selectedRoom ? cmState.selectedRoom.name : 'Chưa chọn phòng'}`,
            cmState.mode === 'online' ? `🔗 ${cmEl('cmMeetingLink')?.value || 'Chưa có link'}` : null,
            ...borrowed.map(eq => `🎤 ${eq.name} x${cmState.borrowQty[eq.id]}`),
            `🔁 ${cmRecurrenceLabel()}`,
        ].filter(Boolean);
        list.innerHTML = items.map(item => `<li>${escapeHtml(item)}</li>`).join('');
    }

    const status = cmEl('cmSummaryStatus');
    if (status) {
        status.className = `cm-status ${conflicts.length ? 'is-warn' : 'is-ok'}`;
        status.textContent = conflicts.length ? '⚠ Có vấn đề cần xử lý' : '✓ Không có xung đột';
    }

    const submit = cmEl('cmSubmit');
    if (submit) {
        submit.disabled = cmState.submitting || Boolean(conflicts.length);
        submit.textContent = cmState.submitting ? 'Đang tạo...' : 'TẠO CUỘC HỌP';
    }
}

function showFormError(message) {
    const box = cmEl('cmFormError');
    if (!box) return;
    box.classList.add('is-open');
    box.textContent = message;
}

function cmTimeIsInPast(date, start) {
    if (!date || !start) return false;
    const startDate = new Date(`${date}T${start}:00`);
    if (Number.isNaN(startDate.getTime())) return false;
    return startDate.getTime() < Date.now();
}

function validateCreateMeeting() {
    hideCmAlerts();
    const title = cmEl('cmTitle');
    const dateInput = cmEl('cmDate');
    const startInput = cmEl('cmStart');
    const endInput = cmEl('cmEnd');
    const onlineLink = cmEl('cmMeetingLink');
    const { date, start, end } = cmGetTimes();
    let ok = true;

    [title, dateInput, startInput, endInput, onlineLink].forEach(el => el?.classList.remove('is-invalid'));

    if (!title?.value.trim()) {
        title.classList.add('is-invalid');
        cmEl('cmTitleError')?.classList.add('is-visible');
        ok = false;
    } else {
        cmEl('cmTitleError')?.classList.remove('is-visible');
    }

    if (!date || !start || !end) {
        [dateInput, startInput, endInput].forEach(el => {
            if (el) el.classList.add('is-invalid');
        });
        showFormError('Chọn ngày, giờ bắt đầu và giờ kết thúc hợp lệ.');
        ok = false;
    }

    if (date && start && cmTimeIsInPast(date, start)) {
        startInput?.classList.add('is-invalid');
        showFormError('Thời gian bắt đầu không được ở quá khứ.');
        ok = false;
    }

    if (date && start && end && end <= start) {
        [startInput, endInput].forEach(el => {
            if (el) el.classList.add('is-invalid');
        });
        showFormError('Giờ kết thúc phải sau giờ bắt đầu.');
        ok = false;
    }

    if (cmState.mode === 'online') {
        const linkValue = onlineLink?.value.trim() || '';
        if (!linkValue) {
            onlineLink?.classList.add('is-invalid');
            showFormError('Cuộc họp online cần link. Bấm Tạo link nếu chưa có.');
            ok = false;
        } else if (!/^https?:\/\//i.test(linkValue)) {
            onlineLink?.classList.add('is-invalid');
            showFormError('Link cuộc họp online không hợp lệ. Vui lòng nhập URL đầy đủ bắt đầu bằng http:// hoặc https://');
            ok = false;
        }
    }

    if (cmState.mode === 'offline' && !cmState.selectedRoom) {
        showFormError('Vui lòng chọn phòng họp.');
        ok = false;
    }

    if (collectConflicts().length && !(cmState.mode === 'offline' && !cmState.selectedRoom)) {
        showFormError('Hãy xử lý xung đột trước khi tạo cuộc họp.');
        ok = false;
    }
    return ok;
}

async function handleCreateMeetingSubmit(event) {
    event.preventDefault();
    if (!validateCreateMeeting()) return;

    const title = cmEl('cmTitle').value.trim();
    const { date, start, end } = cmGetTimes();
    const descriptionParts = [];
    const desc = cmEl('cmDescription')?.value.trim();
    if (desc) descriptionParts.push(desc);

    const recurrenceType = cmEl('cmRecurrence')?.value || 'none';
    const until = cmEl('cmRecurrenceUntil')?.value;
    let recurrenceEndDate = null;
    if (recurrenceType !== 'none') {
        if (until) recurrenceEndDate = `${until}T${end}:00`;
        else {
            const d = new Date(`${date}T${end}:00`);
            d.setMonth(d.getMonth() + (recurrenceType === 'weekly' ? 2 : 1));
            recurrenceEndDate = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}T${end}:00`;
        }
    }

    const realParticipantIds = [...new Set(
        cmState.attendees
            .map(a => a.id)
            .filter(id => Number.isInteger(id))
    )];

    const payload = {
        title,
        description: descriptionParts.join('\n') || null,
        meeting_type: cmState.mode,
        meeting_link: cmState.mode === 'online'
            ? (cmEl('cmMeetingLink')?.value.trim() || null)
            : null,
        room_id: cmState.mode === 'offline'
            ? (cmState.selectedRoom ? parseInt(cmState.selectedRoom.id, 10) : null)
            : null,
        start_time: `${date}T${start}:00`,
        end_time:   `${date}T${end}:00`,
        is_recurring: recurrenceType !== 'none',
        recurrence_type: recurrenceType,
        recurrence_end_date: recurrenceEndDate,
        equipments: cmState.mode === 'offline'
            ? Object.entries(cmState.borrowQty)
                .filter(([, qty]) => qty > 0)
                .map(([eid, qty]) => ({
                    equipment_id: parseInt(eid, 10),
                    quantity: qty
                }))
            : [],
        participant_ids: realParticipantIds,
    };

    const token = typeof getAuthToken === 'function' ? getAuthToken() : '';
    if (!token) {
        const box = cmEl('cmApiError');
        if (box) {
            box.classList.add('is-open');
            box.textContent = 'Vui lòng đăng nhập để tạo cuộc họp.';
        }
        return;
    }

    cmState.submitting = true;
    updateCreateMeetingSummary();
    try {
        const res = await fetch(`${API_BASE}/meetings/book`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify(payload),
        });
        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.detail || 'Không thể tạo cuộc họp.');
        }
        rememberAttendees(realParticipantIds);
        showCreateMeetingSuccess();
        if (typeof fetchRooms === 'function') fetchRooms(localStorage.getItem('role') === 'admin');
        if (typeof fetchMyBookings === 'function') fetchMyBookings();
    } catch (error) {
        const box = cmEl('cmApiError');
        if (box) {
            box.classList.add('is-open');
            box.textContent = `Không tạo được cuộc họp. ${error.message}`;
        }
    } finally {
        cmState.submitting = false;
        updateCreateMeetingSummary();
    }
}

function findFallbackRoomId() {
    const rooms = typeof allRooms !== 'undefined' ? allRooms : [];
    const room = rooms.find(r => r.is_active !== false);
    return room ? room.id : NaN;
}

function showCreateMeetingSuccess() {
    cmEl('cmDialog')?.classList.add('is-success');
}

function showOnlineLocalSuccess() {
    showCreateMeetingSuccess();
}

function bindCreateMeetingEvents() {
    const overlay = cmEl('createMeetingModal');
    if (!overlay) return;

    ['cmTitle', 'cmDescription', 'cmDate', 'cmStart', 'cmEnd', 'cmMeetingLink', 'cmRecurrenceUntil'].forEach(id => {
        cmEl(id)?.addEventListener('input', () => {
            updateCreateMeetingSummary();
            if (['cmDate', 'cmStart', 'cmEnd', 'cmRecurrenceUntil'].includes(id)) {
                scheduleRoomSearchRefresh();
            }
        });
        cmEl(id)?.addEventListener('change', () => {
            updateRecurrenceNote();
            updateCreateMeetingSummary();
            if (['cmDate', 'cmStart', 'cmEnd', 'cmRecurrenceUntil'].includes(id)) {
                scheduleRoomSearchRefresh();
            }
        });
    });

    cmEl('cmRecurrence')?.addEventListener('change', () => setRecurrence());
    cmEl('cmAttendeeSearch')?.addEventListener('input', onAttendeeSearchInput);
    cmEl('cmAttendeeSearch')?.addEventListener('keydown', handleAttendeeKeydown);
    cmEl('cmFixedAmenityOptions')?.addEventListener('change', onFixedAmenityChange);
    cmEl('createMeetingForm')?.addEventListener('submit', handleCreateMeetingSubmit);

    document.addEventListener('click', event => {
        const wrap = document.querySelector('.cm-attendee-search');
        if (wrap && !wrap.contains(event.target)) closeAttendeeSuggest();
    });

    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && overlay.classList.contains('is-open')) closeCreateMeeting();
    });

    if (CM_PREVIEW) openCreateMeeting();
}

document.addEventListener('DOMContentLoaded', bindCreateMeetingEvents);

window.openCreateMeeting = openCreateMeeting;
window.closeCreateMeeting = closeCreateMeeting;
window.setCreateMeetingMode = setCreateMeetingMode;
window.setRecurrence = setRecurrence;
window.removeCreateMeetingAttendee = removeCreateMeetingAttendee;
window.addAllTeamMembers = addAllTeamMembers;
window.pickCreateMeetingAttendee = pickCreateMeetingAttendee;
window.searchMatchingRooms = searchMatchingRooms;
window.selectCreateMeetingRoomById = selectCreateMeetingRoomById;
window.changeCreateMeetingRoom = changeCreateMeetingRoom;
window.changeBorrowQty = changeBorrowQty;
window.reduceEquipmentToAvailable = reduceEquipmentToAvailable;
window.clearBorrowQty = clearBorrowQty;
window.generateMeetingLink = generateMeetingLink;
window.handleCreateMeetingSubmit = handleCreateMeetingSubmit;
window.showCreateMeetingSuccess = showCreateMeetingSuccess;
````

## File: scripts/patch_db.py
````python
import os
import sys
import json
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

engine = create_engine(os.getenv('DATABASE_URL'))

with engine.connect() as conn:
    # 1. Kiểm tra và thêm cột amenities vào bảng rooms nếu chưa có
    cols = [row[0] for row in conn.execute(text("SHOW COLUMNS FROM rooms")).fetchall()]
    if 'amenities' not in cols:
        print("Adding amenities column to rooms table...")
        conn.execute(text("ALTER TABLE rooms ADD COLUMN amenities TEXT DEFAULT NULL AFTER description"))
        conn.commit()
        print("Column 'amenities' added to rooms table.")
    else:
        print("Column 'amenities' already exists in rooms table.")

    # 1.1 Kiểm tra và thêm cột meeting_type, online_link vào bảng meetings nếu chưa có
    cols_meetings = [row[0] for row in conn.execute(text("SHOW COLUMNS FROM meetings")).fetchall()]
    if 'meeting_type' not in cols_meetings:
        print("Adding meeting_type column to meetings table...")
        conn.execute(text("ALTER TABLE meetings ADD COLUMN meeting_type VARCHAR(20) NOT NULL DEFAULT 'offline' AFTER description"))
        conn.commit()
        print("Column 'meeting_type' added to meetings table.")
    if 'online_link' not in cols_meetings:
        print("Adding online_link column to meetings table...")
        conn.execute(text("ALTER TABLE meetings ADD COLUMN online_link VARCHAR(500) DEFAULT NULL AFTER meeting_type"))
        conn.commit()
        print("Column 'online_link' added to meetings table.")
    
    room_id_col = conn.execute(text("SHOW COLUMNS FROM meetings LIKE 'room_id'")).fetchone()
    if room_id_col and room_id_col[2] == 'NO':
        col_type = room_id_col[1]
        conn.execute(text(f"ALTER TABLE meetings MODIFY COLUMN room_id {col_type} NULL"))
        conn.commit()
        print("Column 'room_id' modified to allow NULL.")

    # 2. Cập nhật dữ liệu tiện ích cho các phòng hiện tại
    # Đặc biệt phòng vip viyyyy (id 10) từ ảnh của người dùng
    conn.execute(text("""
        UPDATE rooms 
        SET amenities = :amenities 
        WHERE name = 'vip viyyyy' OR id = 10
    """), {"amenities": json.dumps(["Màn hình", "Wifi", "Video", "Đồ uống"], ensure_ascii=False)})

    # Cập nhật phòng VIP (id 3)
    conn.execute(text("""
        UPDATE rooms 
        SET amenities = :amenities 
        WHERE id = 3
    """), {"amenities": json.dumps(["Màn hình trực tuyến", "Micro hội nghị", "Wifi", "Máy chiếu 4K"], ensure_ascii=False)})

    # Cập nhật phòng A (id 1)
    conn.execute(text("""
        UPDATE rooms 
        SET amenities = :amenities 
        WHERE id = 1
    """), {"amenities": json.dumps(["Màn hình TV", "Wifi tốc độ cao", "Bảng trắng"], ensure_ascii=False)})

    # Cập nhật phòng B (id 2)
    conn.execute(text("""
        UPDATE rooms 
        SET amenities = :amenities 
        WHERE id = 2
    """), {"amenities": json.dumps(["Máy chiếu", "Wifi", "Hệ thống âm thanh", "Bảng viết"], ensure_ascii=False)})

    conn.commit()
    print("Updated rooms with default amenities!")

    # 3. Khởi tạo một số thiết bị kho (equipments) để kho có sẵn thiết bị mượn thêm
    existing_eq_count = conn.execute(text("SELECT COUNT(*) FROM equipments")).scalar()
    if existing_eq_count == 0:
        print("Seeding default warehouse equipments...")
        default_equipments = [
            ("Màn hình di động 55 inch", "DISP-55", "Hiển thị", 3, "Màn hình di động chuyên dụng cho thuyết trình"),
            ("Máy chiếu không dây Full HD", "PROJ-WF", "Trình chiếu", 4, "Máy chiếu độ sáng cao hỗ trợ AirPlay/Miracast"),
            ("Micro không dây hội nghị", "MIC-WL", "Âm thanh", 8, "Bộ 2 micro không dây chống hú"),
            ("Loa họp trực tuyến Jabra Speak", "SPK-JB", "Âm thanh", 5, "Loa hội nghị tích hợp mic định hướng 360 độ"),
            ("Bút trình chiếu Laser đa năng", "PEN-LZ", "Phụ kiện", 6, "Bút laser kèm điều khiển slide qua USB"),
            ("Bộ chuyển đổi HDMI & USB-C", "CAB-AD", "Phụ kiện", 12, "Bộ cáp chuyển đa cổng cho laptop và điện thoại"),
            ("Bảng Flipchart di động", "BRD-FC", "Văn phòng phẩm", 4, "Bảng kẹp giấy viết di động có bánh xe"),
        ]
        for name, code, cat, qty, desc in default_equipments:
            conn.execute(text("""
                INSERT INTO equipments (name, code, category, total_qty, description, is_active, created_at)
                VALUES (:name, :code, :category, :total_qty, :description, 1, NOW())
            """), {
                "name": name,
                "code": code,
                "category": cat,
                "total_qty": qty,
                "description": desc
            })
        conn.commit()
        print(f"Seeded {len(default_equipments)} equipments successfully!")
    else:
        print(f"Equipments table already has {existing_eq_count} items.")

print("Patch DB completed successfully!")
````

## File: tests/test_meetings_mine.py
````python
"""Tests for the personal meeting list and invite responses."""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from app import main
from tests.helpers import (
    _add_participant,
    _auth_header,
    _create_meeting,
    _create_room,
    _create_user,
    _make_token,
)


def test_mine_separates_organizer_and_invitee_and_includes_rsvp(
    client: TestClient, db_session: Session
):
    organizer = _create_user(db_session, "mine_organizer")
    invitee = _create_user(db_session, "mine_invitee")
    outsider = _create_user(db_session, "mine_outsider")
    room = _create_room(db_session, "Mine Room")
    meeting = _create_meeting(
        db_session,
        room,
        organizer,
        datetime.utcnow() + timedelta(days=1),
        datetime.utcnow() + timedelta(days=1, hours=1),
    )
    canceled_meeting = _create_meeting(
        db_session,
        room,
        organizer,
        datetime.utcnow() + timedelta(days=3),
        datetime.utcnow() + timedelta(days=3, hours=1),
        status="canceled",
    )
    participation = _add_participant(db_session, meeting, invitee)
    participation.response_status = "accepted"
    db_session.commit()

    organizer_response = client.get(
        "/api/meetings/mine", headers=_auth_header(_make_token(organizer))
    )
    assert organizer_response.status_code == 200
    organizer_item = organizer_response.json()[0]
    assert organizer_item["id"] == meeting.id
    assert organizer_item["is_organizer"] is True
    assert organizer_item["participants"][0]["response_status"] == "accepted"
    assert all(item["id"] != canceled_meeting.id for item in organizer_response.json())

    invitee_response = client.get(
        "/api/meetings/mine", headers=_auth_header(_make_token(invitee))
    )
    assert invitee_response.status_code == 200
    invitee_item = invitee_response.json()[0]
    assert invitee_item["is_organizer"] is False
    assert invitee_item["my_response_status"] == "accepted"

    outsider_response = client.get(
        "/api/meetings/mine", headers=_auth_header(_make_token(outsider))
    )
    assert outsider_response.status_code == 200
    assert outsider_response.json() == []


def test_invitee_can_update_own_response_but_nonparticipant_cannot(
    client: TestClient, db_session: Session
):
    organizer = _create_user(db_session, "rsvp_organizer")
    invitee = _create_user(db_session, "rsvp_invitee")
    outsider = _create_user(db_session, "rsvp_outsider")
    room = _create_room(db_session, "RSVP Room")
    meeting = _create_meeting(
        db_session,
        room,
        organizer,
        datetime.utcnow() + timedelta(days=2),
        datetime.utcnow() + timedelta(days=2, hours=1),
    )
    _add_participant(db_session, meeting, invitee)

    response = client.patch(
        f"/api/meetings/{meeting.id}/response",
        headers=_auth_header(_make_token(invitee)),
        json={"response_status": "declined"},
    )
    assert response.status_code == 200
    assert response.json()["response_status"] == "declined"

    outsider_response = client.patch(
        f"/api/meetings/{meeting.id}/response",
        headers=_auth_header(_make_token(outsider)),
        json={"response_status": "accepted"},
    )
    assert outsider_response.status_code == 404

    invalid_response = client.patch(
        f"/api/meetings/{meeting.id}/response",
        headers=_auth_header(_make_token(invitee)),
        json={"response_status": "maybe"},
    )
    assert invalid_response.status_code == 422


def test_mine_handles_missing_organizer_and_room_relationships(
    client: TestClient, db_session: Session
):
    organizer = _create_user(db_session, "orphan_organizer")
    invitee = _create_user(db_session, "orphan_invitee")
    room = _create_room(db_session, "Orphan Room")
    meeting = _create_meeting(
        db_session,
        room,
        organizer,
        datetime.utcnow() + timedelta(days=2),
        datetime.utcnow() + timedelta(days=2, hours=1),
    )
    _add_participant(db_session, meeting, invitee)
    meeting.organizer_id = None
    meeting.room_id = None
    db_session.commit()

    response = client.get(
        "/api/meetings/mine", headers=_auth_header(_make_token(invitee))
    )

    assert response.status_code == 200
    item = response.json()[0]
    assert item["organizer_name"] == "Người tổ chức"
    assert item["room_name"] is None
    assert item["is_organizer"] is False


def test_missing_rsvp_column_returns_actionable_service_error(
    client: TestClient, db_session: Session
):
    organizer = _create_user(db_session, "schema_organizer")
    invitee = _create_user(db_session, "schema_invitee")
    room = _create_room(db_session, "Schema Room")
    meeting = _create_meeting(
        db_session,
        room,
        organizer,
        datetime.utcnow() - timedelta(days=4, hours=1),
        datetime.utcnow() - timedelta(days=4),
    )
    _add_participant(db_session, meeting, invitee)
    meeting_id = meeting.id
    db_session.execute(text("ALTER TABLE meeting_participants DROP COLUMN response_status"))
    db_session.commit()

    headers = _auth_header(_make_token(invitee))
    mine_response = client.get("/api/meetings/mine", headers=headers)
    assert mine_response.status_code == 503
    assert "schema/migration" in mine_response.json()["detail"]

    list_response = client.get("/api/meetings/")
    assert list_response.status_code == 503
    history_response = client.get("/api/meetings/history", headers=headers)
    assert history_response.status_code == 503

    rsvp_response = client.patch(
        f"/api/meetings/{meeting_id}/response",
        headers=headers,
        json={"response_status": "accepted"},
    )
    assert rsvp_response.status_code == 503
    assert "schema/migration" in rsvp_response.json()["detail"]


def test_startup_migration_adds_missing_rsvp_column(monkeypatch):
    migration_engine = create_engine("sqlite://")
    with migration_engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE meeting_participants "
            "(id INTEGER PRIMARY KEY, meeting_id INTEGER NOT NULL, user_id INTEGER NOT NULL)"
        ))

    monkeypatch.setattr(main, "engine", migration_engine)
    try:
        main._auto_migrate_schema()
        columns = {column["name"] for column in inspect(migration_engine).get_columns("meeting_participants")}
        assert "response_status" in columns
    finally:
        migration_engine.dispose()
````

## File: .dockerignore
````
__pycache__
*.pyc
.venv
venv
.git
.gitignore
.env
````

## File: Dockerfile
````dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        default-libmysqlclient-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
````

## File: alembic/env.py
````python
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
````

## File: app/core/database.py
````python
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

# Lấy chuỗi kết nối từ .env
DATABASE_URL = os.getenv("DATABASE_URL")

# Nếu chưa tạo file .env thì báo lỗi rõ ràng
if not DATABASE_URL:
    raise ValueError("Chưa tìm thấy DATABASE_URL! Vui lòng tạo file .env từ .env.example")


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Tự kiểm tra kết nối sống[cite: 8]
    pool_size=10,         # Tối đa 10 kết nối thường trực
    max_overflow=20,      # Cho phép mở rộng tối đa thêm 20 kết nối khi quá tải
    pool_recycle=1800     # Tự động làm mới kết nối sau mỗi 30 phút để tránh bị treo
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
````

## File: frontend/assets/index-DDntIe9W.css
````css
@import "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap";@layer components;@layer properties{@supports (((-webkit-hyphens:none)) and (not (margin-trim:inline))) or ((-moz-orient:inline) and (not (color:rgb(from red r g b)))){*,:before,:after,::backdrop{--tw-translate-x:0;--tw-translate-y:0;--tw-translate-z:0;--tw-rotate-x:initial;--tw-rotate-y:initial;--tw-rotate-z:initial;--tw-skew-x:initial;--tw-skew-y:initial;--tw-space-y-reverse:0;--tw-border-style:solid;--tw-leading:initial;--tw-font-weight:initial;--tw-tracking:initial;--tw-shadow:0 0 #0000;--tw-shadow-color:initial;--tw-shadow-alpha:100%;--tw-inset-shadow:0 0 #0000;--tw-inset-shadow-color:initial;--tw-inset-shadow-alpha:100%;--tw-ring-color:initial;--tw-ring-shadow:0 0 #0000;--tw-inset-ring-color:initial;--tw-inset-ring-shadow:0 0 #0000;--tw-ring-inset:initial;--tw-ring-offset-width:0px;--tw-ring-offset-color:#fff;--tw-ring-offset-shadow:0 0 #0000;--tw-blur:initial;--tw-brightness:initial;--tw-contrast:initial;--tw-grayscale:initial;--tw-hue-rotate:initial;--tw-invert:initial;--tw-opacity:initial;--tw-saturate:initial;--tw-sepia:initial;--tw-drop-shadow:initial;--tw-drop-shadow-color:initial;--tw-drop-shadow-alpha:100%;--tw-drop-shadow-size:initial}}}@layer theme{:root,:host{--font-mono:ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;--color-red-500:oklch(63.7% .237 25.331);--color-green-500:oklch(72.3% .219 149.579);--color-blue-400:oklch(70.7% .165 254.624);--color-gray-50:oklch(98.5% .002 247.839);--color-gray-100:oklch(96.7% .003 264.542);--color-gray-200:oklch(92.8% .006 264.531);--color-gray-300:oklch(87.2% .01 258.338);--color-gray-400:oklch(70.7% .022 261.325);--color-gray-500:oklch(55.1% .027 264.364);--color-gray-600:oklch(44.6% .03 256.802);--color-gray-700:oklch(37.3% .034 259.733);--color-gray-800:oklch(27.8% .033 256.848);--color-gray-900:oklch(21% .034 264.665);--color-white:#fff;--spacing:.25rem;--text-xs:.75rem;--text-xs--line-height:calc(1 / .75);--text-sm:.875rem;--text-sm--line-height:calc(1.25 / .875);--text-lg:1.125rem;--text-lg--line-height:calc(1.75 / 1.125);--text-xl:1.25rem;--text-xl--line-height:calc(1.75 / 1.25);--text-2xl:1.5rem;--text-2xl--line-height:calc(2 / 1.5);--font-weight-medium:500;--font-weight-semibold:600;--font-weight-bold:700;--tracking-tight:-.025em;--leading-snug:1.375;--radius-md:.375rem;--radius-lg:.5rem;--default-transition-duration:.15s;--default-transition-timing-function:cubic-bezier(.4, 0, .2, 1);--default-font-family:"Inter", system-ui, sans-serif;--default-mono-font-family:var(--font-mono)}}@layer base{*,:after,:before,::backdrop{box-sizing:border-box;border:0 solid;margin:0;padding:0}::file-selector-button{box-sizing:border-box;border:0 solid;margin:0;padding:0}html,:host{-webkit-text-size-adjust:100%;tab-size:4;line-height:1.5;font-family:var(--default-font-family,-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", "Noto Sans", Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji");font-feature-settings:var(--default-font-feature-settings,normal);font-variation-settings:var(--default-font-variation-settings,normal);-webkit-tap-highlight-color:transparent}hr{height:0;color:inherit;border-top-width:1px}abbr:where([title]){-webkit-text-decoration:underline dotted;text-decoration:underline dotted}h1,h2,h3,h4,h5,h6{font-size:inherit;font-weight:inherit}a{color:inherit;-webkit-text-decoration:inherit;-webkit-text-decoration:inherit;-webkit-text-decoration:inherit;-webkit-text-decoration:inherit;text-decoration:inherit}b,strong{font-weight:bolder}code,kbd,samp,pre{font-family:var(--default-mono-font-family,ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace);font-feature-settings:var(--default-mono-font-feature-settings,normal);font-variation-settings:var(--default-mono-font-variation-settings,normal);font-size:1em}small{font-size:80%}sub,sup{vertical-align:baseline;font-size:75%;line-height:0;position:relative}sub{bottom:-.25em}sup{top:-.5em}table{text-indent:0;border-color:inherit;border-collapse:collapse}:-moz-focusring:where(:not(iframe)){outline:auto}progress{vertical-align:baseline}summary{display:list-item}ol,ul,menu{list-style:none}img,svg,video,canvas,audio,iframe,embed,object{vertical-align:middle;display:block}img,video{max-width:100%;height:auto}button,input,select,optgroup,textarea{font:inherit;font-feature-settings:inherit;font-variation-settings:inherit;letter-spacing:inherit;color:inherit;opacity:1;background-color:#0000;border-radius:0}::file-selector-button{font:inherit;font-feature-settings:inherit;font-variation-settings:inherit;letter-spacing:inherit;color:inherit;opacity:1;background-color:#0000;border-radius:0}:where(select:is([multiple],[size])) optgroup{font-weight:bolder}:where(select:is([multiple],[size])) optgroup option{padding-inline-start:20px}::file-selector-button{margin-inline-end:4px}::placeholder{opacity:1}@supports (not ((-webkit-appearance:-apple-pay-button))) or (contain-intrinsic-size:1px){::placeholder{color:currentColor}@supports (color:color-mix(in lab, red, red)){::placeholder{color:color-mix(in oklab, currentcolor 50%, transparent)}}}textarea{resize:vertical}::-webkit-search-decoration{-webkit-appearance:none}::-webkit-date-and-time-value{min-height:1lh;text-align:inherit}::-webkit-datetime-edit{display:inline-flex}::-webkit-datetime-edit-fields-wrapper{padding:0}::-webkit-datetime-edit{padding-block:0}::-webkit-datetime-edit-year-field{padding-block:0}::-webkit-datetime-edit-month-field{padding-block:0}::-webkit-datetime-edit-day-field{padding-block:0}::-webkit-datetime-edit-hour-field{padding-block:0}::-webkit-datetime-edit-minute-field{padding-block:0}::-webkit-datetime-edit-second-field{padding-block:0}::-webkit-datetime-edit-millisecond-field{padding-block:0}::-webkit-datetime-edit-meridiem-field{padding-block:0}::-webkit-calendar-picker-indicator{line-height:1}:-moz-ui-invalid{box-shadow:none}button,input:where([type=button],[type=reset],[type=submit]){appearance:button}::file-selector-button{appearance:button}::-webkit-inner-spin-button{height:auto}::-webkit-outer-spin-button{height:auto}[hidden]:where(:not([hidden=until-found])){display:none!important}}@layer utilities{.pointer-events-none{pointer-events:none}.absolute{position:absolute}.fixed{position:fixed}.relative{position:relative}.top-0{top:0}.top-1\.5{top:calc(var(--spacing) * 1.5)}.top-1\/2{top:50%}.top-3{top:calc(var(--spacing) * 3)}.right-0{right:0}.right-1\.5{right:calc(var(--spacing) * 1.5)}.right-2{right:calc(var(--spacing) * 2)}.right-3{right:calc(var(--spacing) * 3)}.bottom-0{bottom:0}.left-0{left:0}.left-3{left:calc(var(--spacing) * 3)}.z-50{z-index:50}.mx-1{margin-inline:var(--spacing)}.mt-0\.5{margin-top:calc(var(--spacing) * .5)}.mt-auto{margin-top:auto}.mb-0\.5{margin-bottom:calc(var(--spacing) * .5)}.mb-1{margin-bottom:var(--spacing)}.mb-1\.5{margin-bottom:calc(var(--spacing) * 1.5)}.mb-3{margin-bottom:calc(var(--spacing) * 3)}.mb-4{margin-bottom:calc(var(--spacing) * 4)}.mb-6{margin-bottom:calc(var(--spacing) * 6)}.ml-auto{margin-left:auto}.block{display:block}.flex{display:flex}.grid{display:grid}.hidden{display:none}.inline{display:inline}.inline-block{display:inline-block}.inline-flex{display:inline-flex}.h-0\.5{height:calc(var(--spacing) * .5)}.h-1\.5{height:calc(var(--spacing) * 1.5)}.h-2{height:calc(var(--spacing) * 2)}.h-8{height:calc(var(--spacing) * 8)}.h-9{height:calc(var(--spacing) * 9)}.h-\[56px\]{height:56px}.h-\[60px\]{height:60px}.h-full{height:100%}.min-h-screen{min-height:100vh}.w-1\.5{width:calc(var(--spacing) * 1.5)}.w-2{width:calc(var(--spacing) * 2)}.w-8{width:calc(var(--spacing) * 8)}.w-9{width:calc(var(--spacing) * 9)}.w-\[220px\]{width:220px}.w-full{width:100%}.max-w-\[480px\]{max-width:480px}.min-w-0{min-width:0}.flex-1{flex:1}.flex-shrink-0{flex-shrink:0}.-translate-y-1\/2{--tw-translate-y:calc(calc(1 / 2 * 100%) * -1);translate:var(--tw-translate-x) var(--tw-translate-y)}.transform{transform:var(--tw-rotate-x,) var(--tw-rotate-y,) var(--tw-rotate-z,) var(--tw-skew-x,) var(--tw-skew-y,)}.cursor-pointer{cursor:pointer}.appearance-none{appearance:none}.grid-cols-2{grid-template-columns:repeat(2,minmax(0,1fr))}.grid-cols-3{grid-template-columns:repeat(3,minmax(0,1fr))}.grid-cols-4{grid-template-columns:repeat(4,minmax(0,1fr))}.flex-col{flex-direction:column}.flex-wrap{flex-wrap:wrap}.items-center{align-items:center}.justify-between{justify-content:space-between}.justify-center{justify-content:center}.gap-1{gap:var(--spacing)}.gap-1\.5{gap:calc(var(--spacing) * 1.5)}.gap-2{gap:calc(var(--spacing) * 2)}.gap-3{gap:calc(var(--spacing) * 3)}.gap-4{gap:calc(var(--spacing) * 4)}.gap-5{gap:calc(var(--spacing) * 5)}:where(.space-y-0\.5>:not(:last-child)){--tw-space-y-reverse:0;margin-block-start:calc(calc(var(--spacing) * .5) * var(--tw-space-y-reverse));margin-block-end:calc(calc(var(--spacing) * .5) * calc(1 - var(--tw-space-y-reverse)))}:where(.space-y-3>:not(:last-child)){--tw-space-y-reverse:0;margin-block-start:calc(calc(var(--spacing) * 3) * var(--tw-space-y-reverse));margin-block-end:calc(calc(var(--spacing) * 3) * calc(1 - var(--tw-space-y-reverse)))}:where(.space-y-4>:not(:last-child)){--tw-space-y-reverse:0;margin-block-start:calc(calc(var(--spacing) * 4) * var(--tw-space-y-reverse));margin-block-end:calc(calc(var(--spacing) * 4) * calc(1 - var(--tw-space-y-reverse)))}.truncate{text-overflow:ellipsis;white-space:nowrap;overflow:hidden}.overflow-hidden{overflow:hidden}.overflow-y-auto{overflow-y:auto}.rounded-\[10px\]{border-radius:10px}.rounded-full{border-radius:2147483647px}.rounded-lg{border-radius:var(--radius-lg)}.rounded-md{border-radius:var(--radius-md)}.border{border-style:var(--tw-border-style);border-width:1px}.border-2{border-style:var(--tw-border-style);border-width:2px}.border-t{border-top-style:var(--tw-border-style);border-top-width:1px}.border-r{border-right-style:var(--tw-border-style);border-right-width:1px}.border-b{border-bottom-style:var(--tw-border-style);border-bottom-width:1px}.border-gray-100{border-color:var(--color-gray-100)}.border-gray-200{border-color:var(--color-gray-200)}.border-white{border-color:var(--color-white)}.bg-gray-50{background-color:var(--color-gray-50)}.bg-gray-100{background-color:var(--color-gray-100)}.bg-green-500{background-color:var(--color-green-500)}.bg-red-500{background-color:var(--color-red-500)}.bg-white{background-color:var(--color-white)}.object-cover{object-fit:cover}.p-4{padding:calc(var(--spacing) * 4)}.p-6{padding:calc(var(--spacing) * 6)}.px-2{padding-inline:calc(var(--spacing) * 2)}.px-2\.5{padding-inline:calc(var(--spacing) * 2.5)}.px-3{padding-inline:calc(var(--spacing) * 3)}.px-4{padding-inline:calc(var(--spacing) * 4)}.px-5{padding-inline:calc(var(--spacing) * 5)}.px-6{padding-inline:calc(var(--spacing) * 6)}.py-0\.5{padding-block:calc(var(--spacing) * .5)}.py-1{padding-block:var(--spacing)}.py-1\.5{padding-block:calc(var(--spacing) * 1.5)}.py-2{padding-block:calc(var(--spacing) * 2)}.py-2\.5{padding-block:calc(var(--spacing) * 2.5)}.py-3{padding-block:calc(var(--spacing) * 3)}.py-4{padding-block:calc(var(--spacing) * 4)}.py-5{padding-block:calc(var(--spacing) * 5)}.pt-3{padding-top:calc(var(--spacing) * 3)}.pt-4{padding-top:calc(var(--spacing) * 4)}.pr-4{padding-right:calc(var(--spacing) * 4)}.pr-8{padding-right:calc(var(--spacing) * 8)}.pb-20{padding-bottom:calc(var(--spacing) * 20)}.pl-3{padding-left:calc(var(--spacing) * 3)}.pl-9{padding-left:calc(var(--spacing) * 9)}.text-left{text-align:left}.text-2xl{font-size:var(--text-2xl);line-height:var(--tw-leading,var(--text-2xl--line-height))}.text-lg{font-size:var(--text-lg);line-height:var(--tw-leading,var(--text-lg--line-height))}.text-sm{font-size:var(--text-sm);line-height:var(--tw-leading,var(--text-sm--line-height))}.text-xl{font-size:var(--text-xl);line-height:var(--tw-leading,var(--text-xl--line-height))}.text-xs{font-size:var(--text-xs);line-height:var(--tw-leading,var(--text-xs--line-height))}.text-\[10px\]{font-size:10px}.text-\[11px\]{font-size:11px}.text-\[12px\]{font-size:12px}.text-\[13px\]{font-size:13px}.text-\[14px\]{font-size:14px}.text-\[15px\]{font-size:15px}.leading-snug{--tw-leading:var(--leading-snug);line-height:var(--leading-snug)}.font-bold{--tw-font-weight:var(--font-weight-bold);font-weight:var(--font-weight-bold)}.font-medium{--tw-font-weight:var(--font-weight-medium);font-weight:var(--font-weight-medium)}.font-semibold{--tw-font-weight:var(--font-weight-semibold);font-weight:var(--font-weight-semibold)}.tracking-tight{--tw-tracking:var(--tracking-tight);letter-spacing:var(--tracking-tight)}.text-gray-300{color:var(--color-gray-300)}.text-gray-400{color:var(--color-gray-400)}.text-gray-500{color:var(--color-gray-500)}.text-gray-600{color:var(--color-gray-600)}.text-gray-700{color:var(--color-gray-700)}.text-gray-800{color:var(--color-gray-800)}.text-gray-900{color:var(--color-gray-900)}.text-white{color:var(--color-white)}.placeholder-gray-400::placeholder{color:var(--color-gray-400)}.ring-1{--tw-ring-shadow:var(--tw-ring-inset,) 0 0 0 calc(1px + var(--tw-ring-offset-width)) var(--tw-ring-color,currentcolor);box-shadow:var(--tw-inset-shadow), var(--tw-inset-ring-shadow), var(--tw-ring-offset-shadow), var(--tw-ring-shadow), var(--tw-shadow)}.ring-gray-200{--tw-ring-color:var(--color-gray-200)}.filter{filter:var(--tw-blur,) var(--tw-brightness,) var(--tw-contrast,) var(--tw-grayscale,) var(--tw-hue-rotate,) var(--tw-invert,) var(--tw-saturate,) var(--tw-sepia,) var(--tw-drop-shadow,)}.transition{transition-property:color,background-color,border-color,outline-color,text-decoration-color,fill,stroke,--tw-gradient-from,--tw-gradient-via,--tw-gradient-to,opacity,box-shadow,transform,translate,scale,rotate,filter,-webkit-backdrop-filter,backdrop-filter,display,content-visibility,overlay,pointer-events;transition-timing-function:var(--tw-ease,var(--default-transition-timing-function));transition-duration:var(--tw-duration,var(--default-transition-duration))}.transition-all{transition-property:all;transition-timing-function:var(--tw-ease,var(--default-transition-timing-function));transition-duration:var(--tw-duration,var(--default-transition-duration))}.transition-colors{transition-property:color,background-color,border-color,outline-color,text-decoration-color,fill,stroke,--tw-gradient-from,--tw-gradient-via,--tw-gradient-to;transition-timing-function:var(--tw-ease,var(--default-transition-timing-function));transition-duration:var(--tw-duration,var(--default-transition-duration))}.outline-none{--tw-outline-style:none;outline-style:none}@media (hover:hover){.hover\:border-blue-400:hover{border-color:var(--color-blue-400)}.hover\:bg-gray-50:hover{background-color:var(--color-gray-50)}.hover\:bg-gray-100:hover{background-color:var(--color-gray-100)}}@media (width>=64rem){.lg\:flex{display:flex}.lg\:hidden{display:none}}}*{box-sizing:border-box}body{-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;background-color:#f9fafb;font-family:Inter,system-ui,sans-serif}@property --tw-translate-x{syntax:"*";inherits:false;initial-value:0}@property --tw-translate-y{syntax:"*";inherits:false;initial-value:0}@property --tw-translate-z{syntax:"*";inherits:false;initial-value:0}@property --tw-rotate-x{syntax:"*";inherits:false}@property --tw-rotate-y{syntax:"*";inherits:false}@property --tw-rotate-z{syntax:"*";inherits:false}@property --tw-skew-x{syntax:"*";inherits:false}@property --tw-skew-y{syntax:"*";inherits:false}@property --tw-space-y-reverse{syntax:"*";inherits:false;initial-value:0}@property --tw-border-style{syntax:"*";inherits:false;initial-value:solid}@property --tw-leading{syntax:"*";inherits:false}@property --tw-font-weight{syntax:"*";inherits:false}@property --tw-tracking{syntax:"*";inherits:false}@property --tw-shadow{syntax:"*";inherits:false;initial-value:0 0 #0000}@property --tw-shadow-color{syntax:"*";inherits:false}@property --tw-shadow-alpha{syntax:"<percentage>";inherits:false;initial-value:100%}@property --tw-inset-shadow{syntax:"*";inherits:false;initial-value:0 0 #0000}@property --tw-inset-shadow-color{syntax:"*";inherits:false}@property --tw-inset-shadow-alpha{syntax:"<percentage>";inherits:false;initial-value:100%}@property --tw-ring-color{syntax:"*";inherits:false}@property --tw-ring-shadow{syntax:"*";inherits:false;initial-value:0 0 #0000}@property --tw-inset-ring-color{syntax:"*";inherits:false}@property --tw-inset-ring-shadow{syntax:"*";inherits:false;initial-value:0 0 #0000}@property --tw-ring-inset{syntax:"*";inherits:false}@property --tw-ring-offset-width{syntax:"<length>";inherits:false;initial-value:0}@property --tw-ring-offset-color{syntax:"*";inherits:false;initial-value:#fff}@property --tw-ring-offset-shadow{syntax:"*";inherits:false;initial-value:0 0 #0000}@property --tw-blur{syntax:"*";inherits:false}@property --tw-brightness{syntax:"*";inherits:false}@property --tw-contrast{syntax:"*";inherits:false}@property --tw-grayscale{syntax:"*";inherits:false}@property --tw-hue-rotate{syntax:"*";inherits:false}@property --tw-invert{syntax:"*";inherits:false}@property --tw-opacity{syntax:"*";inherits:false}@property --tw-saturate{syntax:"*";inherits:false}@property --tw-sepia{syntax:"*";inherits:false}@property --tw-drop-shadow{syntax:"*";inherits:false}@property --tw-drop-shadow-color{syntax:"*";inherits:false}@property --tw-drop-shadow-alpha{syntax:"<percentage>";inherits:false;initial-value:100%}@property --tw-drop-shadow-size{syntax:"*";inherits:false}
````

## File: frontend/assets/index-DPhpmZ5j.js
````javascript
var e=Object.create,t=Object.defineProperty,n=Object.getOwnPropertyDescriptor,r=Object.getOwnPropertyNames,i=Object.getPrototypeOf,a=Object.prototype.hasOwnProperty,o=(e,t)=>()=>(t||(e((t={exports:{}}).exports,t),e=null),t.exports),s=(e,i,o,s)=>{if(i&&typeof i==`object`||typeof i==`function`)for(var c=r(i),l=0,u=c.length,d;l<u;l++)d=c[l],!a.call(e,d)&&d!==o&&t(e,d,{get:(e=>i[e]).bind(null,d),enumerable:!(s=n(i,d))||s.enumerable});return e},c=(n,r,o)=>(o=n==null?{}:e(i(n)),s(r||!n||!n.__esModule||!a.call(n,`default`)?t(o,`default`,{value:n,enumerable:!0}):o,n));(function(){let e=document.createElement(`link`).relList;if(e&&e.supports&&e.supports(`modulepreload`))return;for(let e of document.querySelectorAll(`link[rel="modulepreload"]`))n(e);new MutationObserver(e=>{for(let t of e)if(t.type===`childList`)for(let e of t.addedNodes)e.tagName===`LINK`&&e.rel===`modulepreload`&&n(e)}).observe(document,{childList:!0,subtree:!0});function t(e){let t={};return e.integrity&&(t.integrity=e.integrity),e.referrerPolicy&&(t.referrerPolicy=e.referrerPolicy),t.credentials=e.crossOrigin===`use-credentials`?`include`:e.crossOrigin===`anonymous`?`omit`:`same-origin`,t}function n(e){if(e.ep)return;e.ep=!0;let n=t(e);fetch(e.href,n)}})();var l=o((e=>{var t=Symbol.for(`react.transitional.element`),n=Symbol.for(`react.portal`),r=Symbol.for(`react.fragment`),i=Symbol.for(`react.strict_mode`),a=Symbol.for(`react.profiler`),o=Symbol.for(`react.consumer`),s=Symbol.for(`react.context`),c=Symbol.for(`react.forward_ref`),l=Symbol.for(`react.suspense`),u=Symbol.for(`react.memo`),d=Symbol.for(`react.lazy`),f=Symbol.for(`react.activity`),p=Symbol.for(`react.view_transition`),m=Symbol.iterator;function h(e){return typeof e!=`object`||!e?null:(e=m&&e[m]||e[`@@iterator`],typeof e==`function`?e:null)}var g={isMounted:function(){return!1},enqueueForceUpdate:function(){},enqueueReplaceState:function(){},enqueueSetState:function(){}},_=Object.assign,v={};function y(e,t,n){this.props=e,this.context=t,this.refs=v,this.updater=n||g}y.prototype.isReactComponent={},y.prototype.setState=function(e,t){if(typeof e!=`object`&&typeof e!=`function`&&e!=null)throw Error(`takes an object of state variables to update or a function which returns an object of state variables.`);this.updater.enqueueSetState(this,e,t,`setState`)},y.prototype.forceUpdate=function(e){this.updater.enqueueForceUpdate(this,e,`forceUpdate`)};function b(){}b.prototype=y.prototype;function x(e,t,n){this.props=e,this.context=t,this.refs=v,this.updater=n||g}var S=x.prototype=new b;S.constructor=x,_(S,y.prototype),S.isPureReactComponent=!0;var ee=Array.isArray;function te(){}var C={H:null,A:null,T:null,S:null},ne=Object.prototype.hasOwnProperty;function w(e,n,r){var i=r.ref;return{$$typeof:t,type:e,key:n,ref:i===void 0?null:i,props:r}}function re(e,t){return w(e.type,t,e.props)}function ie(e){return typeof e==`object`&&!!e&&e.$$typeof===t}function ae(e){var t={"=":`=0`,":":`=2`};return`$`+e.replace(/[=:]/g,function(e){return t[e]})}var oe=/\/+/g;function se(e,t){return typeof e==`object`&&e&&e.key!=null?ae(``+e.key):t.toString(36)}function ce(e){switch(e.status){case`fulfilled`:return e.value;case`rejected`:throw e.reason;default:switch(typeof e.status==`string`?e.then(te,te):(e.status=`pending`,e.then(function(t){e.status===`pending`&&(e.status=`fulfilled`,e.value=t)},function(t){e.status===`pending`&&(e.status=`rejected`,e.reason=t)})),e.status){case`fulfilled`:return e.value;case`rejected`:throw e.reason}}throw e}function le(e,r,i,a,o){var s=typeof e;(s===`undefined`||s===`boolean`)&&(e=null);var c=!1;if(e===null)c=!0;else switch(s){case`bigint`:case`string`:case`number`:c=!0;break;case`object`:switch(e.$$typeof){case t:case n:c=!0;break;case d:return c=e._init,le(c(e._payload),r,i,a,o)}}if(c)return o=o(e),c=a===``?`.`+se(e,0):a,ee(o)?(i=``,c!=null&&(i=c.replace(oe,`$&/`)+`/`),le(o,r,i,``,function(e){return e})):o!=null&&(ie(o)&&(o=re(o,i+(o.key==null||e&&e.key===o.key?``:(``+o.key).replace(oe,`$&/`)+`/`)+c)),r.push(o)),1;c=0;var l=a===``?`.`:a+`:`;if(ee(e))for(var u=0;u<e.length;u++)a=e[u],s=l+se(a,u),c+=le(a,r,i,s,o);else if(u=h(e),typeof u==`function`)for(e=u.call(e),u=0;!(a=e.next()).done;)a=a.value,s=l+se(a,u++),c+=le(a,r,i,s,o);else if(s===`object`){if(typeof e.then==`function`)return le(ce(e),r,i,a,o);throw r=String(e),Error(`Objects are not valid as a React child (found: `+(r===`[object Object]`?`object with keys {`+Object.keys(e).join(`, `)+`}`:r)+`). If you meant to render a collection of children, use an array instead.`)}return c}function ue(e,t,n){if(e==null)return e;var r=[],i=0;return le(e,r,``,``,function(e){return t.call(n,e,i++)}),r}function de(e){if(e._status===-1){var t=e._result,n=t();n.then(function(t){(e._status===0||e._status===-1)&&(e._status=1,e._result=t,n.status===void 0&&(n.status=`fulfilled`,n.value=t))},function(t){(e._status===0||e._status===-1)&&(e._status=2,e._result=t,n.status===void 0&&(n.status=`rejected`,n.reason=t))}),e._status===-1&&(e._status=0,e._result=n)}if(e._status===1)return e._result.default;throw e._result}var fe=typeof reportError==`function`?reportError:function(e){if(typeof window==`object`&&typeof window.ErrorEvent==`function`){var t=new window.ErrorEvent(`error`,{bubbles:!0,cancelable:!0,message:typeof e==`object`&&e&&typeof e.message==`string`?String(e.message):String(e),error:e});if(!window.dispatchEvent(t))return}else if(typeof process==`object`&&typeof process.emit==`function`){process.emit(`uncaughtException`,e);return}console.error(e)};function pe(e){var t=C.T,n={};n.types=t===null?null:t.types,C.T=n;try{var r=e(),i=C.S;i!==null&&i(n,r),typeof r==`object`&&r&&typeof r.then==`function`&&r.then(te,fe)}catch(e){fe(e)}finally{t!==null&&n.types!==null&&(t.types=n.types),C.T=t}}function me(e){var t=C.T;if(t!==null){var n=t.types;n===null?t.types=[e]:n.indexOf(e)===-1&&n.push(e)}else pe(me.bind(null,e))}var he={map:ue,forEach:function(e,t,n){ue(e,function(){t.apply(this,arguments)},n)},count:function(e){var t=0;return ue(e,function(){t++}),t},toArray:function(e){return ue(e,function(e){return e})||[]},only:function(e){if(!ie(e))throw Error(`React.Children.only expected to receive a single React element child.`);return e}};e.Activity=f,e.Children=he,e.Component=y,e.Fragment=r,e.Profiler=a,e.PureComponent=x,e.StrictMode=i,e.Suspense=l,e.ViewTransition=p,e.__CLIENT_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE=C,e.__COMPILER_RUNTIME={__proto__:null,c:function(e){return C.H.useMemoCache(e)}},e.addTransitionType=me,e.cache=function(e){return function(){return e.apply(null,arguments)}},e.cacheSignal=function(){return null},e.cloneElement=function(e,t,n){if(e==null)throw Error(`The argument must be a React element, but you passed `+e+`.`);var r=_({},e.props),i=e.key;if(t!=null)for(a in t.key!==void 0&&(i=``+t.key),t)!ne.call(t,a)||a===`key`||a===`__self`||a===`__source`||a===`ref`&&t.ref===void 0||(r[a]=t[a]);var a=arguments.length-2;if(a===1)r.children=n;else if(1<a){for(var o=Array(a),s=0;s<a;s++)o[s]=arguments[s+2];r.children=o}return w(e.type,i,r)},e.createContext=function(e){return e={$$typeof:s,_currentValue:e,_currentValue2:e,_threadCount:0,Provider:null,Consumer:null},e.Provider=e,e.Consumer={$$typeof:o,_context:e},e},e.createElement=function(e,t,n){var r,i={},a=null;if(t!=null)for(r in t.key!==void 0&&(a=``+t.key),t)ne.call(t,r)&&r!==`key`&&r!==`__self`&&r!==`__source`&&(i[r]=t[r]);var o=arguments.length-2;if(o===1)i.children=n;else if(1<o){for(var s=Array(o),c=0;c<o;c++)s[c]=arguments[c+2];i.children=s}if(e&&e.defaultProps)for(r in o=e.defaultProps,o)i[r]===void 0&&(i[r]=o[r]);return w(e,a,i)},e.createRef=function(){return{current:null}},e.forwardRef=function(e){return{$$typeof:c,render:e}},e.isValidElement=ie,e.lazy=function(e){return{$$typeof:d,_payload:{_status:-1,_result:e},_init:de}},e.memo=function(e,t){return{$$typeof:u,type:e,compare:t===void 0?null:t}},e.startTransition=pe,e.unstable_useCacheRefresh=function(){return C.H.useCacheRefresh()},e.use=function(e){return C.H.use(e)},e.useActionState=function(e,t,n){return C.H.useActionState(e,t,n)},e.useCallback=function(e,t){return C.H.useCallback(e,t)},e.useContext=function(e){return C.H.useContext(e)},e.useDebugValue=function(){},e.useDeferredValue=function(e,t){return C.H.useDeferredValue(e,t)},e.useEffect=function(e,t){return C.H.useEffect(e,t)},e.useEffectEvent=function(e){return C.H.useEffectEvent(e)},e.useId=function(){return C.H.useId()},e.useImperativeHandle=function(e,t,n){return C.H.useImperativeHandle(e,t,n)},e.useInsertionEffect=function(e,t){return C.H.useInsertionEffect(e,t)},e.useLayoutEffect=function(e,t){return C.H.useLayoutEffect(e,t)},e.useMemo=function(e,t){return C.H.useMemo(e,t)},e.useOptimistic=function(e,t){return C.H.useOptimistic(e,t)},e.useReducer=function(e,t,n){return C.H.useReducer(e,t,n)},e.useRef=function(e){return C.H.useRef(e)},e.useState=function(e){return C.H.useState(e)},e.useSyncExternalStore=function(e,t,n){return C.H.useSyncExternalStore(e,t,n)},e.useTransition=function(){return C.H.useTransition()},e.version=`19.3.0`})),u=o(((e,t)=>{t.exports=l()})),d=o((e=>{function t(e,t){var n=e.length;e.push(t);a:for(;0<n;){var r=n-1>>>1,a=e[r];if(0<i(a,t))e[r]=t,e[n]=a,n=r;else break a}}function n(e){return e.length===0?null:e[0]}function r(e){if(e.length===0)return null;var t=e[0],n=e.pop();if(n!==t){e[0]=n;a:for(var r=0,a=e.length,o=a>>>1;r<o;){var s=2*(r+1)-1,c=e[s],l=s+1,u=e[l];if(0>i(c,n))l<a&&0>i(u,c)?(e[r]=u,e[l]=n,r=l):(e[r]=c,e[s]=n,r=s);else if(l<a&&0>i(u,n))e[r]=u,e[l]=n,r=l;else break a}}return t}function i(e,t){var n=e.sortIndex-t.sortIndex;return n===0?e.id-t.id:n}if(e.unstable_now=void 0,typeof performance==`object`&&typeof performance.now==`function`){var a=performance;e.unstable_now=function(){return a.now()}}else{var o=Date,s=o.now();e.unstable_now=function(){return o.now()-s}}var c=[],l=[],u=1,d=null,f=3,p=!1,m=!1,h=!1,g=!1,_=typeof setTimeout==`function`?setTimeout:null,v=typeof clearTimeout==`function`?clearTimeout:null,y=typeof setImmediate<`u`?setImmediate:null;function b(e){for(var i=n(l);i!==null;){if(i.callback===null)r(l);else if(i.startTime<=e)r(l),i.sortIndex=i.expirationTime,t(c,i);else break;i=n(l)}}function x(e){if(h=!1,b(e),!m){if(n(c)!==null)m=!0,S||(S=!0,re());else{var t=n(l);t!==null&&oe(x,t.startTime-e)}}}var S=!1,ee=-1,te=5,C=-1;function ne(){return g?!0:!(e.unstable_now()-C<te)}function w(){if(g=!1,S){var t=e.unstable_now();C=t;var i=!0;try{a:{m=!1,h&&(h=!1,v(ee),ee=-1),p=!0;var a=f;try{b:{for(b(t),d=n(c);d!==null&&!(d.expirationTime>t&&ne());){var o=d.callback;if(typeof o==`function`){d.callback=null,f=d.priorityLevel;var s=o(d.expirationTime<=t);if(t=e.unstable_now(),typeof s==`function`){d.callback=s,b(t),i=!0;break b}d===n(c)&&r(c),b(t)}else r(c);d=n(c)}if(d!==null)i=!0;else{var u=n(l);u!==null&&oe(x,u.startTime-t),i=!1}}break a}finally{d=null,f=a,p=!1}i=void 0}}finally{i?re():S=!1}}}var re;if(typeof y==`function`)re=function(){y(w)};else if(typeof MessageChannel<`u`){var ie=new MessageChannel,ae=ie.port2;ie.port1.onmessage=w,re=function(){ae.postMessage(null)}}else re=function(){_(w,0)};function oe(t,n){ee=_(function(){t(e.unstable_now())},n)}e.unstable_IdlePriority=5,e.unstable_ImmediatePriority=1,e.unstable_LowPriority=4,e.unstable_NormalPriority=3,e.unstable_Profiling=null,e.unstable_UserBlockingPriority=2,e.unstable_cancelCallback=function(e){e.callback=null},e.unstable_forceFrameRate=function(e){0>e||125<e?console.error(`forceFrameRate takes a positive int between 0 and 125, forcing frame rates higher than 125 fps is not supported`):te=0<e?Math.floor(1e3/e):5},e.unstable_getCurrentPriorityLevel=function(){return f},e.unstable_next=function(e){switch(f){case 1:case 2:case 3:var t=3;break;default:t=f}var n=f;f=t;try{return e()}finally{f=n}},e.unstable_requestPaint=function(){g=!0},e.unstable_runWithPriority=function(e,t){switch(e){case 1:case 2:case 3:case 4:case 5:break;default:e=3}var n=f;f=e;try{return t()}finally{f=n}},e.unstable_scheduleCallback=function(r,i,a){var o=e.unstable_now();switch(typeof a==`object`&&a?(a=a.delay,a=typeof a==`number`&&0<a?o+a:o):a=o,r){case 1:var s=-1;break;case 2:s=250;break;case 5:s=1073741823;break;case 4:s=1e4;break;default:s=5e3}return s=a+s,r={id:u++,callback:i,priorityLevel:r,startTime:a,expirationTime:s,sortIndex:-1},a>o?(r.sortIndex=a,t(l,r),n(c)===null&&r===n(l)&&(h?(v(ee),ee=-1):h=!0,oe(x,a-o))):(r.sortIndex=s,t(c,r),m||p||(m=!0,S||(S=!0,re()))),r},e.unstable_shouldYield=ne,e.unstable_wrapCallback=function(e){var t=f;return function(){var n=f;f=t;try{return e.apply(this,arguments)}finally{f=n}}}})),f=o(((e,t)=>{t.exports=d()})),p=o((e=>{var t=u();function n(e){var t=`https://react.dev/errors/`+e;if(1<arguments.length){t+=`?args[]=`+encodeURIComponent(arguments[1]);for(var n=2;n<arguments.length;n++)t+=`&args[]=`+encodeURIComponent(arguments[n])}return`Minified React error #`+e+`; visit `+t+` for the full message or use the non-minified dev environment for full errors and additional helpful warnings.`}function r(){}var i={d:{f:r,r:function(){throw Error(n(522))},D:r,C:r,L:r,m:r,X:r,S:r,M:r},p:0,findDOMNode:null},a=Symbol.for(`react.portal`),o=Symbol.for(`react.recoverable`),s=Symbol.for(`react.optimistic_key`);function c(e,t,n){var r=3<arguments.length&&arguments[3]!==void 0?arguments[3]:null;return{$$typeof:a,key:r==null?null:r===s?s:``+r,children:e,containerInfo:t,implementation:n}}var l=t.__CLIENT_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE;function d(e,t){if(e===`font`)return``;if(typeof t==`string`)return t===`use-credentials`?t:``}e.__DOM_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE=i,e.browser=function(e){return{$$typeof:o,_reason:e}},e.createPortal=function(e,t){var r=2<arguments.length&&arguments[2]!==void 0?arguments[2]:null;if(!t||t.nodeType!==1&&t.nodeType!==9&&t.nodeType!==11)throw Error(n(299));return c(e,t,null,r)},e.flushSync=function(e){var t=l.T,n=i.p;try{if(l.T=null,i.p=2,e)return e()}finally{l.T=t,i.p=n,i.d.f()}},e.preconnect=function(e,t){typeof e==`string`&&(t?(t=t.crossOrigin,t=typeof t==`string`?t===`use-credentials`?t:``:void 0):t=null,i.d.C(e,t))},e.prefetchDNS=function(e){typeof e==`string`&&i.d.D(e)},e.preinit=function(e,t){if(typeof e==`string`&&t&&typeof t.as==`string`){var n=t.as,r=d(n,t.crossOrigin),a=typeof t.integrity==`string`?t.integrity:void 0,o=typeof t.fetchPriority==`string`?t.fetchPriority:void 0;n===`style`?i.d.S(e,typeof t.precedence==`string`?t.precedence:void 0,{crossOrigin:r,integrity:a,fetchPriority:o}):n===`script`&&i.d.X(e,{crossOrigin:r,integrity:a,fetchPriority:o,nonce:typeof t.nonce==`string`?t.nonce:void 0})}},e.preinitModule=function(e,t){if(typeof e==`string`){if(typeof t==`object`&&t){if(t.as==null||t.as===`script`){var n=d(t.as,t.crossOrigin);i.d.M(e,{crossOrigin:n,integrity:typeof t.integrity==`string`?t.integrity:void 0,nonce:typeof t.nonce==`string`?t.nonce:void 0,fetchPriority:typeof t.fetchPriority==`string`?t.fetchPriority:void 0})}}else t??i.d.M(e)}},e.preload=function(e,t){if(typeof e==`string`&&typeof t==`object`&&t&&typeof t.as==`string`){var n=t.as,r=d(n,t.crossOrigin);i.d.L(e,n,{crossOrigin:r,integrity:typeof t.integrity==`string`?t.integrity:void 0,nonce:typeof t.nonce==`string`?t.nonce:void 0,type:typeof t.type==`string`?t.type:void 0,fetchPriority:typeof t.fetchPriority==`string`?t.fetchPriority:void 0,referrerPolicy:typeof t.referrerPolicy==`string`?t.referrerPolicy:void 0,imageSrcSet:typeof t.imageSrcSet==`string`?t.imageSrcSet:void 0,imageSizes:typeof t.imageSizes==`string`?t.imageSizes:void 0,media:typeof t.media==`string`?t.media:void 0})}},e.preloadModule=function(e,t){if(typeof e==`string`){if(t){var n=d(t.as,t.crossOrigin);i.d.m(e,{as:typeof t.as==`string`&&t.as!==`script`?t.as:void 0,crossOrigin:n,integrity:typeof t.integrity==`string`?t.integrity:void 0,nonce:typeof t.nonce==`string`?t.nonce:void 0,fetchPriority:typeof t.fetchPriority==`string`?t.fetchPriority:void 0})}else i.d.m(e)}},e.requestFormReset=function(e){i.d.r(e)},e.unstable_batchedUpdates=function(e,t){return e(t)},e.useFormState=function(e,t,n){return l.H.useFormState(e,t,n)},e.useFormStatus=function(){return l.H.useHostTransitionStatus()},e.version=`19.3.0`})),m=o(((e,t)=>{function n(){if(typeof __REACT_DEVTOOLS_GLOBAL_HOOK__<`u`&&typeof __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE==`function`)try{__REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE(n)}catch(e){console.error(e)}}n(),t.exports=p()})),h=o((e=>{var t=f(),n=u(),r=m();function i(e){var t=`https://react.dev/errors/`+e;if(1<arguments.length){t+=`?args[]=`+encodeURIComponent(arguments[1]);for(var n=2;n<arguments.length;n++)t+=`&args[]=`+encodeURIComponent(arguments[n])}return`Minified React error #`+e+`; visit `+t+` for the full message or use the non-minified dev environment for full errors and additional helpful warnings.`}function a(e){return!(!e||e.nodeType!==1&&e.nodeType!==9&&e.nodeType!==11)}function o(e){for(var t=e,n=t;n&&!n.alternate;)t=n,t.flags&4098&&(e=t.return),n=t.return;for(;t.return;)t=t.return;return t.tag===3?e:null}function s(e){if(e.tag===13){var t=e.memoizedState;if(t===null&&(e=e.alternate,e!==null&&(t=e.memoizedState)),t!==null)return t.dehydrated}return null}function c(e){if(e.tag===31){var t=e.memoizedState;if(t===null&&(e=e.alternate,e!==null&&(t=e.memoizedState)),t!==null)return t.dehydrated}return null}function l(e){if(o(e)!==e)throw Error(i(188))}function d(e){var t=e.alternate;if(!t){if(t=o(e),t===null)throw Error(i(188));return t===e?e:null}for(var n=e,r=t;;){var a=n.return;if(a===null)break;var s=a.alternate;if(s===null){if(r=a.return,r!==null){n=r;continue}break}if(a.child===s.child){for(s=a.child;s;){if(s===n)return l(a),e;if(s===r)return l(a),t;s=s.sibling}throw Error(i(188))}if(n.return!==r.return)n=a,r=s;else{for(var c=!1,u=a.child;u;){if(u===n){c=!0,n=a,r=s;break}if(u===r){c=!0,r=a,n=s;break}u=u.sibling}if(!c){for(u=s.child;u;){if(u===n){c=!0,n=s,r=a;break}if(u===r){c=!0,r=s,n=a;break}u=u.sibling}if(!c)throw Error(i(189))}}if(n.alternate!==r)throw Error(i(190))}if(n.tag!==3)throw Error(i(188));return n.stateNode.current===n?e:t}function p(e){var t=e.tag;if(t===5||t===26||t===27||t===6)return e;for(e=e.child;e!==null;){if(t=p(e),t!==null)return t;e=e.sibling}return null}function h(e,t,n,r,i,a){for(;e!==null;){if((e.tag===5||e.tag===27||e.tag===6)&&n(e,r,i,a)||(e.tag!==22||e.memoizedState===null)&&(t||e.tag!==5&&e.tag!==27)&&h(e.child,t,n,r,i,a))return!0;e=e.sibling}return!1}function g(e){for(e=e.return;e!==null;){if(e.tag===3||e.tag===5||e.tag===27)return e;e=e.return}return null}function _(e){var t=!1;for(e=e.return;e!==null&&(e.tag===4&&(t=!0),e.tag!==3&&e.tag!==5&&e.tag!==27);)e=e.return;return t}function v(e){var t=[null,null],n=g(e);return n===null||y(t,e,n.child,{foundSelf:!1}),t}function y(e,t,n,r){for(;n!==null;){if(n===t)r.foundSelf=!0;else if(n.tag===5||n.tag===27||n.tag===6){if(r.foundSelf)return e[1]=n,!0;e[0]=n}else if((n.tag!==22||n.memoizedState===null)&&y(e,t,n.child,r))return!0;n=n.sibling}return!1}function b(e){switch(e.tag){case 5:case 27:case 6:return e.stateNode;case 3:return e.stateNode.containerInfo;default:throw Error(i(559))}}var x=null,S=null;function ee(e,t,n){return e===n||e===t&&(x=e,!0)}function te(e,t,n){return e===n?(S=e,!1):e===t&&(S!==null&&(x=e),!0)}function C(e){if(e===null)return null;do e=e===null?null:e.return;while(e&&e.tag!==5&&e.tag!==27&&e.tag!==3);return e||null}function ne(e,t,n){for(var r=0,i=e;i;i=n(i))r++;i=0;for(var a=t;a;a=n(a))i++;for(;0<r-i;)e=n(e),r--;for(;0<i-r;)t=n(t),i--;for(;r--;){if(e===t||t!==null&&e===t.alternate)return e;e=n(e),t=n(t)}return null}var w=Object.assign,re=Symbol.for(`react.element`),ie=Symbol.for(`react.transitional.element`),ae=Symbol.for(`react.portal`),oe=Symbol.for(`react.fragment`),se=Symbol.for(`react.strict_mode`),ce=Symbol.for(`react.profiler`),le=Symbol.for(`react.consumer`),ue=Symbol.for(`react.context`),de=Symbol.for(`react.forward_ref`),fe=Symbol.for(`react.suspense`),pe=Symbol.for(`react.suspense_list`),me=Symbol.for(`react.memo`),he=Symbol.for(`react.lazy`),ge=Symbol.for(`react.activity`),_e=Symbol.for(`react.legacy_hidden`),ve=Symbol.for(`react.memo_cache_sentinel`),ye=Symbol.for(`react.view_transition`),be=Symbol.for(`react.recoverable`),xe=Symbol.iterator;function Se(e){return typeof e!=`object`||!e?null:(e=xe&&e[xe]||e[`@@iterator`],typeof e==`function`?e:null)}var Ce=Symbol.for(`react.client.reference`);function we(e){if(e==null)return null;if(typeof e==`function`)return e.$$typeof===Ce?null:e.displayName||e.name||null;if(typeof e==`string`)return e;switch(e){case oe:return`Fragment`;case ce:return`Profiler`;case se:return`StrictMode`;case fe:return`Suspense`;case pe:return`SuspenseList`;case ge:return`Activity`;case ye:return`ViewTransition`}if(typeof e==`object`)switch(e.$$typeof){case ae:return`Portal`;case ue:return e.displayName||`Context`;case le:return(e._context.displayName||`Context`)+`.Consumer`;case de:var t=e.render;return e=e.displayName,e||=(e=t.displayName||t.name||``,e===``?`ForwardRef`:`ForwardRef(`+e+`)`),e;case me:return t=e.displayName||null,t===null?we(e.type)||`Memo`:t;case he:t=e._payload,e=e._init;try{return we(e(t))}catch{}}return null}var Te=Array.isArray,T=n.__CLIENT_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE,E=r.__DOM_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE,Ee={pending:!1,data:null,method:null,action:null},De=[],Oe=-1;function ke(e){return{current:e}}function Ae(e){0>Oe||(e.current=De[Oe],De[Oe]=null,Oe--)}function D(e,t){Oe++,De[Oe]=e.current,e.current=t}var je=ke(null),Me=ke(null),Ne=ke(null),Pe=ke(null);function Fe(e,t){switch(D(Ne,t),D(Me,e),D(je,null),t.nodeType){case 9:case 11:e=(e=t.documentElement)&&(e=e.namespaceURI)?up(e):0;break;default:if(e=t.tagName,t=t.namespaceURI)t=up(t),e=dp(t,e);else switch(e){case`svg`:e=1;break;case`math`:e=2;break;default:e=0}}Ae(je),D(je,e)}function Ie(){Ae(je),Ae(Me),Ae(Ne)}function Le(e){var t=e.memoizedState;t!==null&&(sh._currentValue=t.memoizedState,D(Pe,e)),t=je.current;var n=dp(t,e.type);t!==n&&(D(Me,e),D(je,n))}function Re(e){Me.current===e&&(Ae(je),Ae(Me)),Pe.current===e&&(Ae(Pe),sh._currentValue=Ee)}var ze,Be;function Ve(e){if(ze===void 0)try{throw Error()}catch(e){var t=e.stack.trim().match(/\n( *(at )?)/);ze=t&&t[1]||``,Be=-1<e.stack.indexOf(`
    at`)?` (<anonymous>)`:-1<e.stack.indexOf(`@`)?`@unknown:0:0`:``}return`
`+ze+e+Be}var He=!1;function Ue(e,t){if(!e||He)return``;He=!0;var n=Error.prepareStackTrace;Error.prepareStackTrace=void 0;try{var r={DetermineComponentFrameRoot:function(){try{if(t){var n=function(){throw Error()};if(Object.defineProperty(n.prototype,"props",{set:function(){throw Error()}}),typeof Reflect==`object`&&Reflect.construct){try{Reflect.construct(n,[])}catch(e){var r=e}Reflect.construct(e,[],n)}else{try{n.call()}catch(e){r=e}n=!1;try{var i=Object.getOwnPropertyDescriptor(e.prototype,`props`);Object.defineProperty(e.prototype,"props",{configurable:!0,set:function(){throw Error()}}),n=!0,new e}finally{n&&(i===void 0?delete e.prototype.props:Object.defineProperty(e.prototype,"props",i))}}}else{try{throw Error()}catch(e){r=e}(n=e())&&typeof n.catch==`function`&&n.catch(function(){})}}catch(e){if(e&&r&&typeof e.stack==`string`)return[e.stack,r.stack]}return[null,null]}};r.DetermineComponentFrameRoot.displayName=`DetermineComponentFrameRoot`;var i=Object.getOwnPropertyDescriptor(r.DetermineComponentFrameRoot,`name`);i&&i.configurable&&Object.defineProperty(r.DetermineComponentFrameRoot,"name",{value:`DetermineComponentFrameRoot`});var a=r.DetermineComponentFrameRoot(),o=a[0],s=a[1];if(o&&s){var c=o.split(`
`),l=s.split(`
`);for(i=r=0;r<c.length&&!c[r].includes(`DetermineComponentFrameRoot`);)r++;for(;i<l.length&&!l[i].includes(`DetermineComponentFrameRoot`);)i++;if(r===c.length||i===l.length)for(r=c.length-1,i=l.length-1;1<=r&&0<=i&&c[r]!==l[i];)i--;for(;1<=r&&0<=i;r--,i--)if(c[r]!==l[i]){if(r!==1||i!==1)do if(r--,i--,0>i||c[r]!==l[i]){var u=`
`+c[r].replace(` at new `,` at `);return e.displayName&&u.includes(`<anonymous>`)&&(u=u.replace(`<anonymous>`,e.displayName)),u}while(1<=r&&0<=i);break}}}finally{He=!1,Error.prepareStackTrace=n}return(n=e?e.displayName||e.name:``)?Ve(n):``}function We(e,t){switch(e.tag){case 26:case 27:case 5:return Ve(e.type);case 16:return Ve(`Lazy`);case 13:return e.child!==t&&t!==null?Ve(`Suspense Fallback`):Ve(`Suspense`);case 19:return Ve(`SuspenseList`);case 0:case 15:return Ue(e.type,!1);case 11:return Ue(e.type.render,!1);case 1:return Ue(e.type,!0);case 31:return Ve(`Activity`);case 30:return Ve(`ViewTransition`);default:return``}}function Ge(e){try{var t=``,n=null;do t+=We(e,n),n=e,e=e.return;while(e);return t}catch(e){return`
Error generating stack: `+e.message+`
`+e.stack}}var Ke=Object.prototype.hasOwnProperty,qe=t.unstable_scheduleCallback,Je=t.unstable_cancelCallback,Ye=t.unstable_shouldYield,Xe=t.unstable_requestPaint,Ze=t.unstable_now,Qe=t.unstable_getCurrentPriorityLevel,$e=t.unstable_ImmediatePriority,et=t.unstable_UserBlockingPriority,tt=t.unstable_NormalPriority,nt=t.unstable_LowPriority,rt=t.unstable_IdlePriority,it=t.log,at=t.unstable_setDisableYieldValue,ot=null,st=null;function ct(e){if(typeof it==`function`&&at(e),st&&typeof st.setStrictMode==`function`)try{st.setStrictMode(ot,e)}catch{}}var lt=Math.clz32?Math.clz32:ft,ut=Math.log,dt=Math.LN2;function ft(e){return e>>>=0,e===0?32:31-(ut(e)/dt|0)|0}var pt=256,mt=262144,ht=4194304;function gt(e){var t=e&42;if(t!==0)return t;switch(e&-e){case 1:return 1;case 2:return 2;case 4:return 4;case 8:return 8;case 16:return 16;case 32:return 32;case 64:return 64;case 128:return 128;case 256:case 512:case 1024:case 2048:case 4096:case 8192:case 16384:case 32768:case 65536:case 131072:return e&-e;case 262144:case 524288:case 1048576:case 2097152:return e&3932160;case 4194304:case 8388608:case 16777216:case 33554432:return e&62914560;case 67108864:return 67108864;case 134217728:return 134217728;case 268435456:return 268435456;case 536870912:return 536870912;case 1073741824:return 0;default:return e}}function _t(e,t,n){var r=e.pendingLanes;if(r===0)return 0;var i=0,a=e.suspendedLanes,o=e.pingedLanes;e=e.warmLanes;var s=r&134217727;return s===0?(s=r&~a,s===0?o===0?n||(n=r&~e,n!==0&&(i=gt(n))):i=gt(o):i=gt(s)):(r=s&~a,r===0?(o&=s,o===0?n||(n=s&~e,n!==0&&(i=gt(n))):i=gt(o)):i=gt(r)),i===0?0:t!==0&&t!==i&&(t&a)===0&&(a=i&-i,n=t&-t,a>=n||a===32&&n&4194048)?t:i}function vt(e,t){return(e.pendingLanes&~(e.suspendedLanes&~e.pingedLanes)&t)===0}function yt(e,t){t&8&&(t|=t&32);var n=e.entangledLanes;if(n!==0)for(e=e.entanglements,n&=t;0<n;){var r=31-lt(n),i=1<<r;t|=e[r],n&=~i}return t}function bt(e,t){switch(e){case 1:case 2:case 4:case 8:case 64:return t+250;case 16:case 32:case 128:case 256:case 512:case 1024:case 2048:case 4096:case 8192:case 16384:case 32768:case 65536:case 131072:case 262144:case 524288:case 1048576:case 2097152:return t+5e3;case 4194304:case 8388608:case 16777216:case 33554432:return-1;case 67108864:case 134217728:case 268435456:case 536870912:case 1073741824:return-1;default:return-1}}function xt(){var e=ht;return ht<<=1,!(ht&62914560)&&(ht=4194304),e}function St(e){for(var t=[],n=0;31>n;n++)t.push(e);return t}function Ct(e,t){e.pendingLanes|=t,t!==268435456&&(e.suspendedLanes=0,e.pingedLanes=0,e.warmLanes=0)}function wt(e,t,n,r,i,a){var o=e.pendingLanes;e.pendingLanes=n,e.suspendedLanes=0,e.pingedLanes=0,e.warmLanes=0,e.expiredLanes&=n,e.entangledLanes&=n,e.errorRecoveryDisabledLanes&=n,e.shellSuspendCounter=0;var s=e.entanglements,c=e.expirationTimes,l=e.hiddenUpdates;for(n=o&~n;0<n;){var u=31-lt(n),d=1<<u;s[u]=0,c[u]=-1;var f=l[u];if(f!==null)for(l[u]=null,u=0;u<f.length;u++){var p=f[u];p!==null&&(p.lane&=-536870913)}n&=~d}r!==0&&Tt(e,r,0),a!==0&&i===0&&e.tag!==0&&(e.suspendedLanes|=a&~(o&~t))}function Tt(e,t,n){e.pendingLanes|=t,e.suspendedLanes&=~t;var r=31-lt(t);e.entangledLanes|=t,e.entanglements[r]=e.entanglements[r]|1073741824|n&261930}function Et(e,t){var n=e.entangledLanes|=t;for(e=e.entanglements;n;){var r=31-lt(n),i=1<<r;i&t|e[r]&t&&(e[r]|=t),n&=~i}}function Dt(e,t){var n=t&-t;return n=n&42?1:Ot(n),(n&(e.suspendedLanes|t))===0?n:0}function Ot(e){switch(e){case 2:e=1;break;case 8:e=4;break;case 32:e=16;break;case 256:case 512:case 1024:case 2048:case 4096:case 8192:case 16384:case 32768:case 65536:case 131072:case 262144:case 524288:case 1048576:case 2097152:case 4194304:case 8388608:case 16777216:case 33554432:e=128;break;case 268435456:e=134217728;break;default:e=0}return e}function kt(e){return e&=-e,2<e?8<e?e&134217727?32:268435456:8:2}function At(){var e=E.p;return e===0?(e=window.event,e===void 0?32:Ch(e.type)):e}function jt(e,t){var n=E.p;try{return E.p=e,t()}finally{E.p=n}}var Mt=Math.random().toString(36).slice(2),Nt=`__reactFiber$`+Mt,Pt=`__reactProps$`+Mt,Ft=`__reactContainer$`+Mt,It=`__reactEvents$`+Mt,Lt=`__reactListeners$`+Mt,Rt=`__reactHandles$`+Mt,zt=`__reactResources$`+Mt,Bt=`__reactMarker$`+Mt,Vt=`__reactLoad$`+Mt;function Ht(e){delete e[Nt],delete e[Pt],delete e[Lt],delete e[Rt]}function Ut(e){var t;if(t=e[Nt])return t;for(var n=e.parentNode;n;){if(t=n[Ft]||n[Nt]){if(n=t.alternate,t.child!==null||n!==null&&n.child!==null)for(e=fm(e);e!==null;){if(n=e[Nt])return n;e=fm(e)}return t}e=n,n=e.parentNode}return null}function Wt(e){if(e=e[Nt]||e[Ft]){var t=e.tag;if(t===5||t===6||t===13||t===31||t===26||t===27||t===3)return e}return null}function Gt(e){var t=e.tag;if(t===5||t===26||t===27||t===6)return e.stateNode;throw Error(i(33))}function Kt(e){var t=e[zt];return t||=e[zt]={hoistableStyles:new Map,hoistableScripts:new Map},t}function O(e){e[Bt]=!0}function qt(e){e[Vt]=void 0}var Jt=new Set,Yt={};function Xt(e,t){Zt(e,t),Zt(e+`Capture`,t)}function Zt(e,t){for(Yt[e]=t,e=0;e<t.length;e++)Jt.add(t[e])}var Qt=RegExp(`^[:A-Z_a-z\\u00C0-\\u00D6\\u00D8-\\u00F6\\u00F8-\\u02FF\\u0370-\\u037D\\u037F-\\u1FFF\\u200C-\\u200D\\u2070-\\u218F\\u2C00-\\u2FEF\\u3001-\\uD7FF\\uF900-\\uFDCF\\uFDF0-\\uFFFD][:A-Z_a-z\\u00C0-\\u00D6\\u00D8-\\u00F6\\u00F8-\\u02FF\\u0370-\\u037D\\u037F-\\u1FFF\\u200C-\\u200D\\u2070-\\u218F\\u2C00-\\u2FEF\\u3001-\\uD7FF\\uF900-\\uFDCF\\uFDF0-\\uFFFD\\-.0-9\\u00B7\\u0300-\\u036F\\u203F-\\u2040]*$`),$t={},en={};function tn(e){return Ke.call(en,e)?!0:Ke.call($t,e)?!1:Qt.test(e)?en[e]=!0:($t[e]=!0,!1)}var k=!1;function nn(){var e=k;return k=!1,e}function rn(e,t,n){if(tn(t)){if(n===null)e.removeAttribute(t);else{switch(typeof n){case`undefined`:case`function`:case`symbol`:e.removeAttribute(t);return;case`boolean`:var r=t.toLowerCase().slice(0,5);if(r!==`data-`&&r!==`aria-`){e.removeAttribute(t);return}}e.setAttribute(t,n)}}}function an(e,t,n){if(n===null)e.removeAttribute(t);else{switch(typeof n){case`undefined`:case`function`:case`symbol`:case`boolean`:e.removeAttribute(t);return}e.setAttribute(t,n)}}function on(e,t,n,r){if(r===null)e.removeAttribute(n);else{switch(typeof r){case`undefined`:case`function`:case`symbol`:case`boolean`:e.removeAttribute(n);return}e.setAttributeNS(t,n,r)}}function sn(e){switch(typeof e){case`bigint`:case`boolean`:case`number`:case`string`:case`undefined`:return e;case`object`:return e;default:return``}}function cn(e){var t=e.type;return(e=e.nodeName)&&e.toLowerCase()===`input`&&(t===`checkbox`||t===`radio`)}function ln(e,t,n){var r=Object.getOwnPropertyDescriptor(e.constructor.prototype,t);if(!e.hasOwnProperty(t)&&r!==void 0&&typeof r.get==`function`&&typeof r.set==`function`){var i=r.get,a=r.set;return Object.defineProperty(e,t,{configurable:!0,get:function(){return i.call(this)},set:function(e){n=``+e,a.call(this,e)}}),Object.defineProperty(e,t,{enumerable:r.enumerable}),{getValue:function(){return n},setValue:function(e){n=``+e},stopTracking:function(){e._valueTracker=null,delete e[t]}}}}function un(e){if(!e._valueTracker){var t=cn(e)?`checked`:`value`;e._valueTracker=ln(e,t,``+e[t])}}function dn(e){if(!e)return!1;var t=e._valueTracker;if(!t)return!0;var n=t.getValue(),r=``;return e&&(r=cn(e)?e.checked?`true`:`false`:e.value),e=r,e!==n&&(t.setValue(e),!0)}var fn=/[\n"\\]/g;function pn(e){return e.replace(fn,function(e){return`\\`+e.charCodeAt(0).toString(16)+` `})}function mn(e,t,n,r,i,a,o,s){e.name=``,o!=null&&typeof o!=`function`&&typeof o!=`symbol`&&typeof o!=`boolean`?e.type=o:e.removeAttribute(`type`),t==null?o!==`submit`&&o!==`reset`||e.removeAttribute(`value`):o===`number`?(t===0&&e.value===``||e.value!=t)&&(e.value=``+sn(t)):e.value!==``+sn(t)&&(e.value=``+sn(t)),t==null?n==null?r!=null&&e.removeAttribute(`value`):gn(e,sn(n)):o===`number`&&e.value==t?gn(e,sn(e.value)):gn(e,sn(t)),i==null&&a!=null&&(e.defaultChecked=!!a),i!=null&&(e.checked=i&&typeof i!=`function`&&typeof i!=`symbol`),s!=null&&typeof s!=`function`&&typeof s!=`symbol`&&typeof s!=`boolean`?e.name=``+sn(s):e.removeAttribute(`name`)}function hn(e,t,n,r,i,a,o,s){if(a!=null&&typeof a!=`function`&&typeof a!=`symbol`&&typeof a!=`boolean`&&(e.type=a),t!=null||n!=null){if(!(a!==`submit`&&a!==`reset`||t!=null)){un(e);return}n=n==null?``:``+sn(n),t=t==null?n:``+sn(t),s||t===e.value||(e.value=t),e.defaultValue=t}r??=i,r=typeof r!=`function`&&typeof r!=`symbol`&&!!r,e.checked=s?e.checked:!!r,e.defaultChecked=!!r,o!=null&&typeof o!=`function`&&typeof o!=`symbol`&&typeof o!=`boolean`&&(e.name=o),un(e)}function gn(e,t){e.defaultValue!==``+t&&(e.defaultValue=``+t)}function _n(e,t,n,r){if(e=e.options,t){t={};for(var i=0;i<n.length;i++)t[`$`+n[i]]=!0;for(n=0;n<e.length;n++)i=t.hasOwnProperty(`$`+e[n].value),e[n].selected!==i&&(e[n].selected=i),i&&r&&(e[n].defaultSelected=!0)}else{for(n=``+sn(n),t=null,i=0;i<e.length;i++){if(e[i].value===n){e[i].selected=!0,r&&(e[i].defaultSelected=!0);return}t!==null||e[i].disabled||(t=e[i])}t!==null&&(t.selected=!0)}}function vn(e,t,n){if(t!=null&&(t=``+sn(t),t!==e.value&&(e.value=t),n==null)){e.defaultValue!==t&&(e.defaultValue=t);return}e.defaultValue=n==null?``:``+sn(n)}function yn(e,t,n,r){if(t==null){if(r!=null){if(n!=null)throw Error(i(92));if(Te(r)){if(1<r.length)throw Error(i(93));r=r[0]}n=r}n??=``,t=n}n=sn(t),e.defaultValue=n,r=e.textContent,r===n&&r!==``&&r!==null&&(e.value=r),un(e)}function bn(e,t){if(t){var n=e.firstChild;if(n&&n===e.lastChild&&n.nodeType===3){n.nodeValue=t;return}}e.textContent=t}var xn=new Set(`animationIterationCount aspectRatio borderImageOutset borderImageSlice borderImageWidth boxFlex boxFlexGroup boxOrdinalGroup columnCount columns flex flexGrow flexPositive flexShrink flexNegative flexOrder gridArea gridRow gridRowEnd gridRowSpan gridRowStart gridColumn gridColumnEnd gridColumnSpan gridColumnStart fontWeight lineClamp lineHeight opacity order orphans scale tabSize widows zIndex zoom fillOpacity floodOpacity stopOpacity strokeDasharray strokeDashoffset strokeMiterlimit strokeOpacity strokeWidth MozAnimationIterationCount MozBoxFlex MozBoxFlexGroup MozLineClamp msAnimationIterationCount msFlex msZoom msFlexGrow msFlexNegative msFlexOrder msFlexPositive msFlexShrink msGridColumn msGridColumnSpan msGridRow msGridRowSpan WebkitAnimationIterationCount WebkitBoxFlex WebKitBoxFlexGroup WebkitBoxOrdinalGroup WebkitColumnCount WebkitColumns WebkitFlex WebkitFlexGrow WebkitFlexPositive WebkitFlexShrink WebkitLineClamp`.split(` `));function Sn(e,t,n){var r=t.indexOf(`--`)===0;n==null||typeof n==`boolean`||n===``?r?e.setProperty(t,``):t===`float`?e.cssFloat=``:e[t]=``:r?e.setProperty(t,n):typeof n!=`number`||n===0||xn.has(t)?t===`float`?e.cssFloat=n:e[t]=(``+n).trim():e[t]=n+`px`}function Cn(e,t,n){if(t!=null&&typeof t!=`object`)throw Error(i(62));if(e=e.style,n!=null){for(var r in n)!n.hasOwnProperty(r)||t!=null&&t.hasOwnProperty(r)||(r.indexOf(`--`)===0?e.setProperty(r,``):r===`float`?e.cssFloat=``:e[r]=``,k=!0);for(var a in t)r=t[a],t.hasOwnProperty(a)&&n[a]!==r&&(Sn(e,a,r),k=!0)}else for(var o in t)t.hasOwnProperty(o)&&Sn(e,o,t[o])}function wn(e){if(e.indexOf(`-`)===-1)return!1;switch(e){case`annotation-xml`:case`color-profile`:case`font-face`:case`font-face-src`:case`font-face-uri`:case`font-face-format`:case`font-face-name`:case`missing-glyph`:return!1;default:return!0}}var Tn=new Map([[`acceptCharset`,`accept-charset`],[`htmlFor`,`for`],[`httpEquiv`,`http-equiv`],[`crossOrigin`,`crossorigin`],[`accentHeight`,`accent-height`],[`alignmentBaseline`,`alignment-baseline`],[`arabicForm`,`arabic-form`],[`baselineShift`,`baseline-shift`],[`capHeight`,`cap-height`],[`clipPath`,`clip-path`],[`clipRule`,`clip-rule`],[`colorInterpolation`,`color-interpolation`],[`colorInterpolationFilters`,`color-interpolation-filters`],[`colorProfile`,`color-profile`],[`colorRendering`,`color-rendering`],[`dominantBaseline`,`dominant-baseline`],[`enableBackground`,`enable-background`],[`fillOpacity`,`fill-opacity`],[`fillRule`,`fill-rule`],[`floodColor`,`flood-color`],[`floodOpacity`,`flood-opacity`],[`fontFamily`,`font-family`],[`fontSize`,`font-size`],[`fontSizeAdjust`,`font-size-adjust`],[`fontStretch`,`font-stretch`],[`fontStyle`,`font-style`],[`fontVariant`,`font-variant`],[`fontWeight`,`font-weight`],[`glyphName`,`glyph-name`],[`glyphOrientationHorizontal`,`glyph-orientation-horizontal`],[`glyphOrientationVertical`,`glyph-orientation-vertical`],[`horizAdvX`,`horiz-adv-x`],[`horizOriginX`,`horiz-origin-x`],[`imageRendering`,`image-rendering`],[`letterSpacing`,`letter-spacing`],[`lightingColor`,`lighting-color`],[`markerEnd`,`marker-end`],[`markerMid`,`marker-mid`],[`markerStart`,`marker-start`],[`maskType`,`mask-type`],[`overlinePosition`,`overline-position`],[`overlineThickness`,`overline-thickness`],[`paintOrder`,`paint-order`],[`panose-1`,`panose-1`],[`pointerEvents`,`pointer-events`],[`renderingIntent`,`rendering-intent`],[`shapeRendering`,`shape-rendering`],[`stopColor`,`stop-color`],[`stopOpacity`,`stop-opacity`],[`strikethroughPosition`,`strikethrough-position`],[`strikethroughThickness`,`strikethrough-thickness`],[`strokeDasharray`,`stroke-dasharray`],[`strokeDashoffset`,`stroke-dashoffset`],[`strokeLinecap`,`stroke-linecap`],[`strokeLinejoin`,`stroke-linejoin`],[`strokeMiterlimit`,`stroke-miterlimit`],[`strokeOpacity`,`stroke-opacity`],[`strokeWidth`,`stroke-width`],[`textAnchor`,`text-anchor`],[`textDecoration`,`text-decoration`],[`textRendering`,`text-rendering`],[`transformOrigin`,`transform-origin`],[`underlinePosition`,`underline-position`],[`underlineThickness`,`underline-thickness`],[`unicodeBidi`,`unicode-bidi`],[`unicodeRange`,`unicode-range`],[`unitsPerEm`,`units-per-em`],[`vAlphabetic`,`v-alphabetic`],[`vHanging`,`v-hanging`],[`vIdeographic`,`v-ideographic`],[`vMathematical`,`v-mathematical`],[`vectorEffect`,`vector-effect`],[`vertAdvY`,`vert-adv-y`],[`vertOriginX`,`vert-origin-x`],[`vertOriginY`,`vert-origin-y`],[`wordSpacing`,`word-spacing`],[`writingMode`,`writing-mode`],[`xmlnsXlink`,`xmlns:xlink`],[`xHeight`,`x-height`]]),En=/^[\u0000-\u001F ]*j[\r\n\t]*a[\r\n\t]*v[\r\n\t]*a[\r\n\t]*s[\r\n\t]*c[\r\n\t]*r[\r\n\t]*i[\r\n\t]*p[\r\n\t]*t[\r\n\t]*:/i;function Dn(e){return En.test(``+e)?`javascript:throw new Error('React has blocked a javascript: URL as a security precaution.')`:e}function On(){}var kn=null;function An(e){return e=e.target||e.srcElement||window,e.correspondingUseElement&&(e=e.correspondingUseElement),e.nodeType===3?e.parentNode:e}var jn=null,Mn=null;function Nn(e){var t=Wt(e);if(t&&(e=t.stateNode)){var n=e[Pt]||null;a:switch(e=t.stateNode,t.type){case`input`:if(mn(e,n.value,n.defaultValue,n.defaultValue,n.checked,n.defaultChecked,n.type,n.name),t=n.name,n.type===`radio`&&t!=null){for(n=e;n.parentNode;)n=n.parentNode;for(n=n.querySelectorAll(`input[name="`+pn(``+t)+`"][type="radio"]`),t=0;t<n.length;t++){var r=n[t];if(r!==e&&r.form===e.form){var a=r[Pt]||null;if(!a)throw Error(i(90));mn(r,a.value,a.defaultValue,a.defaultValue,a.checked,a.defaultChecked,a.type,a.name)}}for(t=0;t<n.length;t++)r=n[t],r.form===e.form&&dn(r)}break a;case`textarea`:vn(e,n.value,n.defaultValue);break a;case`select`:t=n.value,t!=null&&_n(e,!!n.multiple,t,!1)}}}var Pn=!1;function Fn(e,t,n){if(Pn)return e(t,n);Pn=!0;try{return e(t)}finally{if(Pn=!1,(jn!==null||Mn!==null)&&(zd(),jn&&(t=jn,e=Mn,Mn=jn=null,Nn(t),e)))for(t=0;t<e.length;t++)Nn(e[t])}}function In(e,t){var n=e.stateNode;if(n===null)return null;var r=n[Pt]||null;if(r===null)return null;n=r[t];a:switch(t){case`onClick`:case`onClickCapture`:case`onDoubleClick`:case`onDoubleClickCapture`:case`onMouseDown`:case`onMouseDownCapture`:case`onMouseMove`:case`onMouseMoveCapture`:case`onMouseUp`:case`onMouseUpCapture`:case`onMouseEnter`:(r=!r.disabled)||(e=e.type,r=e!==`button`&&e!==`input`&&e!==`select`&&e!==`textarea`),e=!r;break a;default:e=!1}if(e)return null;if(n&&typeof n!=`function`)throw Error(i(231,t,typeof n));return n}var Ln=typeof window<`u`&&window.document!==void 0&&window.document.createElement!==void 0,Rn=!1;if(Ln)try{var zn={};Object.defineProperty(zn,"passive",{get:function(){Rn=!0}}),window.addEventListener(`test`,zn,zn),window.removeEventListener(`test`,zn,zn)}catch{Rn=!1}var Bn=null,Vn=null,Hn=null;function Un(){if(Hn)return Hn;var e,t=Vn,n=t.length,r,i=`value`in Bn?Bn.value:Bn.textContent,a=i.length;for(e=0;e<n&&t[e]===i[e];e++);var o=n-e;for(r=1;r<=o&&t[n-r]===i[a-r];r++);return Hn=i.slice(e,1<r?1-r:void 0)}function Wn(e){var t=e.keyCode;return`charCode`in e?(e=e.charCode,e===0&&t===13&&(e=13)):e=t,e===10&&(e=13),32<=e||e===13?e:0}function Gn(){return!0}function Kn(){return!1}function qn(e){function t(t,n,r,i,a){for(var o in this._reactName=t,this._targetInst=r,this.type=n,this.nativeEvent=i,this.target=a,this.currentTarget=null,e)e.hasOwnProperty(o)&&(t=e[o],this[o]=t?t(i):i[o]);return this.isDefaultPrevented=(i.defaultPrevented==null?!1===i.returnValue:i.defaultPrevented)?Gn:Kn,this.isPropagationStopped=Kn,this}return w(t.prototype,{preventDefault:function(){this.defaultPrevented=!0;var e=this.nativeEvent;e&&(e.preventDefault?e.preventDefault():typeof e.returnValue!=`unknown`&&(e.returnValue=!1),this.isDefaultPrevented=Gn)},stopPropagation:function(){var e=this.nativeEvent;e&&(e.stopPropagation?e.stopPropagation():typeof e.cancelBubble!=`unknown`&&(e.cancelBubble=!0),this.isPropagationStopped=Gn)},persist:function(){},isPersistent:Gn}),t}var Jn={eventPhase:0,bubbles:0,cancelable:0,timeStamp:function(e){return e.timeStamp||Date.now()},defaultPrevented:0,isTrusted:0},Yn=qn(Jn),Xn=w({},Jn,{view:0,detail:0}),Zn=qn(Xn),Qn,$n,er,tr=w({},Xn,{screenX:0,screenY:0,clientX:0,clientY:0,pageX:0,pageY:0,ctrlKey:0,shiftKey:0,altKey:0,metaKey:0,getModifierState:fr,button:0,buttons:0,relatedTarget:function(e){return e.relatedTarget===void 0?e.fromElement===e.srcElement?e.toElement:e.fromElement:e.relatedTarget},movementX:function(e){return`movementX`in e?e.movementX:(e!==er&&(er&&e.type===`mousemove`?(Qn=e.screenX-er.screenX,$n=e.screenY-er.screenY):$n=Qn=0,er=e),Qn)},movementY:function(e){return`movementY`in e?e.movementY:$n}}),nr=qn(tr),rr=qn(w({},tr,{dataTransfer:0})),ir=qn(w({},Xn,{relatedTarget:0})),ar=qn(w({},Jn,{animationName:0,elapsedTime:0,pseudoElement:0})),or=qn(w({},Jn,{clipboardData:function(e){return`clipboardData`in e?e.clipboardData:window.clipboardData}})),sr=qn(w({},Jn,{data:0})),cr={Esc:`Escape`,Spacebar:` `,Left:`ArrowLeft`,Up:`ArrowUp`,Right:`ArrowRight`,Down:`ArrowDown`,Del:`Delete`,Win:`OS`,Menu:`ContextMenu`,Apps:`ContextMenu`,Scroll:`ScrollLock`,MozPrintableKey:`Unidentified`},lr={8:`Backspace`,9:`Tab`,12:`Clear`,13:`Enter`,16:`Shift`,17:`Control`,18:`Alt`,19:`Pause`,20:`CapsLock`,27:`Escape`,32:` `,33:`PageUp`,34:`PageDown`,35:`End`,36:`Home`,37:`ArrowLeft`,38:`ArrowUp`,39:`ArrowRight`,40:`ArrowDown`,45:`Insert`,46:`Delete`,112:`F1`,113:`F2`,114:`F3`,115:`F4`,116:`F5`,117:`F6`,118:`F7`,119:`F8`,120:`F9`,121:`F10`,122:`F11`,123:`F12`,144:`NumLock`,145:`ScrollLock`,224:`Meta`},ur={Alt:`altKey`,Control:`ctrlKey`,Meta:`metaKey`,Shift:`shiftKey`};function dr(e){var t=this.nativeEvent;return t.getModifierState?t.getModifierState(e):(e=ur[e])?!!t[e]:!1}function fr(){return dr}var pr=qn(w({},Xn,{key:function(e){if(e.key){var t=cr[e.key]||e.key;if(t!==`Unidentified`)return t}return e.type===`keypress`?(e=Wn(e),e===13?`Enter`:String.fromCharCode(e)):e.type===`keydown`||e.type===`keyup`?lr[e.keyCode]||`Unidentified`:``},code:0,location:0,ctrlKey:0,shiftKey:0,altKey:0,metaKey:0,repeat:0,locale:0,getModifierState:fr,charCode:function(e){return e.type===`keypress`?Wn(e):0},keyCode:function(e){return e.type===`keydown`||e.type===`keyup`?e.keyCode:0},which:function(e){return e.type===`keypress`?Wn(e):e.type===`keydown`||e.type===`keyup`?e.keyCode:0}})),mr=qn(w({},tr,{pointerId:0,width:0,height:0,pressure:0,tangentialPressure:0,tiltX:0,tiltY:0,twist:0,pointerType:0,isPrimary:0})),hr=qn(w({},Jn,{submitter:0})),gr=qn(w({},Xn,{touches:0,targetTouches:0,changedTouches:0,altKey:0,metaKey:0,ctrlKey:0,shiftKey:0,getModifierState:fr})),_r=qn(w({},Jn,{propertyName:0,elapsedTime:0,pseudoElement:0})),vr=qn(w({},tr,{deltaX:function(e){return`deltaX`in e?e.deltaX:`wheelDeltaX`in e?-e.wheelDeltaX:0},deltaY:function(e){return`deltaY`in e?e.deltaY:`wheelDeltaY`in e?-e.wheelDeltaY:`wheelDelta`in e?-e.wheelDelta:0},deltaZ:0,deltaMode:0})),yr=qn(w({},Jn,{newState:0,oldState:0,source:0})),br=[9,13,27,32],xr=Ln&&`CompositionEvent`in window,Sr=null;Ln&&`documentMode`in document&&(Sr=document.documentMode);var Cr=Ln&&`TextEvent`in window&&!Sr,wr=Ln&&(!xr||Sr&&8<Sr&&11>=Sr),Tr=` `,Er=!1;function Dr(e,t){switch(e){case`keyup`:return br.indexOf(t.keyCode)!==-1;case`keydown`:return t.keyCode!==229;case`keypress`:case`mousedown`:case`focusout`:return!0;default:return!1}}function Or(e){return e=e.detail,typeof e==`object`&&`data`in e?e.data:null}var kr=!1;function Ar(e,t){switch(e){case`compositionend`:return Or(t);case`keypress`:return t.which===32?(Er=!0,Tr):null;case`textInput`:return e=t.data,e===Tr&&Er?null:e;default:return null}}function jr(e,t){if(kr)return e===`compositionend`||!xr&&Dr(e,t)?(e=Un(),Hn=Vn=Bn=null,kr=!1,e):null;switch(e){case`paste`:return null;case`keypress`:if(!(t.ctrlKey||t.altKey||t.metaKey)||t.ctrlKey&&t.altKey){if(t.char&&1<t.char.length)return t.char;if(t.which)return String.fromCharCode(t.which)}return null;case`compositionend`:return wr&&t.locale!==`ko`?null:t.data;default:return null}}var Mr={color:!0,date:!0,datetime:!0,"datetime-local":!0,email:!0,month:!0,number:!0,password:!0,range:!0,search:!0,tel:!0,text:!0,time:!0,url:!0,week:!0};function Nr(e){var t=e&&e.nodeName&&e.nodeName.toLowerCase();return t===`input`?!!Mr[e.type]:t===`textarea`}function Pr(e,t,n,r){jn?Mn?Mn.push(r):Mn=[r]:jn=r,t=Jf(t,`onChange`),0<t.length&&(n=new Yn(`onChange`,`change`,null,n,r),e.push({event:n,listeners:t}))}var Fr=null,Ir=null;function Lr(e){Vf(e,0)}function Rr(e){if(dn(Gt(e)))return e}function zr(e,t){if(e===`change`)return t}var Br=!1;if(Ln){var Vr;if(Ln){var Hr=`oninput`in document;if(!Hr){var Ur=document.createElement(`div`);Ur.setAttribute(`oninput`,`return;`),Hr=typeof Ur.oninput==`function`}Vr=Hr}else Vr=!1;Br=Vr&&(!document.documentMode||9<document.documentMode)}function Wr(){Fr&&(Fr.detachEvent(`onpropertychange`,Gr),Ir=Fr=null)}function Gr(e){if(e.propertyName===`value`&&Rr(Ir)){var t=[];Pr(t,Ir,e,An(e)),Fn(Lr,t)}}function Kr(e,t,n){e===`focusin`?(Wr(),Fr=t,Ir=n,Fr.attachEvent(`onpropertychange`,Gr)):e===`focusout`&&Wr()}function qr(e){if(e===`selectionchange`||e===`keyup`||e===`keydown`)return Rr(Ir)}function Jr(e,t){if(e===`click`)return Rr(t)}function Yr(e,t){if(e===`input`||e===`change`)return Rr(t)}function Xr(e,t){return e===t&&(e!==0||1/e==1/t)||e!==e&&t!==t}var Zr=typeof Object.is==`function`?Object.is:Xr;function Qr(e,t){if(Zr(e,t))return!0;if(typeof e!=`object`||!e||typeof t!=`object`||!t)return!1;var n=Object.keys(e),r=Object.keys(t);if(n.length!==r.length)return!1;for(r=0;r<n.length;r++){var i=n[r];if(!Ke.call(t,i)||!Zr(e[i],t[i]))return!1}return!0}function $r(e){if(e||=typeof document<`u`?document:void 0,e===void 0)return null;try{return e.activeElement||e.body}catch{return e.body}}function ei(e){for(;e&&e.firstChild;)e=e.firstChild;return e}function ti(e,t){var n=ei(e);e=0;for(var r;n;){if(n.nodeType===3){if(r=e+n.textContent.length,e<=t&&r>=t)return{node:n,offset:t-e};e=r}a:{for(;n;){if(n.nextSibling){n=n.nextSibling;break a}n=n.parentNode}n=void 0}n=ei(n)}}function ni(e,t){return e&&t?e===t?!0:e&&e.nodeType===3?!1:t&&t.nodeType===3?ni(e,t.parentNode):`contains`in e?e.contains(t):e.compareDocumentPosition?!!(e.compareDocumentPosition(t)&16):!1:!1}function ri(e){e=e!=null&&e.ownerDocument!=null&&e.ownerDocument.defaultView!=null?e.ownerDocument.defaultView:window;for(var t=$r(e.document);t instanceof e.HTMLIFrameElement;){try{var n=typeof t.contentWindow.location.href==`string`}catch{n=!1}if(n)e=t.contentWindow;else break;t=$r(e.document)}return t}function ii(e){var t=e&&e.nodeName&&e.nodeName.toLowerCase();return t&&(t===`input`&&(e.type===`text`||e.type===`search`||e.type===`tel`||e.type===`url`||e.type===`password`)||t===`textarea`||e.contentEditable===`true`)}var ai=Ln&&`documentMode`in document&&11>=document.documentMode,oi=null,si=null,ci=null,li=!1;function ui(e,t,n){var r=n.window===n?n.document:n.nodeType===9?n:n.ownerDocument;li||oi==null||oi!==$r(r)||(r=oi,`selectionStart`in r&&ii(r)?r={start:r.selectionStart,end:r.selectionEnd}:(r=(r.ownerDocument&&r.ownerDocument.defaultView||window).getSelection(),r={anchorNode:r.anchorNode,anchorOffset:r.anchorOffset,focusNode:r.focusNode,focusOffset:r.focusOffset}),ci&&Qr(ci,r)||(ci=r,r=Jf(si,`onSelect`),0<r.length&&(t=new Yn(`onSelect`,`select`,null,t,n),e.push({event:t,listeners:r}),t.target=oi)))}function di(e,t){var n={};return n[e.toLowerCase()]=t.toLowerCase(),n[`Webkit`+e]=`webkit`+t,n[`Moz`+e]=`moz`+t,n}var fi={animationend:di(`Animation`,`AnimationEnd`),animationiteration:di(`Animation`,`AnimationIteration`),animationstart:di(`Animation`,`AnimationStart`),transitionrun:di(`Transition`,`TransitionRun`),transitionstart:di(`Transition`,`TransitionStart`),transitioncancel:di(`Transition`,`TransitionCancel`),transitionend:di(`Transition`,`TransitionEnd`)},pi={},mi={};Ln&&(mi=document.createElement(`div`).style,`AnimationEvent`in window||(delete fi.animationend.animation,delete fi.animationiteration.animation,delete fi.animationstart.animation),`TransitionEvent`in window||delete fi.transitionend.transition);function hi(e){if(pi[e])return pi[e];if(!fi[e])return e;var t=fi[e],n;for(n in t)if(t.hasOwnProperty(n)&&n in mi)return pi[e]=t[n];return e}var gi=hi(`animationend`),_i=hi(`animationiteration`),vi=hi(`animationstart`),yi=hi(`transitionrun`),bi=hi(`transitionstart`),xi=hi(`transitioncancel`),Si=hi(`transitionend`),Ci=new Map,wi=`abort auxClick beforeToggle cancel canPlay canPlayThrough click close contextMenu copy cut drag dragEnd dragEnter dragExit dragLeave dragOver dragStart drop durationChange emptied encrypted ended error fullscreenChange fullscreenError gotPointerCapture input invalid keyDown keyPress keyUp load loadedData loadedMetadata loadStart lostPointerCapture mouseDown mouseMove mouseOut mouseOver mouseUp paste pause play playing pointerCancel pointerDown pointerMove pointerOut pointerOver pointerUp progress rateChange reset resize seeked seeking stalled submit suspend timeUpdate touchCancel touchEnd touchStart volumeChange scroll toggle touchMove waiting wheel`.split(` `);wi.push(`scrollEnd`);function Ti(e,t){Ci.set(e,t),Xt(t,[e])}var Ei=0;function Di(e,t){if(e.name!=null&&e.name!==`auto`)return e.name;if(t.autoName!==null)return t.autoName;e=bd.identifierPrefix;var n=Ei++;return e=`_`+e+`t_`+n.toString(32)+`_`,t.autoName=e}function Oi(e){if(e==null||typeof e==`string`)return e;var t=null,n=Od;if(n!==null)for(var r=0;r<n.length;r++){var i=e[n[r]];if(i!=null){if(i===`none`)return`none`;t=t==null?i:t+(` `+i)}}return t??e.default}function ki(e,t){return e=Oi(e),t=Oi(t),t==null?e===`auto`?null:e:t===`auto`?null:t}var Ai=typeof reportError==`function`?reportError:function(e){if(typeof window==`object`&&typeof window.ErrorEvent==`function`){var t=new window.ErrorEvent(`error`,{bubbles:!0,cancelable:!0,message:typeof e==`object`&&e&&typeof e.message==`string`?String(e.message):String(e),error:e});if(!window.dispatchEvent(t))return}else if(typeof process==`object`&&typeof process.emit==`function`){process.emit(`uncaughtException`,e);return}console.error(e)},ji=[],Mi=0,Ni=0;function Pi(){for(var e=Mi,t=Ni=Mi=0;t<e;){var n=ji[t];ji[t++]=null;var r=ji[t];ji[t++]=null;var i=ji[t];ji[t++]=null;var a=ji[t];if(ji[t++]=null,r!==null&&i!==null){var o=r.pending;o===null?i.next=i:(i.next=o.next,o.next=i),r.pending=i}a!==0&&Ri(n,i,a)}}function Fi(e,t,n,r){ji[Mi++]=e,ji[Mi++]=t,ji[Mi++]=n,ji[Mi++]=r,Ni|=r,e.lanes|=r,e=e.alternate,e!==null&&(e.lanes|=r)}function Ii(e,t,n,r){return Fi(e,t,n,r),zi(e)}function Li(e,t){return Fi(e,null,null,t),zi(e)}function Ri(e,t,n){e.lanes|=n;var r=e.alternate;r!==null&&(r.lanes|=n);for(var i=!1,a=e.return;a!==null;)a.childLanes|=n,r=a.alternate,r!==null&&(r.childLanes|=n),a.tag===22&&(e=a.stateNode,e===null||e._visibility&1||(i=!0)),e=a,a=a.return;return e.tag===3?(a=e.stateNode,i&&t!==null&&(i=31-lt(n),e=a.hiddenUpdates,r=e[i],r===null?e[i]=[t]:r.push(t),t.lane=n|536870912),a):null}function zi(e){if(50<kd)throw kd=0,Ad=null,Error(i(185));for(var t=e.return;t!==null;)e=t,t=e.return;return e.tag===3?e.stateNode:null}var Bi={};function Vi(e,t,n,r){this.tag=e,this.key=n,this.sibling=this.child=this.return=this.stateNode=this.type=this.elementType=null,this.index=0,this.refCleanup=this.ref=null,this.pendingProps=t,this.dependencies=this.memoizedState=this.updateQueue=this.memoizedProps=null,this.mode=r,this.subtreeFlags=this.flags=0,this.deletions=null,this.childLanes=this.lanes=0,this.alternate=null}function Hi(e,t,n,r){return new Vi(e,t,n,r)}function Ui(e){return e=e.prototype,!(!e||!e.isReactComponent)}function Wi(e,t){var n=e.alternate;return n===null?(n=Hi(e.tag,t,e.key,e.mode),n.elementType=e.elementType,n.type=e.type,n.stateNode=e.stateNode,n.alternate=e,e.alternate=n):(n.pendingProps=t,n.type=e.type,n.flags=0,n.subtreeFlags=0,n.deletions=null),n.flags=e.flags&1206910976,n.childLanes=e.childLanes,n.lanes=e.lanes,n.child=e.child,n.memoizedProps=e.memoizedProps,n.memoizedState=e.memoizedState,n.updateQueue=e.updateQueue,t=e.dependencies,n.dependencies=t===null?null:{lanes:t.lanes,firstContext:t.firstContext},n.sibling=e.sibling,n.index=e.index,n.ref=e.ref,n.refCleanup=e.refCleanup,n}function Gi(e,t){e.flags&=1206910978;var n=e.alternate;return n===null?(e.childLanes=0,e.lanes=t,e.child=null,e.subtreeFlags=0,e.memoizedProps=null,e.memoizedState=null,e.updateQueue=null,e.dependencies=null,e.stateNode=null):(e.childLanes=n.childLanes,e.lanes=n.lanes,e.child=n.child,e.subtreeFlags=0,e.deletions=null,e.memoizedProps=n.memoizedProps,e.memoizedState=n.memoizedState,e.updateQueue=n.updateQueue,e.type=n.type,t=n.dependencies,e.dependencies=t===null?null:{lanes:t.lanes,firstContext:t.firstContext}),e}function Ki(e,t,n,r,a,o){var s=0;if(r=e,typeof r==`function`)Ui(r)&&(s=1);else if(typeof r==`string`)s=qm(e,n,je.current)?26:e===`html`||e===`head`||e===`body`?27:5;else a:switch(r){case ge:return e=Hi(31,n,t,a),e.elementType=ge,e.lanes=o,e;case oe:return qi(n.children,a,o,t);case se:s=8,a|=24;break;case ce:return e=Hi(12,n,t,a|2),e.elementType=ce,e.lanes=o,e;case fe:return e=Hi(13,n,t,a),e.elementType=fe,e.lanes=o,e;case pe:return e=Hi(19,n,t,a),e.elementType=pe,e.lanes=o,e;case _e:case ye:return e=a|32,e=Hi(30,n,t,e),e.elementType=ye,e.lanes=o,e.stateNode={autoName:null,paired:null,clones:null,ref:null},e;default:if(typeof r==`object`&&r)switch(r.$$typeof){case ue:s=10;break a;case le:s=9;break a;case de:s=11;break a;case me:s=14;break a;case he:s=16,r=null;break a}s=29,n=Error(i(130,e===null?`null`:typeof e,``)),r=null}return t=Hi(s,n,t,a),t.elementType=e,t.type=r,t.lanes=o,t}function qi(e,t,n,r){return e=Hi(7,e,r,t),e.lanes=n,e}function Ji(e,t,n){return e=Hi(6,e,null,t),e.lanes=n,e}function Yi(e){var t=Hi(18,null,null,0);return t.stateNode=e,t}function Xi(e,t,n){return t=Hi(4,e.children===null?[]:e.children,e.key,t),t.lanes=n,t.stateNode={containerInfo:e.containerInfo,pendingChildren:null,implementation:e.implementation},t}var Zi=new WeakMap;function Qi(e,t){if(typeof e==`object`&&e){var n=Zi.get(e);return n===void 0?(t={value:e,source:t,stack:Ge(t)},Zi.set(e,t),t):n}return{value:e,source:t,stack:Ge(t)}}var $i=[],ea=0,ta=null,na=0,ra=[],ia=0,aa=null,oa=1,sa=``;function ca(e,t){$i[ea++]=na,$i[ea++]=ta,ta=e,na=t}function la(e,t,n){ra[ia++]=oa,ra[ia++]=sa,ra[ia++]=aa,aa=e;var r=oa;e=sa;var i=32-lt(r)-1;r&=~(1<<i),n+=1;var a=32-lt(t)+i;if(30<a){var o=i-i%5;a=(r&(1<<o)-1).toString(32),r>>=o,i-=o,oa=1<<32-lt(t)+i|n<<i|r,sa=a+e}else oa=1<<a|n<<i|r,sa=e}function ua(e){e.return!==null&&(ca(e,1),la(e,1,0))}function da(e){for(;e===ta;)ta=$i[--ea],$i[ea]=null,na=$i[--ea],$i[ea]=null;for(;e===aa;)aa=ra[--ia],ra[ia]=null,sa=ra[--ia],ra[ia]=null,oa=ra[--ia],ra[ia]=null}function fa(e,t){ra[ia++]=oa,ra[ia++]=sa,ra[ia++]=aa,oa=t.id,sa=t.overflow,aa=e}var pa=null,A=null,j=!1,ma=null,ha=!1,ga=Error(i(519));function _a(e){throw Ca(Qi(Error(i(418,1<arguments.length&&arguments[1]!==void 0&&arguments[1]?`text`:`HTML`,``)),e)),ga}function va(e){var t=e.stateNode,n=e.type,r=e.memoizedProps;switch(t[Nt]=e,t[Pt]=r,n){case`dialog`:Q(`cancel`,t),Q(`close`,t);break;case`iframe`:case`object`:case`embed`:Q(`load`,t);break;case`video`:case`audio`:for(n=0;n<zf.length;n++)Q(zf[n],t);break;case`source`:Q(`error`,t);break;case`img`:case`image`:case`link`:Q(`error`,t),Q(`load`,t);break;case`details`:Q(`toggle`,t);break;case`input`:Q(`invalid`,t),hn(t,r.value,r.defaultValue,r.checked,r.defaultChecked,r.type,r.name,!0);break;case`select`:Q(`invalid`,t);break;case`textarea`:Q(`invalid`,t),yn(t,r.value,r.defaultValue,r.children)}n=r.children,typeof n!=`string`&&typeof n!=`number`&&typeof n!=`bigint`||t.textContent===``+n||!0===r.suppressHydrationWarning||ep(t.textContent,n)?(r.popover!=null&&(Q(`beforetoggle`,t),Q(`toggle`,t)),r.onScroll!=null&&Q(`scroll`,t),r.onScrollEnd!=null&&Q(`scrollend`,t),r.onClick!=null&&(t.onclick=On),t=!0):t=!1,t||_a(e,!0)}function ya(e){for(pa=e.return;pa;)switch(pa.tag){case 5:case 31:case 13:ha=!1;return;case 27:case 3:ha=!0;return;default:pa=pa.return}}function ba(e){if(e!==pa)return!1;if(!j)return ya(e),j=!0,!1;var t=e.tag,n;if((n=t!==3&&t!==27)&&((n=t===5)&&(n=e.type,n=n===`form`||n===`button`||pp(e.type,e.memoizedProps)),n=!n),n&&A&&_a(e),ya(e),t===13){if(e=e.memoizedState,e=e===null?null:e.dehydrated,!e)throw Error(i(317));A=dm(e)}else if(t===31){if(e=e.memoizedState,e=e===null?null:e.dehydrated,!e)throw Error(i(317));A=dm(e)}else t===27?(t=A,Sp(e.type)?(e=um,um=null,A=e):A=t):A=pa?lm(e.stateNode.nextSibling):null;return!0}function xa(){A=pa=null,j=!1}function Sa(){var e=ma;return e!==null&&(pd===null?pd=e:pd.push.apply(pd,e),ma=null),e}function Ca(e){ma===null?ma=[e]:ma.push(e)}var wa=ke(null),Ta=null,Ea=null;function Da(e,t,n){D(wa,t._currentValue),t._currentValue=n}function Oa(e){e._currentValue=wa.current,Ae(wa)}function ka(e,t,n){for(;e!==null;){var r=e.alternate;if((e.childLanes&t)===t?r!==null&&(r.childLanes&t)!==t&&(r.childLanes|=t):(e.childLanes|=t,r!==null&&(r.childLanes|=t)),e===n)break;e=e.return}}function Aa(e,t,n,r){var a=e.child;for(a!==null&&(a.return=e);a!==null;){var o=a.dependencies;if(o!==null){var s=a.child;o=o.firstContext;a:for(;o!==null;){var c=o;o=a;for(var l=0;l<t.length;l++)if(c.context===t[l]){o.lanes|=n,c=o.alternate,c!==null&&(c.lanes|=n),ka(o.return,n,e),r||(s=null);break a}o=c.next}}else if(a.tag===18){if(s=a.return,s===null)throw Error(i(341));s.lanes|=n,o=s.alternate,o!==null&&(o.lanes|=n),ka(s,n,e),s=null}else a.tag===13&&a.memoizedState!==null&&a.memoizedState.dehydrated===null?(a.lanes|=n,s=a.alternate,s!==null&&(s.lanes|=n),ka(a.return,n,e),s=a.child,s=s===null?null:s.sibling):s=a.child;if(s!==null)s.return=a;else for(s=a;s!==null;){if(s===e){s=null;break}if(a=s.sibling,a!==null){a.return=s.return,s=a;break}s=s.return}a=s}}function ja(e,t,n,r){e=null;for(var a=t,o=!1;a!==null;){if(!o){if(a.flags&524288)o=!0;else if(a.flags&262144)break}if(a.tag===10){var s=a.alternate;if(s===null)throw Error(i(387));if(s=s.memoizedProps,s!==null){var c=a.type;Zr(a.pendingProps.value,s.value)||(e===null?e=[c]:e.push(c))}}else if(a===Pe.current){if(s=a.alternate,s===null)throw Error(i(387));s.memoizedState.memoizedState!==a.memoizedState.memoizedState&&(e===null?e=[sh]:e.push(sh))}a=a.return}return e!==null&&Aa(t,e,n,r),t.flags|=262144,e!==null}function Ma(e){for(e=e.firstContext;e!==null;){if(!Zr(e.context._currentValue,e.memoizedValue))return!0;e=e.next}return!1}function Na(e){Ta=e,Ea=null,e=e.dependencies,e!==null&&(e.firstContext=null)}function Pa(e){return Ia(Ta,e)}function Fa(e,t){return Ta===null&&Na(e),Ia(e,t)}function Ia(e,t){var n=t._currentValue;if(t={context:t,memoizedValue:n,next:null},Ea===null){if(e===null)throw Error(i(308));Ea=t,e.dependencies={lanes:0,firstContext:t},e.flags|=524288}else Ea=Ea.next=t;return n}var La=typeof AbortController<`u`?AbortController:function(){var e=[],t=this.signal={aborted:!1,addEventListener:function(t,n){e.push(n)}};this.abort=function(){t.aborted=!0,e.forEach(function(e){return e()})}},Ra=t.unstable_scheduleCallback,za=t.unstable_NormalPriority,M={$$typeof:ue,Consumer:null,Provider:null,_currentValue:null,_currentValue2:null,_threadCount:0};function Ba(){return{controller:new La,data:new Map,refCount:0}}function Va(e){e.refCount--,e.refCount===0&&Ra(za,function(){e.controller.abort()})}function Ha(e,t){if(e.pendingLanes&4194048){var n=e.transitionTypes;for(n===null&&(n=e.transitionTypes=[]),e=0;e<t.length;e++){var r=t[e];n.indexOf(r)===-1&&n.push(r)}}}var Ua=null;function Wa(e){var t=e.transitionTypes;return e.transitionTypes=null,t}var Ga=null,Ka=0,qa=0,Ja=null;function Ya(e,t){if(Ga===null){var n=Ga=[];Ka=0,qa=Pf(),Ja={status:`pending`,value:void 0,then:function(e){n.push(e)}}}return Ka++,t.then(Xa,Xa),t}function Xa(){if(--Ka===0&&(Ua=null,Ga!==null)){Ja!==null&&(Ja.status=`fulfilled`);var e=Ga;Ga=null,qa=0,Ja=null;for(var t=0;t<e.length;t++)(0,e[t])()}}function Za(e,t){var n=[],r={status:`pending`,value:null,reason:null,then:function(e){n.push(e)}};return e.then(function(){r.status=`fulfilled`,r.value=t;for(var e=0;e<n.length;e++)(0,n[e])(t)},function(e){for(r.status=`rejected`,r.reason=e,e=0;e<n.length;e++)(0,n[e])(void 0)}),r}var Qa=T.S;T.S=function(e,t){if(gd=Ze(),typeof t==`object`&&t&&typeof t.then==`function`&&Ya(e,t),Ua!==null)for(var n=bf;n!==null;)Ha(n,Ua),n=n.next;if(n=e.types,n!==null){for(var r=bf;r!==null;)Ha(r,n),r=r.next;if(qa!==0){r=Ua,r===null&&(r=Ua=[]);for(var i=0;i<n.length;i++){var a=n[i];r.indexOf(a)===-1&&r.push(a)}}}Qa!==null&&Qa(e,t)};var $a=ke(null);function eo(){var e=$a.current;return e===null?G.pooledCache:e}function to(e,t){t===null?D($a,$a.current):D($a,t.pool)}function no(){var e=eo();return e===null?null:{parent:M._currentValue,pool:e}}var ro=Error(i(460)),io=Error(i(474)),ao=Error(i(542)),oo={then:function(){}};function so(e){return e=e.status,e===`fulfilled`||e===`rejected`}function co(e,t,n){switch(n=e[n],n===void 0?e.push(t):n!==t&&(t.then(On,On),t=n),t.status){case`fulfilled`:return t.value;case`rejected`:throw e=t.reason,po(e),e===void 0&&!(`reason`in t)?Error(i(600)):e;default:if(typeof t.status==`string`)t.then(On,On);else{if(e=G,e!==null&&100<e.shellSuspendCounter)throw Error(i(482));e=t,e.status=`pending`,e.then(function(e){if(t.status===`pending`){var n=t;n.status=`fulfilled`,n.value=e}},function(e){if(t.status===`pending`){var n=t;n.status=`rejected`,n.reason=e}})}switch(t.status){case`fulfilled`:return t.value;case`rejected`:throw e=t.reason,po(e),e}throw uo=t,ro}}function lo(e){try{var t=e._init;return t(e._payload)}catch(e){throw typeof e==`object`&&e&&typeof e.then==`function`?(uo=e,ro):e}}var uo=null;function fo(){if(uo===null)throw Error(i(459));var e=uo;return uo=null,e}function po(e){if(e===ro||e===ao)throw Error(i(483))}var mo=null,ho=0;function go(e){var t=ho;return ho+=1,mo===null&&(mo=[]),co(mo,e,t)}function _o(e,t){t=t.props.ref,e.ref=t===void 0?null:t}function vo(e,t){throw t.$$typeof===re?Error(i(525)):(e=Object.prototype.toString.call(t),Error(i(31,e===`[object Object]`?`object with keys {`+Object.keys(t).join(`, `)+`}`:e)))}function yo(e){function t(t,n){if(e){var r=t.deletions;r===null?(t.deletions=[n],t.flags|=16):r.push(n)}}function n(n,r){if(!e)return null;for(;r!==null;)t(n,r),r=r.sibling;return null}function r(e){for(var t=new Map;e!==null;)e.key===null?t.set(e.index,e):t.set(e.key,e),e=e.sibling;return t}function a(e,t){return e=Wi(e,t),e.index=0,e.sibling=null,e}function o(t,n,r){return t.index=r,e?(r=t.alternate,r===null?(t.flags|=134217730,n):(r=r.index,r<n?(t.flags|=2,n):r)):(t.flags|=1048576,n)}function s(t){return e&&t.alternate===null&&(t.flags|=134217730),t}function c(e,t,n,r){return t===null||t.tag!==6?(t=Ji(n,e.mode,r),t.return=e,t):(t=a(t,n),t.return=e,t)}function l(e,t,n,r){var i=n.type;return i===oe?(e=d(e,t,n.props.children,r,n.key),_o(e,n),e):t!==null&&(t.elementType===i||typeof i==`object`&&i&&i.$$typeof===he&&lo(i)===t.type)?(t=a(t,n.props),_o(t,n),t.return=e,t):(t=Ki(n.type,n.key,n.props,null,e.mode,r),_o(t,n),t.return=e,t)}function u(e,t,n,r){return t===null||t.tag!==4||t.stateNode.containerInfo!==n.containerInfo||t.stateNode.implementation!==n.implementation?(t=Xi(n,e.mode,r),t.return=e,t):(t=a(t,n.children||[]),t.return=e,t)}function d(e,t,n,r,i){return t===null||t.tag!==7?(t=qi(n,e.mode,r,i),t.return=e,t):(t=a(t,n),t.return=e,t)}function f(e,t,n){if(typeof t==`string`&&t!==``||typeof t==`number`||typeof t==`bigint`)return t=Ji(``+t,e.mode,n),t.return=e,t;if(typeof t==`object`&&t){switch(t.$$typeof){case ie:return n=Ki(t.type,t.key,t.props,null,e.mode,n),_o(n,t),n.return=e,n;case ae:return t=Xi(t,e.mode,n),t.return=e,t;case he:return t=lo(t),f(e,t,n)}if(Te(t)||Se(t))return t=qi(t,e.mode,n,null),t.return=e,t;if(typeof t.then==`function`)return f(e,go(t),n);if(t.$$typeof===ue)return f(e,Fa(e,t),n);vo(e,t)}return null}function p(e,t,n,r){var i=t===null?null:t.key;if(typeof n==`string`&&n!==``||typeof n==`number`||typeof n==`bigint`)return i===null?c(e,t,``+n,r):null;if(typeof n==`object`&&n){switch(n.$$typeof){case ie:return n.key===i?l(e,t,n,r):null;case ae:return n.key===i?u(e,t,n,r):null;case he:return n=lo(n),p(e,t,n,r)}if(Te(n)||Se(n))return i===null?d(e,t,n,r,null):null;if(typeof n.then==`function`)return p(e,t,go(n),r);if(n.$$typeof===ue)return p(e,t,Fa(e,n),r);vo(e,n)}return null}function m(e,t,n,r,i){if(typeof r==`string`&&r!==``||typeof r==`number`||typeof r==`bigint`)return e=e.get(n)||null,c(t,e,``+r,i);if(typeof r==`object`&&r){switch(r.$$typeof){case ie:return e=e.get(r.key===null?n:r.key)||null,l(t,e,r,i);case ae:return e=e.get(r.key===null?n:r.key)||null,u(t,e,r,i);case he:return r=lo(r),m(e,t,n,r,i)}if(Te(r)||Se(r))return e=e.get(n)||null,d(t,e,r,i,null);if(typeof r.then==`function`)return m(e,t,n,go(r),i);if(r.$$typeof===ue)return m(e,t,n,Fa(t,r),i);vo(t,r)}return null}function h(i,a,s,c){for(var l=null,u=null,d=a,h=a=0,g=null;d!==null&&h<s.length;h++){d.index>h?(g=d,d=null):g=d.sibling;var _=p(i,d,s[h],c);if(_===null){d===null&&(d=g);break}e&&d&&_.alternate===null&&t(i,d),a=o(_,a,h),u===null?l=_:u.sibling=_,u=_,d=g}if(h===s.length)return n(i,d),j&&ca(i,h),l;if(d===null){for(;h<s.length;h++)d=f(i,s[h],c),d!==null&&(a=o(d,a,h),u===null?l=d:u.sibling=d,u=d);return j&&ca(i,h),l}for(d=r(d);h<s.length;h++)g=m(d,i,h,s[h],c),g!==null&&(e&&(_=g.alternate,_!==null&&d.delete(_.key===null?h:_.key)),a=o(g,a,h),u===null?l=g:u.sibling=g,u=g);return e&&d.forEach(function(e){return t(i,e)}),j&&ca(i,h),l}function g(a,s,c,l){if(c==null)throw Error(i(151));for(var u=null,d=null,h=s,g=s=0,_=null,v=c.next();h!==null&&!v.done;g++,v=c.next()){h.index>g?(_=h,h=null):_=h.sibling;var y=p(a,h,v.value,l);if(y===null){h===null&&(h=_);break}e&&h&&y.alternate===null&&t(a,h),s=o(y,s,g),d===null?u=y:d.sibling=y,d=y,h=_}if(v.done)return n(a,h),j&&ca(a,g),u;if(h===null){for(;!v.done;g++,v=c.next())v=f(a,v.value,l),v!==null&&(s=o(v,s,g),d===null?u=v:d.sibling=v,d=v);return j&&ca(a,g),u}for(h=r(h);!v.done;g++,v=c.next())v=m(h,a,g,v.value,l),v!==null&&(e&&(_=v.alternate,_!==null&&h.delete(_.key===null?g:_.key)),s=o(v,s,g),d===null?u=v:d.sibling=v,d=v);return e&&h.forEach(function(e){return t(a,e)}),j&&ca(a,g),u}function _(e,r,o,c){if(typeof o==`object`&&o&&o.type===oe&&o.key===null&&o.props.ref===void 0&&(o=o.props.children),typeof o==`object`&&o){switch(o.$$typeof){case ie:a:{for(var l=o.key;r!==null;){if(r.key===l){if(l=o.type,l===oe){if(r.tag===7){n(e,r.sibling),c=a(r,o.props.children),_o(c,o),c.return=e,e=c;break a}}else if(r.elementType===l||typeof l==`object`&&l&&l.$$typeof===he&&lo(l)===r.type){n(e,r.sibling),c=a(r,o.props),_o(c,o),c.return=e,e=c;break a}n(e,r);break}t(e,r),r=r.sibling}o.type===oe?(c=qi(o.props.children,e.mode,c,o.key),_o(c,o),c.return=e,e=c):(c=Ki(o.type,o.key,o.props,null,e.mode,c),_o(c,o),c.return=e,e=c)}return s(e);case ae:a:{for(l=o.key;r!==null;){if(r.key===l){if(r.tag===4&&r.stateNode.containerInfo===o.containerInfo&&r.stateNode.implementation===o.implementation){n(e,r.sibling),c=a(r,o.children||[]),c.return=e,e=c;break a}n(e,r);break}t(e,r),r=r.sibling}c=Xi(o,e.mode,c),c.return=e,e=c}return s(e);case he:return o=lo(o),_(e,r,o,c)}if(Te(o))return h(e,r,o,c);if(Se(o)){if(l=Se(o),typeof l!=`function`)throw Error(i(150));return o=l.call(o),g(e,r,o,c)}if(typeof o.then==`function`)return _(e,r,go(o),c);if(o.$$typeof===ue)return _(e,r,Fa(e,o),c);vo(e,o)}return typeof o==`string`&&o!==``||typeof o==`number`||typeof o==`bigint`?(o=``+o,r!==null&&r.tag===6?(n(e,r.sibling),c=a(r,o),c.return=e,e=c):(n(e,r),c=Ji(o,e.mode,c),c.return=e,e=c),s(e)):n(e,r)}return function(e,t,n,r){try{ho=0;var i=_(e,t,n,r);return mo=null,i}catch(t){if(t===ro||t===ao)throw t;var a=Hi(29,t,null,e.mode);return a.lanes=r,a.return=e,a}}}var bo=yo(!0),xo=yo(!1),So=!1;function Co(e){e.updateQueue={baseState:e.memoizedState,firstBaseUpdate:null,lastBaseUpdate:null,shared:{pending:null,lanes:0,hiddenCallbacks:null},callbacks:null}}function wo(e,t){e=e.updateQueue,t.updateQueue===e&&(t.updateQueue={baseState:e.baseState,firstBaseUpdate:e.firstBaseUpdate,lastBaseUpdate:e.lastBaseUpdate,shared:e.shared,callbacks:null})}function To(e){return{lane:e,tag:0,payload:null,callback:null,next:null}}function Eo(e,t,n){var r=e.updateQueue;if(r===null)return null;if(r=r.shared,W&2){var i=r.pending;return i===null?t.next=t:(t.next=i.next,i.next=t),r.pending=t,t=zi(e),Ri(e,null,n),t}return Fi(e,r,t,n),zi(e)}function Do(e,t,n){if(t=t.updateQueue,t!==null&&(t=t.shared,n&4194048)){var r=t.lanes;r&=e.pendingLanes,n|=r,t.lanes=n,Et(e,n)}}function Oo(e,t){var n=e.updateQueue,r=e.alternate;if(r!==null&&(r=r.updateQueue,n===r)){var i=null,a=null;if(n=n.firstBaseUpdate,n!==null){do{var o={lane:n.lane,tag:n.tag,payload:n.payload,callback:null,next:null};a===null?i=a=o:a=a.next=o,n=n.next}while(n!==null);a===null?i=a=t:a=a.next=t}else i=a=t;n={baseState:r.baseState,firstBaseUpdate:i,lastBaseUpdate:a,shared:r.shared,callbacks:r.callbacks},e.updateQueue=n;return}e=n.lastBaseUpdate,e===null?n.firstBaseUpdate=t:e.next=t,n.lastBaseUpdate=t}var ko=!1;function Ao(){if(ko){var e=Ja;if(e!==null)throw e}}function jo(e,t,n,r){ko=!1;var i=e.updateQueue;So=!1;var a=i.firstBaseUpdate,o=i.lastBaseUpdate,s=i.shared.pending;if(s!==null){i.shared.pending=null;var c=s,l=c.next;c.next=null,o===null?a=l:o.next=l,o=c;var u=e.alternate;u!==null&&(u=u.updateQueue,s=u.lastBaseUpdate,s!==o&&(s===null?u.firstBaseUpdate=l:s.next=l,u.lastBaseUpdate=c))}if(a!==null){var d=i.baseState;o=0,u=l=c=null,s=a;do{var f=s.lane&-536870913,p=f!==s.lane;if(p?(q&f)===f:(r&f)===f){f!==0&&f===qa&&(ko=!0),u!==null&&(u=u.next={lane:0,tag:s.tag,payload:s.payload,callback:null,next:null});a:{var m=e,h=s;f=t;var g=n;switch(h.tag){case 1:if(m=h.payload,typeof m==`function`){d=m.call(g,d,f);break a}d=m;break a;case 3:m.flags=m.flags&-65537|128;case 0:if(m=h.payload,f=typeof m==`function`?m.call(g,d,f):m,f==null)break a;d=w({},d,f);break a;case 2:So=!0}}f=s.callback,f!==null&&(e.flags|=64,p&&(e.flags|=8192),p=i.callbacks,p===null?i.callbacks=[f]:p.push(f))}else p={lane:f,tag:s.tag,payload:s.payload,callback:s.callback,next:null},u===null?(l=u=p,c=d):u=u.next=p,o|=f;if(s=s.next,s===null){if(s=i.shared.pending,s===null)break;p=s,s=p.next,p.next=null,i.lastBaseUpdate=p,i.shared.pending=null}}while(1);u===null&&(c=d),i.baseState=c,i.firstBaseUpdate=l,i.lastBaseUpdate=u,a===null&&(i.shared.lanes=0),sd|=o,e.lanes=o,e.memoizedState=d}}function Mo(e,t){if(typeof e!=`function`)throw Error(i(191,e));e.call(t)}function No(e,t){var n=e.callbacks;if(n!==null)for(e.callbacks=null,e=0;e<n.length;e++)Mo(n[e],t)}var Po=ke(null),Fo=ke(0);function Io(e,t){e=od,D(Fo,e),D(Po,t),od=e|t.baseLanes}function Lo(){D(Fo,od),D(Po,Po.current)}function Ro(){od=Fo.current,Ae(Po),Ae(Fo)}var zo=ke(null),Bo=null;function Vo(e){var t=e.alternate;D(Ko,Ko.current&1),D(zo,e),Bo===null&&(t===null||Po.current!==null||t.memoizedState!==null)&&(Bo=e)}function Ho(e){D(Ko,Ko.current),D(zo,e),Bo===null&&(Bo=e)}function Uo(e){e.tag===22?(D(Ko,Ko.current),D(zo,e),Bo===null&&(Bo=e)):Wo()}function Wo(){D(Ko,Ko.current),D(zo,zo.current)}function Go(e){Ae(zo),Bo===e&&(Bo=null),Ae(Ko)}var Ko=ke(0);function qo(e,t){D(zo,zo.current),D(Ko,t)}function Jo(e){Ae(Ko),Ae(zo),Bo===e&&(Bo=null)}function Yo(e){for(var t=e;t!==null;){if(t.tag===13){var n=t.memoizedState;if(n!==null&&(n=n.dehydrated,n===null||om(n)||sm(n)))return t}else if(t.tag===19&&t.memoizedProps.revealOrder!==`independent`){if(t.flags&128)return t}else if(t.child!==null){t.child.return=t,t=t.child;continue}if(t===e)break;for(;t.sibling===null;){if(t.return===null||t.return===e)return null;t=t.return}t.sibling.return=t.return,t=t.sibling}return null}var Xo=0,N=null,P=null,F=null,Zo=!1,Qo=!1,$o=!1,es=0,ts=0,ns=null,rs=0;function I(){throw Error(i(321))}function is(e,t){if(t===null)return!1;for(var n=0;n<t.length&&n<e.length;n++)if(!Zr(e[n],t[n]))return!1;return!0}function as(e,t,n,r,i,a){return Xo=a,N=t,t.memoizedState=null,t.updateQueue=null,t.lanes=0,T.H=e===null||e.memoizedState===null?xc:Sc,$o=!1,a=n(r,i),$o=!1,Qo&&(a=ss(t,n,r,i)),os(e),a}function os(e){T.H=bc;var t=P!==null&&P.next!==null;if(Xo=0,F=P=N=null,Zo=!1,ts=0,ns=null,t)throw Error(i(300));e===null||R||(e=e.dependencies,e!==null&&Ma(e)&&(R=!0))}function ss(e,t,n,r){N=e;var a=0;do{if(Qo&&(ns=null),ts=0,Qo=!1,25<=a)throw Error(i(301));if(a+=1,F=P=null,e.updateQueue!=null){var o=e.updateQueue;o.lastEffect=null,o.events=null,o.stores=null,o.memoCache!=null&&(o.memoCache.index=0)}T.H=Cc,o=t(n,r)}while(Qo);return o}function cs(){var e=T.H,t=e.useState()[0];return t=typeof t.then==`function`?ms(t):t,e=e.useState()[0],(P===null?null:P.memoizedState)!==e&&(N.flags|=1024),t}function ls(){var e=es!==0;return es=0,e}function us(e,t,n){t.updateQueue=e.updateQueue,t.flags&=-2053,e.lanes&=~n}function ds(e){if(Zo){for(e=e.memoizedState;e!==null;){var t=e.queue;t!==null&&(t.pending=null),e=e.next}Zo=!1}Xo=0,F=P=N=null,Qo=!1,ts=es=0,ns=null}function fs(){var e={memoizedState:null,baseState:null,baseQueue:null,queue:null,next:null};return F===null?N.memoizedState=F=e:F=F.next=e,F}function L(){if(P===null){var e=N.alternate;e=e===null?null:e.memoizedState}else e=P.next;var t=F===null?N.memoizedState:F.next;if(t!==null)F=t,P=e;else{if(e===null)throw N.alternate===null?Error(i(467)):Error(i(310));P=e,e={memoizedState:P.memoizedState,baseState:P.baseState,baseQueue:P.baseQueue,queue:P.queue,next:null},F===null?N.memoizedState=F=e:F=F.next=e}return F}function ps(){return{lastEffect:null,events:null,stores:null,memoCache:null}}function ms(e){var t=ts;return ts+=1,ns===null&&(ns=[]),e=co(ns,e,t),t=N,(F===null?t.memoizedState:F.next)===null&&(t=t.alternate,T.H=t===null||t.memoizedState===null?xc:Sc),e}function hs(e){if(typeof e==`object`&&e){if(typeof e.then==`function`)return ms(e);if(e.$$typeof===be)return;if(e.$$typeof===ue)return Pa(e)}throw Error(i(438,String(e)))}function gs(e){var t=null,n=N.updateQueue;if(n!==null&&(t=n.memoCache),t==null){var r=N.alternate;r!==null&&(r=r.updateQueue,r!==null&&(r=r.memoCache,r!=null&&(t={data:r.data.map(function(e){return e.slice()}),index:0})))}if(t??={data:[],index:0},n===null&&(n=ps(),N.updateQueue=n),n.memoCache=t,n=t.data[t.index],n===void 0)for(n=t.data[t.index]=Array(e),r=0;r<e;r++)n[r]=ve;return t.index++,n}function _s(e,t){return typeof t==`function`?t(e):t}function vs(e){return ys(L(),P,e)}function ys(e,t,n){var r=e.queue;if(r===null)throw Error(i(311));r.lastRenderedReducer=n;var a=e.baseQueue,o=r.pending;if(o!==null){if(a!==null){var s=a.next;a.next=o.next,o.next=s}t.baseQueue=a=o,r.pending=null}if(o=e.baseState,a===null)e.memoizedState=o;else{t=a.next;var c=s=null,l=null,u=t,d=!1;do{var f=u.lane&-536870913;if(f===u.lane?(Xo&f)===f:(q&f)===f){var p=u.revertLane;if(p===0)l!==null&&(l=l.next={lane:0,revertLane:0,gesture:null,action:u.action,hasEagerState:u.hasEagerState,eagerState:u.eagerState,next:null}),f===qa&&(d=!0);else if((Xo&p)===p){u=u.next,p===qa&&(d=!0);continue}else f={lane:0,revertLane:u.revertLane,gesture:null,action:u.action,hasEagerState:u.hasEagerState,eagerState:u.eagerState,next:null},l===null?(c=l=f,s=o):l=l.next=f,N.lanes|=p,sd|=p;f=u.action,$o&&n(o,f),o=u.hasEagerState?u.eagerState:n(o,f)}else p={lane:f,revertLane:u.revertLane,gesture:u.gesture,action:u.action,hasEagerState:u.hasEagerState,eagerState:u.eagerState,next:null},l===null?(c=l=p,s=o):l=l.next=p,N.lanes|=f,sd|=f;u=u.next}while(u!==null&&u!==t);if(l===null?s=o:l.next=c,!Zr(o,e.memoizedState)&&(R=!0,d&&(n=Ja,n!==null)))throw n;e.memoizedState=o,e.baseState=s,e.baseQueue=l,r.lastRenderedState=o}return a===null&&(r.lanes=0),[e.memoizedState,r.dispatch]}function bs(e){var t=L(),n=t.queue;if(n===null)throw Error(i(311));n.lastRenderedReducer=e;var r=n.dispatch,a=n.pending,o=t.memoizedState;if(a!==null){n.pending=null;var s=a=a.next;do o=e(o,s.action),s=s.next;while(s!==a);Zr(o,t.memoizedState)||(R=!0),t.memoizedState=o,t.baseQueue===null&&(t.baseState=o),n.lastRenderedState=o}return[o,r]}function xs(e,t,n){var r=N,a=L(),o=j;if(o){if(n===void 0)throw Error(i(407));n=n()}else n=t();var s=!Zr((P||a).memoizedState,n);if(s&&(a.memoizedState=n,R=!0),a=a.queue,Ks(ws.bind(null,r,a,e),[e]),e=a.getSnapshot!==t||s||F!==null&&!!(F.memoizedState.tag&1),Vs(e?9:8,{destroy:void 0},Cs.bind(null,r,a,n,t),null),e){if(r.flags|=2048,G===null)throw Error(i(349));o||Xo&127||Ss(r,t,n)}return n}function Ss(e,t,n){e.flags|=16384,e={getSnapshot:t,value:n},t=N.updateQueue,t===null?(t=ps(),N.updateQueue=t,t.stores=[e]):(n=t.stores,n===null?t.stores=[e]:n.push(e))}function Cs(e,t,n,r){t.value=n,t.getSnapshot=r,Ts(t)&&Es(e)}function ws(e,t,n){return n(function(){Ts(t)&&Es(e)})}function Ts(e){var t=e.getSnapshot;e=e.value;try{var n=t();return!Zr(e,n)}catch{return!0}}function Es(e){var t=Li(e,2);t!==null&&Pd(t,e,2)}function Ds(e){var t=fs();if(typeof e==`function`){var n=e;if(e=n(),$o){ct(!0);try{n()}finally{ct(!1)}}}return t.memoizedState=t.baseState=e,t.queue={pending:null,lanes:0,dispatch:null,lastRenderedReducer:_s,lastRenderedState:e},t}function Os(e,t,n,r){return e.baseState=n,ys(e,P,typeof r==`function`?r:_s)}function ks(e,t,n,r,a){if(_c(e))throw Error(i(485));if(e=t.action,e!==null){var o={payload:a,action:e,next:null,isTransition:!0,status:`pending`,value:null,reason:null,listeners:[],then:function(e){o.listeners.push(e)}};T.T===null?o.isTransition=!1:n(!0),r(o),n=t.pending,n===null?(o.next=t.pending=o,As(t,o)):(o.next=n.next,t.pending=n.next=o)}}function As(e,t){var n=t.action,r=t.payload,i=e.state;if(t.isTransition){var a=T.T,o={};o.types=a===null?null:a.types,T.T=o;try{var s=n(i,r),c=T.S;c!==null&&c(o,s),js(e,t,s)}catch(n){Ns(e,t,n)}finally{a!==null&&o.types!==null&&(a.types=o.types),T.T=a}}else try{a=n(i,r),js(e,t,a)}catch(n){Ns(e,t,n)}}function js(e,t,n){typeof n==`object`&&n&&typeof n.then==`function`?n.then(function(n){Ms(e,t,n)},function(n){return Ns(e,t,n)}):Ms(e,t,n)}function Ms(e,t,n){t.status=`fulfilled`,t.value=n,Ps(t),e.state=n,t=e.pending,t!==null&&(n=t.next,n===t?e.pending=null:(n=n.next,t.next=n,As(e,n)))}function Ns(e,t,n){var r=e.pending;if(e.pending=null,r!==null){r=r.next;do t.status=`rejected`,t.reason=n,Ps(t),t=t.next;while(t!==r)}e.action=null}function Ps(e){e=e.listeners;for(var t=0;t<e.length;t++)(0,e[t])()}function Fs(e,t){return t}function Is(e,t){if(j){var n=G.formState;if(n!==null){a:{var r=N;if(j){if(A){b:{for(var i=A,a=ha;i.nodeType!==8;){if(!a){i=null;break b}if(i=lm(i.nextSibling),i===null){i=null;break b}}a=i.data,i=a===`F!`||a===`F`?i:null}if(i){A=lm(i.nextSibling),r=i.data===`F!`;break a}}_a(r)}r=!1}r&&(t=n[0])}}return n=fs(),n.memoizedState=n.baseState=t,r={pending:null,lanes:0,dispatch:null,lastRenderedReducer:Fs,lastRenderedState:t},n.queue=r,n=mc.bind(null,N,r),r.dispatch=n,r=Ds(!1),a=gc.bind(null,N,!1,r.queue),r=fs(),i={state:t,dispatch:null,action:e,pending:null},r.queue=i,n=ks.bind(null,N,i,a,n),i.dispatch=n,r.memoizedState=e,[t,n,!1]}function Ls(e){return Rs(L(),P,e)}function Rs(e,t,n){if(t=ys(e,t,Fs)[0],e=vs(_s)[0],typeof t==`object`&&t&&typeof t.then==`function`)try{var r=ms(t)}catch(e){throw e===ro?ao:e}else r=t;t=L();var i=t.queue,a=i.dispatch;return n!==t.memoizedState&&(N.flags|=2048,Vs(9,{destroy:void 0},zs.bind(null,i,n),null)),[r,a,e]}function zs(e,t){e.action=t}function Bs(e){var t=L(),n=P;if(n!==null)return Rs(t,n,e);L(),t=t.memoizedState,n=L();var r=n.queue.dispatch;return n.memoizedState=e,[t,r,!1]}function Vs(e,t,n,r){return e={tag:e,create:n,deps:r,inst:t,next:null},t=N.updateQueue,t===null&&(t=ps(),N.updateQueue=t),n=t.lastEffect,n===null?t.lastEffect=e.next=e:(r=n.next,n.next=e,e.next=r,t.lastEffect=e),e}function Hs(){return L().memoizedState}function Us(e,t,n,r){var i=fs();N.flags|=e,i.memoizedState=Vs(1|t,{destroy:void 0},n,r===void 0?null:r)}function Ws(e,t,n,r){var i=L();r=r===void 0?null:r;var a=i.memoizedState.inst;P!==null&&r!==null&&is(r,P.memoizedState.deps)?i.memoizedState=Vs(t,a,n,r):(N.flags|=e,i.memoizedState=Vs(1|t,a,n,r))}function Gs(e,t){Us(8390656,8,e,t)}function Ks(e,t){Ws(2048,8,e,t)}function qs(e){N.flags|=4;var t=N.updateQueue;if(t===null)t=ps(),N.updateQueue=t,t.events=[e];else{var n=t.events;n===null?t.events=[e]:n.push(e)}}function Js(e){var t=L().memoizedState;return qs({ref:t,nextImpl:e}),function(){if(W&2)throw Error(i(440));return t.impl.apply(void 0,arguments)}}function Ys(e,t){return Ws(4,2,e,t)}function Xs(e,t){return Ws(4,4,e,t)}function Zs(e,t){if(typeof t==`function`){e=e();var n=t(e);return function(){typeof n==`function`?n():t(null)}}if(t!=null)return e=e(),t.current=e,function(){t.current=null}}function Qs(e,t,n){n=n==null?null:n.concat([e]),Ws(4,4,Zs.bind(null,t,e),n)}function $s(){}function ec(e,t){var n=L();t=t===void 0?null:t;var r=n.memoizedState;return t!==null&&is(t,r[1])?r[0]:(n.memoizedState=[e,t],e)}function tc(e,t){var n=L();t=t===void 0?null:t;var r=n.memoizedState;if(t!==null&&is(t,r[1]))return r[0];if(r=e(),$o){ct(!0);try{e()}finally{ct(!1)}}return n.memoizedState=[r,t],r}function nc(e,t,n){return n===void 0||Xo&1073741824&&!(q&261930)?e.memoizedState=t:(e.memoizedState=n,e=Md(),N.lanes|=e,sd|=e,n)}function rc(e,t,n,r){return Zr(n,t)?n:Po.current===null?!(Xo&106)||Xo&1073741824&&!(q&261930)?(R=!0,e.memoizedState=n):(e=Md(),N.lanes|=e,sd|=e,t):(e=nc(e,n,r),Zr(e,t)||(R=!0),e)}function ic(e,t,n,r,i){var a=E.p;E.p=a!==0&&8>a?a:8;var o=T.T,s={};s.types=o===null?null:o.types,T.T=s,gc(e,!1,t,n);try{var c=i(),l=T.S;l!==null&&l(s,c),typeof c==`object`&&c&&typeof c.then==`function`?hc(e,t,Za(c,r),jd(e)):hc(e,t,r,jd(e))}catch(n){hc(e,t,{then:function(){},status:`rejected`,reason:n},jd())}finally{E.p=a,o!==null&&s.types!==null&&(o.types=s.types),T.T=o}}function ac(){}function oc(e,t,n,r){if(e.tag!==5)throw Error(i(476));var a=sc(e).queue;ic(e,a,t,Ee,n===null?ac:function(){return cc(e),n(r)})}function sc(e){var t=e.memoizedState;if(t!==null)return t;t={memoizedState:Ee,baseState:Ee,baseQueue:null,queue:{pending:null,lanes:0,dispatch:null,lastRenderedReducer:_s,lastRenderedState:Ee},next:null};var n={};return t.next={memoizedState:n,baseState:n,baseQueue:null,queue:{pending:null,lanes:0,dispatch:null,lastRenderedReducer:_s,lastRenderedState:n},next:null},e.memoizedState=t,e=e.alternate,e!==null&&(e.memoizedState=t),t}function cc(e){var t=sc(e);t.next===null&&(t=e.alternate.memoizedState),hc(e,t.next.queue,{},jd())}function lc(){return Pa(sh)}function uc(){return L().memoizedState}function dc(){return L().memoizedState}function fc(e){for(var t=e.return;t!==null;){switch(t.tag){case 24:case 3:var n=jd();e=To(n);var r=Eo(t,e,n);r!==null&&(Pd(r,t,n),Do(r,t,n)),t={cache:Ba()},e.payload=t;return}t=t.return}}function pc(e,t,n){var r=jd();n={lane:r,revertLane:0,gesture:null,action:n,hasEagerState:!1,eagerState:null,next:null},_c(e)?vc(t,n):(n=Ii(e,t,n,r),n!==null&&(Pd(n,e,r),yc(n,t,r)))}function mc(e,t,n){hc(e,t,n,jd())}function hc(e,t,n,r){var i={lane:r,revertLane:0,gesture:null,action:n,hasEagerState:!1,eagerState:null,next:null};if(_c(e))vc(t,i);else{var a=e.alternate;if(e.lanes===0&&(a===null||a.lanes===0)&&(a=t.lastRenderedReducer,a!==null))try{var o=t.lastRenderedState,s=a(o,n);if(i.hasEagerState=!0,i.eagerState=s,Zr(s,o))return Fi(e,t,i,0),G===null&&Pi(),!1}catch{}if(n=Ii(e,t,i,r),n!==null)return Pd(n,e,r),yc(n,t,r),!0}return!1}function gc(e,t,n,r){if(r={lane:2,revertLane:Pf(),gesture:null,action:r,hasEagerState:!1,eagerState:null,next:null},_c(e)){if(t)throw Error(i(479))}else t=Ii(e,n,r,2),t!==null&&Pd(t,e,2)}function _c(e){var t=e.alternate;return e===N||t!==null&&t===N}function vc(e,t){Qo=Zo=!0;var n=e.pending;n===null?t.next=t:(t.next=n.next,n.next=t),e.pending=t}function yc(e,t,n){if(n&4194048){var r=t.lanes;r&=e.pendingLanes,n|=r,t.lanes=n,Et(e,n)}}var bc={readContext:Pa,use:hs,useCallback:I,useContext:I,useEffect:I,useImperativeHandle:I,useLayoutEffect:I,useInsertionEffect:I,useMemo:I,useReducer:I,useRef:I,useState:I,useDebugValue:I,useDeferredValue:I,useTransition:I,useSyncExternalStore:I,useId:I,useHostTransitionStatus:I,useFormState:I,useActionState:I,useOptimistic:I,useMemoCache:I,useCacheRefresh:I,useEffectEvent:I},xc={readContext:Pa,use:hs,useCallback:function(e,t){return fs().memoizedState=[e,t===void 0?null:t],e},useContext:Pa,useEffect:Gs,useImperativeHandle:function(e,t,n){n=n==null?null:n.concat([e]),Us(4194308,4,Zs.bind(null,t,e),n)},useLayoutEffect:function(e,t){return Us(4194308,4,e,t)},useInsertionEffect:function(e,t){Us(4,2,e,t)},useMemo:function(e,t){var n=fs();t=t===void 0?null:t;var r=e();if($o){ct(!0);try{e()}finally{ct(!1)}}return n.memoizedState=[r,t],r},useReducer:function(e,t,n){var r=fs();if(n!==void 0){var i=n(t);if($o){ct(!0);try{n(t)}finally{ct(!1)}}}else i=t;return r.memoizedState=r.baseState=i,e={pending:null,lanes:0,dispatch:null,lastRenderedReducer:e,lastRenderedState:i},r.queue=e,e=e.dispatch=pc.bind(null,N,e),[r.memoizedState,e]},useRef:function(e){var t=fs();return e={current:e},t.memoizedState=e},useState:function(e){e=Ds(e);var t=e.queue,n=mc.bind(null,N,t);return t.dispatch=n,[e.memoizedState,n]},useDebugValue:$s,useDeferredValue:function(e,t){return nc(fs(),e,t)},useTransition:function(){var e=Ds(!1);return e=ic.bind(null,N,e.queue,!0,!1),fs().memoizedState=e,[!1,e]},useSyncExternalStore:function(e,t,n){var r=N,a=fs();if(j){if(n===void 0)throw Error(i(407));n=n()}else{if(n=t(),G===null)throw Error(i(349));q&127||Ss(r,t,n)}a.memoizedState=n;var o={value:n,getSnapshot:t};return a.queue=o,Gs(ws.bind(null,r,o,e),[e]),r.flags|=2048,Vs(9,{destroy:void 0},Cs.bind(null,r,o,n,t),null),n},useId:function(){var e=fs(),t=G.identifierPrefix;if(j){var n=sa,r=oa;n=(r&~(1<<32-lt(r)-1)).toString(32)+n,t=`_`+t+`R_`+n,n=es++,0<n&&(t+=`H`+n.toString(32)),t+=`_`}else n=rs++,t=`_`+t+`r_`+n.toString(32)+`_`;return e.memoizedState=t},useHostTransitionStatus:lc,useFormState:Is,useActionState:Is,useOptimistic:function(e){var t=fs();t.memoizedState=t.baseState=e;var n={pending:null,lanes:0,dispatch:null,lastRenderedReducer:null,lastRenderedState:null};return t.queue=n,t=gc.bind(null,N,!0,n),n.dispatch=t,[e,t]},useMemoCache:gs,useCacheRefresh:function(){return fs().memoizedState=fc.bind(null,N)},useEffectEvent:function(e){var t=fs(),n={impl:e};return t.memoizedState=n,function(){if(W&2)throw Error(i(440));return n.impl.apply(void 0,arguments)}}},Sc={readContext:Pa,use:hs,useCallback:ec,useContext:Pa,useEffect:Ks,useImperativeHandle:Qs,useInsertionEffect:Ys,useLayoutEffect:Xs,useMemo:tc,useReducer:vs,useRef:Hs,useState:function(){return vs(_s)},useDebugValue:$s,useDeferredValue:function(e,t){return rc(L(),P.memoizedState,e,t)},useTransition:function(){var e=vs(_s)[0],t=L().memoizedState;return[typeof e==`boolean`?e:ms(e),t]},useSyncExternalStore:xs,useId:uc,useHostTransitionStatus:lc,useFormState:Ls,useActionState:Ls,useOptimistic:function(e,t){return Os(L(),P,e,t)},useMemoCache:gs,useCacheRefresh:dc,useEffectEvent:Js},Cc={readContext:Pa,use:hs,useCallback:ec,useContext:Pa,useEffect:Ks,useImperativeHandle:Qs,useInsertionEffect:Ys,useLayoutEffect:Xs,useMemo:tc,useReducer:bs,useRef:Hs,useState:function(){return bs(_s)},useDebugValue:$s,useDeferredValue:function(e,t){var n=L();return P===null?nc(n,e,t):rc(n,P.memoizedState,e,t)},useTransition:function(){var e=bs(_s)[0],t=L().memoizedState;return[typeof e==`boolean`?e:ms(e),t]},useSyncExternalStore:xs,useId:uc,useHostTransitionStatus:lc,useFormState:Bs,useActionState:Bs,useOptimistic:function(e,t){var n=L();return P===null?(n.baseState=e,[e,n.queue.dispatch]):Os(n,P,e,t)},useMemoCache:gs,useCacheRefresh:dc,useEffectEvent:Js};function wc(e,t,n,r){t=e.memoizedState,n=n(r,t),n=n==null?t:w({},t,n),e.memoizedState=n,e.lanes===0&&(e.updateQueue.baseState=n)}var Tc={enqueueSetState:function(e,t,n){e=e._reactInternals;var r=jd(),i=To(r);i.payload=t,n!=null&&(i.callback=n),t=Eo(e,i,r),t!==null&&(Pd(t,e,r),Do(t,e,r))},enqueueReplaceState:function(e,t,n){e=e._reactInternals;var r=jd(),i=To(r);i.tag=1,i.payload=t,n!=null&&(i.callback=n),t=Eo(e,i,r),t!==null&&(Pd(t,e,r),Do(t,e,r))},enqueueForceUpdate:function(e,t){e=e._reactInternals;var n=jd(),r=To(n);r.tag=2,t!=null&&(r.callback=t),t=Eo(e,r,n),t!==null&&(Pd(t,e,n),Do(t,e,n))}};function Ec(e,t,n,r,i,a,o){return e=e.stateNode,typeof e.shouldComponentUpdate==`function`?e.shouldComponentUpdate(r,a,o):t.prototype&&t.prototype.isPureReactComponent?!Qr(n,r)||!Qr(i,a):!0}function Dc(e,t,n,r){e=t.state,typeof t.componentWillReceiveProps==`function`&&t.componentWillReceiveProps(n,r),typeof t.UNSAFE_componentWillReceiveProps==`function`&&t.UNSAFE_componentWillReceiveProps(n,r),t.state!==e&&Tc.enqueueReplaceState(t,t.state,null)}function Oc(e,t){var n=t;if(`ref`in t)for(var r in n={},t)r!==`ref`&&(n[r]=t[r]);if(e=e.defaultProps)for(var i in n===t&&(n=w({},n)),e)n[i]===void 0&&(n[i]=e[i]);return n}function kc(e){Ai(e)}function Ac(e){console.error(e)}function jc(e){Ai(e)}function Mc(e,t){try{var n=e.onUncaughtError;n(t.value,{componentStack:t.stack})}catch(e){setTimeout(function(){throw e})}}function Nc(e,t,n){try{var r=e.onCaughtError;r(n.value,{componentStack:n.stack,errorBoundary:t.tag===1?t.stateNode:null})}catch(e){setTimeout(function(){throw e})}}function Pc(e,t,n){return n=To(n),n.tag=3,n.payload={element:null},n.callback=function(){Mc(e,t)},n}function Fc(e){return e=To(e),e.tag=3,e}function Ic(e,t,n,r){var i=n.type.getDerivedStateFromError;if(typeof i==`function`){var a=r.value;e.payload=function(){return i(a)},e.callback=function(){Nc(t,n,r)}}var o=n.stateNode;o!==null&&typeof o.componentDidCatch==`function`&&(e.callback=function(){Nc(t,n,r),typeof i!=`function`&&(yd===null?yd=new Set([this]):yd.add(this));var e=r.stack;this.componentDidCatch(r.value,{componentStack:e===null?``:e})})}function Lc(e,t,n,r,a){if(n.flags|=32768,typeof r==`object`&&r&&typeof r.then==`function`){if(t=n.alternate,t!==null&&ja(t,n,a,!0),n=zo.current,n!==null){switch(n.tag){case 31:case 13:case 19:return Bo===null?Kd():n.alternate===null&&Y===0&&(Y=3),n.flags&=-257,n.flags|=65536,n.lanes=a,r===oo?n.flags|=16384:(t=n.updateQueue,t===null?n.updateQueue=new Set([r]):t.add(r),mf(e,r,a)),!1;case 22:return n.flags|=65536,r===oo?n.flags|=16384:(t=n.updateQueue,t===null?(t={transitions:null,markerInstances:null,retryQueue:new Set([r])},n.updateQueue=t):(n=t.retryQueue,n===null?t.retryQueue=new Set([r]):n.add(r)),mf(e,r,a)),!1}throw Error(i(435,n.tag))}return mf(e,r,a),Kd(),!1}if(j)return t=zo.current,t===null?(r!==ga&&(t=Error(i(423),{cause:r}),Ca(Qi(t,n))),e=e.current.alternate,e.flags|=65536,a&=-a,e.lanes|=a,r=Qi(r,n),a=Pc(e.stateNode,r,a),Oo(e,a),Y!==4&&(Y=2)):(!(t.flags&65536)&&(t.flags|=256),t.flags|=65536,t.lanes=a,r!==ga&&(e=Error(i(422),{cause:r}),Ca(Qi(e,n)))),!1;var o=Error(i(520),{cause:r});if(o=Qi(o,n),fd===null?fd=[o]:fd.push(o),Y!==4&&(Y=2),t===null)return!0;r=Qi(r,n),n=t;do{switch(n.tag){case 3:return n.flags|=65536,e=a&-a,n.lanes|=e,e=Pc(n.stateNode,r,e),Oo(n,e),!1;case 1:if(t=n.type,o=n.stateNode,!(n.flags&128)&&(typeof t.getDerivedStateFromError==`function`||o!==null&&typeof o.componentDidCatch==`function`&&(yd===null||!yd.has(o))))return n.flags|=65536,a&=-a,n.lanes|=a,a=Fc(a),Ic(a,e,n,r),Oo(n,a),!1;break;case 22:if(n.memoizedState!==null)return n.flags|=65536,!1}n=n.return}while(n!==null);return!1}var Rc=Error(i(461)),R=!1;function z(e,t,n,r){t.child=e===null?xo(t,null,n,r):bo(t,e.child,n,r)}function zc(e,t,n,r,i){n=n.render;var a=t.ref;if(`ref`in r){var o={};for(var s in r)s!==`ref`&&(o[s]=r[s])}else o=r;return Na(t),r=as(e,t,n,o,a,i),s=ls(),e!==null&&!R?(us(e,t,i),pl(e,t,i)):(j&&s&&ua(t),t.flags|=1,z(e,t,r,i),t.child)}function Bc(e,t,n,r,i){if(e===null){var a=n.type;return typeof a==`function`&&!Ui(a)&&a.defaultProps===void 0&&n.compare===null?(t.tag=15,t.type=a,Vc(e,t,a,r,i)):(e=Ki(n.type,null,r,t,t.mode,i),e.ref=t.ref,e.return=t,t.child=e)}if(a=e.child,!ml(e,i)){var o=a.memoizedProps;if(n=n.compare,n=n===null?Qr:n,n(o,r)&&e.ref===t.ref)return pl(e,t,i)}return t.flags|=1,e=Wi(a,r),e.ref=t.ref,e.return=t,t.child=e}function Vc(e,t,n,r,i){if(e!==null){var a=e.memoizedProps;if(Qr(a,r)&&e.ref===t.ref){if(R=!1,t.pendingProps=r=a,ml(e,i))e.flags&131072&&(R=!0);else return t.lanes=e.lanes,pl(e,t,i)}}return Yc(e,t,n,r,i)}function Hc(e,t,n,r){var i=r.children,a=e===null?null:e.memoizedState;if(e===null&&t.stateNode===null&&(t.stateNode={_visibility:1,_pendingMarkers:null,_retryCache:null,_transitions:null}),r.mode===`hidden`){if(t.flags&128){if(a=a===null?n:a.baseLanes|n,e!==null){for(r=t.child=e.child,i=0;r!==null;)i=i|r.lanes|r.childLanes,r=r.sibling;r=i&~a}else r=0,t.child=null;return Wc(e,t,a,n,r)}if(n&536870912)t.memoizedState={baseLanes:0,cachePool:null},e!==null&&to(t,a===null?null:a.cachePool),a===null?Lo():Io(t,a),Uo(t);else return r=t.lanes=536870912,Wc(e,t,a===null?n:a.baseLanes|n,n,r)}else a===null?(e!==null&&to(t,null),Lo(),Wo()):(to(t,a.cachePool),Io(t,a),Wo(),t.memoizedState=null);return z(e,t,i,n),t.child}function Uc(e,t){return e!==null&&e.tag===22||t.stateNode!==null||(t.stateNode={_visibility:1,_pendingMarkers:null,_retryCache:null,_transitions:null}),t.sibling}function Wc(e,t,n,r,i){var a=eo();return a=a===null?null:{parent:M._currentValue,pool:a},t.memoizedState={baseLanes:n,cachePool:a},e!==null&&to(t,null),Lo(),Uo(t),e!==null&&ja(e,t,r,!0),t.childLanes=i,null}function Gc(e,t){return t=il({mode:t.mode,children:t.children},e.mode),t.ref=e.ref,e.child=t,t.return=e,t}function Kc(e,t,n){return bo(t,e.child,null,n),e=Gc(t,t.pendingProps),e.flags|=2,Go(t),t.memoizedState=null,e}function qc(e,t,n){var r=t.pendingProps,a=!!(t.flags&128);if(t.flags&=-129,e===null){if(j){if(r.mode===`hidden`)return e=Gc(t,r),t.lanes=536870912,e.memoizedState={baseLanes:0,cachePool:null},Uc(null,e);if(Ho(t),(e=A)?(e=am(e,ha),e=e!==null&&e.data===`&`?e:null,e!==null&&(t.memoizedState={dehydrated:e,treeContext:aa===null?null:{id:oa,overflow:sa},retryLane:536870912,hydrationErrors:null},n=Yi(e),n.return=t,t.child=n,pa=t,A=null)):e=null,e===null)throw _a(t);return t.lanes=536870912,null}return Gc(t,r)}var o=e.memoizedState;if(o!==null){var s=o.dehydrated;if(Ho(t),a){if(t.flags&256)t.flags&=-257,t=Kc(e,t,n);else if(t.memoizedState!==null)t.child=e.child,t.flags|=128,t=null;else throw Error(i(558))}else if(R||ja(e,t,n,!1),a=(n&e.childLanes)!==0,R||a){if(Po.current===null){if(r=G,r!==null&&(s=Dt(r,n),s!==0&&s!==o.retryLane))throw o.retryLane=s,Li(e,s),Pd(r,e,s),Rc;Kd()}t=Kc(e,t,n)}else e=o.treeContext,A=lm(s.nextSibling),pa=t,j=!0,ma=null,ha=!1,e!==null&&fa(t,e),t=Gc(t,r),t.flags|=134221824;return t}return e=Wi(e.child,{mode:r.mode,children:r.children}),e.ref=t.ref,t.child=e,e.return=t,e}function Jc(e,t){var n=t.ref;if(n===null)e!==null&&e.ref!==null&&(t.flags|=4194816);else{if(typeof n!=`function`&&typeof n!=`object`)throw Error(i(284));(e===null||e.ref!==n)&&(t.flags|=4194816)}}function Yc(e,t,n,r,i){return Na(t),n=as(e,t,n,r,void 0,i),r=ls(),e!==null&&!R?(us(e,t,i),pl(e,t,i)):(j&&r&&ua(t),t.flags|=1,z(e,t,n,i),t.child)}function Xc(e,t,n,r,i,a){return Na(t),t.updateQueue=null,n=ss(t,r,n,i),os(e),r=ls(),e!==null&&!R?(us(e,t,a),pl(e,t,a)):(j&&r&&ua(t),t.flags|=1,z(e,t,n,a),t.child)}function Zc(e,t,n,r,i){if(Na(t),t.stateNode===null){var a=Bi,o=n.contextType;typeof o==`object`&&o&&(a=Pa(o)),a=new n(r,a),t.memoizedState=a.state!==null&&a.state!==void 0?a.state:null,a.updater=Tc,t.stateNode=a,a._reactInternals=t,a=t.stateNode,a.props=r,a.state=t.memoizedState,a.refs={},Co(t),o=n.contextType,a.context=typeof o==`object`&&o?Pa(o):Bi,a.state=t.memoizedState,o=n.getDerivedStateFromProps,typeof o==`function`&&(wc(t,n,o,r),a.state=t.memoizedState),typeof n.getDerivedStateFromProps==`function`||typeof a.getSnapshotBeforeUpdate==`function`||typeof a.UNSAFE_componentWillMount!=`function`&&typeof a.componentWillMount!=`function`||(o=a.state,typeof a.componentWillMount==`function`&&a.componentWillMount(),typeof a.UNSAFE_componentWillMount==`function`&&a.UNSAFE_componentWillMount(),o!==a.state&&Tc.enqueueReplaceState(a,a.state,null),jo(t,r,a,i),Ao(),a.state=t.memoizedState),typeof a.componentDidMount==`function`&&(t.flags|=4194308),r=!0}else if(e===null){a=t.stateNode;var s=t.memoizedProps,c=Oc(n,s);a.props=c;var l=a.context,u=n.contextType;o=Bi,typeof u==`object`&&u&&(o=Pa(u));var d=n.getDerivedStateFromProps;u=typeof d==`function`||typeof a.getSnapshotBeforeUpdate==`function`,s=t.pendingProps!==s,u||typeof a.UNSAFE_componentWillReceiveProps!=`function`&&typeof a.componentWillReceiveProps!=`function`||(s||l!==o)&&Dc(t,a,r,o),So=!1;var f=t.memoizedState;a.state=f,jo(t,r,a,i),Ao(),l=t.memoizedState,s||f!==l||So?(typeof d==`function`&&(wc(t,n,d,r),l=t.memoizedState),(c=So||Ec(t,n,c,r,f,l,o))?(u||typeof a.UNSAFE_componentWillMount!=`function`&&typeof a.componentWillMount!=`function`||(typeof a.componentWillMount==`function`&&a.componentWillMount(),typeof a.UNSAFE_componentWillMount==`function`&&a.UNSAFE_componentWillMount()),typeof a.componentDidMount==`function`&&(t.flags|=4194308)):(typeof a.componentDidMount==`function`&&(t.flags|=4194308),t.memoizedProps=r,t.memoizedState=l),a.props=r,a.state=l,a.context=o,r=c):(typeof a.componentDidMount==`function`&&(t.flags|=4194308),r=!1)}else{a=t.stateNode,wo(e,t),o=t.memoizedProps,u=Oc(n,o),a.props=u,d=t.pendingProps,f=a.context,l=n.contextType,c=Bi,typeof l==`object`&&l&&(c=Pa(l)),s=n.getDerivedStateFromProps,(l=typeof s==`function`||typeof a.getSnapshotBeforeUpdate==`function`)||typeof a.UNSAFE_componentWillReceiveProps!=`function`&&typeof a.componentWillReceiveProps!=`function`||(o!==d||f!==c)&&Dc(t,a,r,c),So=!1,f=t.memoizedState,a.state=f,jo(t,r,a,i),Ao();var p=t.memoizedState;o!==d||f!==p||So||e!==null&&e.dependencies!==null&&Ma(e.dependencies)?(typeof s==`function`&&(wc(t,n,s,r),p=t.memoizedState),(u=So||Ec(t,n,u,r,f,p,c)||e!==null&&e.dependencies!==null&&Ma(e.dependencies))?(l||typeof a.UNSAFE_componentWillUpdate!=`function`&&typeof a.componentWillUpdate!=`function`||(typeof a.componentWillUpdate==`function`&&a.componentWillUpdate(r,p,c),typeof a.UNSAFE_componentWillUpdate==`function`&&a.UNSAFE_componentWillUpdate(r,p,c)),typeof a.componentDidUpdate==`function`&&(t.flags|=4),typeof a.getSnapshotBeforeUpdate==`function`&&(t.flags|=1024)):(typeof a.componentDidUpdate!=`function`||o===e.memoizedProps&&f===e.memoizedState||(t.flags|=4),typeof a.getSnapshotBeforeUpdate!=`function`||o===e.memoizedProps&&f===e.memoizedState||(t.flags|=1024),t.memoizedProps=r,t.memoizedState=p),a.props=r,a.state=p,a.context=c,r=u):(typeof a.componentDidUpdate!=`function`||o===e.memoizedProps&&f===e.memoizedState||(t.flags|=4),typeof a.getSnapshotBeforeUpdate!=`function`||o===e.memoizedProps&&f===e.memoizedState||(t.flags|=1024),r=!1)}return a=r,Jc(e,t),r=!!(t.flags&128),a||r?(a=t.stateNode,n=r&&typeof n.getDerivedStateFromError!=`function`?null:a.render(),t.flags|=1,e!==null&&r?(t.child=bo(t,e.child,null,i),t.child=bo(t,null,n,i)):z(e,t,n,i),t.memoizedState=a.state,e=t.child):e=pl(e,t,i),e}function Qc(e,t,n,r){return xa(),t.flags|=256,z(e,t,n,r),t.child}var $c={dehydrated:null,treeContext:null,retryLane:0,hydrationErrors:null};function el(e){return{baseLanes:e,cachePool:no()}}function tl(e,t,n){return e=e===null?0:e.childLanes&~n,t&&(e|=ud),e}function nl(e,t,n){var r=t.pendingProps,i=!1,a=!!(t.flags&128),o;if((o=a)||(o=e!==null&&e.memoizedState===null?!1:!!(Ko.current&2)),o&&(i=!0,t.flags&=-129),o=!!(t.flags&32),t.flags&=-33,e===null){if(j){if(i?Vo(t):Wo(),(e=A)?(e=am(e,ha),e=e!==null&&e.data!==`&`?e:null,e!==null&&(t.memoizedState={dehydrated:e,treeContext:aa===null?null:{id:oa,overflow:sa},retryLane:536870912,hydrationErrors:null},n=Yi(e),n.return=t,t.child=n,pa=t,A=null)):e=null,e===null)throw _a(t);return t.lanes=sm(e)?32:536870912,null}return a=r.children,r=r.fallback,i?(Wo(),i=t.mode,a=il({mode:`hidden`,children:a},i),r=qi(r,i,n,null),a.return=t,r.return=t,a.sibling=r,t.child=a,r=t.child,r.memoizedState=el(n),r.childLanes=tl(e,o,n),t.memoizedState=$c,Uc(null,r)):(Vo(t),rl(t,a))}var s=e.memoizedState;if(s!==null){var c=s.dehydrated;if(c!==null)return ol(e,t,a,o,r,c,s,n)}return i?(Wo(),i=r.fallback,a=t.mode,s=e.child,c=s.sibling,r=Wi(s,{mode:`hidden`,children:r.children}),r.subtreeFlags=s.subtreeFlags&1206910976,c===null?(i=qi(i,a,n,null),i.flags|=2):i=Wi(c,i),i.return=t,r.return=t,r.sibling=i,t.child=r,Uc(null,r),r=t.child,i=e.child.memoizedState,i===null?i=el(n):(a=i.cachePool,a===null?a=no():(s=M._currentValue,a=a.parent===s?a:{parent:s,pool:s}),i={baseLanes:i.baseLanes|n,cachePool:a}),r.memoizedState=i,r.childLanes=tl(e,o,n),t.memoizedState=$c,Uc(e.child,r)):(Vo(t),n=e.child,e=n.sibling,n=Wi(n,{mode:`visible`,children:r.children}),n.return=t,n.sibling=null,e!==null&&(o=t.deletions,o===null?(t.deletions=[e],t.flags|=16):o.push(e)),t.child=n,t.memoizedState=null,n)}function rl(e,t){return t=il({mode:`visible`,children:t},e.mode),t.return=e,e.child=t}function il(e,t){return e=Hi(22,e,null,t),e.lanes=0,e}function al(e,t,n){return bo(t,e.child,null,n),e=rl(t,t.pendingProps.children),e.flags|=2,t.memoizedState=null,e}function ol(e,t,n,r,a,o,s,c){if(n)return t.flags&256?(Vo(t),t.flags&=-257,al(e,t,c)):t.memoizedState===null?(Wo(),o=a.fallback,s=t.mode,a=il({mode:`visible`,children:a.children},s),o=qi(o,s,c,null),o.flags|=2,a.return=t,o.return=t,a.sibling=o,t.child=a,bo(t,e.child,null,c),a=t.child,a.memoizedState=el(c),a.childLanes=tl(e,r,c),t.memoizedState=$c,Uc(null,a)):(Wo(),t.child=e.child,t.flags|=128,null);if(Vo(t),sm(o)){if(r=o.nextSibling&&o.nextSibling.dataset,r)var l=r.dgst;return r=l,r!==``&&(a=Error(i(419)),a.stack=``,a.digest=r,Ca({value:a,source:null,stack:null})),al(e,t,c)}if(R||ja(e,t,c,!1),r=(c&e.childLanes)!==0,R||r){if(Po.current!==null)return al(e,t,c);if(r=G,r!==null&&(a=Dt(r,c),a!==0&&a!==s.retryLane))throw s.retryLane=a,Li(e,a),Pd(r,e,a),Rc;return om(o)||Kd(),al(e,t,c)}return om(o)?(t.flags|=192,t.child=e.child,null):(e=s.treeContext,A=lm(o.nextSibling),pa=t,j=!0,ma=null,ha=!1,e!==null&&fa(t,e),t=rl(t,a.children),t.flags|=134221824,t)}function sl(e,t,n){e.lanes|=t;var r=e.alternate;r!==null&&(r.lanes|=t),ka(e.return,t,n)}function cl(e){for(var t=null;e!==null;){var n=e.alternate;n!==null&&Yo(n)===null&&(t=e),e=e.sibling}return t}function ll(e,t,n,r,i,a){var o=e.memoizedState;o===null?e.memoizedState={isBackwards:t,rendering:null,renderingStartTime:0,last:r,tail:n,tailMode:i,treeForkCount:a}:(o.isBackwards=t,o.rendering=null,o.renderingStartTime=0,o.last=r,o.tail=n,o.tailMode=i,o.treeForkCount=a)}function ul(e){var t=e.child;for(e.child=null;t!==null;){var n=t.sibling;t.sibling=e.child,e.child=t,t=n}}function dl(e,t,n){var r=t.pendingProps,i=r.revealOrder,a=r.tail;r=r.children;var o=Ko.current;if(t.flags&128)return qo(t,o),null;var s=!!(o&2);if(s?(o=o&1|2,t.flags|=128):o&=1,qo(t,o),i===`backwards`&&e!==null?(ul(e),z(e,t,r,n),ul(e)):z(e,t,r,n),r=j?na:0,!s&&e!==null&&e.flags&128)a:for(e=t.child;e!==null;){if(e.tag===13)e.memoizedState!==null&&sl(e,n,t);else if(e.tag===19)sl(e,n,t);else if(e.child!==null){e.child.return=e,e=e.child;continue}if(e===t)break a;for(;e.sibling===null;){if(e.return===null||e.return===t)break a;e=e.return}e.sibling.return=e.return,e=e.sibling}switch(i){case`backwards`:n=cl(t.child),n===null?(i=t.child,t.child=null):(i=n.sibling,n.sibling=null,ul(t)),ll(t,!0,i,null,a,r);break;case`unstable_legacy-backwards`:for(n=null,i=t.child,t.child=null;i!==null;){if(e=i.alternate,e!==null&&Yo(e)===null){t.child=i;break}e=i.sibling,i.sibling=n,n=i,i=e}ll(t,!0,n,null,a,r);break;case`together`:ll(t,!1,null,null,void 0,r);break;case`independent`:t.memoizedState=null;break;default:n=cl(t.child),n===null?(i=t.child,t.child=null):(i=n.sibling,n.sibling=null),ll(t,!1,i,n,a,r)}return t.child}function fl(e,t,n){var r=t.pendingProps;return Da(t,t.type,r.value),z(e,t,r.children,n),t.child}function pl(e,t,n){if(e!==null&&(t.dependencies=e.dependencies),sd|=t.lanes,(n&t.childLanes)===0){if(e!==null){if(ja(e,t,n,!1),(n&t.childLanes)===0)return null}else return null}if(e!==null&&t.child!==e.child)throw Error(i(153));if(t.child!==null){for(e=t.child,n=Wi(e,e.pendingProps),t.child=n,n.return=t;e.sibling!==null;)e=e.sibling,n=n.sibling=Wi(e,e.pendingProps),n.return=t;n.sibling=null}return t.child}function ml(e,t){return(e.lanes&t)!==0||(e=e.dependencies,!!(e!==null&&Ma(e)))}function hl(e,t,n){switch(t.tag){case 3:Fe(t,t.stateNode.containerInfo),Da(t,M,e.memoizedState.cache),xa();break;case 27:case 5:Le(t);break;case 4:Fe(t,t.stateNode.containerInfo);break;case 10:Da(t,t.type,t.memoizedProps.value);break;case 31:if(t.memoizedState!==null)return t.flags|=128,Ho(t),null;break;case 13:var r=t.memoizedState;if(r!==null){if(r.dehydrated!==null)return Vo(t),t.flags|=128,null;r=ja(e,t,n,!1);var i=t.child.childLanes;return r||(n&i)!==0?nl(e,t,n):(Vo(t),e=pl(e,t,n),e===null?null:e.sibling)}Vo(t);break;case 19:if(t.flags&128)return dl(e,t,n);if(i=!!(e.flags&128),r=(n&t.childLanes)!==0,r||=(ja(e,t,n,!1),(n&t.childLanes)!==0),i){if(r)return dl(e,t,n);t.flags|=128}if(i=t.memoizedState,i!==null&&(i.rendering=null,i.tail=null,i.lastEffect=null),qo(t,Ko.current),r)break;return null;case 22:return t.lanes=0,Hc(e,t,n,t.pendingProps);case 24:Da(t,M,e.memoizedState.cache)}return pl(e,t,n)}function gl(e,t,n){if(e!==null){if(e.memoizedProps!==t.pendingProps)R=!0;else{if(!ml(e,n)&&!(t.flags&128))return R=!1,hl(e,t,n);R=!!(e.flags&131072)}}else R=!1,j&&t.flags&1048576&&la(t,na,t.index);switch(t.lanes=0,t.tag){case 16:a:{var r=t.pendingProps;if(e=lo(t.elementType),t.type=e,typeof e==`function`)Ui(e)?(r=Oc(e,r),t.tag=1,t=Zc(null,t,e,r,n)):(t.tag=0,t=Yc(null,t,e,r,n));else{if(e!=null){var a=e.$$typeof;if(a===de){t.tag=11,t=zc(null,t,e,r,n);break a}if(a===me){t.tag=14,t=Bc(null,t,e,r,n);break a}if(a===ue){t.tag=10,t.type=e,t=fl(null,t,n);break a}}throw t=we(e)||e,Error(i(306,t,``))}}return t;case 0:return Yc(e,t,t.type,t.pendingProps,n);case 1:return r=t.type,a=Oc(r,t.pendingProps),Zc(e,t,r,a,n);case 3:a:{if(Fe(t,t.stateNode.containerInfo),e===null)throw Error(i(387));r=t.pendingProps;var o=t.memoizedState;a=o.element,wo(e,t),jo(t,r,null,n);var s=t.memoizedState;if(r=s.cache,Da(t,M,r),r!==o.cache&&Aa(t,[M],n,!0),Ao(),r=s.element,o.isDehydrated){if(o={element:r,isDehydrated:!1,cache:s.cache},t.updateQueue.baseState=o,t.memoizedState=o,t.flags&256){t=Qc(e,t,r,n);break a}if(r!==a){a=Qi(Error(i(424)),t),Ca(a),t=Qc(e,t,r,n);break a}switch(e=t.stateNode.containerInfo,e.nodeType){case 9:e=e.body;break;default:e=e.nodeName===`HTML`?e.ownerDocument.body:e}for(A=lm(e.firstChild),pa=t,j=!0,ma=null,ha=!0,n=xo(t,null,r,n),t.child=n;n;)n.flags=n.flags&-3|134221824,n=n.sibling}else{if(xa(),r===a){t=pl(e,t,n);break a}z(e,t,r,n)}t=t.child}return t;case 26:return Jc(e,t),e===null?(n=Nm(t.type,null,t.pendingProps,null))?t.memoizedState=n:j||(t.stateNode=fp(t.type,t.pendingProps,Ne.current,t)):t.memoizedState=Nm(t.type,e.memoizedProps,t.pendingProps,e.memoizedState),null;case 27:return Le(t),e===null&&j&&(r=t.stateNode=hm(t.type,t.pendingProps,Ne.current),pa=t,ha=!0,a=A,Sp(t.type)?(um=a,A=lm(r.firstChild)):A=a),z(e,t,t.pendingProps.children,n),Jc(e,t),e===null&&(t.flags|=4194304),t.child;case 5:return e===null&&j&&((a=r=A)&&(r=rm(r,t.type,t.pendingProps,ha),r===null?a=!1:(t.stateNode=r,pa=t,A=lm(r.firstChild),ha=!1,a=!0)),a||_a(t)),Le(t),a=t.type,o=t.pendingProps,s=e===null?null:e.memoizedProps,r=o.children,pp(a,o)?r=null:s!==null&&pp(a,s)&&(t.flags|=32),t.memoizedState!==null&&(a=as(e,t,cs,null,null,n),sh._currentValue=a),Jc(e,t),z(e,t,r,n),t.child;case 6:return e===null&&j&&((e=n=A)&&(n=im(n,t.pendingProps,ha),n===null?e=!1:(t.stateNode=n,pa=t,A=null,e=!0)),e||_a(t)),null;case 13:return nl(e,t,n);case 4:return Fe(t,t.stateNode.containerInfo),r=t.pendingProps,e===null?t.child=bo(t,null,r,n):z(e,t,r,n),t.child;case 11:return zc(e,t,t.type,t.pendingProps,n);case 7:return r=t.pendingProps,Jc(e,t),z(e,t,r,n),t.child;case 8:return z(e,t,t.pendingProps.children,n),t.child;case 12:return z(e,t,t.pendingProps.children,n),t.child;case 10:return fl(e,t,n);case 9:return a=t.type._context,r=t.pendingProps.children,Na(t),a=Pa(a),r=r(a),t.flags|=1,z(e,t,r,n),t.child;case 14:return Bc(e,t,t.type,t.pendingProps,n);case 15:return Vc(e,t,t.type,t.pendingProps,n);case 19:return dl(e,t,n);case 31:return qc(e,t,n);case 22:return Hc(e,t,n,t.pendingProps);case 24:return Na(t),r=Pa(M),e===null?(a=eo(),a===null&&(a=G,o=Ba(),a.pooledCache=o,o.refCount++,o!==null&&(a.pooledCacheLanes|=n),a=o),t.memoizedState={parent:r,cache:a},Co(t),Da(t,M,a)):((e.lanes&n)!==0&&(wo(e,t),jo(t,null,null,n),Ao()),a=e.memoizedState,o=t.memoizedState,a.parent===r?(r=o.cache,Da(t,M,r),r!==a.cache&&Aa(t,[M],n,!0)):(a={parent:r,cache:r},t.memoizedState=a,t.lanes===0&&(t.memoizedState=t.updateQueue.baseState=a),Da(t,M,r))),z(e,t,t.pendingProps.children,n),t.child;case 30:return t.stateNode===null&&(t.stateNode={autoName:null,paired:null,clones:null,ref:null}),r=t.pendingProps,r.name!=null&&r.name!==`auto`?t.flags|=e===null?18882560:18874368:j&&ua(t),e!==null&&e.memoizedProps.name!==r.name?t.flags|=4194816:Jc(e,t),z(e,t,r.children,n),t.child;case 29:throw t.pendingProps}throw Error(i(156,t.tag))}function _l(e){e.flags|=4}function vl(e,t,n,r,i){var a;if((a=!!(e.mode&32))&&(a=n===null?Jm(t,r):Jm(t,r)&&(r.src!==n.src||r.srcSet!==n.srcSet)),a){if(e.flags|=16777216,(i&335544128)===i){if(e.stateNode.complete)e.flags|=8192;else if(Ud())e.flags|=8192;else throw uo=oo,io}}else e.flags&=-16777217}function yl(e,t){if(t.type!==`stylesheet`||t.state.loading&4)e.flags&=-16777217;else if(e.flags|=16777216,!Ym(t)){if(Ud())e.flags|=8192;else throw uo=oo,io}}function bl(e,t){t!==null&&(e.flags|=4),e.flags&16384&&(t=e.tag===22?536870912:xt(),e.lanes|=t,dd|=t)}function xl(e,t){if(!j)switch(e.tailMode){case`visible`:break;case`collapsed`:for(var n=e.tail,r=null;n!==null;)n.alternate!==null&&(r=n),n=n.sibling;r===null?t||e.tail===null?e.tail=null:e.tail.sibling=null:r.sibling=null;break;default:for(t=e.tail,n=null;t!==null;)t.alternate!==null&&(n=t),t=t.sibling;n===null?e.tail=null:n.sibling=null}}function B(e){var t=e.alternate!==null&&e.alternate.child===e.child,n=0,r=0;if(t)for(var i=e.child;i!==null;)n|=i.lanes|i.childLanes,r|=i.subtreeFlags&1206910976,r|=i.flags&1206910976,i.return=e,i=i.sibling;else for(i=e.child;i!==null;)n|=i.lanes|i.childLanes,r|=i.subtreeFlags,r|=i.flags,i.return=e,i=i.sibling;return e.subtreeFlags|=r,e.childLanes=n,t}function Sl(e,t,n){var r=t.pendingProps;switch(da(t),t.tag){case 16:case 15:case 0:case 11:case 7:case 8:case 12:case 9:case 14:return B(t),null;case 1:return B(t),null;case 3:return n=t.stateNode,r=null,e!==null&&(r=e.memoizedState.cache),t.memoizedState.cache!==r&&(t.flags|=2048),Oa(M),Ie(),n.pendingContext&&(n.context=n.pendingContext,n.pendingContext=null),(e===null||e.child===null)&&(ba(t)?_l(t):e===null||e.memoizedState.isDehydrated&&!(t.flags&256)||(t.flags|=1024,Sa())),B(t),null;case 26:var a=t.type,o=t.memoizedState;return e===null?(_l(t),o===null?(B(t),vl(t,a,null,r,n)):(B(t),yl(t,o))):o?o===e.memoizedState?(B(t),t.flags&=-16777217):(_l(t),B(t),yl(t,o)):(e=e.memoizedProps,e!==r&&_l(t),B(t),vl(t,a,e,r,n)),null;case 27:if(Re(t),n=Ne.current,a=t.type,e!==null&&t.stateNode!=null)e.memoizedProps!==r&&_l(t);else{if(!r){if(t.stateNode===null)throw Error(i(166));return B(t),t.subtreeFlags&=-33554433,null}e=je.current,ba(t)?va(t,e):(e=hm(a,r,n),t.stateNode=e,_l(t))}return B(t),t.subtreeFlags&=-33554433,null;case 5:if(Re(t),a=t.type,e!==null&&t.stateNode!=null)e.memoizedProps!==r&&_l(t);else{if(!r){if(t.stateNode===null)throw Error(i(166));return B(t),t.subtreeFlags&=-33554433,null}if(o=je.current,ba(t))va(t,o);else{var s=lp(Ne.current);switch(o){case 1:o=s.createElementNS(`http://www.w3.org/2000/svg`,a);break;case 2:o=s.createElementNS(`http://www.w3.org/1998/Math/MathML`,a);break;default:switch(a){case`svg`:o=s.createElementNS(`http://www.w3.org/2000/svg`,a);break;case`math`:o=s.createElementNS(`http://www.w3.org/1998/Math/MathML`,a);break;case`script`:o=s.createElement(`div`),o.innerHTML=`<script><\/script>`,o=o.removeChild(o.firstChild);break;case`select`:o=typeof r.is==`string`?s.createElement(`select`,{is:r.is}):s.createElement(`select`),r.multiple?o.multiple=!0:r.size&&(o.size=r.size);break;default:o=typeof r.is==`string`?s.createElement(a,{is:r.is}):s.createElement(a)}}o[Nt]=t,o[Pt]=r;a:for(s=t.child;s!==null;){if(s.tag===5||s.tag===6)o.appendChild(s.stateNode);else if(s.tag!==4&&s.tag!==27&&s.child!==null){s.child.return=s,s=s.child;continue}if(s===t)break a;for(;s.sibling===null;){if(s.return===null||s.return===t)break a;s=s.return}s.sibling.return=s.return,s=s.sibling}t.stateNode=o;a:switch(np(o,a,r),a){case`button`:case`input`:case`select`:case`textarea`:r=!!r.autoFocus;break a;case`img`:r=!0;break a;default:r=!1}r&&_l(t)}}return B(t),t.subtreeFlags&=-33554433,vl(t,t.type,e===null?null:e.memoizedProps,t.pendingProps,n),null;case 6:if(e&&t.stateNode!=null)e.memoizedProps!==r&&_l(t);else{if(typeof r!=`string`&&t.stateNode===null)throw Error(i(166));if(e=Ne.current,ba(t)){if(e=t.stateNode,n=t.memoizedProps,r=null,a=pa,a!==null)switch(a.tag){case 27:case 5:r=a.memoizedProps}e[Nt]=t,e=!!(e.nodeValue===n||r!==null&&!0===r.suppressHydrationWarning||ep(e.nodeValue,n)),e||_a(t,!0)}else e=lp(e).createTextNode(r),e[Nt]=t,t.stateNode=e}return B(t),null;case 31:if(n=t.memoizedState,e===null||e.memoizedState!==null){if(r=ba(t),n!==null){if(e===null){if(!r)throw Error(i(318));if(e=t.memoizedState,e=e===null?null:e.dehydrated,!e)throw Error(i(557));e[Nt]=t}else xa(),!(t.flags&128)&&(t.memoizedState=null),t.flags|=4;B(t),e=!1}else n=Sa(),e!==null&&e.memoizedState!==null&&(e.memoizedState.hydrationErrors=n),e=!0;if(!e)return t.flags&256?(Go(t),t):(Go(t),null);if(t.flags&128)throw Error(i(558))}return B(t),null;case 13:if(r=t.memoizedState,e===null||e.memoizedState!==null&&e.memoizedState.dehydrated!==null){if(a=ba(t),r!==null&&r.dehydrated!==null){if(e===null){if(!a)throw Error(i(318));if(a=t.memoizedState,a=a===null?null:a.dehydrated,!a)throw Error(i(317));a[Nt]=t}else xa(),!(t.flags&128)&&(t.memoizedState=null),t.flags|=4;B(t),a=!1}else a=Sa(),e!==null&&e.memoizedState!==null&&(e.memoizedState.hydrationErrors=a),a=!0;if(!a)return t.flags&256?(Go(t),t):(Go(t),null)}return Go(t),t.flags&128?(t.lanes=n,t):(n=r!==null,e=e!==null&&e.memoizedState!==null,n&&(r=t.child,a=null,r.alternate!==null&&r.alternate.memoizedState!==null&&r.alternate.memoizedState.cachePool!==null&&(a=r.alternate.memoizedState.cachePool.pool),o=null,r.memoizedState!==null&&r.memoizedState.cachePool!==null&&(o=r.memoizedState.cachePool.pool),o!==a&&(r.flags|=2048)),n!==e&&n&&(t.child.flags|=8192),bl(t,t.updateQueue),B(t),null);case 4:return Ie(),e===null&&Wf(t.stateNode.containerInfo),t.flags|=67108864,B(t),null;case 10:return Oa(t.type),B(t),null;case 19:if(Jo(t),r=t.memoizedState,r===null)return B(t),null;if(a=!!(t.flags&128),o=r.rendering,o===null){if(a)xl(r,!1);else{if(Y!==0||e!==null&&e.flags&128)for(e=t.child;e!==null;){if(o=Yo(e),o!==null){for(t.flags|=128,xl(r,!1),e=o.updateQueue,t.updateQueue=e,bl(t,e),t.subtreeFlags=0,e=n,n=t.child;n!==null;)Gi(n,e),n=n.sibling;return qo(t,Ko.current&1|2),j&&ca(t,r.treeForkCount),t.child}e=e.sibling}r.tail!==null&&Ze()>_d&&(t.flags|=128,a=!0,xl(r,!1),t.lanes=4194304)}}else{if(!a){if(e=Yo(o),e!==null){if(t.flags|=128,a=!0,e=e.updateQueue,t.updateQueue=e,bl(t,e),xl(r,!0),r.tail===null&&r.tailMode!==`collapsed`&&r.tailMode!==`visible`&&!o.alternate&&!j)return B(t),null}else 2*Ze()-r.renderingStartTime>_d&&n!==536870912&&(t.flags|=128,a=!0,xl(r,!1),t.lanes=4194304)}r.isBackwards?(o.sibling=t.child,t.child=o):(e=r.last,e===null?t.child=o:e.sibling=o,r.last=o)}if(r.tail!==null){e=r.tail;a:{for(n=e;n!==null;){if(n.alternate!==null){n=!1;break a}n=n.sibling}n=!0}return r.rendering=e,r.tail=e.sibling,r.renderingStartTime=Ze(),e.sibling=null,o=Ko.current,o=a?o&1|2:o&1,r.tailMode===`visible`||r.tailMode===`collapsed`||!n||j?qo(t,o):(n=o,D(zo,t),D(Ko,n),Bo===null&&(Bo=t)),j&&ca(t,r.treeForkCount),e}return B(t),null;case 22:case 23:return Go(t),Ro(),r=t.memoizedState!==null,e===null?r&&(t.flags|=8192):e.memoizedState!==null!==r&&(t.flags|=8192),r?n&536870912&&!(t.flags&128)&&(B(t),t.subtreeFlags&6&&(t.flags|=8192)):B(t),n=t.updateQueue,n!==null&&bl(t,n.retryQueue),n=null,e!==null&&e.memoizedState!==null&&e.memoizedState.cachePool!==null&&(n=e.memoizedState.cachePool.pool),r=null,t.memoizedState!==null&&t.memoizedState.cachePool!==null&&(r=t.memoizedState.cachePool.pool),r!==n&&(t.flags|=2048),e!==null&&Ae($a),null;case 24:return n=null,e!==null&&(n=e.memoizedState.cache),t.memoizedState.cache!==n&&(t.flags|=2048),Oa(M),B(t),null;case 25:return null;case 30:return t.flags|=33554432,B(t),null}throw Error(i(156,t.tag))}function Cl(e,t){switch(da(t),t.tag){case 1:return e=t.flags,e&65536?(t.flags=e&-65537|128,t):null;case 3:return Oa(M),Ie(),e=t.flags,e&65536&&!(e&128)?(t.flags=e&-65537|128,t):null;case 26:case 27:case 5:return Re(t),null;case 31:if(t.memoizedState!==null){if(Go(t),t.alternate===null)throw Error(i(340));xa()}return e=t.flags,e&65536?(t.flags=e&-65537|128,t):null;case 13:if(Go(t),e=t.memoizedState,e!==null&&e.dehydrated!==null){if(t.alternate===null)throw Error(i(340));xa()}return e=t.flags,e&65536?(t.flags=e&-65537|128,t):null;case 19:return Jo(t),e=t.flags,e&65536?(t.flags=e&-65537|128,e=t.memoizedState,e!==null&&(e.rendering=null,e.tail=null),t.flags|=4,t):null;case 4:return Ie(),null;case 10:return Oa(t.type),null;case 22:case 23:return Go(t),Ro(),e!==null&&Ae($a),e=t.flags,e&65536?(t.flags=e&-65537|128,t):null;case 24:return Oa(M),null;case 25:return null;default:return null}}function wl(e,t){switch(da(t),t.tag){case 3:Oa(M),Ie();break;case 26:case 27:case 5:Re(t);break;case 4:Ie();break;case 31:t.memoizedState!==null&&Go(t);break;case 13:Go(t);break;case 19:Jo(t);break;case 10:Oa(t.type);break;case 22:case 23:Go(t),Ro(),e!==null&&Ae($a);break;case 24:Oa(M)}}function Tl(e,t){try{var n=t.updateQueue,r=n===null?null:n.lastEffect;if(r!==null){var i=r.next;n=i;do{if((n.tag&e)===e){r=void 0;var a=n.create,o=n.inst;r=a(),o.destroy=r}n=n.next}while(n!==i)}}catch(e){Z(t,t.return,e)}}function El(e,t,n){try{var r=t.updateQueue,i=r===null?null:r.lastEffect;if(i!==null){var a=i.next;r=a;do{if((r.tag&e)===e){var o=r.inst,s=o.destroy;if(s!==void 0){o.destroy=void 0,i=t;var c=n,l=s;try{l()}catch(e){Z(i,c,e)}}}r=r.next}while(r!==a)}}catch(e){Z(t,t.return,e)}}function Dl(e){var t=e.updateQueue;if(t!==null){var n=e.stateNode;try{No(t,n)}catch(t){Z(e,e.return,t)}}}function Ol(e,t,n){n.props=Oc(e.type,e.memoizedProps),n.state=e.memoizedState;try{n.componentWillUnmount()}catch(n){Z(e,t,n)}}function kl(e,t){try{var n=e.ref;if(n!==null){switch(e.tag){case 26:case 27:case 5:var r=e.stateNode;break;case 30:var i=e.stateNode,a=Di(e.memoizedProps,i);(i.ref===null||i.ref.name!==a)&&(i.ref=Pp(a)),r=i.ref;break;case 7:if(e.stateNode===null){var o=new Fp(e);h(e.child,!1,Qp,o,void 0,void 0),e.stateNode=o}r=e.stateNode;break;default:r=e.stateNode}typeof n==`function`?e.refCleanup=n(r):n.current=r}}catch(n){Z(e,t,n)}}function Al(e,t){var n=e.ref,r=e.refCleanup;if(n!==null){if(typeof r==`function`)try{r()}catch(n){Z(e,t,n)}finally{e.refCleanup=null,e=e.alternate,e!=null&&(e.refCleanup=null)}else if(typeof n==`function`)try{n(null)}catch(n){Z(e,t,n)}else n.current=null}}function jl(e,t){if((e.tag===5||e.tag===27||e.tag===6)&&e.alternate===null&&t!==null)for(var n=0;n<t.length;n++)em(e.stateNode,t[n])}function Ml(e){for(var t=e.return;t!==null&&(Fl(t)&&em(e.stateNode,t.stateNode),!Pl(t));)t=t.return}function Nl(e){for(var t=e.return;t!==null&&(Fl(t)&&tm(e.stateNode,t.stateNode),!Pl(t));)t=t.return}function Pl(e){return e.tag===5||e.tag===3||e.tag===27}function Fl(e){return e&&e.tag===7&&e.stateNode!==null}function Il(e){var t=e.type,n=e.memoizedProps,r=e.stateNode;try{a:switch(t){case`button`:case`input`:case`select`:case`textarea`:n.autoFocus&&r.focus();break a;case`img`:n.src?r.src=n.src:n.srcSet&&(r.srcset=n.srcSet)}}catch(t){Z(e,e.return,t)}}function Ll(e,t,n){try{var r=e.stateNode;ip(r,e.type,n,t),r[Pt]=t}catch(t){Z(e,e.return,t)}}function Rl(e){return e.tag===5||e.tag===3||e.tag===26||e.tag===27&&Sp(e.type)||e.tag===4}function zl(e){a:for(;;){for(;e.sibling===null;){if(e.return===null||Rl(e.return))return null;e=e.return}for(e.sibling.return=e.return,e=e.sibling;e.tag!==5&&e.tag!==6&&e.tag!==18;){if(e.tag===27&&Sp(e.type)||e.flags&2||e.child===null||e.tag===4)continue a;e.child.return=e,e=e.child}if(!(e.flags&2))return e.stateNode}}function Bl(e,t,n,r){var i=e.tag;if(i===5||i===6)i=e.stateNode,t?(n.nodeType===9?n.body:n.nodeName===`HTML`?n.ownerDocument.body:n).insertBefore(i,t):(t=n.nodeType===9?n.body:n.nodeName===`HTML`?n.ownerDocument.body:n,t.appendChild(i),n=n._reactRootContainer,n!=null||t.onclick!==null||(t.onclick=On)),jl(e,r),k=!0;else if(i!==4&&(i===27&&(jl(e,r),r=null,Sp(e.type)&&(n=e.stateNode,t=null)),e=e.child,e!==null))for(Bl(e,t,n,r),e=e.sibling;e!==null;)Bl(e,t,n,r),e=e.sibling}function Vl(e,t,n,r){var i=e.tag;if(i===5||i===6)i=e.stateNode,t?n.insertBefore(i,t):n.appendChild(i),jl(e,r),k=!0;else if(i!==4&&(i===27&&(jl(e,r),r=null,Sp(e.type)&&(n=e.stateNode)),e=e.child,e!==null))for(Vl(e,t,n,r),e=e.sibling;e!==null;)Vl(e,t,n,r),e=e.sibling}function Hl(e){var t=e.stateNode,n=e.memoizedProps;try{for(var r=e.type,i=t.attributes;i.length;)t.removeAttributeNode(i[0]);np(t,r,n),t[Nt]=e,t[Pt]=n}catch(t){Z(e,e.return,t)}}var Ul=!1,Wl=null;function Gl(e){(e.tag===30||e.subtreeFlags&33554432)&&(Ul=!0)}var Kl=null;function ql(){var e=Kl;return Kl=null,e}var Jl=0;function Yl(e,t,n,r,i){return Jl=0,Xl(e.child,t,n,r,i)}function Xl(e,t,n,r,i){for(var a=!1;e!==null;){if(e.tag===5){var o=e.stateNode;if(r!==null){var s=Op(o);r.push(s),s.view&&(a=!0)}else a||Op(o).view&&(a=!0);Ul=!0,Tp(o,Jl===0?t:t+`_`+Jl,n),Jl++}else(e.tag!==22||e.memoizedState===null)&&(e.tag===30&&i||Xl(e.child,t,n,r,i)&&(a=!0));e=e.sibling}return a}function Zl(e,t){for(;e!==null;)e.tag===5?Ep(e.stateNode,e.memoizedProps):(e.tag!==22||e.memoizedState===null)&&(e.tag===30&&t||Zl(e.child,t)),e=e.sibling}function Ql(e){if(e.subtreeFlags&18874368)for(e=e.child;e!==null;){if((e.tag!==22||e.memoizedState===null)&&(Ql(e),e.tag===30&&e.flags&18874368&&e.stateNode.paired)){var t=e.memoizedProps;if(t.name==null||t.name===`auto`)throw Error(i(544));var n=t.name;t=ki(t.default,t.share),t!==`none`&&(Yl(e,n,t,null,!1)||Zl(e.child,!1))}e=e.sibling}}function $l(e,t){if(e.tag===30){var n=e.stateNode,r=e.memoizedProps,i=Di(r,n),a=ki(r.default,n.paired?r.share:r.enter);a===`none`?Ql(e):Yl(e,i,a,null,!1)?(Ql(e),n.paired||t||Nd(e,r.onEnter)):Zl(e.child,!1)}else if(e.subtreeFlags&33554432)for(e=e.child;e!==null;)$l(e,t),e=e.sibling;else Ql(e)}function eu(e){if(Wl!==null&&Wl.size!==0){var t=Wl;if(e.subtreeFlags&18874368)for(e=e.child;e!==null;){if(e.tag!==22||e.memoizedState===null){if(e.tag===30&&e.flags&18874368){var n=e.memoizedProps,r=n.name;if(r!=null&&r!==`auto`){var i=t.get(r);if(i!==void 0){var a=ki(n.default,n.share);if(a!==`none`&&(Yl(e,r,a,null,!1)?(a=e.stateNode,i.paired=a,a.paired=i,Nd(e,n.onShare)):Zl(e.child,!1)),t.delete(r),t.size===0)break}}}eu(e)}e=e.sibling}}}function tu(e){if(e.tag===30){var t=e.memoizedProps,n=Di(t,e.stateNode),r=Wl===null?void 0:Wl.get(n),i=ki(t.default,r===void 0?t.exit:t.share);i!==`none`&&(Yl(e,n,i,null,!1)?r===void 0?Nd(e,t.onExit):(i=e.stateNode,r.paired=i,i.paired=r,Wl.delete(n),Nd(e,t.onShare)):Zl(e.child,!1)),Wl!==null&&eu(e)}else if(e.subtreeFlags&33554432)for(e=e.child;e!==null;)tu(e),e=e.sibling;else Wl!==null&&eu(e)}function nu(e){for(e=e.child;e!==null;){if(e.tag===30){var t=e.memoizedProps,n=Di(t,e.stateNode);t=ki(t.default,t.update),e.flags&=-5,t!==`none`&&Yl(e,n,t,e.memoizedState=[],!1)}else e.subtreeFlags&33554432&&nu(e);e=e.sibling}}function ru(e){if(e.subtreeFlags&18874368)for(e=e.child;e!==null;){if(e.tag!==22||e.memoizedState===null){if(e.tag===30&&e.flags&18874368){var t=e.stateNode;t.paired!==null&&(t.paired=null,Zl(e.child,!1))}ru(e)}e=e.sibling}}function iu(e){if(e.tag===30)e.stateNode.paired=null,Zl(e.child,!1),ru(e);else if(e.subtreeFlags&33554432)for(e=e.child;e!==null;)iu(e),e=e.sibling;else ru(e)}function au(e){for(e=e.child;e!==null;)e.tag===30?Zl(e.child,!1):e.subtreeFlags&33554432&&au(e),e=e.sibling}function ou(e,t,n,r,i,a,o){for(var s=!1;t!==null;){if(t.tag===5){var c=t.stateNode;if(a!==null&&Jl<a.length){var l=a[Jl],u=Op(c);(l.view||u.view)&&(s=!0);var d;if(d=!(e.flags&4)){if(u.clip)d=!0;else{d=l.rect;var f=u.rect;d=d.y!==f.y||d.x!==f.x||d.height!==f.height||d.width!==f.width}}d&&(e.flags|=4),u.abs?u=!l.abs:(l=l.rect,u=u.rect,u=l.height!==u.height||l.width!==u.width),u&&(e.flags|=32)}else e.flags|=32;e.flags&4&&Tp(c,Jl===0?n:n+`_`+Jl,i),s&&e.flags&4||(Kl===null&&(Kl=[]),Kl.push(c,Jl===0?r:r+`_`+Jl,t.memoizedProps)),Jl++}else(t.tag!==22||t.memoizedState===null)&&(t.tag===30&&o?e.flags|=t.flags&32:ou(e,t.child,n,r,i,a,o)&&(s=!0));t=t.sibling}return s}function su(e,t){for(e=e.child;e!==null;){if(e.tag===30){var n=e.memoizedProps,r=e.stateNode,i=Di(n,r),a=ki(n.default,n.update);if(t){r=r.clones;var o=r===null?null:r.map(kp)}else o=e.memoizedState,e.memoizedState=null;r=e;var s=e.child;Jl=0,i=ou(r,s,i,i,a,o,!1),e.flags&4&&i&&(t||Nd(e,n.onUpdate))}else e.subtreeFlags&33554432&&su(e,t);e=e.sibling}}var V=!1,H=!1,cu=!1,lu=!1,uu=typeof WeakSet==`function`?WeakSet:Set,du=null,fu=!1,pu=!1,mu=!1,hu=!1;function gu(e,t,n){if(e=e.containerInfo,sp=gh,e=ri(e),ii(e)){if(`selectionStart`in e)var r={start:e.selectionStart,end:e.selectionEnd};else a:{r=(r=e.ownerDocument)&&r.defaultView||window;var i=r.getSelection&&r.getSelection();if(i&&i.rangeCount!==0){r=i.anchorNode;var a=i.anchorOffset,o=i.focusNode;i=i.focusOffset;try{r.nodeType,o.nodeType}catch{r=null;break a}var s=0,c=-1,l=-1,u=0,d=0,f=e,p=null;b:for(;;){for(var m;f!==r||a!==0&&f.nodeType!==3||(c=s+a),f!==o||i!==0&&f.nodeType!==3||(l=s+i),f.nodeType===3&&(s+=f.nodeValue.length),(m=f.firstChild)!==null;)p=f,f=m;for(;;){if(f===e)break b;if(p===r&&++u===a&&(c=s),p===o&&++d===i&&(l=s),(m=f.nextSibling)!==null)break;f=p,p=f.parentNode}f=m}r=c===-1||l===-1?null:{start:c,end:l}}else r=null}r||={start:0,end:0}}else r=null;for(cp={focusedElem:e,selectionRange:r},gh=!1,n=(n&335544064)===n,du=t,t=n?9270:1024;du!==null;){if(e=du,n&&(r=e.deletions,r!==null))for(a=0;a<r.length;a++)n&&tu(r[a]);if(e.alternate===null&&e.flags&2)n&&Gl(e),_u(n);else{if(e.tag===22){if(r=e.alternate,e.memoizedState!==null){r!==null&&r.memoizedState===null&&n&&tu(r),_u(n);continue}if(r!==null&&r.memoizedState!==null){n&&Gl(e),_u(n);continue}}r=e.child,(e.subtreeFlags&t)!==0&&r!==null?(r.return=e,du=r):(n&&nu(e),_u(n))}}Wl=null}function _u(e){for(;du!==null;){var t=du,n=e,r=t.alternate,a=t.flags;switch(t.tag){case 0:case 11:case 15:break;case 1:if(a&1024&&r!==null){n=void 0,a=r.memoizedProps,r=r.memoizedState;var o=t.stateNode;try{var s=Oc(t.type,a);n=o.getSnapshotBeforeUpdate(s,r),o.__reactInternalSnapshotBeforeUpdate=n}catch(e){Z(t,t.return,e)}}break;case 3:if(a&1024){if(r=t.stateNode.containerInfo,n=r.nodeType,n===9)nm(r);else if(n===1)switch(r.nodeName){case`HEAD`:case`HTML`:case`BODY`:nm(r);break;default:r.textContent=``}}break;case 5:case 26:case 27:case 6:case 4:case 17:break;case 30:n&&r!==null&&(n=Di(r.memoizedProps,r.stateNode),a=t.memoizedProps,a=ki(a.default,a.update),a!==`none`&&Yl(r,n,a,r.memoizedState=[],!0));break;default:if(a&1024)throw Error(i(163))}if(r=t.sibling,r!==null){r.return=t.return,du=r;break}du=t.return}}function vu(e,t,n){var r=n.flags;switch(n.tag){case 0:case 11:case 15:Lu(e,n),r&4&&Tl(5,n);break;case 1:if(Lu(e,n),r&4){if(e=n.stateNode,t===null)try{e.componentDidMount()}catch(e){Z(n,n.return,e)}else{var i=Oc(n.type,t.memoizedProps);t=t.memoizedState;try{e.componentDidUpdate(i,t,e.__reactInternalSnapshotBeforeUpdate)}catch(e){Z(n,n.return,e)}}}r&64&&Dl(n),r&512&&kl(n,n.return);break;case 3:if(Lu(e,n),r&64&&(e=n.updateQueue,e!==null)){if(t=null,n.child!==null)switch(n.child.tag){case 27:case 5:t=n.child.stateNode;break;case 1:t=n.child.stateNode}try{No(e,t)}catch(e){Z(n,n.return,e)}}break;case 27:t===null&&r&4&&Hl(n);case 26:case 5:Lu(e,n),t===null&&r&4&&Il(n),r&512&&kl(n,n.return);break;case 12:Lu(e,n);break;case 31:Lu(e,n),r&4&&Eu(e,n);break;case 13:Lu(e,n),r&4&&Du(e,n),r&64&&(e=n.memoizedState,e!==null&&(e=e.dehydrated,e!==null&&(n=_f.bind(null,n),cm(e,n))));break;case 22:if(r=n.memoizedState!==null||V,!r){var a=t!==null&&t.memoizedState!==null||H;t=V,i=H,V=r,(H=a)&&!i?(r=2,n.subtreeFlags&8772&&(r|=1),zu(e,n,r)):Lu(e,n),V=t,H=i}break;case 30:Lu(e,n),r&512&&kl(n,n.return);break;case 7:r&512&&kl(n,n.return);default:Lu(e,n)}}function yu(e,t){for(e=e.child;e!==null;)bu(e,t),e=e.sibling}function bu(e,t){switch(e.tag){case 5:case 26:try{var n=e.stateNode;if(t){var r=n.style;typeof r.setProperty==`function`?r.setProperty(`display`,`none`,`important`):r.display=`none`}else{var i=e.stateNode,a=e.memoizedProps.style,o=a!=null&&a.hasOwnProperty(`display`)?a.display:null;i.style.display=o==null||typeof o==`boolean`?``:(``+o).trim()}}catch(t){Z(e,e.return,t)}xu(e,t);break;case 6:try{e.stateNode.nodeValue=t?``:e.memoizedProps,k=!0}catch(t){Z(e,e.return,t)}break;case 18:try{var s=e.stateNode;t?wp(s,!0):wp(e.stateNode,!1)}catch(t){Z(e,e.return,t)}break;case 22:case 23:e.memoizedState===null&&yu(e,t);break;default:yu(e,t)}}function xu(e,t){if(e.subtreeFlags&67108864)for(e=e.child;e!==null;){a:{var n=e,r=t;switch(n.tag){case 4:bu(n,r);break a;case 22:n.memoizedState===null&&xu(n,r);break a;default:xu(n,r)}}e=e.sibling}}function Su(e){var t=e.alternate;t!==null&&(e.alternate=null,Su(t)),e.child=null,e.deletions=null,e.sibling=null,e.tag===5&&(t=e.stateNode,t!==null&&Ht(t)),e.stateNode=null,e.return=null,e.dependencies=null,e.memoizedProps=null,e.memoizedState=null,e.pendingProps=null,e.stateNode=null,e.updateQueue=null}var U=null,Cu=!1;function wu(e,t,n){for(n=n.child;n!==null;)Tu(e,t,n),n=n.sibling}function Tu(e,t,n){if(st&&typeof st.onCommitFiberUnmount==`function`)try{st.onCommitFiberUnmount(ot,n)}catch{}switch(n.tag){case 26:H||Al(n,t),wu(e,t,n),n.memoizedState?n.memoizedState.count--:n.stateNode&&!H&&(n=n.stateNode,n.parentNode.removeChild(n));break;case 27:H||Al(n,t),Nl(n);var r=U,i=Cu;Sp(n.type)&&(U=n.stateNode,Cu=!1),wu(e,t,n),gm(n.stateNode,n.type,n.memoizedProps),U=r,Cu=i;break;case 5:H||Al(n,t),Nl(n);case 6:if(n.tag===6&&Nl(n),r=U,i=Cu,U=null,wu(e,t,n),U=r,Cu=i,U!==null){if(Cu)try{(U.nodeType===9?U.body:U.nodeName===`HTML`?U.ownerDocument.body:U).removeChild(n.stateNode),k=!0}catch(e){Z(n,t,e)}else try{U.removeChild(n.stateNode),k=!0}catch(e){Z(n,t,e)}}break;case 18:U!==null&&(Cu?(e=U,Cp(e.nodeType===9?e.body:e.nodeName===`HTML`?e.ownerDocument.body:e,n.stateNode),Hh(e)):Cp(U,n.stateNode));break;case 4:r=U,i=Cu,U=n.stateNode.containerInfo,Cu=!0,wu(e,t,n),U=r,Cu=i;break;case 0:case 11:case 14:case 15:El(2,n,t),H||El(4,n,t),wu(e,t,n);break;case 1:H||(Al(n,t),r=n.stateNode,typeof r.componentWillUnmount==`function`&&Ol(n,t,r)),wu(e,t,n);break;case 21:wu(e,t,n);break;case 22:H=(r=H)||n.memoizedState!==null,wu(e,t,n),H=r;break;case 30:Al(n,t),wu(e,t,n);break;case 7:H||Al(n,t),wu(e,t,n);break;default:wu(e,t,n)}}function Eu(e,t){if(t.memoizedState===null&&(e=t.alternate,e!==null&&(e=e.memoizedState,e!==null))){e=e.dehydrated;try{Hh(e)}catch(e){Z(t,t.return,e)}}}function Du(e,t){if(t.memoizedState===null&&(e=t.alternate,e!==null&&(e=e.memoizedState,e!==null&&(e=e.dehydrated,e!==null))))try{Hh(e)}catch(e){Z(t,t.return,e)}}function Ou(e){switch(e.tag){case 31:case 13:case 19:var t=e.stateNode;return t===null&&(t=e.stateNode=new uu),t;case 22:return e=e.stateNode,t=e._retryCache,t===null&&(t=e._retryCache=new uu),t;default:throw Error(i(435,e.tag))}}function ku(e,t){var n=Ou(e);t.forEach(function(t){if(!n.has(t)){n.add(t);var r=vf.bind(null,e,t);t.then(r,r)}})}function Au(e,t,n){var r=t.deletions;if(r!==null)for(var a=0;a<r.length;a++){var o=r[a],s=e,c=t,l=c;a:for(;l!==null;){switch(l.tag){case 27:if(Sp(l.type)){U=l.stateNode,Cu=!1;break a}break;case 5:U=l.stateNode,Cu=!1;break a;case 3:case 4:U=l.stateNode.containerInfo,Cu=!0;break a}l=l.return}if(U===null)throw Error(i(160));Tu(s,c,o),U=null,Cu=!1,s=o.alternate,s!==null&&(s.return=null),o.return=null}if(t.subtreeFlags&13886)for(t=t.child;t!==null;)Mu(t,e,n),t=t.sibling}var ju=null;function Mu(e,t,n){var r=e.alternate,a=e.flags;switch(e.tag){case 0:case 11:case 14:case 15:if(a&4&&(r=e.updateQueue,r=r===null?null:r.events,r!==null))for(var o=0;o<r.length;o++){var s=r[o];s.ref.impl=s.nextImpl}Au(t,e,n),Nu(e),a&4&&(El(3,e,e.return),Tl(3,e),El(5,e,e.return));break;case 1:Au(t,e,n),Nu(e),a&512&&(H||r===null||Al(r,r.return)),a&64&&V&&(e=e.updateQueue,e!==null&&(t=e.callbacks,t!==null&&(n=e.shared.hiddenCallbacks,e.shared.hiddenCallbacks=n===null?t:n.concat(t))));break;case 26:if(o=ju,Au(t,e,n),Nu(e),a&512&&(H||r===null||Al(r,r.return)),a&4){if(a=r===null?null:r.memoizedState,n=e.memoizedState,r===null){if(n===null){if(e.stateNode===null){if(V)e.stateNode=fp(e.type,e.memoizedProps,t.containerInfo,e);else{a:{t=e.type,n=e.memoizedProps,a=o.ownerDocument||o;b:switch(t){case`title`:r=a.getElementsByTagName(`title`)[0],(!r||r[Bt]||r[Nt]||r.namespaceURI===`http://www.w3.org/2000/svg`||r.hasAttribute(`itemprop`))&&(r=a.createElement(t),a.head.insertBefore(r,a.querySelector(`head > title`))),np(r,t,n),r[Nt]=e,O(r),t=r;break a;case`link`:if(o=Gm(`link`,`href`,a).get(t+(n.href||``))){for(s=0;s<o.length;s++)if(r=o[s],r.getAttribute(`href`)===(n.href==null||n.href===``?null:n.href)&&r.getAttribute(`rel`)===(n.rel==null?null:n.rel)&&r.getAttribute(`title`)===(n.title==null?null:n.title)&&r.getAttribute(`crossorigin`)===(n.crossOrigin==null?null:n.crossOrigin)){o.splice(s,1);break b}}r=a.createElement(t),np(r,t,n),a.head.appendChild(r);break;case`meta`:if(o=Gm(`meta`,`content`,a).get(t+(n.content||``))){for(s=0;s<o.length;s++)if(r=o[s],r.getAttribute(`content`)===(n.content==null?null:``+n.content)&&r.getAttribute(`name`)===(n.name==null?null:n.name)&&r.getAttribute(`property`)===(n.property==null?null:n.property)&&r.getAttribute(`http-equiv`)===(n.httpEquiv==null?null:n.httpEquiv)&&r.getAttribute(`charset`)===(n.charSet==null?null:n.charSet)){o.splice(s,1);break b}}r=a.createElement(t),np(r,t,n),a.head.appendChild(r);break;default:throw Error(i(468,t))}r[Nt]=e,O(r),t=r}e.stateNode=t}}else V||Km(o,e.type,e.stateNode)}else e.stateNode=Bm(o,n,e.memoizedProps)}else a===n?n===null&&e.stateNode!==null&&Ll(e,e.memoizedProps,r.memoizedProps):(a===null?(t=r.stateNode,t===null||H||t.parentNode.removeChild(t)):a.count--,n===null?V||Km(o,e.type,e.stateNode):Bm(o,n,e.memoizedProps))}break;case 27:Au(t,e,n),Nu(e),a&512&&(H||r===null||Al(r,r.return)),r!==null&&a&4&&Ll(e,e.memoizedProps,r.memoizedProps);break;case 5:if(o=cu,cu=!1,Au(t,e,n),cu=o,Nu(e),a&512&&(H||r===null||Al(r,r.return)),e.flags&32){t=e.stateNode;try{bn(t,``),k=!0}catch(t){Z(e,e.return,t)}}a&4&&e.stateNode!=null&&(t=e.memoizedProps,Ll(e,t,r===null?t:r.memoizedProps)),a&1024&&(lu=!0);break;case 6:if(Au(t,e,n),Nu(e),a&4){if(e.stateNode===null)throw Error(i(162));t=e.memoizedProps,n=e.stateNode;try{n.nodeValue=t,k=!0}catch(t){Z(e,e.return,t)}}break;case 3:if(k=!1,Wm=null,o=ju,ju=bm(t.containerInfo),Au(t,e,n),ju=o,Nu(e),a&4&&r!==null&&r.memoizedState.isDehydrated)try{Hh(t.containerInfo)}catch(t){Z(e,e.return,t)}lu&&(lu=!1,Pu(e)),k=!1;break;case 4:a=cu,cu=V,r=nn(),o=ju,ju=bm(e.stateNode.containerInfo),Au(t,e,n),Nu(e),ju=o,k&&pu&&(mu=!0),k=r,cu=a;break;case 12:Au(t,e,n),Nu(e);break;case 31:Au(t,e,n),Nu(e),a&4&&(t=e.updateQueue,t!==null&&(e.updateQueue=null,ku(e,t)));break;case 13:Au(t,e,n),Nu(e),e.child.flags&8192&&e.memoizedState!==null!=(r!==null&&r.memoizedState!==null)&&(hd=Ze()),a&4&&(t=e.updateQueue,t!==null&&(e.updateQueue=null,ku(e,t)));break;case 22:o=e.memoizedState!==null,s=r!==null&&r.memoizedState!==null;var c=V,l=H,u=cu;V=c||o,cu=u||o,H=l||s,Au(t,e,n),H=l,cu=u,V=c,Nu(e),a&8192&&(t=e.stateNode,t._visibility=o?t._visibility&-2:t._visibility|1,!o||r===null||s||V||H||(t=s||H,n=V,r=H,V=o||V,H=t,Ru(e,2),V=n,H=r),!o&&cu||yu(e,o)),a&4&&(t=e.updateQueue,t!==null&&(n=t.retryQueue,n!==null&&(t.retryQueue=null,ku(e,n))));break;case 19:Au(t,e,n),Nu(e),a&4&&(t=e.updateQueue,t!==null&&(e.updateQueue=null,ku(e,t)));break;case 30:a&512&&(H||r===null||Al(r,r.return)),a=nn(),o=pu,s=(n&335544064)===n,c=e.memoizedProps,pu=s&&ki(c.default,c.update)!==`none`,Au(t,e,n),Nu(e),s&&r!==null&&k&&(e.flags|=4),pu=o,k=a;break;case 21:break;case 7:a&512&&(H||r===null||Al(r,r.return)),r&&r.stateNode!==null&&(r.stateNode._fragmentFiber=e);default:Au(t,e,n),Nu(e)}}function Nu(e){var t=e.flags;if(t&2){try{for(var n,r=e.return;r!==null;){if(Rl(r)){n=r;break}r=r.return}r=null;for(var a=e.return;a!==null;){if(Fl(a)){var o=a.stateNode;r===null?r=[o]:r.push(o)}if(Pl(a))break;a=a.return}var s=r;if(n==null)throw Error(i(160));switch(n.tag){case 27:var c=n.stateNode;Vl(e,zl(e),c,s);break;case 5:var l=n.stateNode;n.flags&32&&(bn(l,``),n.flags&=-33),Vl(e,zl(e),l,s);break;case 3:case 4:var u=n.stateNode.containerInfo;Bl(e,zl(e),u,s);break;default:throw Error(i(161))}}catch(t){Z(e,e.return,t)}e.flags&=-3}t&4096&&(e.flags&=-4097)}function Pu(e){if(e.subtreeFlags&1024)for(e=e.child;e!==null;){var t=e;Pu(t),t.tag===5&&t.flags&1024&&(t=t.stateNode,gh=!0,t.reset(),gh=!1),e=e.sibling}}function Fu(e,t){if(t.subtreeFlags&9270)for(t=t.child;t!==null;)Iu(t,e),t=t.sibling;else su(t,!1)}function Iu(e,t){var n=e.alternate;if(n===null)$l(e,!1);else switch(e.tag){case 3:if(hu=fu=!1,ql(),Fu(t,e),!fu&&!mu){if(e=Kl,e!==null)for(var r=0;r<e.length;r+=3){n=e[r];var i=e[r+1];Ep(n,e[r+2]),n=n.ownerDocument.documentElement,n!==null&&n.animate({opacity:[0,0],pointerEvents:[`none`,`none`]},{duration:0,fill:`forwards`,pseudoElement:`::view-transition-group(`+i+`)`})}e=t.containerInfo,e=e.nodeType===9?e.documentElement:e.ownerDocument.documentElement,e!==null&&e.style.viewTransitionName===``&&(e.style.viewTransitionName=`none`,e.animate({opacity:[0,0],pointerEvents:[`none`,`none`]},{duration:0,fill:`forwards`,pseudoElement:`::view-transition-group(root)`}),e.animate({width:[0,0],height:[0,0]},{duration:0,fill:`forwards`,pseudoElement:`::view-transition`})),hu=!0}Kl=null;break;case 5:Fu(t,e);break;case 4:r=fu,fu=!1,Fu(t,e),fu&&(mu=!0),fu=r;break;case 22:e.memoizedState===null&&(n.memoizedState===null?Fu(t,e):$l(e,!1));break;case 30:r=fu,i=ql(),fu=!1,Fu(t,e),fu&&(e.flags|=4);var a=e.memoizedProps,o=e.stateNode;t=Di(a,o),o=Di(n.memoizedProps,o);var s=ki(a.default,a.update);s===`none`?t=!1:(a=n.memoizedState,n.memoizedState=null,n=e.child,Jl=0,t=ou(e,n,t,o,s,a,!0),Jl!==(a===null?0:a.length)&&(e.flags|=32)),e.flags&4&&t?(Nd(e,e.memoizedProps.onUpdate),Kl=i):i!==null&&(i.push.apply(i,Kl),Kl=i),fu=e.flags&32?!0:r;break;default:Fu(t,e)}}function Lu(e,t){if(t.subtreeFlags&8772)for(t=t.child;t!==null;)vu(e,t.alternate,t),t=t.sibling}function Ru(e,t){for(e=e.child;e!==null;){var n=e,r=t;switch(n.tag){case 0:case 11:case 14:case 15:El(4,n,n.return),Ru(n,r);break;case 1:Al(n,n.return);var i=n.stateNode;typeof i.componentWillUnmount==`function`&&Ol(n,n.return,i),Ru(n,r);break;case 27:r&2&&gm(n.stateNode,n.type,n.memoizedProps);case 5:Al(n,n.return),n.tag!==5&&n.tag!==27||Nl(n),Ru(n,r);break;case 6:Nl(n);break;case 26:Al(n,n.return),i=n.stateNode,n.memoizedState!==null||i===null||H||i.parentNode.removeChild(i),Ru(n,r);break;case 22:n.memoizedState===null&&Ru(n,r);break;case 30:Al(n,n.return),Ru(n,r);break;case 7:Al(n,n.return);default:Ru(n,r)}e=e.sibling}}function zu(e,t,n){for(n=t.subtreeFlags&8772?n:n&-2,t=t.child;t!==null;){var r=t.alternate,i=e,a=t,o=a.flags,s=!!(n&1);switch(a.tag){case 0:case 11:case 15:zu(i,a,n),Tl(4,a);break;case 1:if(zu(i,a,n),r=a,i=r.stateNode,typeof i.componentDidMount==`function`)try{i.componentDidMount()}catch(e){Z(r,r.return,e)}if(r=a,i=r.updateQueue,i!==null){var c=r.stateNode;try{var l=i.shared.hiddenCallbacks;if(l!==null)for(i.shared.hiddenCallbacks=null,i=0;i<l.length;i++)Mo(l[i],c)}catch(e){Z(r,r.return,e)}}s&&o&64&&Dl(a),kl(a,a.return);break;case 27:n&2&&Hl(a);case 5:a.tag!==5&&a.tag!==27||Ml(a),zu(i,a,n),s&&r===null&&o&4&&Il(a),kl(a,a.return);break;case 6:Ml(a);break;case 26:c=a.stateNode,a.memoizedState!==null||c===null||V||Km(bm(c.ownerDocument),a.type,c),zu(i,a,n),s&&r===null&&o&4&&Il(a),kl(a,a.return);break;case 12:zu(i,a,n);break;case 31:zu(i,a,n),s&&o&4&&Eu(i,a);break;case 13:zu(i,a,n),s&&o&4&&Du(i,a);break;case 22:a.memoizedState===null&&zu(i,a,n),kl(a,a.return);break;case 30:zu(i,a,n),kl(a,a.return);break;case 7:kl(a,a.return);default:zu(i,a,n)}t=t.sibling}}function Bu(e,t){var n=null;e!==null&&e.memoizedState!==null&&e.memoizedState.cachePool!==null&&(n=e.memoizedState.cachePool.pool),e=null,t.memoizedState!==null&&t.memoizedState.cachePool!==null&&(e=t.memoizedState.cachePool.pool),e!==n&&(e!=null&&e.refCount++,n!=null&&Va(n))}function Vu(e,t){e=null,t.alternate!==null&&(e=t.alternate.memoizedState.cache),t=t.memoizedState.cache,t!==e&&(t.refCount++,e!=null&&Va(e))}function Hu(e,t,n,r){var i=(n&335544064)===n;if(t.subtreeFlags&(i?10262:10256))for(t=t.child;t!==null;)Uu(e,t,n,r),t=t.sibling;else i&&au(t)}function Uu(e,t,n,r){var i=(n&335544064)===n;i&&t.alternate===null&&t.return!==null&&t.return.alternate!==null&&iu(t);var a=t.flags;switch(t.tag){case 0:case 11:case 15:Hu(e,t,n,r),a&2048&&Tl(9,t);break;case 1:Hu(e,t,n,r);break;case 3:Hu(e,t,n,r),i&&hu&&(e=e.containerInfo,e=e.nodeType===9?e.body:e.nodeName===`HTML`?e.ownerDocument.body:e,e.style.viewTransitionName===`root`&&(e.style.viewTransitionName=``),e=e.ownerDocument.documentElement,e!==null&&e.style.viewTransitionName===`none`&&(e.style.viewTransitionName=``)),a&2048&&(a=null,t.alternate!==null&&(a=t.alternate.memoizedState.cache),t=t.memoizedState.cache,t!==a&&(t.refCount++,a!=null&&Va(a)));break;case 12:if(a&2048){Hu(e,t,n,r),a=t.stateNode;try{var o=t.memoizedProps,s=o.id,c=o.onPostCommit;typeof c==`function`&&c(s,t.alternate===null?`mount`:`update`,a.passiveEffectDuration,-0)}catch(e){Z(t,t.return,e)}}else Hu(e,t,n,r);break;case 31:Hu(e,t,n,r);break;case 13:Hu(e,t,n,r);break;case 23:break;case 22:o=t.stateNode,s=t.alternate,t.memoizedState===null?(i&&s!==null&&s.memoizedState!==null&&iu(t),o._visibility&2?Hu(e,t,n,r):(o._visibility|=2,Wu(e,t,n,r,!!(t.subtreeFlags&10256)||!1))):(i&&s!==null&&s.memoizedState===null&&iu(s),o._visibility&2?Hu(e,t,n,r):Gu(e,t)),a&2048&&Bu(s,t);break;case 24:Hu(e,t,n,r),a&2048&&Vu(t.alternate,t);break;case 30:i&&(a=t.alternate,a!==null&&(Zl(a.child,!0),Zl(t.child,!0))),Hu(e,t,n,r);break;default:Hu(e,t,n,r)}}function Wu(e,t,n,r,i){for(i&&=!!(t.subtreeFlags&10256)||!1,t=t.child;t!==null;){var a=e,o=t,s=n,c=r,l=o.flags;switch(o.tag){case 0:case 11:case 15:Wu(a,o,s,c,i),Tl(8,o);break;case 23:break;case 22:var u=o.stateNode;o.memoizedState===null?(u._visibility|=2,Wu(a,o,s,c,i)):u._visibility&2?Wu(a,o,s,c,i):Gu(a,o),i&&l&2048&&Bu(o.alternate,o);break;case 24:Wu(a,o,s,c,i),i&&l&2048&&Vu(o.alternate,o);break;default:Wu(a,o,s,c,i)}t=t.sibling}}function Gu(e,t){if(t.subtreeFlags&10256)for(t=t.child;t!==null;){var n=e,r=t,i=r.flags;switch(r.tag){case 22:Gu(n,r),i&2048&&Bu(r.alternate,r);break;case 24:Gu(n,r),i&2048&&Vu(r.alternate,r);break;default:Gu(n,r)}t=t.sibling}}var Ku=8192;function qu(e,t,n){if(e.subtreeFlags&Ku)for(e=e.child;e!==null;)Ju(e,t,n),e=e.sibling}function Ju(e,t,n){switch(e.tag){case 26:qu(e,t,n),e.flags&Ku&&(e.memoizedState===null?(e=e.stateNode,(t&335544128)===t&&Zm(n,e)):Qm(n,ju,e.memoizedState,e.memoizedProps));break;case 5:qu(e,t,n),e.flags&Ku&&(e=e.stateNode,(t&335544128)===t&&Zm(n,e));break;case 3:case 4:var r=ju;ju=bm(e.stateNode.containerInfo),qu(e,t,n),ju=r;break;case 22:e.memoizedState===null&&(r=e.alternate,r!==null&&r.memoizedState!==null?(r=Ku,Ku=16777216,qu(e,t,n),Ku=r):qu(e,t,n));break;case 30:if((e.flags&Ku)!==0&&(r=e.memoizedProps.name,r!=null&&r!==`auto`)){var i=e.stateNode;i.paired=null,Wl===null&&(Wl=new Map),Wl.set(r,i)}qu(e,t,n);break;default:qu(e,t,n)}}function Yu(e){var t=e.alternate;if(t!==null&&(e=t.child,e!==null)){t.child=null;do t=e.sibling,e.sibling=null,e=t;while(e!==null)}}function Xu(e){var t=e.deletions;if(e.flags&16){if(t!==null)for(var n=0;n<t.length;n++){var r=t[n];du=r,$u(r,e)}Yu(e)}if(e.subtreeFlags&10256)for(e=e.child;e!==null;)Zu(e),e=e.sibling}function Zu(e){switch(e.tag){case 0:case 11:case 15:Xu(e),e.flags&2048&&El(9,e,e.return);break;case 3:Xu(e);break;case 12:Xu(e);break;case 22:var t=e.stateNode;e.memoizedState!==null&&t._visibility&2&&(e.return===null||e.return.tag!==13)?(t._visibility&=-3,Qu(e)):Xu(e);break;default:Xu(e)}}function Qu(e){var t=e.deletions;if(e.flags&16){if(t!==null)for(var n=0;n<t.length;n++){var r=t[n];du=r,$u(r,e)}Yu(e)}for(e=e.child;e!==null;){switch(t=e,t.tag){case 0:case 11:case 15:El(8,t,t.return),Qu(t);break;case 22:n=t.stateNode,n._visibility&2&&(n._visibility&=-3,Qu(t));break;default:Qu(t)}e=e.sibling}}function $u(e,t){for(;du!==null;){var n=du;switch(n.tag){case 0:case 11:case 15:El(8,n,t);break;case 23:case 22:if(n.memoizedState!==null&&n.memoizedState.cachePool!==null){var r=n.memoizedState.cachePool.pool;r!=null&&r.refCount++}break;case 24:Va(n.memoizedState.cache)}if(r=n.child,r!==null)r.return=n,du=r;else a:for(n=e;du!==null;){r=du;var i=r.sibling,a=r.return;if(Su(r),r===n){du=null;break a}if(i!==null){i.return=a,du=i;break a}du=a}}}var ed={getCacheForType:function(e){var t=Pa(M),n=t.data.get(e);return n===void 0&&(n=e(),t.data.set(e,n)),n},cacheSignal:function(){return Pa(M).controller.signal}},td=typeof WeakMap==`function`?WeakMap:Map,W=0,G=null,K=null,q=0,J=0,nd=null,rd=!1,id=!1,ad=!1,od=0,Y=0,sd=0,cd=0,ld=0,ud=0,dd=0,fd=null,pd=null,md=!1,hd=0,gd=0,_d=1/0,vd=null,yd=null,X=0,bd=null,xd=null,Sd=0,Cd=0,wd=null,Td=null,Ed=null,Dd=null,Od=null,kd=0,Ad=null;function jd(){return W&2&&q!==0?q&-q:T.T===null?At():Pf()}function Md(){if(ud===0){if(!(q&536870912)||j){var e=mt;mt<<=1,!(mt&3932160)&&(mt=262144),ud=e}else ud=536870912}return e=zo.current,e!==null&&(e.flags|=32),ud}function Nd(e,t){if(t!=null){var n=e.stateNode,r=n.ref;r===null&&(r=n.ref=Pp(Di(e.memoizedProps,n))),Dd===null&&(Dd=[]),Dd.push(t.bind(null,r))}}function Pd(e,t,n){(e===G&&(J===2||J===9)||e.cancelPendingCommit!==null)&&(Vd(e,0),Rd(e,q,ud,!1)),Ct(e,n),(!(W&2)||e!==G)&&(e===G&&(!(W&2)&&(cd|=n),Y===4&&Rd(e,q,ud,!1)),Ef(e))}function Fd(e,t,n){if(W&6)throw Error(i(327));var r=!n&&!(t&127)&&(t&e.expiredLanes)===0||vt(e,t),a=r?Yd(e,t):qd(e,t,!0),o=r;do{if(a===0){id&&!r&&Rd(e,t,0,!1);break}if(n=e.current.alternate,o&&!Ld(n)){a=qd(e,t,!1),o=!1;continue}if(a===2){if(o=t,e.errorRecoveryDisabledLanes&o)var s=0;else s=e.pendingLanes&-536870913,s=s===0?s&536870912?536870912:0:s;if(s!==0){t=s;a:{var c=e;a=fd;var l=c.current.memoizedState.isDehydrated;if(l&&(Vd(c,s).flags|=256),s=qd(c,s,!1),s!==2&&s!==6){if(ad&&!l){c.errorRecoveryDisabledLanes|=o,cd|=o,a=4;break a}o=pd,pd=a,o!==null&&(pd===null?pd=o:pd.push.apply(pd,o))}a=s}if(o=!1,a!==2)continue}}if(a===1){Vd(e,0),Rd(e,t,0,!0);break}a:{switch(r=e,o=a,o){case 0:case 1:throw Error(i(345));case 4:if((t&4194048)!==t&&(t&62914560)!==t)break;case 6:Rd(r,t,ud,!rd);break a;case 2:pd=null;break;case 3:case 5:break;default:throw Error(i(329))}if((t&62914560)===t&&(a=hd+300-Ze(),10<a)){if(Rd(r,t,ud,!rd),_t(r,0,!0)!==0)break a;Sd=t,r.timeoutHandle=gp(Id.bind(null,r,n,pd,vd,md,t,ud,cd,dd,rd,o,`Throttled`,-0,0),a);break a}Id(r,n,pd,vd,md,t,ud,cd,dd,rd,o,null,-0,0)}break}while(1);Ef(e)}function Id(e,t,n,r,i,a,o,s,c,l,u,d,f,p){e.timeoutHandle=-1;var m=t.subtreeFlags,h=(a&335544064)===a;if(d=null,(h||m&8192||(m&16785408)==16785408)&&(d={stylesheets:null,count:0,imgCount:0,imgBytes:0,suspenseyImages:[],waitingForImages:!0,waitingForViewTransition:!1,unsuspend:On},Wl=null,Ju(t,a,d),h&&(m=d,h=e.containerInfo,h=(h.nodeType===9?h:h.ownerDocument).__reactViewTransition,h!=null&&(m.count++,m.waitingForViewTransition=!0,m=nh.bind(m),h.finished.then(m,m))),m=(a&62914560)===a?hd-Ze():(a&4194048)===a?gd-Ze():0,m=eh(d,m),m!==null)){Sd=a,e.cancelPendingCommit=m(nf.bind(null,e,t,a,n,r,i,o,s,c,l,u,d,null,f,p)),Rd(e,a,o,!l);return}nf(e,t,a,n,r,i,o,s,c,l,u,d)}function Ld(e){for(var t=e;;){var n=t.tag;if((n===0||n===11||n===15)&&t.flags&16384&&(n=t.updateQueue,n!==null&&(n=n.stores,n!==null)))for(var r=0;r<n.length;r++){var i=n[r],a=i.getSnapshot;i=i.value;try{if(!Zr(a(),i))return!1}catch{return!1}}if(n=t.child,t.subtreeFlags&16384&&n!==null)n.return=t,t=n;else{if(t===e)break;for(;t.sibling===null;){if(t.return===null||t.return===e)return!0;t=t.return}t.sibling.return=t.return,t=t.sibling}}return!0}function Rd(e,t,n,r){t=yt(e,t),t&=~ld,t&=~cd,e.suspendedLanes|=t,e.pingedLanes&=~t,r&&(e.warmLanes|=t),r=e.expirationTimes;for(var i=t;0<i;){var a=31-lt(i),o=1<<a;r[a]=-1,i&=~o}n!==0&&Tt(e,n,t)}function zd(){return W&6?!0:(Df(0,!1),!1)}function Bd(){if(K!==null){if(J===0)var e=K.return;else e=K,Ea=Ta=null,ds(e),mo=null,ho=0,e=K;for(;e!==null;)wl(e.alternate,e),e=e.return;K=null}}function Vd(e,t){var n=e.timeoutHandle;return n!==-1&&(e.timeoutHandle=-1,_p(n)),n=e.cancelPendingCommit,n!==null&&(e.cancelPendingCommit=null,n()),Sd=0,Bd(),G=e,K=n=Wi(e.current,null),q=t,J=0,nd=null,rd=!1,id=vt(e,t),ad=!1,dd=ud=ld=cd=sd=Y=0,pd=fd=null,md=!1,od=yt(e,t),Pi(),n}function Hd(e,t){N=null,T.H=bc,t===ro||t===ao?(t=fo(),J=3):t===io?(t=fo(),J=4):J=t===Rc?8:typeof t==`object`&&t&&typeof t.then==`function`?6:1,nd=t,K===null&&(Y=1,Mc(e,Qi(t,e.current)))}function Ud(){var e=zo.current;return e===null?!0:(q&4194048)===q?Bo===null:(q&62914560)===q||q&536870912?e===Bo:!1}function Wd(){var e=T.H;return T.H=bc,e===null?bc:e}function Gd(){var e=T.A;return T.A=ed,e}function Kd(){Y=4,rd||(q&4194048)!==q&&zo.current!==null||(id=!0),!(sd&134217727)&&!(cd&134217727)||G===null||Rd(G,q,ud,!1)}function qd(e,t,n){var r=W;W|=2;var i=Wd(),a=Gd();(G!==e||q!==t)&&(vd=null,Vd(e,t)),t=!1;var o=Y;a:do try{if(J!==0&&K!==null){var s=K,c=nd;switch(J){case 8:Bd(),o=6;break a;case 3:case 2:case 9:case 6:zo.current===null&&(t=!0);var l=J;if(J=0,nd=null,$d(e,s,c,l),n&&id){o=0;break a}break;default:l=J,J=0,nd=null,$d(e,s,c,l)}}Jd(),o=Y;break}catch(t){Hd(e,t)}while(1);return t&&e.shellSuspendCounter++,Ea=Ta=null,W=r,T.H=i,T.A=a,K===null&&(G=null,q=0,Pi()),o}function Jd(){for(;K!==null;)Zd(K)}function Yd(e,t){var n=W;W|=2;var r=Wd(),a=Gd();G!==e||q!==t?(vd=null,_d=Ze()+500,Vd(e,t)):id=vt(e,t);a:do try{if(J!==0&&K!==null){t=K;var o=nd;b:switch(J){case 1:J=0,nd=null,$d(e,t,o,1);break;case 2:case 9:if(so(o)){J=0,nd=null,Qd(t);break}t=function(){J!==2&&J!==9||G!==e||(J=7),Ef(e)},o.then(t,t);break a;case 3:J=7;break a;case 4:J=5;break a;case 7:so(o)?(J=0,nd=null,Qd(t)):(J=0,nd=null,$d(e,t,o,7));break;case 5:var s=null;switch(K.tag){case 26:s=K.memoizedState;case 5:case 27:var c=K;if(s?Ym(s):c.stateNode.complete){J=0,nd=null;var l=c.sibling;if(l!==null)K=l;else{var u=c.return;u===null?K=null:(K=u,ef(u))}break b}}J=0,nd=null,$d(e,t,o,5);break;case 6:J=0,nd=null,$d(e,t,o,6);break;case 8:Bd(),Y=6;break a;default:throw Error(i(462))}}Xd();break}catch(t){Hd(e,t)}while(1);return Ea=Ta=null,T.H=r,T.A=a,W=n,K===null?(G=null,q=0,Pi(),Y):0}function Xd(){for(;K!==null&&!Ye();)Zd(K)}function Zd(e){var t=gl(e.alternate,e,od);e.memoizedProps=e.pendingProps,t===null?ef(e):K=t}function Qd(e){var t=e,n=t.alternate;switch(t.tag){case 15:case 0:t=Xc(n,t,t.pendingProps,t.type,void 0,q);break;case 11:t=Xc(n,t,t.pendingProps,t.type.render,t.ref,q);break;case 5:ds(t);var r=t;r===pa&&(j?(ya(r),r.tag===5&&r.stateNode!=null&&(A=r.stateNode)):(ya(r),j=!0));default:wl(n,t),t=K=Gi(t,od),t=gl(n,t,od)}e.memoizedProps=e.pendingProps,t===null?ef(e):K=t}function $d(e,t,n,r){Ea=Ta=null,ds(t),mo=null,ho=0;var i=t.return;try{if(Lc(e,i,t,n,q)){Y=1,Mc(e,Qi(n,e.current)),K=null;return}}catch(t){if(i!==null)throw K=i,t;Y=1,Mc(e,Qi(n,e.current)),K=null;return}t.flags&32768?(j||r===1?e=!0:id||q&536870912?e=!1:(rd=e=!0,(r===2||r===9||r===3||r===6)&&(r=zo.current,r!==null&&r.tag===13&&(r.flags|=16384))),tf(t,e)):ef(t)}function ef(e){var t=e;do{if(t.flags&32768){tf(t,rd);return}e=t.return;var n=Sl(t.alternate,t,od);if(n!==null){K=n;return}if(t=t.sibling,t!==null){K=t;return}K=t=e}while(t!==null);Y===0&&(Y=5)}function tf(e,t){do{var n=Cl(e.alternate,e);if(n!==null){n.flags&=32767,K=n;return}if(n=e.return,n!==null&&(n.flags|=32768,n.subtreeFlags=0,n.deletions=null),!t&&(e=e.sibling,e!==null)){K=e;return}K=e=n}while(e!==null);Y=6,K=null}function nf(e,t,n,r,a,o,s,c,l,u,d,f){e.cancelPendingCommit=null;do df();while(X!==0);if(W&6)throw Error(i(327));if(t!==null){if(t===e.current)throw Error(i(177));e===G&&(K=G=null,q=0),xd=t,bd=e,Sd=n,wd=a,Td=r,rf(e,t,n,s,c,l,f)}}function rf(e,t,n,r,i,a,o){var s=t.lanes|t.childLanes;if(Cd=s,s|=Ni,wt(e,n,s,r,i,a),Dd=null,(n&335544064)===n?(Od=Wa(e),r=10262):(Od=null,r=10256),(t.subtreeFlags&r)!==0||(t.flags&r)!==0?(e.callbackNode=null,e.callbackPriority=0,yf(tt,function(){return ff(),null})):(e.callbackNode=null,e.callbackPriority=0),Ul=!1,r=!!(t.flags&13878),t.subtreeFlags&13878||r){r=T.T,T.T=null,i=E.p,E.p=2,a=W,W|=4;try{gu(e,t,n)}finally{W=a,E.p=i,T.T=r}}X=1,Ul?Ed=Mp(o,e.containerInfo,Od,sf,cf,of,lf,ff,af,null,null):(sf(),cf(),lf())}function af(e){if(X!==0){var t=bd.onRecoverableError;t(e,{componentStack:null})}}function of(){X===3&&(X=0,Iu(xd,bd),X=4)}function sf(){if(X===1){X=0;var e=bd,t=xd,n=Sd,r=!!(t.flags&13878);if(t.subtreeFlags&13878||r){r=T.T,T.T=null;var i=E.p;E.p=2;var a=W;W|=4;try{pu=mu=!1,Mu(t,e,n),n=cp;var o=ri(e.containerInfo),s=n.focusedElem,c=n.selectionRange;if(o!==s&&s&&s.ownerDocument&&ni(s.ownerDocument.documentElement,s)){if(c!==null&&ii(s)){var l=c.start,u=c.end;if(u===void 0&&(u=l),`selectionStart`in s)s.selectionStart=l,s.selectionEnd=Math.min(u,s.value.length);else{var d=s.ownerDocument||document,f=d&&d.defaultView||window;if(f.getSelection){var p=f.getSelection(),m=s.textContent.length,h=Math.min(c.start,m),g=c.end===void 0?h:Math.min(c.end,m);!p.extend&&h>g&&(o=g,g=h,h=o);var _=ti(s,h),v=ti(s,g);if(_&&v&&(p.rangeCount!==1||p.anchorNode!==_.node||p.anchorOffset!==_.offset||p.focusNode!==v.node||p.focusOffset!==v.offset)){var y=d.createRange();y.setStart(_.node,_.offset),p.removeAllRanges(),h>g?(p.addRange(y),p.extend(v.node,v.offset)):(y.setEnd(v.node,v.offset),p.addRange(y))}}}}for(d=[],p=s;p=p.parentNode;)p.nodeType===1&&d.push({element:p,left:p.scrollLeft,top:p.scrollTop});for(typeof s.focus==`function`&&s.focus(),s=0;s<d.length;s++){var b=d[s];b.element.scrollLeft=b.left,b.element.scrollTop=b.top}}gh=!!sp,cp=sp=null}finally{W=a,E.p=i,T.T=r}}e.current=t,X=2}}function cf(){if(X===2){X=0;var e=bd,t=xd,n=!!(t.flags&8772);if(t.subtreeFlags&8772||n){n=T.T,T.T=null;var r=E.p;E.p=2;var i=W;W|=4;try{vu(e,t.alternate,t)}finally{W=i,E.p=r,T.T=n}}X=3}}function lf(){if(X===4||X===3){X=0;var e=Ed;Ed=null,Xe();var t=bd,n=xd,r=Sd,i=Td,a=(r&335544064)===r?10262:10256;if((n.subtreeFlags&a)!==0||(n.flags&a)!==0?X=5:(X=0,xd=bd=null,uf(t,t.pendingLanes)),a=t.pendingLanes,a===0&&(yd=null),kt(r),n=n.stateNode,st&&typeof st.onCommitFiberRoot==`function`)try{st.onCommitFiberRoot(ot,n,void 0,(n.current.flags&128)==128)}catch{}if(i!==null){n=T.T,a=E.p,E.p=2,T.T=null;try{for(var o=t.onRecoverableError,s=0;s<i.length;s++){var c=i[s];o(c.value,{componentStack:c.stack})}}finally{T.T=n,E.p=a}}if(i=Dd,o=Od,Od=null,i!==null&&(Dd=null,o===null&&(o=[]),e!==null))for(c=0;c<i.length;c++)n=(0,i[c])(o),n!==void 0&&e.finished.finally(n);Sd&3&&df(),Ef(t),a=t.pendingLanes,r&261930&&a&42?t===Ad?kd++:(kd=0,Ad=t):(kd=0,Ad=null),Df(0,!1)}}function uf(e,t){(e.pooledCacheLanes&=t)===0&&(t=e.pooledCache,t!=null&&(e.pooledCache=null,Va(t)))}function df(){return Ed!==null&&(Ed.skipTransition(),Ed=null),sf(),cf(),lf(),ff()}function ff(){if(X!==5)return!1;var e=bd,t=Cd;Cd=0;var n=kt(Sd),r=T.T,a=E.p;try{E.p=32>n?32:n,T.T=null,n=wd,wd=null;var o=bd,s=Sd;if(X=0,xd=bd=null,Sd=0,W&6)throw Error(i(331));var c=W;if(W|=4,Zu(o.current),Uu(o,o.current,s,n),W=c,Df(0,!1),st&&typeof st.onPostCommitFiberRoot==`function`)try{st.onPostCommitFiberRoot(ot,o)}catch{}return!0}finally{E.p=a,T.T=r,uf(e,t)}}function pf(e,t,n){t=Qi(n,t),t=Pc(e.stateNode,t,2),e=Eo(e,t,2),e!==null&&(Ct(e,2),Ef(e))}function Z(e,t,n){if(e.tag===3)pf(e,e,n);else for(;t!==null;){if(t.tag===3){pf(t,e,n);break}if(t.tag===1){var r=t.stateNode;if(typeof t.type.getDerivedStateFromError==`function`||typeof r.componentDidCatch==`function`&&(yd===null||!yd.has(r))){e=Qi(n,e),n=Fc(2),r=Eo(t,n,2),r!==null&&(Ic(n,r,t,e),Ct(r,2),Ef(r));break}}t=t.return}}function mf(e,t,n){var r=e.pingCache;if(r===null){r=e.pingCache=new td;var i=new Set;r.set(t,i)}else i=r.get(t),i===void 0&&(i=new Set,r.set(t,i));i.has(n)||(ad=!0,i.add(n),e=hf.bind(null,e,t,n),t.then(e,e))}function hf(e,t,n){var r=e.pingCache;r!==null&&r.delete(t),e.pingedLanes|=e.suspendedLanes&n,e.warmLanes&=~n,G===e&&(q&n)===n&&(Y===4||Y===3&&(q&62914560)===q&&300>Ze()-hd?W&2?ld|=n:Vd(e,0):ld|=n,dd===q&&(dd=0)),Ef(e)}function gf(e,t){t===0&&(t=xt()),e=Li(e,t),e!==null&&(Ct(e,t),Ef(e))}function _f(e){var t=e.memoizedState,n=0;t!==null&&(n=t.retryLane),gf(e,n)}function vf(e,t){var n=0;switch(e.tag){case 31:case 13:var r=e.stateNode,a=e.memoizedState;a!==null&&(n=a.retryLane);break;case 19:r=e.stateNode;break;case 22:r=e.stateNode._retryCache;break;default:throw Error(i(314))}r!==null&&r.delete(t),gf(e,n)}function yf(e,t){return qe(e,t)}var bf=null,xf=null,Sf=!1,Cf=!1,wf=!1,Tf=0;function Ef(e){e!==xf&&e.next===null&&(xf===null?bf=xf=e:xf=xf.next=e),Cf=!0,Sf||(Sf=!0,Nf())}function Df(e,t){if(!wf&&Cf){wf=!0;do for(var n=!1,r=bf;r!==null;){if(!t){if(e!==0){var i=r.pendingLanes;if(i===0)var a=0;else{var o=r.suspendedLanes,s=r.pingedLanes;a=(1<<31-lt(42|e)+1)-1,a&=i&~(o&~s),a=a&201326741?a&201326741|1:a?a|2:0}a!==0&&(n=!0,Mf(r,a))}else a=q,a=_t(r,r===G?a:0,r.cancelPendingCommit!==null||r.timeoutHandle!==-1),!(a&3)||vt(r,a)||(n=!0,Mf(r,a))}r=r.next}while(n);wf=!1}}function Of(){kf()}function kf(){Cf=Sf=!1;var e=0;Tf!==0&&hp()&&(e=Tf);for(var t=Ze(),n=null,r=bf;r!==null;){var i=r.next,a=Af(r,t);a===0?(r.next=null,n===null?bf=i:n.next=i,i===null&&(xf=n)):(n=r,(e!==0||a&3)&&(Cf=!0)),r=i}X!==0&&X!==5||Df(e,!1),Tf!==0&&(Tf=0)}function Af(e,t){for(var n=e.suspendedLanes,r=e.pingedLanes,i=e.expirationTimes,a=e.pendingLanes&-62914561;0<a;){var o=31-lt(a),s=1<<o,c=i[o];c===-1?((s&n)===0||(s&r)!==0)&&(i[o]=bt(s,t)):c<=t&&(e.expiredLanes|=s),a&=~s}if(t=G,n=q,n=_t(e,e===t?n:0,e.cancelPendingCommit!==null||e.timeoutHandle!==-1),r=e.callbackNode,n===0||e===t&&(J===2||J===9)||e.cancelPendingCommit!==null)return r!==null&&r!==null&&Je(r),e.callbackNode=null,e.callbackPriority=0;if(!(n&3)||vt(e,n)){if(t=n&-n,t===e.callbackPriority)return t;switch(r!==null&&Je(r),kt(n)){case 2:case 8:n=et;break;case 32:n=tt;break;case 268435456:n=rt;break;default:n=tt}return r=jf.bind(null,e),n=qe(n,r),e.callbackPriority=t,e.callbackNode=n,t}return r!==null&&r!==null&&Je(r),e.callbackPriority=2,e.callbackNode=null,2}function jf(e,t){if(X!==0&&X!==5)return e.callbackNode=null,e.callbackPriority=0,null;var n=e.callbackNode;if(df()&&e.callbackNode!==n)return null;var r=q;return r=_t(e,e===G?r:0,e.cancelPendingCommit!==null||e.timeoutHandle!==-1),r===0?null:(Fd(e,r,t),Af(e,Ze()),e.callbackNode!=null&&e.callbackNode===n?jf.bind(null,e):null)}function Mf(e,t){if(df())return null;Fd(e,t,!0)}function Nf(){bp(function(){W&6?qe($e,Of):kf()})}function Pf(){if(Tf===0){var e=qa;e===0&&(e=pt,pt<<=1,!(pt&261888)&&(pt=256)),Tf=e}return Tf}function Ff(e){return e==null||typeof e==`symbol`||typeof e==`boolean`?null:typeof e==`function`?e:Dn(e)}function If(e,t,n,r,i){if(t===`submit`&&n&&n.stateNode===i){var a=Ff((i[Pt]||null).action),o=r.submitter;o&&(t=(t=o[Pt]||null)?Ff(t.formAction):o.getAttribute(`formAction`),t!==null&&(a=t,o=null));var s=new Yn(`action`,`action`,null,r,i);e.push({event:s,listeners:[{instance:null,listener:function(){if(r.defaultPrevented){if(Tf!==0){var e=new FormData(i,o);oc(n,{pending:!0,data:e,method:i.method,action:a},null,e)}}else typeof a==`function`&&(s.preventDefault(),e=new FormData(i,o),oc(n,{pending:!0,data:e,method:i.method,action:a},a,e))},currentTarget:i}]})}}for(var Lf=0;Lf<wi.length;Lf++){var Rf=wi[Lf];Ti(Rf.toLowerCase(),`on`+(Rf[0].toUpperCase()+Rf.slice(1)))}Ti(gi,`onAnimationEnd`),Ti(_i,`onAnimationIteration`),Ti(vi,`onAnimationStart`),Ti(`dblclick`,`onDoubleClick`),Ti(`focusin`,`onFocus`),Ti(`focusout`,`onBlur`),Ti(yi,`onTransitionRun`),Ti(bi,`onTransitionStart`),Ti(xi,`onTransitionCancel`),Ti(Si,`onTransitionEnd`),Zt(`onMouseEnter`,[`mouseout`,`mouseover`]),Zt(`onMouseLeave`,[`mouseout`,`mouseover`]),Zt(`onPointerEnter`,[`pointerout`,`pointerover`]),Zt(`onPointerLeave`,[`pointerout`,`pointerover`]),Xt(`onChange`,`change click focusin focusout input keydown keyup selectionchange`.split(` `)),Xt(`onSelect`,`focusout contextmenu dragend focusin keydown keyup mousedown mouseup selectionchange`.split(` `)),Xt(`onBeforeInput`,[`compositionend`,`keypress`,`textInput`,`paste`]),Xt(`onCompositionEnd`,`compositionend focusout keydown keypress keyup mousedown`.split(` `)),Xt(`onCompositionStart`,`compositionstart focusout keydown keypress keyup mousedown`.split(` `)),Xt(`onCompositionUpdate`,`compositionupdate focusout keydown keypress keyup mousedown`.split(` `));var zf=`abort canplay canplaythrough durationchange emptied encrypted ended error loadeddata loadedmetadata loadstart pause play playing progress ratechange resize seeked seeking stalled suspend timeupdate volumechange waiting`.split(` `),Bf=new Set(`beforetoggle cancel close invalid load scroll scrollend toggle`.split(` `).concat(zf));function Vf(e,t){t=!!(t&4);for(var n=0;n<e.length;n++){var r=e[n],i=r.event;r=r.listeners;a:{var a=void 0;if(t)for(var o=r.length-1;0<=o;o--){var s=r[o],c=s.instance,l=s.currentTarget;if(s=s.listener,c!==a&&i.isPropagationStopped())break a;a=s,i.currentTarget=l;try{a(i)}catch(e){Ai(e)}i.currentTarget=null,a=c}else for(o=0;o<r.length;o++){if(s=r[o],c=s.instance,l=s.currentTarget,s=s.listener,c!==a&&i.isPropagationStopped())break a;a=s,i.currentTarget=l;try{a(i)}catch(e){Ai(e)}i.currentTarget=null,a=c}}}}function Q(e,t){var n=t[It];n===void 0&&(n=t[It]=new Set);var r=e+`__bubble`;n.has(r)||(Gf(t,e,2,!1),n.add(r))}function Hf(e,t,n){var r=0;t&&(r|=4),Gf(n,e,r,t)}var Uf=`_reactListening`+Math.random().toString(36).slice(2);function Wf(e){if(!e[Uf]){e[Uf]=!0,Jt.forEach(function(t){t!==`selectionchange`&&(Bf.has(t)||Hf(t,!1,e),Hf(t,!0,e))});var t=e.nodeType===9?e:e.ownerDocument;t===null||t[Uf]||(t[Uf]=!0,Hf(`selectionchange`,!1,t))}}function Gf(e,t,n,r){switch(Ch(t)){case 2:var i=_h;break;case 8:i=vh;break;default:i=yh}n=i.bind(null,t,n,e),i=void 0,!Rn||t!==`touchstart`&&t!==`touchmove`&&t!==`wheel`||(i=!0),r?i===void 0?e.addEventListener(t,n,!0):e.addEventListener(t,n,{capture:!0,passive:i}):i===void 0?e.addEventListener(t,n,!1):e.addEventListener(t,n,{passive:i})}function Kf(e,t,n,r,i){var a=r;if(!(t&1)&&!(t&2)&&r!==null)a:for(;;){if(r===null)return;var s=r.tag;if(s===3||s===4){var c=r.stateNode.containerInfo;if(c===i)break;if(s===4)for(s=r.return;s!==null;){var l=s.tag;if((l===3||l===4)&&s.stateNode.containerInfo===i)return;s=s.return}for(;c!==null;){if(s=Ut(c),s===null)return;if(l=s.tag,l===5||l===6||l===26||l===27){r=a=s;continue a}c=c.parentNode}}r=r.return}Fn(function(){var r=a,i=An(n),s=[];a:{var c=Ci.get(e);if(c!==void 0){var l=Yn,u=e;switch(e){case`keypress`:if(Wn(n)===0)break a;case`keydown`:case`keyup`:l=pr;break;case`focusin`:u=`focus`,l=ir;break;case`focusout`:u=`blur`,l=ir;break;case`beforeblur`:case`afterblur`:l=ir;break;case`click`:if(n.button===2)break a;case`auxclick`:case`dblclick`:case`mousedown`:case`mousemove`:case`mouseup`:case`mouseout`:case`mouseover`:case`contextmenu`:l=nr;break;case`drag`:case`dragend`:case`dragenter`:case`dragexit`:case`dragleave`:case`dragover`:case`dragstart`:case`drop`:l=rr;break;case`touchcancel`:case`touchend`:case`touchmove`:case`touchstart`:l=gr;break;case gi:case _i:case vi:l=ar;break;case Si:l=_r;break;case`scroll`:case`scrollend`:l=Zn;break;case`wheel`:l=vr;break;case`copy`:case`cut`:case`paste`:l=or;break;case`gotpointercapture`:case`lostpointercapture`:case`pointercancel`:case`pointerdown`:case`pointermove`:case`pointerout`:case`pointerover`:case`pointerup`:l=mr;break;case`submit`:l=hr;break;case`toggle`:case`beforetoggle`:l=yr}var d=!!(t&4),f=!d&&(e===`scroll`||e===`scrollend`),p=d?c===null?null:c+`Capture`:c;d=[];for(var m=r,h;m!==null;){var g=m;if(h=g.stateNode,g=g.tag,g!==5&&g!==26&&g!==27||h===null||p===null||(g=In(m,p),g!=null&&d.push(qf(m,g,h))),f)break;m=m.return}0<d.length&&(c=new l(c,u,null,n,i),s.push({event:c,listeners:d}))}}if(!(t&7)){a:{if(l=e===`mouseover`||e===`pointerover`,c=e===`mouseout`||e===`pointerout`,l&&n!==kn&&(u=n.relatedTarget||n.fromElement)&&(Ut(u)||u[Ft]))break a;(c||l)&&(u=i.window===i?i:(l=i.ownerDocument)?l.defaultView||l.parentWindow:window,c?(l=n.relatedTarget||n.toElement,c=r,l=l?Ut(l):null,l!==null&&(f=o(l),d=l.tag,l!==f||d!==5&&d!==27&&d!==6)&&(l=null)):(c=null,l=r),c!==l&&(d=nr,g=`onMouseLeave`,p=`onMouseEnter`,m=`mouse`,(e===`pointerout`||e===`pointerover`)&&(d=mr,g=`onPointerLeave`,p=`onPointerEnter`,m=`pointer`),f=c==null?u:Gt(c),h=l==null?u:Gt(l),u=new d(g,m+`leave`,c,n,i),u.target=f,u.relatedTarget=h,g=null,Ut(i)===r&&(d=new d(p,m+`enter`,l,n,i),d.target=h,d.relatedTarget=f,g=d),f=g,d=c&&l?ne(c,l,Yf):null,c!==null&&Xf(s,u,c,d,!1),l!==null&&f!==null&&Xf(s,f,l,d,!0)))}a:{if(c=r?Gt(r):window,l=c.nodeName&&c.nodeName.toLowerCase(),l===`select`||l===`input`&&c.type===`file`)var _=zr;else if(Nr(c)){if(Br)_=Yr;else{_=qr;var v=Kr}}else l=c.nodeName,!l||l.toLowerCase()!==`input`||c.type!==`checkbox`&&c.type!==`radio`?r&&wn(r.elementType)&&(_=zr):_=Jr;if(_&&=_(e,r)){Pr(s,_,n,i);break a}v&&v(e,c,r)}switch(v=r?Gt(r):window,e){case`focusin`:(Nr(v)||v.contentEditable===`true`)&&(oi=v,si=r,ci=null);break;case`focusout`:ci=si=oi=null;break;case`mousedown`:li=!0;break;case`contextmenu`:case`mouseup`:case`dragend`:li=!1,ui(s,n,i);break;case`selectionchange`:if(ai)break;case`keydown`:case`keyup`:ui(s,n,i)}var y;if(xr)b:{switch(e){case`compositionstart`:var b=`onCompositionStart`;break b;case`compositionend`:b=`onCompositionEnd`;break b;case`compositionupdate`:b=`onCompositionUpdate`;break b}b=void 0}else kr?Dr(e,n)&&(b=`onCompositionEnd`):e===`keydown`&&n.keyCode===229&&(b=`onCompositionStart`);b&&(wr&&n.locale!==`ko`&&(kr||b!==`onCompositionStart`?b===`onCompositionEnd`&&kr&&(y=Un()):(Bn=i,Vn=`value`in Bn?Bn.value:Bn.textContent,kr=!0)),v=Jf(r,b),0<v.length&&(b=new sr(b,e,null,n,i),s.push({event:b,listeners:v}),y?b.data=y:(y=Or(n),y!==null&&(b.data=y)))),(y=Cr?Ar(e,n):jr(e,n))&&(b=Jf(r,`onBeforeInput`),0<b.length&&(v=new sr(`onBeforeInput`,`beforeinput`,null,n,i),s.push({event:v,listeners:b}),v.data=y)),If(s,e,r,n,i)}Vf(s,t)})}function qf(e,t,n){return{instance:e,listener:t,currentTarget:n}}function Jf(e,t){for(var n=t+`Capture`,r=[];e!==null;){var i=e,a=i.stateNode;if(i=i.tag,i!==5&&i!==26&&i!==27||a===null||(i=In(e,n),i!=null&&r.unshift(qf(e,i,a)),i=In(e,t),i!=null&&r.push(qf(e,i,a))),e.tag===3)return r;e=e.return}return[]}function Yf(e){if(e===null)return null;do e=e.return;while(e&&e.tag!==5&&e.tag!==27);return e||null}function Xf(e,t,n,r,i){for(var a=t._reactName,o=[];n!==null&&n!==r;){var s=n,c=s.alternate,l=s.stateNode;if(s=s.tag,c!==null&&c===r)break;s!==5&&s!==26&&s!==27||l===null||(c=l,i?(l=In(n,a),l!=null&&o.unshift(qf(n,l,c))):i||(l=In(n,a),l!=null&&o.push(qf(n,l,c)))),n=n.return}o.length!==0&&e.push({event:t,listeners:o})}var Zf=/\r\n?/g,Qf=/\u0000|\uFFFD/g;function $f(e){return(typeof e==`string`?e:``+e).replace(Zf,`
`).replace(Qf,``)}function ep(e,t){return t=$f(t),$f(e)===t}function $(e,t,n,r,a,o){switch(n){case`children`:if(typeof r==`string`)t===`body`||t===`textarea`&&r===``||bn(e,r);else if(typeof r==`number`||typeof r==`bigint`)t!==`body`&&bn(e,``+r);else return;break;case`className`:an(e,`class`,r);break;case`tabIndex`:an(e,`tabindex`,r);break;case`dir`:case`role`:case`viewBox`:case`width`:case`height`:an(e,n,r);break;case`style`:Cn(e,r,o);return;case`data`:if(t!==`object`){an(e,`data`,r);break}case`src`:case`href`:if(r===``&&(t!==`a`||n!==`href`)){e.removeAttribute(n);break}if(r==null||typeof r==`function`||typeof r==`symbol`||typeof r==`boolean`){e.removeAttribute(n);break}r=Dn(r),e.setAttribute(n,r);break;case`action`:case`formAction`:if(typeof r==`function`){e.setAttribute(n,`javascript:throw new Error('A React form was unexpectedly submitted. If you called form.submit() manually, consider using form.requestSubmit() instead. If you\\'re trying to use event.stopPropagation() in a submit event handler, consider also calling event.preventDefault().')`);break}if(typeof o==`function`&&(n===`formAction`?(t!==`input`&&$(e,t,`name`,a.name,a,null),$(e,t,`formEncType`,a.formEncType,a,null),$(e,t,`formMethod`,a.formMethod,a,null),$(e,t,`formTarget`,a.formTarget,a,null)):($(e,t,`encType`,a.encType,a,null),$(e,t,`method`,a.method,a,null),$(e,t,`target`,a.target,a,null))),r==null||typeof r==`symbol`||typeof r==`boolean`){e.removeAttribute(n);break}r=Dn(r),e.setAttribute(n,r);break;case`onClick`:r!=null&&(e.onclick=On);return;case`onScroll`:r!=null&&Q(`scroll`,e);return;case`onScrollEnd`:r!=null&&Q(`scrollend`,e);return;case`dangerouslySetInnerHTML`:if(r!=null){if(typeof r!=`object`||!(`__html`in r))throw Error(i(61));if(n=r.__html,n!=null){if(a.children!=null)throw Error(i(60));o?.__html!==n&&(e.innerHTML=n)}}break;case`multiple`:e.multiple=r&&typeof r!=`function`&&typeof r!=`symbol`;break;case`muted`:e.muted=r&&typeof r!=`function`&&typeof r!=`symbol`;break;case`suppressContentEditableWarning`:case`suppressHydrationWarning`:case`defaultValue`:case`defaultChecked`:case`innerHTML`:case`ref`:break;case`autoFocus`:break;case`xlinkHref`:if(r==null||typeof r==`function`||typeof r==`boolean`||typeof r==`symbol`){e.removeAttribute(`xlink:href`);break}n=Dn(r),e.setAttributeNS(`http://www.w3.org/1999/xlink`,`xlink:href`,n);break;case`contentEditable`:case`spellCheck`:case`draggable`:case`value`:case`autoReverse`:case`externalResourcesRequired`:case`focusable`:case`preserveAlpha`:r!=null&&typeof r!=`function`&&typeof r!=`symbol`?e.setAttribute(n,r):e.removeAttribute(n);break;case`inert`:case`allowFullScreen`:case`async`:case`autoPlay`:case`controls`:case`credentialless`:case`default`:case`defer`:case`disabled`:case`disablePictureInPicture`:case`disableRemotePlayback`:case`formNoValidate`:case`hidden`:case`loop`:case`noModule`:case`noValidate`:case`open`:case`playsInline`:case`readOnly`:case`required`:case`reversed`:case`scoped`:case`seamless`:case`itemScope`:r&&typeof r!=`function`&&typeof r!=`symbol`?e.setAttribute(n,``):e.removeAttribute(n);break;case`capture`:case`download`:!0===r?e.setAttribute(n,``):!1!==r&&r!=null&&typeof r!=`function`&&typeof r!=`symbol`?e.setAttribute(n,r):e.removeAttribute(n);break;case`cols`:case`rows`:case`size`:case`span`:r!=null&&typeof r!=`function`&&typeof r!=`symbol`&&!isNaN(r)&&1<=r?e.setAttribute(n,r):e.removeAttribute(n);break;case`rowSpan`:case`start`:r==null||typeof r==`function`||typeof r==`symbol`||isNaN(r)?e.removeAttribute(n):e.setAttribute(n,r);break;case`popover`:Q(`beforetoggle`,e),Q(`toggle`,e),rn(e,`popover`,r);break;case`xlinkActuate`:on(e,`http://www.w3.org/1999/xlink`,`xlink:actuate`,r);break;case`xlinkArcrole`:on(e,`http://www.w3.org/1999/xlink`,`xlink:arcrole`,r);break;case`xlinkRole`:on(e,`http://www.w3.org/1999/xlink`,`xlink:role`,r);break;case`xlinkShow`:on(e,`http://www.w3.org/1999/xlink`,`xlink:show`,r);break;case`xlinkTitle`:on(e,`http://www.w3.org/1999/xlink`,`xlink:title`,r);break;case`xlinkType`:on(e,`http://www.w3.org/1999/xlink`,`xlink:type`,r);break;case`xmlBase`:on(e,`http://www.w3.org/XML/1998/namespace`,`xml:base`,r);break;case`xmlLang`:on(e,`http://www.w3.org/XML/1998/namespace`,`xml:lang`,r);break;case`xmlSpace`:on(e,`http://www.w3.org/XML/1998/namespace`,`xml:space`,r);break;case`is`:rn(e,`is`,r);break;case`innerText`:case`textContent`:return;default:if(!(2<n.length)||n[0]!==`o`&&n[0]!==`O`||n[1]!==`n`&&n[1]!==`N`)n=Tn.get(n)||n,rn(e,n,r);else return}k=!0}function tp(e,t,n,r,a,o){switch(n){case`style`:Cn(e,r,o);return;case`dangerouslySetInnerHTML`:if(r!=null){if(typeof r!=`object`||!(`__html`in r))throw Error(i(61));if(n=r.__html,n!=null){if(a.children!=null)throw Error(i(60));o?.__html!==n&&(e.innerHTML=n)}}break;case`children`:if(typeof r==`string`)bn(e,r);else if(typeof r==`number`||typeof r==`bigint`)bn(e,``+r);else return;break;case`onScroll`:r!=null&&Q(`scroll`,e);return;case`onScrollEnd`:r!=null&&Q(`scrollend`,e);return;case`onClick`:r!=null&&(e.onclick=On);return;case`suppressContentEditableWarning`:case`suppressHydrationWarning`:case`innerHTML`:case`ref`:return;case`innerText`:case`textContent`:return;default:if(!Yt.hasOwnProperty(n))a:{if(n[0]===`o`&&n[1]===`n`&&(a=n.endsWith(`Capture`),o=n.slice(2,a?n.length-7:void 0),t=e[Pt]||null,t=t==null?null:t[n],typeof t==`function`&&e.removeEventListener(o,t,a),typeof r==`function`)){typeof t!=`function`&&t!==null&&(n in e?e[n]=null:e.hasAttribute(n)&&e.removeAttribute(n)),e.addEventListener(o,r,a);break a}k=!0,n in e?e[n]=r:!0===r?e.setAttribute(n,``):rn(e,n,r)}return}k=!0}function np(e,t,n){switch(t){case`div`:case`span`:case`svg`:case`path`:case`a`:case`g`:case`p`:case`li`:break;case`img`:Q(`error`,e),Q(`load`,e);var r=!1,a=!1,o;for(o in n)if(n.hasOwnProperty(o)){var s=n[o];if(s!=null)switch(o){case`src`:r=!0;break;case`srcSet`:a=!0;break;case`children`:case`dangerouslySetInnerHTML`:throw Error(i(137,t));default:$(e,t,o,s,n,null)}}a&&$(e,t,`srcSet`,n.srcSet,n,null),r&&$(e,t,`src`,n.src,n,null);return;case`input`:Q(`invalid`,e);var c=o=s=a=null,l=null,u=null;for(r in n)if(n.hasOwnProperty(r)){var d=n[r];if(d!=null)switch(r){case`name`:a=d;break;case`type`:s=d;break;case`checked`:l=d;break;case`defaultChecked`:u=d;break;case`value`:o=d;break;case`defaultValue`:c=d;break;case`children`:case`dangerouslySetInnerHTML`:if(d!=null)throw Error(i(137,t));break;default:$(e,t,r,d,n,null)}}hn(e,o,c,l,u,s,a,!1);return;case`select`:for(a in Q(`invalid`,e),r=s=o=null,n)if(n.hasOwnProperty(a)&&(c=n[a],c!=null))switch(a){case`value`:o=c;break;case`defaultValue`:s=c;break;case`multiple`:r=c;default:$(e,t,a,c,n,null)}t=o,n=s,e.multiple=!!r,t==null?n!=null&&_n(e,!!r,n,!0):_n(e,!!r,t,!1);return;case`textarea`:for(s in Q(`invalid`,e),o=a=r=null,n)if(n.hasOwnProperty(s)&&(c=n[s],c!=null))switch(s){case`value`:r=c;break;case`defaultValue`:a=c;break;case`children`:o=c;break;case`dangerouslySetInnerHTML`:if(c!=null)throw Error(i(91));break;default:$(e,t,s,c,n,null)}yn(e,r,a,o);return;case`option`:for(l in n)if(n.hasOwnProperty(l)&&(r=n[l],r!=null))switch(l){case`selected`:e.selected=r&&typeof r!=`function`&&typeof r!=`symbol`;break;default:$(e,t,l,r,n,null)}return;case`dialog`:Q(`beforetoggle`,e),Q(`toggle`,e),Q(`cancel`,e),Q(`close`,e);break;case`iframe`:case`object`:Q(`load`,e);break;case`video`:case`audio`:for(r=0;r<zf.length;r++)Q(zf[r],e);break;case`image`:Q(`error`,e),Q(`load`,e);break;case`details`:Q(`toggle`,e);break;case`embed`:case`source`:case`link`:Q(`error`,e),Q(`load`,e);case`area`:case`base`:case`br`:case`col`:case`hr`:case`keygen`:case`meta`:case`param`:case`track`:case`wbr`:case`menuitem`:for(u in n)if(n.hasOwnProperty(u)&&(r=n[u],r!=null))switch(u){case`children`:case`dangerouslySetInnerHTML`:throw Error(i(137,t));default:$(e,t,u,r,n,null)}return;default:if(wn(t)){for(d in n)n.hasOwnProperty(d)&&(r=n[d],r!==void 0&&tp(e,t,d,r,n,void 0));return}}for(c in n)n.hasOwnProperty(c)&&(r=n[c],r!=null&&$(e,t,c,r,n,null))}var rp={};function ip(e,t,n,r){switch(t){case`div`:case`span`:case`svg`:case`path`:case`a`:case`g`:case`p`:case`li`:break;case`input`:var a=null,o=null,s=null,c=null,l=null,u=null,d=null;for(m in n){var f=n[m];if(n.hasOwnProperty(m)&&f!=null)switch(m){case`checked`:break;case`value`:break;case`defaultValue`:l=f;default:r.hasOwnProperty(m)||$(e,t,m,null,r,f)}}for(var p in r){var m=r[p];if(f=n[p],r.hasOwnProperty(p)&&(m!=null||f!=null))switch(p){case`type`:m!==f&&(k=!0),o=m;break;case`name`:m!==f&&(k=!0),a=m;break;case`checked`:m!==f&&(k=!0),u=m;break;case`defaultChecked`:m!==f&&(k=!0),d=m;break;case`value`:m!==f&&(k=!0),s=m;break;case`defaultValue`:m!==f&&(k=!0),c=m;break;case`children`:case`dangerouslySetInnerHTML`:if(m!=null)throw Error(i(137,t));break;default:m!==f&&$(e,t,p,m,r,f)}}mn(e,s,c,l,u,d,o,a);return;case`select`:for(o in m=s=c=p=null,n)if(l=n[o],n.hasOwnProperty(o)&&l!=null)switch(o){case`value`:break;case`multiple`:m=l;default:r.hasOwnProperty(o)||$(e,t,o,null,r,l)}for(a in r)if(o=r[a],l=n[a],r.hasOwnProperty(a)&&(o!=null||l!=null))switch(a){case`value`:o!==l&&(k=!0),p=o;break;case`defaultValue`:o!==l&&(k=!0),c=o;break;case`multiple`:o!==l&&(k=!0),s=o;default:o!==l&&$(e,t,a,o,r,l)}t=c,n=s,r=m,p==null?!!r!=!!n&&(t==null?_n(e,!!n,n?[]:``,!1):_n(e,!!n,t,!0)):_n(e,!!n,p,!1);return;case`textarea`:for(c in m=p=null,n)if(a=n[c],n.hasOwnProperty(c)&&a!=null&&!r.hasOwnProperty(c))switch(c){case`value`:break;case`children`:break;default:$(e,t,c,null,r,a)}for(s in r)if(a=r[s],o=n[s],r.hasOwnProperty(s)&&(a!=null||o!=null))switch(s){case`value`:a!==o&&(k=!0),p=a;break;case`defaultValue`:a!==o&&(k=!0),m=a;break;case`children`:break;case`dangerouslySetInnerHTML`:if(a!=null)throw Error(i(91));break;default:a!==o&&$(e,t,s,a,r,o)}vn(e,p,m);return;case`option`:for(var h in n)if(p=n[h],n.hasOwnProperty(h)&&p!=null&&!r.hasOwnProperty(h))switch(h){case`selected`:e.selected=!1;break;default:$(e,t,h,null,r,p)}for(l in r)if(p=r[l],m=n[l],r.hasOwnProperty(l)&&p!==m&&(p!=null||m!=null))switch(l){case`selected`:p!==m&&(k=!0),e.selected=p&&typeof p!=`function`&&typeof p!=`symbol`;break;default:$(e,t,l,p,r,m)}return;case`img`:case`link`:case`area`:case`base`:case`br`:case`col`:case`embed`:case`hr`:case`keygen`:case`meta`:case`param`:case`source`:case`track`:case`wbr`:case`menuitem`:for(var g in n)p=n[g],n.hasOwnProperty(g)&&p!=null&&!r.hasOwnProperty(g)&&$(e,t,g,null,r,p);for(u in r)if(p=r[u],m=n[u],r.hasOwnProperty(u)&&p!==m&&(p!=null||m!=null))switch(u){case`children`:case`dangerouslySetInnerHTML`:if(p!=null)throw Error(i(137,t));break;default:$(e,t,u,p,r,m)}return;default:if(wn(t)){for(var _ in n)p=n[_],n.hasOwnProperty(_)&&p!==void 0&&!r.hasOwnProperty(_)&&tp(e,t,_,void 0,r,p);for(d in r)p=r[d],m=n[d],!r.hasOwnProperty(d)||p===m||p===void 0&&m===void 0||tp(e,t,d,p,r,m);return}}for(var v in n)p=n[v],n.hasOwnProperty(v)&&p!=null&&!r.hasOwnProperty(v)&&$(e,t,v,null,r,p);for(f in r)p=r[f],m=n[f],!r.hasOwnProperty(f)||p===m||p==null&&m==null||$(e,t,f,p,r,m)}function ap(e){switch(e){case`css`:case`script`:case`font`:case`img`:case`image`:case`input`:case`link`:return!0;default:return!1}}function op(){if(typeof performance.getEntriesByType==`function`){for(var e=0,t=0,n=performance.getEntriesByType(`resource`),r=0;r<n.length;r++){var i=n[r],a=i.transferSize,o=i.initiatorType,s=i.duration;if(a&&s&&ap(o)){for(o=0,s=i.responseEnd,r+=1;r<n.length;r++){var c=n[r],l=c.startTime;if(l>s)break;var u=c.transferSize,d=c.initiatorType;u&&ap(d)&&(c=c.responseEnd,o+=u*(c<s?1:(s-l)/(c-l)))}if(--r,t+=8*(a+o)/(i.duration/1e3),e++,10<e)break}}if(0<e)return t/e/1e6}return navigator.connection&&(e=navigator.connection.downlink,typeof e==`number`)?e:5}var sp=null,cp=null;function lp(e){return e.nodeType===9?e:e.ownerDocument}function up(e){switch(e){case`http://www.w3.org/2000/svg`:return 1;case`http://www.w3.org/1998/Math/MathML`:return 2;default:return 0}}function dp(e,t){if(e===0)switch(t){case`svg`:return 1;case`math`:return 2;default:return 0}return e===1&&t===`foreignObject`?0:e}function fp(e,t,n,r){return n=lp(n).createElement(e),n[Nt]=r,n[Pt]=t,np(n,e,t),O(n),n}function pp(e,t){return e===`textarea`||e===`noscript`||typeof t.children==`string`||typeof t.children==`number`||typeof t.children==`bigint`||typeof t.dangerouslySetInnerHTML==`object`&&t.dangerouslySetInnerHTML!==null&&t.dangerouslySetInnerHTML.__html!=null}var mp=null;function hp(){var e=window.event;return e&&e.type===`popstate`?e!==mp&&(mp=e,!0):(mp=null,!1)}var gp=typeof setTimeout==`function`?setTimeout:void 0,_p=typeof clearTimeout==`function`?clearTimeout:void 0,vp=typeof Promise==`function`?Promise:void 0,yp=typeof requestAnimationFrame==`function`?requestAnimationFrame:gp,bp=typeof queueMicrotask==`function`?queueMicrotask:vp===void 0?gp:function(e){return vp.resolve(null).then(e).catch(xp)};function xp(e){setTimeout(function(){throw e})}function Sp(e){return e===`head`}function Cp(e,t){var n=t,r=0;do{var i=n.nextSibling;if(e.removeChild(n),i&&i.nodeType===8){if(n=i.data,n===`/$`||n===`/&`){if(r===0){e.removeChild(i),Hh(t);return}r--}else if(n===`$`||n===`$?`||n===`$~`||n===`$!`||n===`&`)r++;else if(n===`html`)_m(e.ownerDocument.documentElement);else if(n===`head`){n=e.ownerDocument.head,_m(n);for(var a=n.firstChild;a;){var o=a.nextSibling,s=a.nodeName;a[Bt]||s===`SCRIPT`||s===`STYLE`||s===`LINK`&&a.rel.toLowerCase()===`stylesheet`||n.removeChild(a),a=o}}else n===`body`&&_m(e.ownerDocument.body)}n=i}while(n);Hh(t)}function wp(e,t){var n=e;e=0;do{var r=n.nextSibling;if(n.nodeType===1?t?(n._stashedDisplay=n.style.display,n.style.display=`none`):(n.style.display=n._stashedDisplay||``,n.getAttribute(`style`)===``&&n.removeAttribute(`style`)):n.nodeType===3&&(t?(n._stashedText=n.nodeValue,n.nodeValue=``):n.nodeValue=n._stashedText||``),r&&r.nodeType===8){if(n=r.data,n===`/$`){if(e===0)break;e--}else n!==`$`&&n!==`$?`&&n!==`$~`&&n!==`$!`||e++}n=r}while(n)}function Tp(e,t,n){if(t=CSS.escape(t)===t?t:`r-`+btoa(t).replace(/=/g,``),e.style.viewTransitionName=t,n!=null&&(e.style.viewTransitionClass=n),n=getComputedStyle(e),n.display===`inline`){if(t=e.getClientRects(),t.length===1)var r=1;else for(var i=r=0;i<t.length;i++){var a=t[i];0<a.width&&0<a.height&&r++}r===1&&(e=e.style,e.display=t.length===1?`inline-block`:`block`,e.marginTop=`-`+n.paddingTop,e.marginBottom=`-`+n.paddingBottom)}}function Ep(e,t){e=e.style,t=t.style;var n=t==null?null:t.hasOwnProperty(`viewTransitionName`)?t.viewTransitionName:t.hasOwnProperty(`view-transition-name`)?t[`view-transition-name`]:null;e.viewTransitionName=n==null||typeof n==`boolean`?``:(``+n).trim(),n=t==null?null:t.hasOwnProperty(`viewTransitionClass`)?t.viewTransitionClass:t.hasOwnProperty(`view-transition-class`)?t[`view-transition-class`]:null,e.viewTransitionClass=n==null||typeof n==`boolean`?``:(``+n).trim(),e.display===`inline-block`&&(t==null?e.display=e.margin=``:(n=t.display,e.display=n==null||typeof n==`boolean`?``:n,n=t.margin,n==null?(n=t.hasOwnProperty(`marginTop`)?t.marginTop:t[`margin-top`],e.marginTop=n==null||typeof n==`boolean`?``:n,t=t.hasOwnProperty(`marginBottom`)?t.marginBottom:t[`margin-bottom`],e.marginBottom=t==null||typeof t==`boolean`?``:t):e.margin=n))}function Dp(e,t,n){return n=n.ownerDocument.defaultView,{rect:e,abs:t.position===`absolute`||t.position===`fixed`,clip:t.clipPath!==`none`||t.overflow!==`visible`||t.filter!==`none`||t.mask!==`none`||t.mask!==`none`||t.borderRadius!==`0px`,view:0<=e.bottom&&0<=e.right&&e.top<=n.innerHeight&&e.left<=n.innerWidth}}function Op(e){return Dp(e.getBoundingClientRect(),getComputedStyle(e),e)}function kp(e){var t=e.getBoundingClientRect();t=new DOMRect(t.x+2e4,t.y+2e4,t.width,t.height);var n=getComputedStyle(e);return Dp(t,n,e)}function Ap(e){return e.documentElement.clientHeight}function jp(e){this.addEventListener(`load`,e),this.addEventListener(`error`,e)}function Mp(e,t,n,r,i,a,o,s,c){var l=t.nodeType===9?t:t.ownerDocument;try{var u=l.startViewTransition({update:function(){var t=l.defaultView,n=t.navigation&&t.navigation.transition,o=l.fonts.status;r();var s=[];if(o===`loaded`&&(Ap(l),l.fonts.status===`loading`&&s.push(l.fonts.ready)),o=s.length,e!==null)for(var c=e.suspenseyImages,u=0,d=0;d<c.length;d++){var f=c[d];if(!f.complete){var p=f.getBoundingClientRect();if(0<p.bottom&&0<p.right&&p.top<t.innerHeight&&p.left<t.innerWidth){if(u+=Xm(f),u>$m){s.length=o;break}f=new Promise(jp.bind(f)),s.push(f)}}}if(0<s.length)return t=Promise.race([Promise.all(s),new Promise(function(e){return setTimeout(e,500)})]).then(i,i),(n?Promise.allSettled([n.finished,t]):t).then(a,a);if(i(),n)return n.finished.then(a,a);a()},types:n});l.__reactViewTransition=u;var d=[];return u.ready.then(function(){for(var e=l.documentElement.getAnimations({subtree:!0}),t=0;t<e.length;t++){var n=e[t],r=n.effect,i=r.pseudoElement;if(i!=null&&i.startsWith(`::view-transition`)){d.push(n),n=r.getKeyframes();for(var a=i=void 0,s=!0,c=0;c<n.length;c++){var u=n[c],f=u.width;if(i===void 0)i=f;else if(i!==f){s=!1;break}if(f=u.height,a===void 0)a=f;else if(a!==f){s=!1;break}delete u.width,delete u.height,u.transform===`none`&&delete u.transform}s&&i!==void 0&&a!==void 0&&(r.setKeyframes(n),s=getComputedStyle(r.target,r.pseudoElement),s.width!==i||s.height!==a)&&(s=n[0],s.width=i,s.height=a,s=n[n.length-1],s.width=i,s.height=a,r.setKeyframes(n))}}o()},function(e){l.__reactViewTransition===u&&(l.__reactViewTransition=null);try{if(typeof e==`object`&&e)switch(e.name){case`InvalidStateError`:(e.message===`View transition was skipped because document visibility state is hidden.`||e.message===`Skipping view transition because document visibility state has become hidden.`||e.message===`Skipping view transition because viewport size changed.`||e.message===`Transition was aborted because of invalid state`)&&(e=null)}e!==null&&c(e)}finally{r(),i(),o()}}),u.finished.finally(function(){for(var e=0;e<d.length;e++)d[e].cancel();l.__reactViewTransition===u&&(l.__reactViewTransition=null),s()}),u}catch{return r(),i(),o(),null}}function Np(e,t){this._scope=document.documentElement,this._selector=`::view-transition-`+e+`(`+t+`)`}Np.prototype.animate=function(e,t){return t=typeof t==`number`?{duration:t}:w({},t),t.pseudoElement=this._selector,this._scope.animate(e,t)},Np.prototype.getAnimations=function(){for(var e=this._scope,t=this._selector,n=e.getAnimations({subtree:!0}),r=[],i=0;i<n.length;i++){var a=n[i].effect;a!==null&&a.target===e&&a.pseudoElement===t&&r.push(n[i])}return r},Np.prototype.getComputedStyle=function(){return getComputedStyle(this._scope,this._selector)};function Pp(e){return{name:e,group:new Np(`group`,e),imagePair:new Np(`image-pair`,e),old:new Np(`old`,e),new:new Np(`new`,e)}}function Fp(e){this._fragmentFiber=e,this._observers=this._eventListeners=null}Fp.prototype.addEventListener=function(e,t,n){var r=null,i=null;if(!(n!=null&&typeof n!=`boolean`&&(r=n.signal||null,r!==null&&r.aborted))){this._eventListeners===null&&(this._eventListeners=[]);var a=this._eventListeners;if(Bp(a,e,t,n)===-1){var o=this,s=t;n!=null&&typeof n!=`boolean`&&!0===n.once&&(s=function(r){o.removeEventListener(e,t,n),typeof t==`function`?t.call(this,r):t.handleEvent(r)}),r!==null&&(i=o.removeEventListener.bind(o,e,t,n),r.addEventListener(`abort`,i,{once:!0}),i=r.removeEventListener.bind(r,`abort`,i)),r=Rp(n),a.push({type:e,listener:t,optionsOrUseCapture:n,attachedListener:s,cleanup:i}),h(this._fragmentFiber.child,!1,Ip,e,s,r)}this._eventListeners=a}};function Ip(e,t,n,r){return b(e).addEventListener(t,n,r),!1}Fp.prototype.removeEventListener=function(e,t,n){var r=this._eventListeners;if(r!==null&&(t=Bp(r,e,t,n),t!==-1)){var i=r[t];n=i.attachedListener;var a=i.cleanup;i=Rp(i.optionsOrUseCapture),h(this._fragmentFiber.child,!1,Lp,e,n,i),r.splice(t,1),a!==null&&a()}};function Lp(e,t,n,r){return b(e).removeEventListener(t,n,r),!1}function Rp(e){return e!=null&&typeof e!=`boolean`&&(!0===e.once||e.signal instanceof AbortSignal)?{capture:e.capture,passive:e.passive}:e}function zp(e){return e==null?`c=0`:typeof e==`boolean`?`c=`+(e?`1`:`0`):`c=`+(e.capture?`1`:`0`)}function Bp(e,t,n,r){if(e.length===0)return-1;r=zp(r);for(var i=0;i<e.length;i++){var a=e[i];if(a.type===t&&a.listener===n&&zp(a.optionsOrUseCapture)===r)return i}return-1}Fp.prototype.dispatchEvent=function(e){var t=g(this._fragmentFiber);if(t===null)return!0;t=b(t);var n=this._eventListeners;if(n!==null&&0<n.length||!e.bubbles){var r=t.nodeType===9?t.createComment(``):document.createTextNode(``);if(n)for(var i=0;i<n.length;i++){var a=n[i];r.addEventListener(a.type,a.attachedListener,Rp(a.optionsOrUseCapture))}if(t.appendChild(r),e=r.dispatchEvent(e),n)for(i=0;i<n.length;i++)a=n[i],r.removeEventListener(a.type,a.attachedListener,Rp(a.optionsOrUseCapture));return t.removeChild(r),e}return t.dispatchEvent(e)},Fp.prototype.focus=function(e){h(this._fragmentFiber.child,!0,Vp,e,void 0,void 0)};function Vp(e,t){return e.tag!==6&&(e=b(e),pm(e,t))}Fp.prototype.focusLast=function(e){var t=[];h(this._fragmentFiber.child,!0,Hp,t,void 0,void 0);for(var n=t.length-1;0<=n&&!Vp(t[n],e);n--);};function Hp(e,t){return t.push(e),!1}Fp.prototype.blur=function(){var e=g(this._fragmentFiber);e!==null&&(e=b(e),e=lp(e).activeElement,e!==null&&h(this._fragmentFiber.child,!1,Up,e,void 0,void 0))};function Up(e,t){return e.tag!==6&&(e=b(e),e===t||e.contains(t)?(t.blur(),!0):!1)}Fp.prototype.observeUsing=function(e){this._observers===null&&(this._observers=new Set),this._observers.add(e),h(this._fragmentFiber.child,!1,Wp,e,void 0,void 0)};function Wp(e,t){return e.tag!==6&&(e=b(e),t.observe(e),!1)}Fp.prototype.unobserveUsing=function(e){var t=this._observers;if(t!==null&&t.has(e)){t.delete(e),h(this._fragmentFiber.child,!1,Gp,e,void 0,void 0);for(var n=t=0;n<Kp.length;n++){var r=Kp[n];r.fragmentInstance===this&&r.observer===e?e.unobserve(r.instance):Kp[t++]=r}Kp.length=t}};function Gp(e,t){return e.tag!==6&&(e=b(e),t.unobserve(e),!1)}var Kp=[],qp=!1;function Jp(e,t,n){Kp.push({fragmentInstance:e,observer:t,instance:n}),qp||(qp=!0,mm(function(){qp=!1;var e=Kp;Kp=[];for(var t=0;t<e.length;t++){var n=e[t];n.observer.unobserve(n.instance)}}))}Fp.prototype.getClientRects=function(){var e=[];return h(this._fragmentFiber.child,!1,Yp,e,void 0,void 0),e};function Yp(e,t){if(e.tag===6){e=e.stateNode;var n=e.ownerDocument.createRange();n.selectNodeContents(e),t.push.apply(t,n.getClientRects())}else e=b(e),t.push.apply(t,e.getClientRects());return!1}Fp.prototype.getRootNode=function(e){var t=g(this._fragmentFiber);return t===null?this:b(t).getRootNode(e)},Fp.prototype.compareDocumentPosition=function(e){var t=g(this._fragmentFiber);if(t===null)return Node.DOCUMENT_POSITION_DISCONNECTED;var n=[];h(this._fragmentFiber.child,!1,Hp,n,void 0,void 0);var r=b(t);if(n.length===0){if(n=r,_(this._fragmentFiber)){a:{for(t=this._fragmentFiber.return;t!==null;){if(t.tag===4){t=t.stateNode.containerInfo;break a}if(t.tag===3||t.tag===5||t.tag===27)break;t=t.return}t=null}t!=null&&(n=t)}t=this._fragmentFiber;var i=r=n.compareDocumentPosition(e);return n===e?i=Node.DOCUMENT_POSITION_CONTAINS:r&Node.DOCUMENT_POSITION_CONTAINED_BY&&(n=v(t)[1],n===null?i=Node.DOCUMENT_POSITION_PRECEDING:(e=b(n).compareDocumentPosition(e),i=e===0||e&Node.DOCUMENT_POSITION_FOLLOWING?Node.DOCUMENT_POSITION_FOLLOWING:Node.DOCUMENT_POSITION_PRECEDING)),i|=Node.DOCUMENT_POSITION_IMPLEMENTATION_SPECIFIC}t=b(n[0]),i=b(n[n.length-1]);var a=_(this._fragmentFiber)?t.parentElement:r;if(a==null)return Node.DOCUMENT_POSITION_DISCONNECTED;r=a.compareDocumentPosition(t)&Node.DOCUMENT_POSITION_CONTAINED_BY,a=a.compareDocumentPosition(i)&Node.DOCUMENT_POSITION_CONTAINED_BY;var o=t.compareDocumentPosition(e),s=i.compareDocumentPosition(e),c=o&Node.DOCUMENT_POSITION_CONTAINED_BY||s&Node.DOCUMENT_POSITION_CONTAINED_BY;return s=r&&a&&o&Node.DOCUMENT_POSITION_FOLLOWING&&s&Node.DOCUMENT_POSITION_PRECEDING,t=r&&t===e||a&&i===e||c||s?Node.DOCUMENT_POSITION_CONTAINED_BY:!r&&t===e||!a&&i===e?Node.DOCUMENT_POSITION_IMPLEMENTATION_SPECIFIC:o,t&Node.DOCUMENT_POSITION_DISCONNECTED||t&Node.DOCUMENT_POSITION_IMPLEMENTATION_SPECIFIC||Xp(t,this._fragmentFiber,n[0],n[n.length-1],e)?t:Node.DOCUMENT_POSITION_IMPLEMENTATION_SPECIFIC};function Xp(e,t,n,r,i){var a=Ut(i);if(e&Node.DOCUMENT_POSITION_CONTAINED_BY){if(n=!!a)a:{for(;a!==null;){if(a.tag===7&&(a===t||a.alternate===t)){n=!0;break a}a=a.return}n=!1}return n}if(e&Node.DOCUMENT_POSITION_CONTAINS){if(a===null)return a=i.ownerDocument,i===a||i===a.documentElement||i===a.body;a:{for(a=t,t=g(t);a!==null;){if(!(a.tag!==5&&a.tag!==3&&a.tag!==27||a!==t&&a.alternate!==t)){a=!0;break a}a=a.return}a=!1}return a}return e&Node.DOCUMENT_POSITION_PRECEDING?((t=!!a)&&!(t=a===n)&&(t=ne(n,a,C),t===null?t=!1:(h(t,!0,ee,a,n),a=x,x=null,t=a!==null)),t):e&Node.DOCUMENT_POSITION_FOLLOWING?((t=!!a)&&!(t=a===r)&&(t=ne(r,a,C),t===null?t=!1:(h(t,!0,te,a,r),a=x,S=x=null,t=a!==null)),t):!1}function Zp(e,t){var n=e.ownerDocument.createRange();n.selectNodeContents(e),e=n.getBoundingClientRect(),window.scrollTo(window.scrollX+e.left,t?window.scrollY+e.top:window.scrollY+e.bottom-window.innerHeight)}Fp.prototype.scrollIntoView=function(e){if(typeof e==`object`)throw Error(i(566));var t=[];h(this._fragmentFiber.child,!1,Hp,t,void 0,void 0);var n=!1!==e;if(t.length===0){var r=v(this._fragmentFiber);if(r=n?r[1]||r[0]||g(this._fragmentFiber):r[0]||r[1],r===null)return;if(r.tag===6){e=b(r),Zp(e,n);return}if(r=b(r),r.nodeType!==9){if(r.nodeType===11){n=`host`in r?r.host:null,n!==null&&n.scrollIntoView(e);return}r.scrollIntoView(e)}}for(r=n?t.length-1:0;r!==(n?-1:t.length);){var a=t[r];a.tag===6?(a=b(a),Zp(a,n)):b(a).scrollIntoView(e),r+=n?-1:1}};function Qp(e,t){return e=b(e),$p(e,t),!1}function $p(e,t){e.reactFragments??=new Set,e.reactFragments.add(t)}function em(e,t){var n=t._eventListeners;if(n!==null)for(var r=0;r<n.length;r++){var i=n[r];e.addEventListener(i.type,i.attachedListener,Rp(i.optionsOrUseCapture))}e.nodeType!==3&&(n=t._observers,n!==null&&n.forEach(function(n){for(var r=0,i=0;i<Kp.length;i++){var a=Kp[i];(a.fragmentInstance!==t||a.observer!==n||a.instance!==e)&&(Kp[r++]=a)}Kp.length=r,n.observe(e)}),$p(e,t))}function tm(e,t){var n=t._eventListeners;if(n!==null)for(var r=0;r<n.length;r++){var i=n[r];e.removeEventListener(i.type,i.attachedListener,Rp(i.optionsOrUseCapture))}e.nodeType!==3&&(n=t._observers,n!==null&&n.forEach(function(n){typeof n.rootMargin==`string`?Jp(t,n,e):n.unobserve(e)}),e.reactFragments!=null&&e.reactFragments.delete(t))}function nm(e){var t=e.firstChild;for(t&&t.nodeType===10&&(t=t.nextSibling);t;){var n=t;switch(t=t.nextSibling,n.nodeName){case`HTML`:case`HEAD`:case`BODY`:nm(n),Ht(n);continue;case`SCRIPT`:case`STYLE`:continue;case`LINK`:if(n.rel.toLowerCase()===`stylesheet`)continue}e.removeChild(n)}}function rm(e,t,n,r){for(;e.nodeType===1;){var i=n;if(e.nodeName.toLowerCase()!==t.toLowerCase()){if(!r&&(e.nodeName!==`INPUT`||e.type!==`hidden`))break}else if(!r){if(t===`input`&&e.type===`hidden`){var a=i.name==null?null:``+i.name;if(i.type===`hidden`&&e.getAttribute(`name`)===a)return e}else return e}else if(!e[Bt])switch(t){case`meta`:if(!e.hasAttribute(`itemprop`))break;return e;case`link`:if(a=e.getAttribute(`rel`),a===`stylesheet`&&e.hasAttribute(`data-precedence`)||a!==i.rel||e.getAttribute(`href`)!==(i.href==null||i.href===``?null:i.href)||e.getAttribute(`crossorigin`)!==(i.crossOrigin==null?null:i.crossOrigin)||e.getAttribute(`title`)!==(i.title==null?null:i.title))break;return e;case`style`:if(e.hasAttribute(`data-precedence`))break;return e;case`script`:if(a=e.getAttribute(`src`),(a!==(i.src==null?null:i.src)||e.getAttribute(`type`)!==(i.type==null?null:i.type)||e.getAttribute(`crossorigin`)!==(i.crossOrigin==null?null:i.crossOrigin))&&a&&e.hasAttribute(`async`)&&!e.hasAttribute(`itemprop`))break;return e;default:return e}if(e=lm(e.nextSibling),e===null)break}return null}function im(e,t,n){if(t===``)return null;for(;e.nodeType!==3;)if((e.nodeType!==1||e.nodeName!==`INPUT`||e.type!==`hidden`)&&!n||(e=lm(e.nextSibling),e===null))return null;return e}function am(e,t){for(;e.nodeType!==8;)if((e.nodeType!==1||e.nodeName!==`INPUT`||e.type!==`hidden`)&&!t||(e=lm(e.nextSibling),e===null))return null;return e}function om(e){return e.data===`$?`||e.data===`$~`}function sm(e){return e.data===`$!`||e.data===`$?`&&e.ownerDocument.readyState!==`loading`}function cm(e,t){var n=e.ownerDocument;if(e.data===`$~`)e._reactRetry=t;else if(e.data!==`$?`||n.readyState!==`loading`)t();else{var r=function(){t(),n.removeEventListener(`DOMContentLoaded`,r)};n.addEventListener(`DOMContentLoaded`,r),e._reactRetry=r}}function lm(e){for(;e!=null;e=e.nextSibling){var t=e.nodeType;if(t===1||t===3)break;if(t===8){if(t=e.data,t===`$`||t===`$!`||t===`$?`||t===`$~`||t===`&`||t===`F!`||t===`F`)break;if(t===`/$`||t===`/&`)return null}}return e}var um=null;function dm(e){e=e.nextSibling;for(var t=0;e;){if(e.nodeType===8){var n=e.data;if(n===`/$`||n===`/&`){if(t===0)return lm(e.nextSibling);t--}else n!==`$`&&n!==`$!`&&n!==`$?`&&n!==`$~`&&n!==`&`||t++}e=e.nextSibling}return null}function fm(e){e=e.previousSibling;for(var t=0;e;){if(e.nodeType===8){var n=e.data;if(n===`$`||n===`$!`||n===`$?`||n===`$~`||n===`&`){if(t===0)return e;t--}else n!==`/$`&&n!==`/&`||t++}e=e.previousSibling}return null}function pm(e,t){function n(){r=!0}if(e.ownerDocument.activeElement===e)return!0;var r=!1;try{e.ownerDocument.addEventListener(`focus`,n,!0),(e.focus||HTMLElement.prototype.focus).call(e,t)}finally{e.ownerDocument.removeEventListener(`focus`,n,!0)}return r}function mm(e){yp(function(){yp(function(t){return e(t)})})}function hm(e,t,n){switch(t=lp(n),e){case`html`:if(e=t.documentElement,!e)throw Error(i(452));return e;case`head`:if(e=t.head,!e)throw Error(i(453));return e;case`body`:if(e=t.body,!e)throw Error(i(454));return e;default:throw Error(i(451))}}function gm(e,t,n){for(var r in n){var i=n[r];n.hasOwnProperty(r)&&i!=null&&$(e,t,r,null,rp,i)}n.dangerouslySetInnerHTML!=null&&(e.textContent=``),e.onclick===On&&(e.onclick=null),Ht(e)}function _m(e){for(var t=e.attributes;t.length;)e.removeAttributeNode(t[0]);Ht(e)}var vm=new Map,ym=new Set;function bm(e){if(typeof e.getRootNode==`function`){var t=e.getRootNode();if(t.nodeType===9||t.nodeType===11)return t}return e.nodeType===9?e:e.ownerDocument}var xm=E.d;E.d={f:Sm,r:Cm,D:Em,C:Dm,L:Om,m:km,X:jm,S:Am,M:Mm};function Sm(){var e=xm.f(),t=zd();return e||t}function Cm(e){var t=Wt(e);t!==null&&t.tag===5&&t.type===`form`?cc(t):xm.r(e)}var wm=typeof document>`u`?null:document;function Tm(e,t,n){var r=wm;if(r&&typeof t==`string`&&t){var i=pn(t);i=`link[rel="`+e+`"][href="`+i+`"]`,typeof n==`string`&&(i+=`[crossorigin="`+n+`"]`),ym.has(i)||(ym.add(i),e={rel:e,crossOrigin:n,href:t},r.querySelector(i)===null&&(t=r.createElement(`link`),np(t,`link`,e),O(t),r.head.appendChild(t)))}}function Em(e){xm.D(e),Tm(`dns-prefetch`,e,null)}function Dm(e,t){xm.C(e,t),Tm(`preconnect`,e,t)}function Om(e,t,n){xm.L(e,t,n);var r=wm;if(r&&e&&t){var i=`link[rel="preload"][as="`+pn(t)+`"]`;t===`image`&&n&&n.imageSrcSet?(i+=`[imagesrcset="`+pn(n.imageSrcSet)+`"]`,typeof n.imageSizes==`string`&&(i+=`[imagesizes="`+pn(n.imageSizes)+`"]`)):i+=`[href="`+pn(e)+`"]`;var a=i;switch(t){case`style`:a=Pm(e);break;case`script`:a=Rm(e)}if(!(vm.has(a)||(e=w({rel:`preload`,href:t===`image`&&n&&n.imageSrcSet?void 0:e,as:t},n),vm.set(a,e),r.querySelector(i)!==null||t===`style`&&r.querySelector(Fm(a))||t===`script`&&r.querySelector(zm(a))))){var o=r.createElement(`link`);np(o,`link`,e),t===`style`&&(o[Vt]=!0,o.onload=o.onerror=function(){qt(o)}),O(o),r.head.appendChild(o)}}}function km(e,t){xm.m(e,t);var n=wm;if(n&&e){var r=t&&typeof t.as==`string`?t.as:`script`,i=`link[rel="modulepreload"][as="`+pn(r)+`"][href="`+pn(e)+`"]`,a=i;switch(r){case`audioworklet`:case`paintworklet`:case`serviceworker`:case`sharedworker`:case`worker`:case`script`:a=Rm(e)}if(!vm.has(a)&&(e=w({rel:`modulepreload`,href:e},t),vm.set(a,e),n.querySelector(i)===null)){switch(r){case`audioworklet`:case`paintworklet`:case`serviceworker`:case`sharedworker`:case`worker`:case`script`:if(n.querySelector(zm(a)))return}r=n.createElement(`link`),np(r,`link`,e),O(r),n.head.appendChild(r)}}}function Am(e,t,n){xm.S(e,t,n);var r=wm;if(r&&e){var i=Kt(r).hoistableStyles,a=Pm(e);t||=`default`;var o=i.get(a);if(!o){var s={loading:0,preload:null};if(o=r.querySelector(Fm(a)))s.loading=5;else{e=w({rel:`stylesheet`,href:e,"data-precedence":t},n),(n=vm.get(a))&&Hm(e,n);var c=o=r.createElement(`link`);O(c),np(c,`link`,e),c._p=new Promise(function(e,t){c.onload=e,c.onerror=t}),c.addEventListener(`load`,function(){s.loading|=1}),c.addEventListener(`error`,function(){s.loading|=2}),s.loading|=4,Vm(o,t,r)}o={type:`stylesheet`,instance:o,count:1,state:s},i.set(a,o)}}}function jm(e,t){xm.X(e,t);var n=wm;if(n&&e){var r=Kt(n).hoistableScripts,i=Rm(e),a=r.get(i);a||(a=n.querySelector(zm(i)),a||(e=w({src:e,async:!0},t),(t=vm.get(i))&&Um(e,t),a=n.createElement(`script`),O(a),np(a,`link`,e),n.head.appendChild(a)),a={type:`script`,instance:a,count:1,state:null},r.set(i,a))}}function Mm(e,t){xm.M(e,t);var n=wm;if(n&&e){var r=Kt(n).hoistableScripts,i=Rm(e),a=r.get(i);a||(a=n.querySelector(zm(i)),a||(e=w({src:e,async:!0,type:`module`},t),(t=vm.get(i))&&Um(e,t),a=n.createElement(`script`),O(a),np(a,`link`,e),n.head.appendChild(a)),a={type:`script`,instance:a,count:1,state:null},r.set(i,a))}}function Nm(e,t,n,r){var a=(a=Ne.current)?bm(a):null;if(!a)throw Error(i(446));switch(e){case`meta`:case`title`:return null;case`style`:return typeof n.precedence==`string`&&typeof n.href==`string`?(n=Pm(n.href),t=Kt(a).hoistableStyles,r=t.get(n),r||(r={type:`style`,instance:null,count:0,state:null},t.set(n,r)),r):{type:`void`,instance:null,count:0,state:null};case`link`:if(n.rel===`stylesheet`&&typeof n.href==`string`&&typeof n.precedence==`string`){e=Pm(n.href);var o=Kt(a).hoistableStyles,s=o.get(e);if(s||(a=a.ownerDocument||a,s={type:`stylesheet`,instance:null,count:0,state:{loading:0,preload:null}},o.set(e,s),(o=a.querySelector(Fm(e)))?o._p||(s.instance=o,s.state.loading=5):(o=vm.get(e),o||(o={rel:`preload`,as:`style`,href:n.href,crossOrigin:n.crossOrigin,integrity:n.integrity,media:n.media,hrefLang:n.hrefLang,referrerPolicy:n.referrerPolicy},vm.set(e,o)),Lm(a,e,o,s.state))),t&&r===null)throw Error(i(528,``));return s}if(t&&r!==null)throw Error(i(529,``));return null;case`script`:return t=n.async,n=n.src,typeof n==`string`&&t&&typeof t!=`function`&&typeof t!=`symbol`?(n=Rm(n),t=Kt(a).hoistableScripts,r=t.get(n),r||(r={type:`script`,instance:null,count:0,state:null},t.set(n,r)),r):{type:`void`,instance:null,count:0,state:null};default:throw Error(i(444,e))}}function Pm(e){return`href="`+pn(e)+`"`}function Fm(e){return`link[rel="stylesheet"][`+e+`]`}function Im(e){return w({},e,{"data-precedence":e.precedence,precedence:null})}function Lm(e,t,n,r){if(t=e.querySelector(`link[rel="preload"][as="style"][`+t+`]`)){if(!0!==t[Vt]){r.loading=1;return}}else t=e.createElement(`link`),t[Vt]=!0,t.onload=t.onerror=qt.bind(null,t),np(t,`link`,n),O(t),e.head.appendChild(t);r.preload=t,t.addEventListener(`load`,function(){return r.loading|=1}),t.addEventListener(`error`,function(){return r.loading|=2})}function Rm(e){return`[src="`+pn(e)+`"]`}function zm(e){return`script[async]`+e}function Bm(e,t,n){if(t.count++,t.instance===null)switch(t.type){case`style`:var r=e.querySelector(`style[data-href~="`+pn(n.href)+`"]`);if(r)return t.instance=r,O(r),r;var a=w({},n,{"data-href":n.href,"data-precedence":n.precedence,href:null,precedence:null});return r=(e.ownerDocument||e).createElement(`style`),O(r),np(r,`style`,a),Vm(r,n.precedence,e),t.instance=r;case`stylesheet`:a=Pm(n.href);var o=e.querySelector(Fm(a));if(o)return t.state.loading|=4,t.instance=o,O(o),o;r=Im(n),(a=vm.get(a))&&Hm(r,a),o=(e.ownerDocument||e).createElement(`link`),O(o);var s=o;return s._p=new Promise(function(e,t){s.onload=e,s.onerror=t}),np(o,`link`,r),t.state.loading|=4,Vm(o,n.precedence,e),t.instance=o;case`script`:return o=Rm(n.src),(a=e.querySelector(zm(o)))?(t.instance=a,O(a),a):(r=n,(a=vm.get(o))&&(r=w({},n),Um(r,a)),e=e.ownerDocument||e,a=e.createElement(`script`),O(a),np(a,`link`,r),e.head.appendChild(a),t.instance=a);case`void`:return null;default:throw Error(i(443,t.type))}else t.type===`stylesheet`&&!(t.state.loading&4)&&(r=t.instance,t.state.loading|=4,Vm(r,n.precedence,e));return t.instance}function Vm(e,t,n){for(var r=n.querySelectorAll(`link[rel="stylesheet"][data-precedence],style[data-precedence]`),i=r.length?r[r.length-1]:null,a=i,o=0;o<r.length;o++){var s=r[o];if(s.dataset.precedence===t)a=s;else if(a!==i)break}a?a.parentNode.insertBefore(e,a.nextSibling):(t=n.nodeType===9?n.head:n,t.insertBefore(e,t.firstChild))}function Hm(e,t){e.crossOrigin??=t.crossOrigin,e.referrerPolicy??=t.referrerPolicy,e.title??=t.title}function Um(e,t){e.crossOrigin??=t.crossOrigin,e.referrerPolicy??=t.referrerPolicy,e.integrity??=t.integrity}var Wm=null;function Gm(e,t,n){if(Wm===null){var r=new Map,i=Wm=new Map;i.set(n,r)}else i=Wm,r=i.get(n),r||(r=new Map,i.set(n,r));if(r.has(e))return r;for(r.set(e,null),n=n.getElementsByTagName(e),i=0;i<n.length;i++){var a=n[i];if(!(a[Bt]||a[Nt]||e===`link`&&a.getAttribute(`rel`)===`stylesheet`)&&a.namespaceURI!==`http://www.w3.org/2000/svg`){var o=a.getAttribute(t)||``;o=e+o;var s=r.get(o);s?s.push(a):r.set(o,[a])}}return r}function Km(e,t,n){e=e.ownerDocument||e,e.head.insertBefore(n,t===`title`?e.querySelector(`head > title`):null)}function qm(e,t,n){if(n===1||t.itemProp!=null)return!1;switch(e){case`meta`:case`title`:return!0;case`style`:if(typeof t.precedence!=`string`||typeof t.href!=`string`||t.href===``)break;return!0;case`link`:if(typeof t.rel!=`string`||typeof t.href!=`string`||t.href===``||t.onLoad||t.onError)break;switch(t.rel){case`stylesheet`:return e=t.disabled,typeof t.precedence==`string`&&e==null;default:return!0}case`script`:if(t.async&&typeof t.async!=`function`&&typeof t.async!=`symbol`&&!t.onLoad&&!t.onError&&t.src&&typeof t.src==`string`)return!0}return!1}function Jm(e,t){return e===`img`&&t.src!=null&&t.src!==``&&t.onLoad==null&&t.loading!==`lazy`}function Ym(e){return!(e.type===`stylesheet`&&!(e.state.loading&3))}function Xm(e){return(e.width||100)*(e.height||100)*(typeof devicePixelRatio==`number`?devicePixelRatio:1)*.25}function Zm(e,t){typeof t.decode==`function`&&(e.imgCount++,t.complete||(e.imgBytes+=Xm(t),e.suspenseyImages.push(t)),e=rh.bind(e),t.decode().then(e,e))}function Qm(e,t,n,r){if(n.type===`stylesheet`&&(typeof r.media!=`string`||!1!==matchMedia(r.media).matches)&&!(n.state.loading&4)){if(n.instance===null){var i=Pm(r.href),a=t.querySelector(Fm(i));if(a){t=a._p,typeof t==`object`&&t&&typeof t.then==`function`&&(e.count++,e=nh.bind(e),t.then(e,e)),n.state.loading|=4,n.instance=a,O(a);return}a=t.ownerDocument||t,r=Im(r),(i=vm.get(i))&&Hm(r,i),a=a.createElement(`link`),O(a);var o=a;o._p=new Promise(function(e,t){o.onload=e,o.onerror=t}),np(a,`link`,r),n.instance=a}e.stylesheets===null&&(e.stylesheets=new Map),e.stylesheets.set(n,t),(t=n.state.preload)&&!(n.state.loading&3)&&(e.count++,n=nh.bind(e),t.addEventListener(`load`,n),t.addEventListener(`error`,n))}}var $m=0;function eh(e,t){return e.stylesheets&&e.count===0&&ah(e,e.stylesheets),0<e.count||0<e.imgCount?function(n){var r=setTimeout(function(){if(e.stylesheets&&ah(e,e.stylesheets),e.unsuspend){var t=e.unsuspend;e.unsuspend=null,t()}},6e4+t);0<e.imgBytes&&$m===0&&($m=62500*op());var i=setTimeout(function(){if(e.waitingForImages=!1,e.count===0&&(e.stylesheets&&ah(e,e.stylesheets),e.unsuspend)){var t=e.unsuspend;e.unsuspend=null,t()}},(e.imgBytes>$m?50:800)+t);return e.unsuspend=n,function(){e.unsuspend=null,clearTimeout(r),clearTimeout(i)}}:null}function th(e){if(e.count===0&&(e.imgCount===0||!e.waitingForImages)){if(e.stylesheets)ah(e,e.stylesheets);else if(e.unsuspend){var t=e.unsuspend;e.unsuspend=null,t()}}}function nh(){this.count--,th(this)}function rh(){this.imgCount--,th(this)}var ih=null;function ah(e,t){e.stylesheets=null,e.unsuspend!==null&&(e.count++,ih=new Map,t.forEach(oh,e),ih=null,nh.call(e))}function oh(e,t){if(!(t.state.loading&4)){var n=ih.get(e);if(n)var r=n.get(null);else{n=new Map,ih.set(e,n);for(var i=e.querySelectorAll(`link[data-precedence],style[data-precedence]`),a=0;a<i.length;a++){var o=i[a];(o.nodeName===`LINK`||o.getAttribute(`media`)!==`not all`)&&(n.set(o.dataset.precedence,o),r=o)}r&&n.set(null,r)}i=t.instance,o=i.getAttribute(`data-precedence`),a=n.get(o)||r,a===r&&n.set(null,i),n.set(o,i),this.count++,r=nh.bind(this),i.addEventListener(`load`,r),i.addEventListener(`error`,r),a?a.parentNode.insertBefore(i,a.nextSibling):(e=e.nodeType===9?e.head:e,e.insertBefore(i,e.firstChild)),t.state.loading|=4}}var sh={$$typeof:ue,Provider:null,Consumer:null,_currentValue:Ee,_currentValue2:Ee,_threadCount:0};function ch(e,t,n,r,i,a,o,s,c){this.tag=1,this.containerInfo=e,this.pingCache=this.current=this.pendingChildren=null,this.timeoutHandle=-1,this.callbackNode=this.next=this.pendingContext=this.context=this.cancelPendingCommit=null,this.callbackPriority=0,this.expirationTimes=St(-1),this.entangledLanes=this.shellSuspendCounter=this.errorRecoveryDisabledLanes=this.expiredLanes=this.warmLanes=this.pingedLanes=this.suspendedLanes=this.pendingLanes=0,this.entanglements=St(0),this.hiddenUpdates=St(null),this.identifierPrefix=r,this.onUncaughtError=i,this.onCaughtError=a,this.onRecoverableError=o,this.pooledCache=null,this.pooledCacheLanes=0,this.formState=c,this.transitionTypes=null,this.incompleteTransitions=new Map}function lh(e,t,n,r,i,a,o,s,c,l,u,d){return e=new ch(e,t,n,o,c,l,u,d,s),t=1,!0===a&&(t|=24),a=Hi(3,null,null,t),e.current=a,a.stateNode=e,t=Ba(),t.refCount++,e.pooledCache=t,t.refCount++,a.memoizedState={element:r,isDehydrated:n,cache:t},Co(a),e}function uh(e){return e?(e=Bi,e):Bi}function dh(e,t,n,r,i,a){i=uh(i),r.context===null?r.context=i:r.pendingContext=i,r=To(t),r.payload={element:n},a=a===void 0?null:a,a!==null&&(r.callback=a),n=Eo(e,r,t),n!==null&&(Pd(n,e,t),Do(n,e,t))}function fh(e,t){if(e=e.memoizedState,e!==null&&e.dehydrated!==null){var n=e.retryLane;e.retryLane=n!==0&&n<t?n:t}}function ph(e,t){fh(e,t),(e=e.alternate)&&fh(e,t)}function mh(e){if(e.tag===13||e.tag===31){var t=Li(e,67108864);t!==null&&Pd(t,e,67108864),ph(e,67108864)}}function hh(e){if(e.tag===13||e.tag===31){var t=jd();t=Ot(t);var n=Li(e,t);n!==null&&Pd(n,e,t),ph(e,t)}}var gh=!0;function _h(e,t,n,r){var i=T.T;T.T=null;var a=E.p;try{E.p=2,yh(e,t,n,r)}finally{E.p=a,T.T=i}}function vh(e,t,n,r){var i=T.T;T.T=null;var a=E.p;try{E.p=8,yh(e,t,n,r)}finally{E.p=a,T.T=i}}function yh(e,t,n,r){if(gh){var i=bh(r);if(i===null)Kf(e,t,r,xh,n),Mh(e,r);else if(Ph(i,e,t,n,r))r.stopPropagation();else if(Mh(e,r),t&4&&-1<jh.indexOf(e)){for(;i!==null;){var a=Wt(i);if(a!==null)switch(a.tag){case 3:if(a=a.stateNode,a.current.memoizedState.isDehydrated){var o=gt(a.pendingLanes);if(o!==0){var s=a;for(s.pendingLanes|=2,s.entangledLanes|=2;o;){var c=1<<31-lt(o);s.entanglements[1]|=c,o&=~c}Ef(a),!(W&6)&&(_d=Ze()+500,Df(0,!1))}}break;case 31:case 13:s=Li(a,2),s!==null&&Pd(s,a,2),zd(),ph(a,2)}if(a=bh(r),a===null&&Kf(e,t,r,xh,n),a===i)break;i=a}i!==null&&r.stopPropagation()}else Kf(e,t,r,null,n)}}function bh(e){return e=An(e),Sh(e)}var xh=null;function Sh(e){if(xh=null,e=Ut(e),e!==null){var t=o(e);if(t===null)e=null;else{var n=t.tag;if(n===13){if(e=s(t),e!==null)return e;e=null}else if(n===31){if(e=c(t),e!==null)return e;e=null}else if(n===3){if(t.stateNode.current.memoizedState.isDehydrated)return t.tag===3?t.stateNode.containerInfo:null;e=null}else t!==e&&(e=null)}}return xh=e,null}function Ch(e){switch(e){case`beforetoggle`:case`cancel`:case`click`:case`close`:case`contextmenu`:case`copy`:case`cut`:case`auxclick`:case`dblclick`:case`dragend`:case`dragstart`:case`drop`:case`focusin`:case`focusout`:case`input`:case`invalid`:case`keydown`:case`keypress`:case`keyup`:case`mousedown`:case`mouseup`:case`paste`:case`pause`:case`play`:case`pointercancel`:case`pointerdown`:case`pointerup`:case`ratechange`:case`reset`:case`seeked`:case`submit`:case`toggle`:case`touchcancel`:case`touchend`:case`touchstart`:case`volumechange`:case`change`:case`selectionchange`:case`textInput`:case`compositionstart`:case`compositionend`:case`compositionupdate`:case`beforeblur`:case`afterblur`:case`beforeinput`:case`blur`:case`fullscreenchange`:case`fullscreenerror`:case`focus`:case`hashchange`:case`popstate`:case`select`:case`selectstart`:return 2;case`drag`:case`dragenter`:case`dragexit`:case`dragleave`:case`dragover`:case`mousemove`:case`mouseout`:case`mouseover`:case`pointermove`:case`pointerout`:case`pointerover`:case`resize`:case`scroll`:case`touchmove`:case`wheel`:case`mouseenter`:case`mouseleave`:case`pointerenter`:case`pointerleave`:return 8;case`message`:switch(Qe()){case $e:return 2;case et:return 8;case tt:case nt:return 32;case rt:return 268435456;default:return 32}default:return 32}}var wh=!1,Th=null,Eh=null,Dh=null,Oh=new Map,kh=new Map,Ah=[],jh=`mousedown mouseup touchcancel touchend touchstart auxclick dblclick pointercancel pointerdown pointerup dragend dragstart drop compositionend compositionstart keydown keypress keyup input textInput copy cut paste click change contextmenu reset`.split(` `);function Mh(e,t){switch(e){case`focusin`:case`focusout`:Th=null;break;case`dragenter`:case`dragleave`:Eh=null;break;case`mouseover`:case`mouseout`:Dh=null;break;case`pointerover`:case`pointerout`:Oh.delete(t.pointerId);break;case`gotpointercapture`:case`lostpointercapture`:kh.delete(t.pointerId)}}function Nh(e,t,n,r,i,a){return e===null||e.nativeEvent!==a?(e={blockedOn:t,domEventName:n,eventSystemFlags:r,nativeEvent:a,targetContainers:[i]},t!==null&&(t=Wt(t),t!==null&&mh(t)),e):(e.eventSystemFlags|=r,t=e.targetContainers,i!==null&&t.indexOf(i)===-1&&t.push(i),e)}function Ph(e,t,n,r,i){switch(t){case`focusin`:return Th=Nh(Th,e,t,n,r,i),!0;case`dragenter`:return Eh=Nh(Eh,e,t,n,r,i),!0;case`mouseover`:return Dh=Nh(Dh,e,t,n,r,i),!0;case`pointerover`:var a=i.pointerId;return Oh.set(a,Nh(Oh.get(a)||null,e,t,n,r,i)),!0;case`gotpointercapture`:return a=i.pointerId,kh.set(a,Nh(kh.get(a)||null,e,t,n,r,i)),!0}return!1}function Fh(e){var t=Ut(e.target);if(t!==null){var n=o(t);if(n!==null){if(t=n.tag,t===13){if(t=s(n),t!==null){e.blockedOn=t,jt(e.priority,function(){hh(n)});return}}else if(t===31){if(t=c(n),t!==null){e.blockedOn=t,jt(e.priority,function(){hh(n)});return}}else if(t===3&&n.stateNode.current.memoizedState.isDehydrated){e.blockedOn=n.tag===3?n.stateNode.containerInfo:null;return}}}e.blockedOn=null}function Ih(e){if(e.blockedOn!==null)return!1;for(var t=e.targetContainers;0<t.length;){var n=bh(e.nativeEvent);if(n===null){n=e.nativeEvent;var r=new n.constructor(n.type,n);kn=r,n.target.dispatchEvent(r),kn=null}else return t=Wt(n),t!==null&&mh(t),e.blockedOn=n,!1;t.shift()}return!0}function Lh(e,t,n){Ih(e)&&n.delete(t)}function Rh(){wh=!1,Th!==null&&Ih(Th)&&(Th=null),Eh!==null&&Ih(Eh)&&(Eh=null),Dh!==null&&Ih(Dh)&&(Dh=null),Oh.forEach(Lh),kh.forEach(Lh)}function zh(e,n){e.blockedOn===n&&(e.blockedOn=null,wh||(wh=!0,t.unstable_scheduleCallback(t.unstable_NormalPriority,Rh)))}var Bh=null;function Vh(e){Bh!==e&&(Bh=e,t.unstable_scheduleCallback(t.unstable_NormalPriority,function(){Bh===e&&(Bh=null);for(var t=0;t<e.length;t+=3){var n=e[t],r=e[t+1],i=e[t+2];if(typeof r!=`function`){if(Sh(r||n)===null)continue;break}var a=Wt(n);a!==null&&(e.splice(t,3),t-=3,oc(a,{pending:!0,data:i,method:n.method,action:r},r,i))}}))}function Hh(e){function t(t){return zh(t,e)}Th!==null&&zh(Th,e),Eh!==null&&zh(Eh,e),Dh!==null&&zh(Dh,e),Oh.forEach(t),kh.forEach(t);for(var n=0;n<Ah.length;n++){var r=Ah[n];r.blockedOn===e&&(r.blockedOn=null)}for(;0<Ah.length&&(n=Ah[0],n.blockedOn===null);)Fh(n),n.blockedOn===null&&Ah.shift();if(n=(e.ownerDocument||e).$$reactFormReplay,n!=null)for(r=0;r<n.length;r+=3){var i=n[r],a=n[r+1],o=i[Pt]||null;if(typeof a==`function`)o||Vh(n);else if(o){var s=null;if(a&&a.hasAttribute(`formAction`)){if(i=a,o=a[Pt]||null)s=o.formAction;else if(Sh(i)!==null)continue}else s=o.action;typeof s==`function`?n[r+1]=s:(n.splice(r,3),r-=3),Vh(n)}}}function Uh(){function e(e){e.canIntercept&&e.info===`react-transition`&&e.intercept({handler:function(){return new Promise(function(e){return i=e})},focusReset:`manual`,scroll:`manual`})}function t(){i!==null&&(i(),i=null),r||setTimeout(n,20)}function n(){if(!r&&!navigation.transition){var e=navigation.currentEntry;e&&e.url!=null&&navigation.navigate(e.url,{state:e.getState(),info:`react-transition`,history:`replace`})}}if(typeof navigation==`object`){var r=!1,i=null;return navigation.addEventListener(`navigate`,e),navigation.addEventListener(`navigatesuccess`,t),navigation.addEventListener(`navigateerror`,t),setTimeout(n,100),function(){r=!0,navigation.removeEventListener(`navigate`,e),navigation.removeEventListener(`navigatesuccess`,t),navigation.removeEventListener(`navigateerror`,t),i!==null&&(i(),i=null)}}}function Wh(e){this._internalRoot=e}Gh.prototype.render=Wh.prototype.render=function(e){var t=this._internalRoot;if(t===null)throw Error(i(409));var n=t.current;dh(n,jd(),e,t,null,null)},Gh.prototype.unmount=Wh.prototype.unmount=function(){var e=this._internalRoot;if(e!==null){this._internalRoot=null;var t=e.containerInfo;dh(e.current,2,null,e,null,null),zd(),t[Ft]=null}};function Gh(e){this._internalRoot=e}Gh.prototype.unstable_scheduleHydration=function(e){if(e){var t=At();e={blockedOn:null,target:e,priority:t};for(var n=0;n<Ah.length&&t!==0&&t<Ah[n].priority;n++);Ah.splice(n,0,e),n===0&&Fh(e)}};var Kh=n.version;if(Kh!==`19.3.0`)throw Error(i(527,Kh,`19.3.0`));E.findDOMNode=function(e){var t=e._reactInternals;if(t===void 0)throw typeof e.render==`function`?Error(i(188)):(e=Object.keys(e).join(`,`),Error(i(268,e)));return e=d(t),e=e===null?null:p(e),e=e===null?null:e.stateNode,e};var qh={bundleType:0,version:`19.3.0`,rendererPackageName:`react-dom`,currentDispatcherRef:T,reconcilerVersion:`19.3.0`};if(typeof __REACT_DEVTOOLS_GLOBAL_HOOK__<`u`){var Jh=__REACT_DEVTOOLS_GLOBAL_HOOK__;if(!Jh.isDisabled&&Jh.supportsFiber)try{ot=Jh.inject(qh),st=Jh}catch{}}e.createRoot=function(e,t){if(!a(e))throw Error(i(299));var n=!1,r=``,o=kc,s=Ac,c=jc;return t!=null&&(!0===t.unstable_strictMode&&(n=!0),t.identifierPrefix!==void 0&&(r=t.identifierPrefix),t.onUncaughtError!==void 0&&(o=t.onUncaughtError),t.onCaughtError!==void 0&&(s=t.onCaughtError),t.onRecoverableError!==void 0&&(c=t.onRecoverableError)),t=lh(e,1,!1,null,null,n,r,null,o,s,c,Uh),e[Ft]=t.current,Wf(e),new Wh(t)}})),g=o(((e,t)=>{function n(){if(typeof __REACT_DEVTOOLS_GLOBAL_HOOK__<`u`&&typeof __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE==`function`)try{__REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE(n)}catch(e){console.error(e)}}n(),t.exports=h()})),_=o((e=>{var t=Symbol.for(`react.transitional.element`),n=Symbol.for(`react.fragment`);function r(e,n,r){var i=null;if(r!==void 0&&(i=``+r),n.key!==void 0&&(i=``+n.key),`key`in n)for(var a in r={},n)a!==`key`&&(r[a]=n[a]);else r=n;return n=r.ref,{$$typeof:t,type:e,key:i,ref:n===void 0?null:n,props:r}}e.Fragment=n,e.jsx=r,e.jsxs=r})),v=o(((e,t)=>{t.exports=_()})),y=c(g(),1),b=c(u(),1),x=v(),S={dashboard:[`M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z`,`M9 22V12h6v10`],rooms:[`M3 3h7v7H3z`,`M14 3h7v7h-7z`,`M14 14h7v7h-7z`,`M3 14h7v7H3z`],bookings:[`M8 6h13`,`M8 12h13`,`M8 18h13`,`M3 6h.01`,`M3 12h.01`,`M3 18h.01`],settings:`M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z`,search:[`M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16z`,`M21 21l-4.35-4.35`],bell:[`M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9`,`M13.73 21a2 2 0 0 1-3.46 0`],users:[`M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2`,`M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z`,`M23 21v-2a4 4 0 0 0-3-3.87`,`M16 3.13a4 4 0 0 1 0 7.75`],map:[`M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z`,`M12 13a3 3 0 1 0 0-6 3 3 0 0 0 0 6z`],calendar:[`M8 2v4`,`M16 2v4`,`M3 10h18`,`rect x="3" y="4" width="18" height="18" rx="2"`],filter:`M22 3H2l8 9.46V19l4 2v-8.54L22 3z`,chevronDown:`M6 9l6 6 6-6`,screen:[`M8 21h8`,`M12 17v4`,`M2 3h20v14H2z`],wifi:[`M1.42 9a16 16 0 0 1 21.16 0`,`M5 12.55a11 11 0 0 1 14.08 0`,`M8.53 16.11a6 6 0 0 1 6.95 0`,`M12 20h.01`],coffee:[`M18 8h1a4 4 0 0 1 0 8h-1`,`M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z`,`M6 1v3`,`M10 1v3`,`M14 1v3`],video:[`M23 7l-7 5 7 5V7z`,`M1 5h15v14H1z`]},ee=[{id:1,name:`Phòng Họp Hội Đồng`,location:`Tầng 5`,capacity:`16–20 người`,status:`available`,amenities:[`Màn hình`,`Wifi`,`Video`],floor:5,img:`https://images.unsplash.com/photo-1740933084056-078fac872bff?w=600&h=340&fit=crop&auto=format`},{id:2,name:`Phòng Họp Sáng Tạo`,location:`Tầng 3`,capacity:`6–8 người`,status:`booked`,amenities:[`Màn hình`,`Wifi`,`Đồ uống`],floor:3,img:`https://images.unsplash.com/photo-1771147372799-d94991e92ce7?w=600&h=340&fit=crop&auto=format`},{id:3,name:`Phòng Hội Nghị A`,location:`Tầng 2`,capacity:`10–12 người`,status:`available`,amenities:[`Màn hình`,`Video`,`Wifi`],floor:2,img:`https://images.unsplash.com/photo-1772112334844-2eed0111e690?w=600&h=340&fit=crop&auto=format`},{id:4,name:`Phòng Điều Hành`,location:`Tầng 7`,capacity:`8–10 người`,status:`available`,amenities:[`Video`,`Wifi`,`Đồ uống`],floor:7,img:`https://images.unsplash.com/photo-1771270759486-1f7703945072?w=600&h=340&fit=crop&auto=format`},{id:5,name:`Phòng Họp Nhỏ B`,location:`Tầng 1`,capacity:`4–6 người`,status:`booked`,amenities:[`Màn hình`,`Wifi`],floor:1,img:`https://images.unsplash.com/photo-1771147372634-976f022c0033?w=600&h=340&fit=crop&auto=format`},{id:6,name:`Phòng Đào Tạo`,location:`Tầng 4`,capacity:`20–30 người`,status:`available`,amenities:[`Màn hình`,`Video`,`Wifi`,`Đồ uống`],floor:4,img:`https://images.unsplash.com/photo-1740933084077-edca148dbd5a?w=600&h=340&fit=crop&auto=format`}],te=[{label:`Tổng quan`,icon:S.dashboard,key:`dashboard`},{label:`Phòng họp`,icon:S.rooms,key:`rooms`},{label:`Đặt lịch của tôi`,icon:S.bookings,key:`bookings`},{label:`Cài đặt`,icon:S.settings,key:`settings`}],C={"Màn hình":S.screen,Wifi:S.wifi,"Đồ uống":S.coffee,Video:S.video};function ne(){return(0,x.jsxs)(`div`,{className:`flex items-center gap-2`,children:[(0,x.jsx)(`div`,{className:`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0`,style:{backgroundColor:`#004CFF`},children:(0,x.jsxs)(`svg`,{width:`18`,height:`18`,viewBox:`0 0 24 24`,fill:`none`,children:[(0,x.jsx)(`rect`,{x:`3`,y:`4`,width:`18`,height:`16`,rx:`2`,stroke:`white`,strokeWidth:`2`}),(0,x.jsx)(`path`,{d:`M8 2v4M16 2v4M3 10h18`,stroke:`white`,strokeWidth:`2`,strokeLinecap:`round`}),(0,x.jsx)(`circle`,{cx:`8.5`,cy:`15`,r:`1.5`,fill:`white`}),(0,x.jsx)(`circle`,{cx:`12`,cy:`15`,r:`1.5`,fill:`white`}),(0,x.jsx)(`circle`,{cx:`15.5`,cy:`15`,r:`1.5`,fill:`white`})]})}),(0,x.jsx)(`span`,{className:`text-[15px] font-semibold text-gray-900 tracking-tight`,children:`RoomSync`})]})}function w({size:e=36}){return(0,x.jsx)(`div`,{className:`rounded-full overflow-hidden flex-shrink-0 border-2 border-white ring-1 ring-gray-200`,style:{width:e,height:e},children:(0,x.jsx)(`img`,{src:`https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=80&h=80&fit=crop&face&auto=format`,alt:`Ảnh đại diện người dùng`,className:`w-full h-full object-cover`})})}function re({label:e}){let t=C[e];return(0,x.jsxs)(`span`,{className:`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium text-gray-500 bg-gray-100`,children:[t&&(0,x.jsx)(`svg`,{width:`11`,height:`11`,viewBox:`0 0 24 24`,fill:`none`,stroke:`currentColor`,strokeWidth:`2`,strokeLinecap:`round`,strokeLinejoin:`round`,children:(Array.isArray(t)?t:[t]).map((e,t)=>(0,x.jsx)(`path`,{d:e},t))}),e]})}function ie({status:e}){return e===`available`?(0,x.jsxs)(`span`,{className:`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold`,style:{backgroundColor:`#DCFCE7`,color:`#15803D`},children:[(0,x.jsx)(`span`,{className:`w-1.5 h-1.5 rounded-full bg-green-500 inline-block`}),`Còn trống`]}):(0,x.jsxs)(`span`,{className:`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold`,style:{backgroundColor:`#FEE2E2`,color:`#B91C1C`},children:[(0,x.jsx)(`span`,{className:`w-1.5 h-1.5 rounded-full bg-red-500 inline-block`}),`Đã đặt`]})}function ae({room:e}){return(0,x.jsxs)(`div`,{className:`bg-white rounded-[10px] overflow-hidden flex flex-col`,style:{boxShadow:`0 1px 4px rgba(0,0,0,0.07), 0 4px 16px rgba(0,0,0,0.05)`},children:[(0,x.jsxs)(`div`,{className:`relative overflow-hidden bg-gray-100`,style:{height:172},children:[(0,x.jsx)(`img`,{src:e.img,alt:e.name,className:`w-full h-full object-cover`}),(0,x.jsx)(`div`,{className:`absolute top-3 right-3`,children:(0,x.jsx)(ie,{status:e.status})})]}),(0,x.jsxs)(`div`,{className:`flex flex-col flex-1 p-4`,children:[(0,x.jsx)(`h3`,{className:`text-[14px] font-semibold text-gray-900 leading-snug mb-1`,children:e.name}),(0,x.jsxs)(`div`,{className:`flex items-center gap-3 mb-3`,children:[(0,x.jsxs)(`span`,{className:`flex items-center gap-1 text-[12px] text-gray-500`,children:[(0,x.jsxs)(`svg`,{width:`13`,height:`13`,viewBox:`0 0 24 24`,fill:`none`,stroke:`currentColor`,strokeWidth:`2`,strokeLinecap:`round`,strokeLinejoin:`round`,children:[(0,x.jsx)(`path`,{d:`M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z`}),(0,x.jsx)(`circle`,{cx:`12`,cy:`10`,r:`3`})]}),e.location]}),(0,x.jsxs)(`span`,{className:`flex items-center gap-1 text-[12px] text-gray-500`,children:[(0,x.jsxs)(`svg`,{width:`13`,height:`13`,viewBox:`0 0 24 24`,fill:`none`,stroke:`currentColor`,strokeWidth:`2`,strokeLinecap:`round`,strokeLinejoin:`round`,children:[(0,x.jsx)(`path`,{d:`M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2`}),(0,x.jsx)(`circle`,{cx:`9`,cy:`7`,r:`4`}),(0,x.jsx)(`path`,{d:`M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75`})]}),e.capacity]})]}),(0,x.jsx)(`div`,{className:`flex flex-wrap gap-1.5 mb-4`,children:e.amenities.map(e=>(0,x.jsx)(re,{label:e},e))}),(0,x.jsxs)(`div`,{className:`flex gap-2 mt-auto pt-3 border-t border-gray-100`,children:[(0,x.jsx)(`button`,{className:`flex-1 py-2 rounded-lg text-[12px] font-medium text-gray-700 border border-gray-200 bg-white hover:bg-gray-50 transition-colors`,children:`Xem lịch`}),(0,x.jsx)(`button`,{className:`flex-1 py-2 rounded-lg text-[12px] font-semibold text-white transition-colors`,style:{backgroundColor:e.status===`booked`?`#9CA3AF`:`#004CFF`},disabled:e.status===`booked`,onMouseEnter:t=>{e.status!==`booked`&&(t.currentTarget.style.backgroundColor=`#0038CC`)},onMouseLeave:t=>{e.status!==`booked`&&(t.currentTarget.style.backgroundColor=`#004CFF`)},children:e.status===`booked`?`Hết chỗ`:`Đặt ngay`})]})]})]})}function oe(){let[e,t]=(0,b.useState)(``),[n,r]=(0,b.useState)([]),i=e=>r(t=>t.includes(e)?t.filter(t=>t!==e):[...t,e]);return(0,x.jsxs)(`div`,{className:`flex flex-wrap items-center gap-3 mb-6`,children:[(0,x.jsxs)(`div`,{className:`flex items-center gap-2 px-3 py-2 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 cursor-pointer hover:border-blue-400 transition-colors`,style:{minWidth:160},children:[(0,x.jsxs)(`svg`,{width:`15`,height:`15`,viewBox:`0 0 24 24`,fill:`none`,stroke:`#004CFF`,strokeWidth:`2`,strokeLinecap:`round`,strokeLinejoin:`round`,children:[(0,x.jsx)(`rect`,{x:`3`,y:`4`,width:`18`,height:`18`,rx:`2`}),(0,x.jsx)(`path`,{d:`M8 2v4M16 2v4M3 10h18`})]}),(0,x.jsx)(`span`,{children:`Hôm nay — 24/09/2026`})]}),(0,x.jsxs)(`div`,{className:`relative`,children:[(0,x.jsxs)(`select`,{value:e,onChange:e=>t(e.target.value),className:`appearance-none pl-3 pr-8 py-2 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 cursor-pointer hover:border-blue-400 transition-colors outline-none`,children:[(0,x.jsx)(`option`,{value:``,children:`Sức chứa`}),(0,x.jsx)(`option`,{value:`small`,children:`1–6 người`}),(0,x.jsx)(`option`,{value:`medium`,children:`6–12 người`}),(0,x.jsx)(`option`,{value:`large`,children:`12–20 người`}),(0,x.jsx)(`option`,{value:`xlarge`,children:`20+ người`})]}),(0,x.jsx)(`svg`,{className:`absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none text-gray-400`,width:`14`,height:`14`,viewBox:`0 0 24 24`,fill:`none`,stroke:`currentColor`,strokeWidth:`2.5`,strokeLinecap:`round`,strokeLinejoin:`round`,children:(0,x.jsx)(`path`,{d:`M6 9l6 6 6-6`})})]}),(0,x.jsx)(`div`,{className:`flex items-center gap-2 flex-wrap`,children:[`Màn hình`,`Wifi`,`Video`,`Đồ uống`].map(e=>(0,x.jsx)(`button`,{onClick:()=>i(e),className:`px-3 py-2 rounded-lg text-sm border transition-all`,style:{backgroundColor:n.includes(e)?`#EEF3FF`:`#fff`,borderColor:n.includes(e)?`#004CFF`:`#E5E7EB`,color:n.includes(e)?`#004CFF`:`#6B7280`,fontWeight:n.includes(e)?600:400},children:e},e))}),(0,x.jsxs)(`div`,{className:`ml-auto flex items-center gap-2 text-sm text-gray-500`,children:[(0,x.jsx)(`span`,{className:`font-medium text-gray-900`,children:ee.filter(e=>e.status===`available`).length}),` phòng còn trống`,(0,x.jsx)(`span`,{className:`mx-1 text-gray-300`,children:`|`}),(0,x.jsx)(`span`,{className:`font-medium text-gray-900`,children:ee.filter(e=>e.status===`booked`).length}),` đã đặt`]})]})}function se(){return(0,x.jsx)(`div`,{className:`grid grid-cols-4 gap-4 mb-6`,children:[{label:`Tổng phòng họp`,value:`24`,sub:`+2 so với tháng trước`,color:`#004CFF`},{label:`Đang sử dụng`,value:`9`,sub:`37.5% công suất`,color:`#F59E0B`},{label:`Còn trống hôm nay`,value:`15`,sub:`trong 24 phòng`,color:`#10B981`},{label:`Lượt đặt trong tuần`,value:`142`,sub:`↑ 18% so với tuần trước`,color:`#8B5CF6`}].map(e=>(0,x.jsxs)(`div`,{className:`bg-white rounded-[10px] px-5 py-4 border border-gray-100`,style:{boxShadow:`0 1px 4px rgba(0,0,0,0.05)`},children:[(0,x.jsx)(`div`,{className:`text-xs text-gray-500 mb-1`,children:e.label}),(0,x.jsx)(`div`,{className:`text-2xl font-bold text-gray-900 mb-0.5`,style:{color:e.color},children:e.value}),(0,x.jsx)(`div`,{className:`text-[11px] text-gray-400`,children:e.sub})]},e.label))})}function ce(){let[e,t]=(0,b.useState)(`rooms`),[n,r]=(0,b.useState)(``);return(0,x.jsxs)(`div`,{className:`hidden lg:flex w-full min-h-screen`,style:{backgroundColor:`#F3F4F6`,fontFamily:`Inter, system-ui, sans-serif`},children:[(0,x.jsxs)(`aside`,{className:`w-[220px] flex-shrink-0 bg-white border-r border-gray-100 flex flex-col`,style:{minHeight:`100vh`},children:[(0,x.jsx)(`div`,{className:`px-5 py-5 border-b border-gray-100`,children:(0,x.jsx)(ne,{})}),(0,x.jsx)(`nav`,{className:`flex-1 px-3 py-4 space-y-0.5`,children:te.map(n=>{let r=e===n.key;return(0,x.jsxs)(`button`,{onClick:()=>t(n.key),className:`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all text-left`,style:{backgroundColor:r?`#EEF3FF`:`transparent`,color:r?`#004CFF`:`#6B7280`,fontWeight:r?600:400},onMouseEnter:e=>{r||(e.currentTarget.style.backgroundColor=`#F9FAFB`)},onMouseLeave:e=>{r||(e.currentTarget.style.backgroundColor=`transparent`)},children:[(0,x.jsx)(`svg`,{width:`18`,height:`18`,viewBox:`0 0 24 24`,fill:`none`,stroke:`currentColor`,strokeWidth:`1.8`,strokeLinecap:`round`,strokeLinejoin:`round`,style:{color:r?`#004CFF`:`#9CA3AF`},children:(Array.isArray(n.icon)?n.icon:[n.icon]).map((e,t)=>(0,x.jsx)(`path`,{d:e},t))}),n.label]},n.key)})}),(0,x.jsx)(`div`,{className:`px-4 py-4 border-t border-gray-100`,children:(0,x.jsxs)(`div`,{className:`flex items-center gap-3`,children:[(0,x.jsx)(w,{size:34}),(0,x.jsxs)(`div`,{className:`overflow-hidden`,children:[(0,x.jsx)(`div`,{className:`text-[13px] font-semibold text-gray-800 truncate`,children:`Nguyễn Minh Tuấn`}),(0,x.jsx)(`div`,{className:`text-[11px] text-gray-400 truncate`,children:`Quản trị viên`})]})]})})]}),(0,x.jsxs)(`div`,{className:`flex-1 flex flex-col min-w-0`,children:[(0,x.jsxs)(`header`,{className:`h-[60px] bg-white border-b border-gray-100 flex items-center px-6 gap-4 flex-shrink-0`,style:{boxShadow:`0 1px 3px rgba(0,0,0,0.04)`},children:[(0,x.jsxs)(`div`,{className:`flex-1 max-w-[480px] relative`,children:[(0,x.jsxs)(`svg`,{className:`absolute left-3 top-1/2 -translate-y-1/2 text-gray-400`,width:`16`,height:`16`,viewBox:`0 0 24 24`,fill:`none`,stroke:`currentColor`,strokeWidth:`2`,strokeLinecap:`round`,strokeLinejoin:`round`,children:[(0,x.jsx)(`circle`,{cx:`11`,cy:`11`,r:`8`}),(0,x.jsx)(`path`,{d:`M21 21l-4.35-4.35`})]}),(0,x.jsx)(`input`,{type:`text`,value:n,onChange:e=>r(e.target.value),placeholder:`Tìm kiếm phòng họp, tầng, tiện ích...`,className:`w-full pl-9 pr-4 py-2 rounded-lg border border-gray-200 text-sm text-gray-700 placeholder-gray-400 bg-gray-50 outline-none transition-colors`,onFocus:e=>{e.currentTarget.style.borderColor=`#004CFF`,e.currentTarget.style.backgroundColor=`#fff`,e.currentTarget.style.boxShadow=`0 0 0 3px rgba(0,76,255,0.08)`},onBlur:e=>{e.currentTarget.style.borderColor=`#E5E7EB`,e.currentTarget.style.backgroundColor=`#F9FAFB`,e.currentTarget.style.boxShadow=`none`}})]}),(0,x.jsxs)(`div`,{className:`flex items-center gap-3 ml-auto`,children:[(0,x.jsxs)(`button`,{className:`relative w-9 h-9 flex items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 transition-colors`,children:[(0,x.jsxs)(`svg`,{width:`18`,height:`18`,viewBox:`0 0 24 24`,fill:`none`,stroke:`currentColor`,strokeWidth:`2`,strokeLinecap:`round`,strokeLinejoin:`round`,children:[(0,x.jsx)(`path`,{d:`M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9`}),(0,x.jsx)(`path`,{d:`M13.73 21a2 2 0 0 1-3.46 0`})]}),(0,x.jsx)(`span`,{className:`absolute top-1.5 right-1.5 w-2 h-2 rounded-full`,style:{backgroundColor:`#004CFF`}})]}),(0,x.jsx)(w,{size:34})]})]}),(0,x.jsxs)(`main`,{className:`flex-1 p-6 overflow-y-auto`,children:[(0,x.jsxs)(`div`,{className:`flex items-center justify-between mb-6`,children:[(0,x.jsxs)(`div`,{children:[(0,x.jsx)(`h1`,{className:`text-xl font-bold text-gray-900`,children:`Phòng họp hiện có`}),(0,x.jsxs)(`p`,{className:`text-sm text-gray-500 mt-0.5`,children:[`Thứ Tư, 24 tháng 9 năm 2026 · Đang hiển thị `,ee.length,` phòng`]})]}),(0,x.jsxs)(`button`,{className:`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-white transition-colors`,style:{backgroundColor:`#004CFF`},onMouseEnter:e=>e.currentTarget.style.backgroundColor=`#0038CC`,onMouseLeave:e=>e.currentTarget.style.backgroundColor=`#004CFF`,children:[(0,x.jsx)(`svg`,{width:`15`,height:`15`,viewBox:`0 0 24 24`,fill:`none`,stroke:`currentColor`,strokeWidth:`2.5`,strokeLinecap:`round`,strokeLinejoin:`round`,children:(0,x.jsx)(`path`,{d:`M12 5v14M5 12h14`})}),`Thêm phòng họp`]})]}),(0,x.jsx)(se,{}),(0,x.jsx)(oe,{}),(0,x.jsx)(`div`,{className:`grid grid-cols-3 gap-5`,children:ee.map(e=>(0,x.jsx)(ae,{room:e},e.id))})]})]})]})}function le(){let[e,t]=(0,b.useState)(`rooms`),[n,r]=(0,b.useState)(!1);return(0,x.jsxs)(`div`,{className:`flex lg:hidden flex-col min-h-screen`,style:{backgroundColor:`#F3F4F6`,fontFamily:`Inter, system-ui, sans-serif`},children:[(0,x.jsxs)(`header`,{className:`h-[56px] bg-white border-b border-gray-100 flex items-center justify-between px-4 flex-shrink-0`,style:{boxShadow:`0 1px 3px rgba(0,0,0,0.05)`},children:[(0,x.jsx)(ne,{}),(0,x.jsxs)(`div`,{className:`flex items-center gap-2`,children:[(0,x.jsxs)(`button`,{className:`relative w-9 h-9 flex items-center justify-center rounded-lg text-gray-500`,children:[(0,x.jsxs)(`svg`,{width:`18`,height:`18`,viewBox:`0 0 24 24`,fill:`none`,stroke:`currentColor`,strokeWidth:`2`,strokeLinecap:`round`,strokeLinejoin:`round`,children:[(0,x.jsx)(`path`,{d:`M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9`}),(0,x.jsx)(`path`,{d:`M13.73 21a2 2 0 0 1-3.46 0`})]}),(0,x.jsx)(`span`,{className:`absolute top-1.5 right-1.5 w-2 h-2 rounded-full`,style:{backgroundColor:`#004CFF`}})]}),(0,x.jsx)(w,{size:32})]})]}),(0,x.jsx)(`main`,{className:`flex-1 overflow-y-auto pb-20`,children:(0,x.jsxs)(`div`,{className:`px-4 pt-4`,children:[(0,x.jsxs)(`div`,{className:`mb-4`,children:[(0,x.jsx)(`h1`,{className:`text-lg font-bold text-gray-900`,children:`Phòng họp hiện có`}),(0,x.jsxs)(`p`,{className:`text-xs text-gray-500 mt-0.5`,children:[`24/09/2026 · `,ee.length,` phòng`]})]}),(0,x.jsx)(`div`,{className:`grid grid-cols-2 gap-3 mb-4`,children:[{label:`Tổng phòng`,value:`24`,color:`#004CFF`},{label:`Còn trống`,value:`15`,color:`#10B981`},{label:`Đang dùng`,value:`9`,color:`#F59E0B`},{label:`Đặt trong tuần`,value:`142`,color:`#8B5CF6`}].map(e=>(0,x.jsxs)(`div`,{className:`bg-white rounded-[10px] px-4 py-3 border border-gray-100`,children:[(0,x.jsx)(`div`,{className:`text-xs text-gray-500 mb-0.5`,children:e.label}),(0,x.jsx)(`div`,{className:`text-xl font-bold`,style:{color:e.color},children:e.value})]},e.label))}),(0,x.jsxs)(`button`,{onClick:()=>r(e=>!e),className:`w-full flex items-center justify-between px-4 py-3 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 mb-3 transition-colors`,style:{borderColor:n?`#004CFF`:`#E5E7EB`},children:[(0,x.jsxs)(`span`,{className:`flex items-center gap-2 font-medium`,style:{color:n?`#004CFF`:`#374151`},children:[(0,x.jsx)(`svg`,{width:`16`,height:`16`,viewBox:`0 0 24 24`,fill:`none`,stroke:`currentColor`,strokeWidth:`2`,strokeLinecap:`round`,strokeLinejoin:`round`,children:(0,x.jsx)(`path`,{d:`M22 3H2l8 9.46V19l4 2v-8.54L22 3z`})}),`Bộ lọc`]}),(0,x.jsx)(`svg`,{width:`16`,height:`16`,viewBox:`0 0 24 24`,fill:`none`,stroke:`currentColor`,strokeWidth:`2.5`,strokeLinecap:`round`,strokeLinejoin:`round`,style:{transform:n?`rotate(180deg)`:`rotate(0deg)`,transition:`transform 0.2s`,color:n?`#004CFF`:`#9CA3AF`},children:(0,x.jsx)(`path`,{d:`M6 9l6 6 6-6`})})]}),n&&(0,x.jsxs)(`div`,{className:`bg-white border border-gray-200 rounded-lg p-4 mb-4 space-y-3`,children:[(0,x.jsxs)(`div`,{children:[(0,x.jsx)(`label`,{className:`text-xs font-medium text-gray-600 mb-1.5 block`,children:`Ngày đặt`}),(0,x.jsxs)(`div`,{className:`flex items-center gap-2 px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-700`,children:[(0,x.jsxs)(`svg`,{width:`14`,height:`14`,viewBox:`0 0 24 24`,fill:`none`,stroke:`#004CFF`,strokeWidth:`2`,strokeLinecap:`round`,strokeLinejoin:`round`,children:[(0,x.jsx)(`rect`,{x:`3`,y:`4`,width:`18`,height:`18`,rx:`2`}),(0,x.jsx)(`path`,{d:`M8 2v4M16 2v4M3 10h18`})]}),`Hôm nay — 24/09/2026`]})]}),(0,x.jsxs)(`div`,{children:[(0,x.jsx)(`label`,{className:`text-xs font-medium text-gray-600 mb-1.5 block`,children:`Sức chứa`}),(0,x.jsxs)(`select`,{className:`w-full px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-700 outline-none`,children:[(0,x.jsx)(`option`,{children:`Tất cả sức chứa`}),(0,x.jsx)(`option`,{children:`1–6 người`}),(0,x.jsx)(`option`,{children:`6–12 người`}),(0,x.jsx)(`option`,{children:`12–20 người`}),(0,x.jsx)(`option`,{children:`20+ người`})]})]}),(0,x.jsxs)(`div`,{children:[(0,x.jsx)(`label`,{className:`text-xs font-medium text-gray-600 mb-1.5 block`,children:`Tiện ích`}),(0,x.jsx)(`div`,{className:`flex flex-wrap gap-2`,children:[`Màn hình`,`Wifi`,`Video`,`Đồ uống`].map(e=>(0,x.jsx)(`button`,{className:`px-3 py-1.5 rounded-lg text-xs border border-gray-200 bg-gray-50 text-gray-600`,children:e},e))})]}),(0,x.jsx)(`button`,{className:`w-full py-2.5 rounded-lg text-sm font-semibold text-white`,style:{backgroundColor:`#004CFF`},children:`Áp dụng bộ lọc`})]}),(0,x.jsxs)(`div`,{className:`flex items-center gap-2 mb-3`,children:[(0,x.jsxs)(`span`,{className:`text-xs text-gray-500`,children:[(0,x.jsx)(`span`,{className:`font-semibold text-gray-800`,children:ee.filter(e=>e.status===`available`).length}),` còn trống`]}),(0,x.jsx)(`span`,{className:`text-gray-300 text-xs`,children:`·`}),(0,x.jsxs)(`span`,{className:`text-xs text-gray-500`,children:[(0,x.jsx)(`span`,{className:`font-semibold text-gray-800`,children:ee.filter(e=>e.status===`booked`).length}),` đã đặt`]})]}),(0,x.jsx)(`div`,{className:`space-y-4`,children:ee.map(e=>(0,x.jsx)(ae,{room:e},e.id))})]})}),(0,x.jsx)(`nav`,{className:`fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 flex z-50`,style:{boxShadow:`0 -4px 12px rgba(0,0,0,0.06)`},children:te.map(n=>{let r=e===n.key;return(0,x.jsxs)(`button`,{onClick:()=>t(n.key),className:`flex-1 flex flex-col items-center justify-center py-2.5 gap-1 transition-colors`,style:{color:r?`#004CFF`:`#9CA3AF`},children:[(0,x.jsx)(`svg`,{width:`20`,height:`20`,viewBox:`0 0 24 24`,fill:`none`,stroke:`currentColor`,strokeWidth:r?`2.2`:`1.8`,strokeLinecap:`round`,strokeLinejoin:`round`,children:(Array.isArray(n.icon)?n.icon:[n.icon]).map((e,t)=>(0,x.jsx)(`path`,{d:e},t))}),(0,x.jsx)(`span`,{className:`text-[10px] font-medium`,children:n.label}),r&&(0,x.jsx)(`span`,{className:`absolute top-0 w-8 h-0.5 rounded-full`,style:{backgroundColor:`#004CFF`}})]},n.key)})})]})}function ue(){return(0,x.jsxs)(x.Fragment,{children:[(0,x.jsx)(ce,{}),(0,x.jsx)(le,{})]})}y.createRoot(document.getElementById(`root`)).render((0,x.jsx)(b.StrictMode,{children:(0,x.jsx)(ue,{})}));
````

## File: frontend/robots.txt
````
User-agent: *
Disallow: /
````

## File: tests/test_equipment_admin.py
````python
"""Unit tests for Equipment Admin flow (POST, PUT, GET include_inactive, permission checks)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.equipment import Equipment, MeetingEquipment
from app.models.user import User
from tests.helpers import _auth_header, _create_meeting, _create_room, _create_user, _make_token


def _create_test_equipment(db: Session, name: str = "Mic Test", total_qty: int = 5, is_active: bool = True) -> Equipment:
    equip = Equipment(
        name=name,
        code="TEST-01",
        category="Audio",
        total_qty=total_qty,
        is_active=is_active,
    )
    db.add(equip)
    db.commit()
    db.refresh(equip)
    return equip


def test_post_and_put_require_admin_token(client: TestClient, db_session: Session):
    """Test API POST và PUT: Phải trả về 403 Forbidden hoặc 401 Unauthorized nếu không có token Admin."""
    employee = _create_user(db_session, username="employee1", role="employee")
    emp_token = _make_token(employee)

    payload = {
        "name": "Projector Ultra HD",
        "code": "PRJ-999",
        "category": "Visual",
        "total_qty": 2,
    }

    # 1. POST without token -> 401 Unauthorized
    resp_no_auth = client.post("/api/equipments/", json=payload)
    assert resp_no_auth.status_code in (401, 403)

    # 2. POST with employee token -> 403 Forbidden
    resp_emp = client.post("/api/equipments/", json=payload, headers=_auth_header(emp_token))
    assert resp_emp.status_code == 403

    # Create an equipment for testing PUT permission
    equip = _create_test_equipment(db_session)

    update_payload = {"name": "Mic Test Updated"}

    # 3. PUT without token -> 401/403
    resp_put_no_auth = client.put(f"/api/equipments/{equip.id}", json=update_payload)
    assert resp_put_no_auth.status_code in (401, 403)

    # 4. PUT with employee token -> 403 Forbidden
    resp_put_emp = client.put(f"/api/equipments/{equip.id}", json=update_payload, headers=_auth_header(emp_token))
    assert resp_put_emp.status_code == 403


def test_toggle_is_active_and_include_inactive_query(client: TestClient, db_session: Session):
    """Tạo 1 thiết bị, sau đó gọi PUT để đổi is_active từ True sang False.

    Gọi GET /?include_inactive=true để kiểm tra thiết bị vừa tắt vẫn hiển thị trong list của Admin.
    """
    admin = _create_user(db_session, username="admin1", role="admin")
    admin_token = _make_token(admin)
    headers = _auth_header(admin_token)

    # 1. Admin POST to create a new equipment (is_active Defaults to True)
    create_payload = {
        "name": "Smart Board 75 inch",
        "code": "SB-075",
        "category": "Display",
        "total_qty": 3,
        "is_active": True,
    }
    create_resp = client.post("/api/equipments/", json=create_payload, headers=headers)
    assert create_resp.status_code == 201
    created_id = create_resp.json()["id"]
    assert create_resp.json()["is_active"] is True

    # 2. Call PUT to change is_active from True to False
    put_payload = {"is_active": False}
    put_resp = client.put(f"/api/equipments/{created_id}", json=put_payload, headers=headers)
    assert put_resp.status_code == 200
    assert put_resp.json()["is_active"] is False

    # 3. GET /api/equipments/ (default include_inactive=false) -> Should NOT contain the inactive equipment
    get_active_resp = client.get("/api/equipments/", headers=headers)
    assert get_active_resp.status_code == 200
    active_ids = [item["id"] for item in get_active_resp.json()]
    assert created_id not in active_ids

    # 4. GET /api/equipments/?include_inactive=true -> MUST contain the inactive equipment for Admin
    get_all_resp = client.get("/api/equipments/?include_inactive=true", headers=headers)
    assert get_all_resp.status_code == 200
    all_ids = [item["id"] for item in get_all_resp.json()]
    assert created_id in all_ids


def test_update_total_qty_does_not_corrupt_meeting_equipments(client: TestClient, db_session: Session):
    """AC 4: Khi Admin sửa total_qty của 1 thiết bị, sự thay đổi lưu thành công mà không làm hỏng dữ liệu meeting_equipments."""
    admin = _create_user(db_session, username="admin_qty", role="admin")
    admin_token = _make_token(admin)
    headers = _auth_header(admin_token)

    equip = _create_test_equipment(db_session, total_qty=5)
    organizer = _create_user(db_session, username="organizer_qty")
    room = _create_room(db_session, name="Room Qty")
    from datetime import datetime
    meeting = _create_meeting(db_session, room, organizer, datetime.now(), datetime.now())

    # Link meeting to equipment
    me = MeetingEquipment(meeting_id=meeting.id, equipment_id=equip.id, quantity=2, note="For workshop")
    db_session.add(me)
    db_session.commit()

    # Admin updates total_qty from 5 to 12
    put_resp = client.put(f"/api/equipments/{equip.id}", json={"total_qty": 12}, headers=headers)
    assert put_resp.status_code == 200
    assert put_resp.json()["total_qty"] == 12

    # Verify meeting_equipments link is intact
    db_session.expire_all()
    me_db = db_session.query(MeetingEquipment).filter_by(meeting_id=meeting.id, equipment_id=equip.id).first()
    assert me_db is not None
    assert me_db.quantity == 2
    assert me_db.equipment.total_qty == 12
````

## File: tests/test_google_auth.py
````python
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit

from cryptography.fernet import Fernet

from app.models.user import User
from app.routers import auth as auth_router
from app.core.security import hash_password
from app.services.google_calendar_service import (
    decrypt_refresh_token,
    encrypt_refresh_token,
    make_calendar_consent_url,
)
from tests.helpers import _auth_header, _create_user, _make_token


class MockGoogleResponse:
    def __init__(self, body):
        self.body = body

    def raise_for_status(self):
        return None

    def json(self):
        return self.body


def _configure_google_oauth(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-google-client")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-google-secret")
    monkeypatch.setenv(
        "GOOGLE_REDIRECT_URI",
        "http://localhost:8000/api/auth/google/callback",
    )
    monkeypatch.setenv(
        "FRONTEND_LOGIN_URL",
        "http://localhost:8000/static/login.html",
    )


def _mock_google_profile(monkeypatch, profile, token_data=None):
    token_data = token_data or {"access_token": "google-access-token"}
    monkeypatch.setattr(
        auth_router.httpx,
        "post",
        lambda *args, **kwargs: MockGoogleResponse(token_data),
    )
    monkeypatch.setattr(
        auth_router.httpx,
        "get",
        lambda *args, **kwargs: MockGoogleResponse(profile),
    )


def _start_google_login(client):
    response = client.get("/api/auth/google/login", follow_redirects=False)
    assert response.status_code == 307
    return response, urlsplit(response.headers["location"])


def _complete_google_login(client, login_response, location):
    state = login_response.cookies[auth_router.GOOGLE_STATE_COOKIE].split("|", 1)[0]
    return client.get(
        f"/api/auth/google/callback?code=test-code&state={state}",
        follow_redirects=False,
    )


def test_google_login_redirect_requests_openid_email_profile(client, monkeypatch):
    _configure_google_oauth(monkeypatch)

    response, location = _start_google_login(client)
    query = parse_qs(location.query)

    assert location.hostname == "accounts.google.com"
    assert query["scope"] == ["openid email profile"]
    assert query["response_type"] == ["code"]
    assert response.cookies[auth_router.GOOGLE_STATE_COOKIE].startswith(query["state"][0] + "|")


def test_calendar_settings_authorization_returns_url_and_state_cookie(
    client, db_session, monkeypatch
):
    _configure_google_oauth(monkeypatch)
    user = _create_user(db_session, "settings-calendar-owner")

    response = client.get(
        "/api/auth/google/calendar/authorize",
        headers=_auth_header(_make_token(user)),
    )

    assert response.status_code == 200
    authorization_url = response.json()["authorization_url"]
    query = parse_qs(urlsplit(authorization_url).query)
    assert query["scope"] == [
        "openid email profile https://www.googleapis.com/auth/calendar.events"
    ]
    assert query["access_type"] == ["offline"]
    assert query["prompt"] == ["consent"]
    assert response.cookies[auth_router.GOOGLE_STATE_COOKIE].split("|")[1] == "calendar_settings"


def test_calendar_settings_can_connect_a_different_google_account(
    client, db_session, monkeypatch
):
    _configure_google_oauth(monkeypatch)
    monkeypatch.setenv("GOOGLE_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    user = _create_user(db_session, "settings-calendar-different-google")
    user.google_refresh_token = encrypt_refresh_token("old-refresh-token")
    db_session.commit()
    monkeypatch.setattr(auth_router, "sync_user_meetings_to_google", lambda user_id: None)
    authorization = client.get(
        "/api/auth/google/calendar/authorize",
        headers=_auth_header(_make_token(user)),
    )
    state = authorization.cookies[auth_router.GOOGLE_STATE_COOKIE].split("|", 1)[0]
    _mock_google_profile(
        monkeypatch,
        {
            "email": "personal.calendar@example.test",
            "email_verified": True,
            "name": "Personal Calendar",
        },
        {"access_token": "google-access-token", "refresh_token": "private-refresh-token"},
    )

    callback = client.get(
        f"/api/auth/google/callback?code=calendar-code&state={state}",
        follow_redirects=False,
    )

    assert callback.status_code == 303
    assert callback.headers["location"].startswith(
        "http://localhost:8000/static/dashboard.html?calendar_connected=1"
    )
    db_session.refresh(user)
    assert decrypt_refresh_token(user.google_refresh_token) != "old-refresh-token"
    assert decrypt_refresh_token(user.google_refresh_token) == "private-refresh-token"


def test_calendar_status_and_disconnect(client, db_session, monkeypatch):
    user = _create_user(db_session, "settings-calendar-disconnect")
    headers = _auth_header(_make_token(user))
    revoke_calls = []
    monkeypatch.setattr(
        auth_router,
        "revoke_google_refresh_token",
        revoke_calls.append,
    )

    disconnected = client.get("/api/auth/google/calendar/status", headers=headers)
    assert disconnected.status_code == 200
    assert disconnected.json() == {"connected": False, "connected_at": None}

    user.google_refresh_token = "encrypted-refresh-token"
    user.google_calendar_connected_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db_session.commit()
    connected = client.get("/api/auth/google/calendar/status", headers=headers)
    assert connected.json()["connected"] is True

    response = client.delete(
        "/api/auth/google/calendar/disconnect",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == {"connected": False}
    assert revoke_calls == ["encrypted-refresh-token"]
    db_session.refresh(user)
    assert user.google_refresh_token is None
    assert user.google_calendar_connected_at is None


def test_google_callback_registers_new_user_and_redirects_with_token(
    client, db_session, monkeypatch
):
    _configure_google_oauth(monkeypatch)
    _mock_google_profile(
        monkeypatch,
        {
            "email": "new.person@example.test",
            "email_verified": True,
            "name": "New Person",
            "picture": "https://images.example.test/person.png",
        },
    )
    login_response, location = _start_google_login(client)

    response = _complete_google_login(client, login_response, location)

    assert response.status_code == 303
    redirect = urlsplit(response.headers["location"])
    values = parse_qs(redirect.fragment)
    user = db_session.query(User).filter_by(email="new.person@example.test").one()
    assert user.full_name == "New Person"
    assert user.role == "employee"
    assert values["access_token"]
    assert values["email"] == [user.email]
    assert values["picture"] == ["https://images.example.test/person.png"]


def test_google_callback_logs_in_existing_user(client, db_session, monkeypatch):
    _configure_google_oauth(monkeypatch)
    user = User(
        username="known-google-user",
        email="known@example.test",
        full_name="Existing User",
        hashed_password=hash_password("local-password"),
        role="employee",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    _mock_google_profile(
        monkeypatch,
        {
            "email": "known@example.test",
            "email_verified": True,
            "name": "Google Display Name",
            "picture": "https://images.example.test/known.png",
        },
    )
    login_response, location = _start_google_login(client)

    response = _complete_google_login(client, login_response, location)

    assert response.status_code == 303
    values = parse_qs(urlsplit(response.headers["location"]).fragment)
    assert values["username"] == ["known-google-user"]
    assert db_session.query(User).filter_by(email="known@example.test").count() == 1


def test_google_callback_rejects_invalid_state(client, monkeypatch):
    _configure_google_oauth(monkeypatch)
    _start_google_login(client)

    response = client.get(
        "/api/auth/google/callback?code=test-code&state=wrong-state",
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid OAuth state"


def test_invitee_calendar_consent_stores_encrypted_token_and_starts_sync(
    client, db_session, monkeypatch
):
    _configure_google_oauth(monkeypatch)
    monkeypatch.setenv("GOOGLE_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    user = User(
        username="calendar-invitee",
        email="invitee@example.test",
        full_name="Calendar Invitee",
        hashed_password=hash_password("local-password"),
        role="employee",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    consent_url = make_calendar_consent_url(user)
    consent_parts = urlsplit(consent_url)

    consent_response = client.get(
        f"{consent_parts.path}?{consent_parts.query}",
        follow_redirects=False,
    )
    assert consent_response.status_code == 307
    consent_query = parse_qs(urlsplit(consent_response.headers["location"]).query)
    assert "https://www.googleapis.com/auth/calendar.events" in consent_query["scope"][0]
    assert consent_query["access_type"] == ["offline"]

    _mock_google_profile(
        monkeypatch,
        {"email": "invitee@example.test", "email_verified": True, "name": "Calendar Invitee"},
        {"access_token": "google-access-token", "refresh_token": "private-refresh-token"},
    )
    state = consent_response.cookies[auth_router.GOOGLE_STATE_COOKIE].split("|", 1)[0]
    monkeypatch.setattr(auth_router, "sync_user_meetings_to_google", lambda user_id: None)
    callback = client.get(
        f"/api/auth/google/callback?code=calendar-code&state={state}",
        follow_redirects=False,
    )

    assert callback.status_code == 303
    assert "calendar_connected=1" in callback.headers["location"]
    db_session.expire_all()
    saved_user = db_session.query(User).filter_by(id=user.id).one()
    assert saved_user.google_refresh_token != "private-refresh-token"
    assert decrypt_refresh_token(saved_user.google_refresh_token) == "private-refresh-token"
    assert saved_user.google_calendar_connected_at is not None


def test_calendar_consent_rejects_google_email_mismatch(client, db_session, monkeypatch):
    _configure_google_oauth(monkeypatch)
    monkeypatch.setenv("GOOGLE_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    user = User(
        username="calendar-owner",
        email="owner@example.test",
        full_name="Calendar Owner",
        hashed_password=hash_password("local-password"),
        role="employee",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    consent_parts = urlsplit(make_calendar_consent_url(user))
    consent_response = client.get(
        f"{consent_parts.path}?{consent_parts.query}",
        follow_redirects=False,
    )
    _mock_google_profile(
        monkeypatch,
        {"email": "other@example.test", "email_verified": True, "name": "Different Account"},
        {"access_token": "google-access-token", "refresh_token": "private-refresh-token"},
    )
    state = consent_response.cookies[auth_router.GOOGLE_STATE_COOKIE].split("|", 1)[0]

    callback = client.get(
        f"/api/auth/google/callback?code=calendar-code&state={state}",
        follow_redirects=False,
    )

    assert callback.status_code == 403
    db_session.expire_all()
    saved_user = db_session.query(User).filter_by(id=user.id).one()
    assert saved_user.google_refresh_token is None
````

## File: tests/test_google_calendar_service.py
````python
from datetime import datetime, timedelta

from cryptography.fernet import Fernet
import httpx
from sqlalchemy.orm import sessionmaker

from app.models.google_calendar_event import GoogleCalendarEvent
from app.models.meeting import MeetingParticipant
from app.services import google_calendar_service
from app.services.google_calendar_service import encrypt_refresh_token
from tests.conftest import test_engine
from tests.helpers import _add_participant, _create_meeting, _create_room, _create_user


class FakeGoogleResponse:
    status_code = 200

    def raise_for_status(self):
        return None



def test_invitee_meeting_is_inserted_once_in_google_calendar(db_session, monkeypatch):
    monkeypatch.setenv("GOOGLE_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    monkeypatch.setenv("APP_TIMEZONE", "Asia/Ho_Chi_Minh")
    organizer = _create_user(db_session, "calendar-sync-organizer")
    invitee = _create_user(db_session, "calendar-sync-invitee")
    invitee.google_refresh_token = encrypt_refresh_token("stored-refresh-token")
    db_session.commit()
    room = _create_room(db_session, "Calendar Sync Room")
    start = datetime.now() + timedelta(days=3)
    meeting = _create_meeting(db_session, room, organizer, start, start + timedelta(hours=1))
    meeting.title = "Project sync"
    meeting.description = "Planning session"
    db_session.add(MeetingParticipant(meeting_id=meeting.id, user_id=invitee.id))
    db_session.commit()

    session_factory = sessionmaker(bind=test_engine)
    monkeypatch.setattr(google_calendar_service, "SessionLocal", session_factory)
    monkeypatch.setattr(google_calendar_service, "_access_token", lambda token: "google-access-token")
    inserted_events = []

    def fake_insert(url, **kwargs):
        inserted_events.append((url, kwargs))
        return FakeGoogleResponse()

    monkeypatch.setattr(google_calendar_service.httpx, "post", fake_insert)

    google_calendar_service.sync_user_meetings_to_google(invitee.id)
    google_calendar_service.sync_user_meetings_to_google(invitee.id)

    assert len(inserted_events) == 1
    url, request = inserted_events[0]
    payload = request["json"]
    assert url == google_calendar_service.GOOGLE_EVENTS_URL
    assert request["headers"]["Authorization"] == "Bearer google-access-token"
    assert payload["summary"] == "Project sync"
    assert payload["location"] == "Calendar Sync Room - Floor 1"
    assert payload["start"]["timeZone"] == "Asia/Ho_Chi_Minh"
    assert db_session.query(GoogleCalendarEvent).filter_by(user_id=invitee.id, meeting_id=meeting.id).count() == 1


def test_organizer_meeting_is_inserted_with_invitees(db_session, monkeypatch):
    monkeypatch.setenv("GOOGLE_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    organizer = _create_user(db_session, "calendar-sync-connected-organizer")
    organizer.google_refresh_token = encrypt_refresh_token("organizer-refresh-token")
    invitee = _create_user(db_session, "calendar-sync-organizer-invitee")
    db_session.commit()
    room = _create_room(db_session, "Organizer Calendar Room")
    start = datetime.now() + timedelta(days=3)
    meeting = _create_meeting(db_session, room, organizer, start, start + timedelta(hours=1))
    _add_participant(db_session, meeting, invitee)

    monkeypatch.setattr(google_calendar_service, "SessionLocal", sessionmaker(bind=test_engine))
    monkeypatch.setattr(google_calendar_service, "_access_token", lambda token: "google-access-token")
    inserted_events = []

    def fake_insert(url, **kwargs):
        inserted_events.append((url, kwargs))
        return FakeGoogleResponse()

    monkeypatch.setattr(google_calendar_service.httpx, "post", fake_insert)
    google_calendar_service.sync_user_meetings_to_google(organizer.id)

    assert len(inserted_events) == 1
    url, request = inserted_events[0]
    assert url == google_calendar_service.GOOGLE_EVENTS_URL
    assert request["params"] == {"sendUpdates": "all"}
    assert request["json"]["attendees"] == [{"email": invitee.email}]
    assert db_session.query(GoogleCalendarEvent).filter_by(
        user_id=organizer.id,
        meeting_id=meeting.id,
    ).count() == 1


def test_calendar_permission_403_logs_reconnect_guidance(db_session, monkeypatch, caplog):
    monkeypatch.setenv("GOOGLE_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    organizer = _create_user(db_session, "calendar-sync-403-organizer")
    organizer.google_refresh_token = encrypt_refresh_token("organizer-refresh-token")
    db_session.commit()
    room = _create_room(db_session, "Calendar 403 Room")
    start = datetime.now() + timedelta(days=3)
    meeting = _create_meeting(db_session, room, organizer, start, start + timedelta(hours=1))

    monkeypatch.setattr(google_calendar_service, "SessionLocal", sessionmaker(bind=test_engine))
    monkeypatch.setattr(google_calendar_service, "_access_token", lambda token: "google-access-token")

    def forbidden_insert(url, **kwargs):
        response = httpx.Response(
            403,
            json={
                "error": {
                    "code": 403,
                    "message": "Insufficient Permission",
                    "errors": [{"reason": "insufficientPermissions"}],
                }
            },
            request=httpx.Request("POST", url),
        )
        response.raise_for_status()

    monkeypatch.setattr(google_calendar_service.httpx, "post", forbidden_insert)

    google_calendar_service.sync_user_meetings_to_google(organizer.id)

    assert "insufficientPermissions" in caplog.text
    assert "disconnect Google Calendar in Settings and connect again" in caplog.text
    assert db_session.query(GoogleCalendarEvent).filter_by(
        user_id=organizer.id,
        meeting_id=meeting.id,
    ).count() == 0


def test_access_token_refresh_sends_client_credentials(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "oauth-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "oauth-client-secret")
    requests = []

    class TokenResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"access_token": "fresh-access-token"}

    def fake_post(url, **kwargs):
        requests.append((url, kwargs))
        return TokenResponse()

    monkeypatch.setattr(google_calendar_service.httpx, "post", fake_post)

    assert google_calendar_service._access_token("refresh-token") == "fresh-access-token"
    url, request = requests[0]
    assert url == google_calendar_service.GOOGLE_TOKEN_URL
    assert request["data"] == {
        "client_id": "oauth-client-id",
        "client_secret": "oauth-client-secret",
        "refresh_token": "refresh-token",
        "grant_type": "refresh_token",
    }


def test_access_token_refresh_logs_google_oauth_error(monkeypatch, caplog):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "oauth-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "oauth-client-secret")

    def failed_refresh(url, **kwargs):
        response = httpx.Response(
            400,
            json={
                "error": "invalid_grant",
                "error_description": "Token has been expired or revoked.",
            },
            request=httpx.Request("POST", url),
        )
        return response

    monkeypatch.setattr(google_calendar_service.httpx, "post", failed_refresh)

    try:
        google_calendar_service._access_token("secret-refresh-token-value")
    except httpx.HTTPStatusError:
        pass
    else:
        raise AssertionError("Expected the Google token refresh request to fail")

    assert "invalid_grant" in caplog.text
    assert "Token has been expired or revoked." in caplog.text
    assert "oauth-client-secret" not in caplog.text
    assert "secret-refresh-token-value" not in caplog.text
````

## File: tests/test_meeting_cancel.py
````python
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from tests.helpers import (
    _add_participant,
    _auth_header,
    _create_meeting,
    _create_room,
    _create_user,
    _make_token,
)
from app.models.meeting import MeetingParticipant


def _future_window():
    start = datetime.utcnow() + timedelta(days=2)
    return start, start + timedelta(hours=1)


def test_organizer_can_cancel_and_repeat_safely(client: TestClient, db_session: Session):
    organizer = _create_user(db_session, "cancel-organizer")
    participant = _create_user(db_session, "cancel-participant")
    room = _create_room(db_session, "Cancel Room")
    start, end = _future_window()
    meeting = _create_meeting(db_session, room, organizer, start, end)
    _add_participant(db_session, meeting, participant)

    headers = _auth_header(_make_token(organizer))
    response = client.patch(f"/api/meetings/{meeting.id}/cancel", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"

    repeated = client.patch(f"/api/meetings/{meeting.id}/cancel", headers=headers)
    assert repeated.status_code == 200
    assert repeated.json()["status"] == "CANCELLED"

    db_session.expire_all()
    saved = db_session.get(type(meeting), meeting.id)
    assert saved.status == "CANCELLED"
    assert db_session.query(MeetingParticipant).filter_by(meeting_id=meeting.id).count() == 1


def test_admin_can_cancel(client: TestClient, db_session: Session):
    organizer = _create_user(db_session, "admin-target-organizer")
    admin = _create_user(db_session, "cancel-admin", role="admin")
    room = _create_room(db_session, "Admin Cancel Room")
    start, end = _future_window()
    meeting = _create_meeting(db_session, room, organizer, start, end)

    response = client.patch(
        f"/api/meetings/{meeting.id}/cancel",
        headers=_auth_header(_make_token(admin)),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


def test_organizer_can_cancel_with_delete_endpoint(client: TestClient, db_session: Session):
    organizer = _create_user(db_session, "delete-organizer")
    room = _create_room(db_session, "Delete Organizer Room")
    start, end = _future_window()
    meeting = _create_meeting(db_session, room, organizer, start, end)

    response = client.delete(
        f"/api/meetings/{meeting.id}",
        headers=_auth_header(_make_token(organizer)),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


def test_admin_can_cancel_with_delete_endpoint(client: TestClient, db_session: Session):
    organizer = _create_user(db_session, "delete-admin-target")
    admin = _create_user(db_session, "delete-admin", role="admin")
    room = _create_room(db_session, "Delete Admin Room")
    start, end = _future_window()
    meeting = _create_meeting(db_session, room, organizer, start, end)

    response = client.delete(
        f"/api/meetings/{meeting.id}",
        headers=_auth_header(_make_token(admin)),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


def test_admin_role_is_case_insensitive(client: TestClient, db_session: Session):
    organizer = _create_user(db_session, "upper-admin-target")
    admin = _create_user(db_session, "upper-case-admin", role="ADMIN")
    room = _create_room(db_session, "Upper Admin Room")
    start, end = _future_window()
    meeting = _create_meeting(db_session, room, organizer, start, end)

    response = client.delete(
        f"/api/meetings/{meeting.id}",
        headers=_auth_header(_make_token(admin)),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


def test_invitee_cannot_cancel_with_delete_endpoint(client: TestClient, db_session: Session):
    organizer = _create_user(db_session, "delete-protected-organizer")
    invitee = _create_user(db_session, "delete-protected-invitee")
    room = _create_room(db_session, "Delete Protected Room")
    start, end = _future_window()
    meeting = _create_meeting(db_session, room, organizer, start, end)
    _add_participant(db_session, meeting, invitee)

    response = client.delete(
        f"/api/meetings/{meeting.id}",
        headers=_auth_header(_make_token(invitee)),
    )

    assert response.status_code == 403
    db_session.expire_all()
    assert db_session.get(type(meeting), meeting.id).status == "scheduled"


def test_non_organizer_cannot_cancel(client: TestClient, db_session: Session):
    organizer = _create_user(db_session, "protected-organizer")
    outsider = _create_user(db_session, "cancel-outsider")
    room = _create_room(db_session, "Protected Cancel Room")
    start, end = _future_window()
    meeting = _create_meeting(db_session, room, organizer, start, end)

    response = client.patch(
        f"/api/meetings/{meeting.id}/cancel",
        headers=_auth_header(_make_token(outsider)),
    )
    assert response.status_code == 403
    db_session.expire_all()
    assert db_session.get(type(meeting), meeting.id).status == "scheduled"


def test_cancel_requires_authentication(client: TestClient, db_session: Session):
    organizer = _create_user(db_session, "auth-cancel-organizer")
    room = _create_room(db_session, "Auth Cancel Room")
    start, end = _future_window()
    meeting = _create_meeting(db_session, room, organizer, start, end)

    response = client.patch(f"/api/meetings/{meeting.id}/cancel")
    assert response.status_code == 401


def test_cancel_missing_meeting_returns_404(client: TestClient, db_session: Session):
    user = _create_user(db_session, "missing-cancel-user")
    response = client.patch(
        "/api/meetings/999999/cancel",
        headers=_auth_header(_make_token(user)),
    )
    assert response.status_code == 404


def test_room_can_be_booked_again_after_cancel(client: TestClient, db_session: Session):
    organizer = _create_user(db_session, "reuse-organizer")
    room = _create_room(db_session, "Reusable Room")
    start, end = _future_window()
    meeting = _create_meeting(db_session, room, organizer, start, end)

    cancel = client.patch(
        f"/api/meetings/{meeting.id}/cancel",
        headers=_auth_header(_make_token(organizer)),
    )
    assert cancel.status_code == 200

    booking = client.post(
        "/api/meetings/book",
        json={
            "title": "Replacement meeting",
            "room_id": room.id,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        },
        headers=_auth_header(_make_token(organizer)),
    )
    assert booking.status_code == 201
    assert len(booking.json()) == 1

    available = client.get(
        "/api/rooms/available/",
        params={"start_time": start.isoformat(), "end_time": end.isoformat()},
    )
    assert available.status_code == 200
    assert room.id not in {item["id"] for item in available.json()}
````

## File: tests/test_meeting_create.py
````python
from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.routers import meetings as meetings_router
from tests.helpers import _auth_header, _create_room, _create_user, _make_token


def _future_window():
    start = datetime.utcnow() + timedelta(days=2)
    return start, start + timedelta(hours=1)


def test_create_offline_meeting_with_room(client: TestClient, db_session: Session):
    organizer = _create_user(db_session, "create-offline-organizer")
    room = _create_room(db_session, "Create Offline Room")
    start, end = _future_window()

    response = client.post(
        "/api/meetings/book",
        json={
            "title": "Offline meeting",
            "meeting_type": "offline",
            "room_id": room.id,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        },
        headers=_auth_header(_make_token(organizer)),
    )

    assert response.status_code == 201
    meeting = response.json()[0]
    assert meeting["meeting_type"] == "offline"
    assert meeting["room_id"] == room.id


def test_create_offline_meeting_without_room_returns_400(
    client: TestClient, db_session: Session
):
    organizer = _create_user(db_session, "create-offline-no-room")
    start, end = _future_window()

    response = client.post(
        "/api/meetings/book",
        json={
            "title": "Offline meeting without room",
            "meeting_type": "offline",
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        },
        headers=_auth_header(_make_token(organizer)),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Offline meetings require a room_id"


def test_create_online_meeting_with_link(client: TestClient, db_session: Session):
    organizer = _create_user(db_session, "create-online-organizer")
    start, end = _future_window()

    response = client.post(
        "/api/meetings/book",
        json={
            "title": "Online meeting",
            "meeting_type": "online",
            "meeting_link": "https://meet.test/room",
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        },
        headers=_auth_header(_make_token(organizer)),
    )

    assert response.status_code == 201
    meeting = response.json()[0]
    assert meeting["meeting_type"] == "online"
    assert meeting["meeting_link"] == "https://meet.test/room"
    assert meeting["room_id"] is None


def test_create_online_meeting_without_link_returns_400(
    client: TestClient, db_session: Session
):
    organizer = _create_user(db_session, "create-online-no-link")
    start, end = _future_window()

    response = client.post(
        "/api/meetings/book",
        json={
            "title": "Online meeting without link",
            "meeting_type": "online",
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        },
        headers=_auth_header(_make_token(organizer)),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Online meetings require a meeting_link"


def test_create_meeting_schedules_google_sync_for_connected_organizer(
    client: TestClient, db_session: Session, monkeypatch
):
    organizer = _create_user(db_session, "create-connected-organizer")
    organizer.google_refresh_token = "encrypted-refresh-token"
    db_session.commit()
    room = _create_room(db_session, "Connected Organizer Room")
    start, end = _future_window()
    synced_user_ids = []
    monkeypatch.setattr(
        meetings_router,
        "sync_user_meetings_to_google",
        synced_user_ids.append,
    )

    response = client.post(
        "/api/meetings/book",
        json={
            "title": "Automatically synced meeting",
            "meeting_type": "offline",
            "room_id": room.id,
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        },
        headers=_auth_header(_make_token(organizer)),
    )

    assert response.status_code == 201
    assert synced_user_ids == [organizer.id]
````

## File: .gitignore
````
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[codz]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
#   Usually these files are written by a python script from a template
#   before PyInstaller builds the exe, so as to inject date/other infos into it.
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py.cover
.hypothesis/
.pytest_cache/
cover/

# Translations
*.mo
*.pot

# Django stuff:
*.log
local_settings.py
db.sqlite3
db.sqlite3-journal

# Flask stuff:
instance/
.webassets-cache

# Scrapy stuff:
.scrapy

# Sphinx documentation
docs/_build/

# PyBuilder
.pybuilder/
target/

# Jupyter Notebook
.ipynb_checkpoints

# IPython
profile_default/
ipython_config.py

# pyenv
#   For a library or package, you might want to ignore these files since the code is
#   intended to run in multiple environments; otherwise, check them in:
# .python-version

# pipenv
#   According to pypa/pipenv#598, it is recommended to include Pipfile.lock in version control.
#   However, in case of collaboration, if having platform-specific dependencies or dependencies
#   having no cross-platform support, pipenv may install dependencies that don't work, or not
#   install all needed dependencies.
# Pipfile.lock

# UV
#   Similar to Pipfile.lock, it is generally recommended to include uv.lock in version control.
#   This is especially recommended for binary packages to ensure reproducibility, and is more
#   commonly ignored for libraries.
# uv.lock

# poetry
#   Similar to Pipfile.lock, it is generally recommended to include poetry.lock in version control.
#   This is especially recommended for binary packages to ensure reproducibility, and is more
#   commonly ignored for libraries.
#   https://python-poetry.org/docs/basic-usage/#commit-your-poetrylock-file-to-version-control
# poetry.lock
# poetry.toml

# pdm
#   Similar to Pipfile.lock, it is generally recommended to include pdm.lock in version control.
#   pdm recommends including project-wide configuration in pdm.toml, but excluding .pdm-python.
#   https://pdm-project.org/en/latest/usage/project/#working-with-version-control
# pdm.lock
# pdm.toml
.pdm-python
.pdm-build/

# pixi
#   Similar to Pipfile.lock, it is generally recommended to include pixi.lock in version control.
# pixi.lock
#   Pixi creates a virtual environment in the .pixi directory, just like venv module creates one
#   in the .venv directory. It is recommended not to include this directory in version control.
.pixi

# PEP 582; used by e.g. github.com/David-OConnor/pyflow and github.com/pdm-project/pdm
__pypackages__/

# Celery stuff
celerybeat-schedule
celerybeat.pid

# Redis
*.rdb
*.aof
*.pid

# RabbitMQ
mnesia/
rabbitmq/
rabbitmq-data/

# ActiveMQ
activemq-data/

# SageMath parsed files
*.sage.py

# Environments
.env
.envrc
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# Pyre type checker
.pyre/

# pytype static type analyzer
.pytype/

# Cython debug symbols
cython_debug/

# PyCharm
#   JetBrains specific template is maintained in a separate JetBrains.gitignore that can
#   be found at https://github.com/github/gitignore/blob/main/Global/JetBrains.gitignore
#   and can be added to the global gitignore or merged into this file.  For a more nuclear
#   option (not recommended) you can uncomment the following to ignore the entire idea folder.
# .idea/

# Abstra
#   Abstra is an AI-powered process automation framework.
#   Ignore directories containing user credentials, local state, and settings.
#   Learn more at https://abstra.io/docs
.abstra/

# Visual Studio Code
#   Visual Studio Code specific template is maintained in a separate VisualStudioCode.gitignore 
#   that can be found at https://github.com/github/gitignore/blob/main/Global/VisualStudioCode.gitignore
#   and can be added to the global gitignore or merged into this file. However, if you prefer, 
#   you could uncomment the following to ignore the entire vscode folder
# .vscode/
# Temporary file for partial code execution
tempCodeRunnerFile.py

# Ruff stuff:
.ruff_cache/

# PyPI configuration file
.pypirc

# Marimo
marimo/_static/
marimo/_lsp/
__marimo__/

# Streamlit
.streamlit/secrets.toml



venv/
__pycache__/
.env

# Test database
test.db
````

## File: package.json
````json
{
  "name": "meeting-system",
  "version": "1.0.0",
  "description": "Meeting Room Management System",
  "scripts": {
    "frontend": "npx serve frontend -l 3000"
  }
}
````

## File: app/models/__init__.py
````python
# app/models/__init__.py

from app.core.database import Base
from app.models.user import User
from app.models.room import Room
from app.models.meeting import Meeting
from app.models.equipment import Equipment, MeetingEquipment, RoomEquipment

__all__ = [
    "Base",
    "User",
    "Room",
    "Meeting",
    "Equipment",
    "MeetingEquipment",
    "RoomEquipment",
]
````

## File: app/models/room.py
````python
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, event, func
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Mapper, relationship
from app.db.session import Base


class Room(Base):
    """Phòng họp."""

    __tablename__ = "rooms"
    default_equipments = relationship("RoomEquipment", back_populates="room", cascade="all, delete-orphan")
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True, comment="Tên phòng")
    location = Column(String(255), nullable=True, comment="Vị trí phòng")
    capacity = Column(Integer, nullable=False, default=1, comment="Sức chứa")
    description = Column(Text, nullable=True, comment="Mô tả")
    amenities = Column(Text, nullable=True, comment="Tiện ích phòng họp (JSON list)")
    is_active = Column(Boolean, nullable=False, default=True, comment="Trạng thái phòng")
    qr_token = Column(String(64), nullable=True, unique=True, index=True, default=lambda: str(uuid4()))
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())

    def generate_qr_token(self) -> str:
        """Generate a stable QR token for this room when it does not have one."""
        if not self.qr_token:
            self.qr_token = str(uuid4())
        return self.qr_token

    def __repr__(self) -> str:
        return f"<Room id={self.id} name={self.name!r}>"


@event.listens_for(Room, "before_insert")
def _ensure_room_qr_token(mapper: Mapper[Room], connection: Connection, room: Room) -> None:
    room.generate_qr_token()
````

## File: tests/test_meetings_history.py
````python
"""Tests for GET /api/meetings/history."""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.helpers import (
    _create_user,
    _create_room,
    _create_meeting,
    _add_participant,
    _make_token,
    _auth_header,
)


class TestNoToken:
    def test_returns_401_without_token(self, client: TestClient):
        resp = client.get("/api/meetings/history")
        assert resp.status_code == 401


class TestOrganizerSeesMeeting:
    def test_organizer_in_history(self, client: TestClient, db_session: Session):
        org = _create_user(db_session, "organizer")
        room = _create_room(db_session)
        past = datetime.utcnow() - timedelta(days=3)
        end = datetime.utcnow() - timedelta(days=1)
        m = _create_meeting(db_session, room, org, past, end)

        resp = client.get("/api/meetings/history", headers=_auth_header(_make_token(org)))
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()]
        assert m.id in ids


class TestParticipantSeesMeeting:
    def test_invited_user_in_history(self, client: TestClient, db_session: Session):
        org = _create_user(db_session, "organizer2")
        invitee = _create_user(db_session, "invitee")
        room = _create_room(db_session, "Room B")
        past = datetime.utcnow() - timedelta(days=5)
        end = datetime.utcnow() - timedelta(days=4)
        m = _create_meeting(db_session, room, org, past, end)
        _add_participant(db_session, m, invitee)

        resp = client.get("/api/meetings/history", headers=_auth_header(_make_token(invitee)))
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()]
        assert m.id in ids


class TestNonParticipantExcluded:
    def test_outsider_sees_nothing(self, client: TestClient, db_session: Session):
        org = _create_user(db_session, "organizer3")
        outsider = _create_user(db_session, "outsider")
        room = _create_room(db_session, "Room C")
        past = datetime.utcnow() - timedelta(days=7)
        end = datetime.utcnow() - timedelta(days=6)
        _create_meeting(db_session, room, org, past, end)

        resp = client.get("/api/meetings/history", headers=_auth_header(_make_token(outsider)))
        assert resp.status_code == 200
        assert resp.json() == []


class TestFutureMeetingExcluded:
    def test_future_meeting_not_in_history(self, client: TestClient, db_session: Session):
        org = _create_user(db_session, "organizer4")
        room = _create_room(db_session, "Room D")
        future_start = datetime.utcnow() + timedelta(days=1)
        future_end = datetime.utcnow() + timedelta(days=2)
        m = _create_meeting(db_session, room, org, future_start, future_end)

        resp = client.get("/api/meetings/history", headers=_auth_header(_make_token(org)))
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()]
        assert m.id not in ids


class TestCanceledMeetingExcluded:
    def test_canceled_meeting_not_in_history(self, client: TestClient, db_session: Session):
        org = _create_user(db_session, "organizer5")
        room = _create_room(db_session, "Room E")
        past = datetime.utcnow() - timedelta(days=10)
        end = datetime.utcnow() - timedelta(days=9)
        m = _create_meeting(db_session, room, org, past, end, status="canceled")

        resp = client.get("/api/meetings/history", headers=_auth_header(_make_token(org)))
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()]
        assert m.id not in ids


class TestNoDuplicates:
    def test_no_duplicate_when_organizer_and_participant(self, client: TestClient, db_session: Session):
        org = _create_user(db_session, "organizer6")
        room = _create_room(db_session, "Room F")
        past = datetime.utcnow() - timedelta(days=2)
        end = datetime.utcnow() - timedelta(hours=1)
        m = _create_meeting(db_session, room, org, past, end)
        _add_participant(db_session, m, org)

        resp = client.get("/api/meetings/history", headers=_auth_header(_make_token(org)))
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()]
        assert ids.count(m.id) == 1, "Duplicate records must not be returned"


class TestOrderByDesc:
    def test_ordered_by_end_time_desc(self, client: TestClient, db_session: Session):
        org = _create_user(db_session, "organizer7")
        room = _create_room(db_session, "Room G")
        m1 = _create_meeting(db_session, room, org,
                             datetime.utcnow() - timedelta(days=10),
                             datetime.utcnow() - timedelta(days=9))
        m2 = _create_meeting(db_session, room, org,
                             datetime.utcnow() - timedelta(days=3),
                             datetime.utcnow() - timedelta(days=2))
        m3 = _create_meeting(db_session, room, org,
                             datetime.utcnow() - timedelta(days=20),
                             datetime.utcnow() - timedelta(days=19))

        resp = client.get("/api/meetings/history", headers=_auth_header(_make_token(org)))
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()]
        assert ids == [m2.id, m1.id, m3.id]


class TestResponseShape:
    def test_response_has_expected_fields(self, client: TestClient, db_session: Session):
        org = _create_user(db_session, "organizer8")
        room = _create_room(db_session, "Room H")
        past = datetime.utcnow() - timedelta(days=5)
        end = datetime.utcnow() - timedelta(days=4)
        _create_meeting(db_session, room, org, past, end)

        resp = client.get("/api/meetings/history", headers=_auth_header(_make_token(org)))
        assert resp.status_code == 200
        item = resp.json()[0]
        expected = {
            "id", "title", "description",
            "meeting_type", "meeting_link", "online_link",
            "room_id", "organizer_id",
            "start_time", "end_time", "status",
            "is_recurring", "recurring_type",
            "equipments", "participant_ids",
        }
        assert set(item.keys()) == expected
````

## File: docker-compose.yml
````yaml
services:
  roomsync_db:
    image: mysql:8.0
    container_name: roomsync_db
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:-03062006}
      MYSQL_DATABASE: meeting_db
      MYSQL_USER: roomsync_user
      MYSQL_PASSWORD: roomsync_pass
    ports:
      - "3307:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    healthcheck:
      test: ["CMD-SHELL", "mysqladmin ping -h localhost -uroot -p$$MYSQL_ROOT_PASSWORD"]
      interval: 5s
      timeout: 5s
      retries: 10
      start_period: 20s

  web:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: roomsync_backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: mysql+pymysql://root:${MYSQL_ROOT_PASSWORD:-03062006}@roomsync_db:3306/meeting_db
      SECRET_KEY: roomsync_super_secret_jwt_key
    volumes:
      - .:/app
    depends_on:
      roomsync_db:
        condition: service_healthy

volumes:
  mysql_data:
````

## File: schema.sql
````sql
CREATE DATABASE IF NOT EXISTS meeting_db
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE meeting_db;

CREATE TABLE IF NOT EXISTS users (
    id              INT UNSIGNED NOT NULL AUTO_INCREMENT,
    username        VARCHAR(50) NOT NULL,
    email           VARCHAR(150) DEFAULT NULL,
    full_name       VARCHAR(150) DEFAULT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role            VARCHAR(20) NOT NULL DEFAULT 'user',
    is_active       TINYINT(1) NOT NULL DEFAULT 1,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_users_username (username),
    UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS rooms (
    id          INT UNSIGNED NOT NULL AUTO_INCREMENT,
    name        VARCHAR(100) NOT NULL,
    location    VARCHAR(255) DEFAULT NULL,
    capacity    INT NOT NULL DEFAULT 1,
    description TEXT DEFAULT NULL,
    amenities   TEXT DEFAULT NULL,
    is_active   TINYINT(1) NOT NULL DEFAULT 1,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_rooms_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS meetings (
    id             INT UNSIGNED NOT NULL AUTO_INCREMENT,
    title          VARCHAR(200) NOT NULL,
    description    TEXT DEFAULT NULL,
    meeting_type   VARCHAR(20) NOT NULL DEFAULT 'offline',
    online_link    VARCHAR(500) DEFAULT NULL,
    is_recurring   TINYINT(1) NOT NULL DEFAULT 0,
    recurring_type VARCHAR(20) DEFAULT NULL,
    room_id        INT UNSIGNED DEFAULT NULL,
    organizer_id   INT UNSIGNED DEFAULT NULL,
    start_time     DATETIME NOT NULL,
    end_time       DATETIME NOT NULL,
    status         VARCHAR(20) NOT NULL DEFAULT 'scheduled',
    created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_meetings_room_id (room_id),
    KEY idx_meetings_organizer_id (organizer_id),
    KEY idx_meetings_start_time (start_time),
    CONSTRAINT fk_meetings_room FOREIGN KEY (room_id) REFERENCES rooms (id) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_meetings_organizer FOREIGN KEY (organizer_id) REFERENCES users (id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS meeting_participants (
    id         INT UNSIGNED NOT NULL AUTO_INCREMENT,
    meeting_id INT UNSIGNED NOT NULL,
    user_id    INT UNSIGNED NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_meeting_participant (meeting_id, user_id),
    CONSTRAINT fk_meeting_participants_meeting FOREIGN KEY (meeting_id) REFERENCES meetings (id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_meeting_participants_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
````

## File: app/core/security.py
````python
from datetime import datetime, timedelta
from typing import Any, Dict
import hashlib
import os
import secrets

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY is not configured")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
DEFAULT_ITERATIONS = 100_000

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(plain_password: str, salt: str | None = None, iterations: int = DEFAULT_ITERATIONS) -> str:
    """Return a PBKDF2-HMAC-SHA256 password hash."""
    salt = salt or secrets.token_hex(12)
    digest = hashlib.pbkdf2_hmac(
        "sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), iterations
    )
    return f"pbkdf2_sha256${iterations}${salt}${digest.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        algorithm, iterations_text, salt, expected = hashed_password.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), int(iterations_text)
        )
        return secrets.compare_digest(digest.hex(), expected)
    except (TypeError, ValueError):
        return False


def authenticate_user(db: Session, username: str, password: str) -> User:
    """Authenticate with a username or email against the MySQL users table."""
    user = db.query(User).filter(
        (User.username == username) | (User.email == username)
    ).first()
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sai tên đăng nhập hoặc mật khẩu",
    )
    if user is None or not verify_password(password, user.hashed_password):
        raise invalid
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị khóa")
    return user


def create_access_token(data: Dict[str, Any], expires_delta: timedelta | None = None) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Phiên đăng nhập không hợp lệ hoặc đã hết hạn",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_role(required_role: str):
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role != required_role and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Quyền hạn không đủ! Yêu cầu vai trò {required_role.upper()}.",
            )
        return current_user

    return role_checker
````

## File: app/models/user.py
````python
# app/models/user.py
from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, func
from app.core.database import Base


class User(Base):
    """Model đại diện cho bảng người dùng (tài khoản) trong hệ thống."""

    __tablename__ = "users"

    # ✅ Sửa primary_primary_key thành primary_key
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True, comment="Tên đăng nhập")
    email = Column(String(150), unique=True, nullable=True, comment="Địa chỉ Email")
    full_name = Column(String(150), nullable=True, comment="Họ và tên người dùng")
    hashed_password = Column(String(255), nullable=False, comment="Mật khẩu đã băm")
    google_refresh_token = Column(Text, nullable=True)
    google_calendar_connected_at = Column(DateTime, nullable=True)
    google_refresh_token = Column(Text, nullable=True)
    google_calendar_connected_at = Column(DateTime, nullable=True)
    role = Column(String(20), nullable=False, default="employee", comment="Vai trò: admin/employee")
    is_active = Column(Boolean, nullable=False, default=True, comment="Trạng thái tài khoản (active/inactive)")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), comment="Thời gian tạo")
    updated_at = Column(DateTime, nullable=True, onupdate=func.now(), comment="Thời gian cập nhật gần nhất")

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r} role={self.role!r}>"
````

## File: app/routers/auth.py
````python
import os
import re
import secrets
from datetime import datetime
from urllib.parse import urlencode, urlsplit, urlunsplit

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    authenticate_user,
    create_access_token,
    get_current_user,
    hash_password,
    require_role,
)
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.services.google_calendar_service import (
    GOOGLE_CALENDAR_EVENTS_SCOPE,
    encrypt_refresh_token,
    revoke_google_refresh_token,
    sync_user_meetings_to_google,
    verify_calendar_consent_signature,
)

router = APIRouter(prefix="/auth")

GOOGLE_AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GOOGLE_STATE_COOKIE = "google_oauth_state"


def _google_oauth_config() -> tuple[str, str, str, str]:
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = os.getenv(
        "GOOGLE_REDIRECT_URI",
        "http://localhost:8000/api/auth/google/callback",
    )
    frontend_login_url = os.getenv(
        "FRONTEND_LOGIN_URL",
        "http://localhost:8000/static/login.html",
    )
    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google sign-in is not configured",
        )
    return client_id, client_secret, redirect_uri, frontend_login_url


def _frontend_redirect(frontend_login_url: str, values: dict[str, str], *, fragment: bool) -> str:
    parts = urlsplit(frontend_login_url)
    encoded_values = urlencode(values)
    if fragment:
        return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, encoded_values))
    query = f"{parts.query}&{encoded_values}" if parts.query else encoded_values
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, ""))


def _unique_google_username(db: Session, email: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9_.-]", "_", email.split("@", 1)[0]).strip("._-")[:40]
    base = base or "google_user"
    username = base
    suffix = 1
    while db.query(User.id).filter(User.username == username).first():
        suffix_text = f"_{suffix}"
        username = f"{base[:50 - len(suffix_text)]}{suffix_text}"
        suffix += 1
    return username


def _google_authorization_redirect(
    flow: str,
    user_id: int | None = None,
    *,
    return_authorization_url: bool = False,
):
    client_id, _, redirect_uri, _ = _google_oauth_config()
    state = secrets.token_urlsafe(32)
    cookie_value = f"{state}|{flow}|{user_id or ''}"
    query = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    if flow.startswith("calendar"):
        query["scope"] += f" {GOOGLE_CALENDAR_EVENTS_SCOPE}"
        query["access_type"] = "offline"
        query["prompt"] = "consent"
    authorization_url = f"{GOOGLE_AUTHORIZATION_URL}?{urlencode(query)}"
    response = (
        JSONResponse({"authorization_url": authorization_url})
        if return_authorization_url
        else RedirectResponse(authorization_url)
    )
    response.set_cookie(
        GOOGLE_STATE_COOKIE,
        cookie_value,
        max_age=600,
        path="/api/auth/google",
        secure=redirect_uri.startswith("https://"),
        httponly=True,
        samesite="lax",
    )
    return response


def _frontend_dashboard_url(frontend_login_url: str) -> str:
    configured_url = os.getenv("FRONTEND_DASHBOARD_URL")
    if configured_url:
        return configured_url
    parts = urlsplit(frontend_login_url)
    if parts.path.endswith("/login.html"):
        path = f"{parts.path[:-len('login.html')]}dashboard.html"
    else:
        path = "/static/dashboard.html"
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def issue_token(user: User) -> TokenResponse:
    token = create_access_token(data={"sub": user.username, "user_id": user.id, "role": user.role})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        role=user.role,
        username=user.username,
        full_name=user.full_name or user.username,
    )


@router.post("/login", response_model=TokenResponse, summary="Đăng nhập")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    return issue_token(authenticate_user(db, payload.username, payload.password))


@router.get("/google/login", summary="Đăng nhập bằng Google")
def google_login():
    return _google_authorization_redirect("login")


@router.get("/google/calendar/connect", summary="Cấp quyền Google Calendar")
def google_calendar_connect(
    user_id: int,
    expires: int,
    signature: str,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user or not verify_calendar_consent_signature(user, expires, signature):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Calendar consent link is invalid or expired")
    return _google_authorization_redirect("calendar", user.id)


@router.get("/google/calendar/authorize", summary="Kết nối Google Calendar cá nhân")
def google_calendar_authorize(current_user: User = Depends(get_current_user)):
    return _google_authorization_redirect(
        "calendar_settings",
        current_user.id,
        return_authorization_url=True,
    )


@router.get("/google/callback", summary="Hoàn tất đăng nhập Google")
def google_callback(
    request: Request,
    background_tasks: BackgroundTasks,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    _, client_secret, redirect_uri, frontend_login_url = _google_oauth_config()
    cookie_parts = request.cookies.get(GOOGLE_STATE_COOKIE, "").split("|", 2)
    if len(cookie_parts) != 3:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state")
    expected_state, flow, flow_user_text = cookie_parts
    if not state or not expected_state or not secrets.compare_digest(state, expected_state):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state")
    if flow not in {"login", "calendar", "calendar_settings"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth flow")
    if error:
        error_code = (
            "calendar_permission_denied"
            if flow in {"calendar", "calendar_settings"} and error == "access_denied"
            else "access_denied" if error == "access_denied" else "oauth_failed"
        )
        redirect_url = (
            _frontend_dashboard_url(frontend_login_url)
            if flow == "calendar_settings"
            else frontend_login_url
        )
        return RedirectResponse(
            _frontend_redirect(redirect_url, {"google_error": error_code}, fragment=False),
            status_code=status.HTTP_303_SEE_OTHER,
        )
    if not code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing OAuth code")

    try:
        token_response = httpx.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": os.environ["GOOGLE_CLIENT_ID"],
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        token_response.raise_for_status()
        token_data = token_response.json()
        google_access_token = token_data.get("access_token")
        if not google_access_token:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Google did not return an access token")

        profile_response = httpx.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {google_access_token}"},
            timeout=10,
        )
        profile_response.raise_for_status()
        profile = profile_response.json()
    except HTTPException:
        raise
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not complete Google sign-in",
        ) from exc

    email = str(profile.get("email") or "").strip().lower()
    if not email or profile.get("email_verified") is not True:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google account email is not verified")

    if flow in {"calendar", "calendar_settings"}:
        try:
            calendar_user_id = int(flow_user_text)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid calendar account") from exc
        user = db.query(User).filter(User.id == calendar_user_id, User.is_active.is_(True)).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Calendar account is not available",
            )
        if flow == "calendar" and (
            not user.email or user.email.strip().lower() != email
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Google email must match the invited RoomSync account",
            )
        refresh_token = token_data.get("refresh_token")
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Google did not return calendar authorization; retry consent",
            )
        try:
            user.google_refresh_token = encrypt_refresh_token(refresh_token)
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        user.google_calendar_connected_at = datetime.now()
        db.commit()
        background_tasks.add_task(sync_user_meetings_to_google, user.id)
        _, _, redirect_uri, frontend_login_url = _google_oauth_config()
        redirect = RedirectResponse(
            _frontend_redirect(
                _frontend_dashboard_url(frontend_login_url),
                {"calendar_connected": "1"},
                fragment=False,
            ),
            status_code=status.HTTP_303_SEE_OTHER,
        )
        redirect.delete_cookie(
            GOOGLE_STATE_COOKIE,
            path="/api/auth/google",
            secure=redirect_uri.startswith("https://"),
            httponly=True,
            samesite="lax",
        )
        return redirect

    user = db.query(User).filter(func.lower(User.email) == email).first()
    if user is None:
        user = User(
            username=_unique_google_username(db, email),
            email=email,
            full_name=str(profile.get("name") or email.split("@", 1)[0])[:150],
            hashed_password=hash_password(secrets.token_urlsafe(48)),
            role="employee",
            is_active=True,
        )
        try:
            db.add(user)
            db.commit()
            db.refresh(user)
        except IntegrityError as exc:
            db.rollback()
            user = db.query(User).filter(func.lower(User.email) == email).first()
            if user is None:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Could not create Google account") from exc
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị khóa")

    token = issue_token(user)
    redirect_values = {
        "access_token": token.access_token,
        "token_type": token.token_type,
        "role": user.role,
        "username": user.username,
        "full_name": user.full_name or user.username,
        "email": user.email or "",
        "user_id": str(user.id),
        "picture": str(profile.get("picture") or ""),
    }
    redirect = RedirectResponse(
        _frontend_redirect(frontend_login_url, redirect_values, fragment=True),
        status_code=status.HTTP_303_SEE_OTHER,
    )
    redirect.delete_cookie(
        GOOGLE_STATE_COOKIE,
        path="/api/auth/google",
        secure=redirect_uri.startswith("https://"),
        httponly=True,
        samesite="lax",
    )
    return redirect


@router.get("/me", response_model=UserResponse, summary="Lấy thông tin cá nhân")
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/google/calendar/status", summary="Trạng thái kết nối Google Calendar")
def google_calendar_status(current_user: User = Depends(get_current_user)):
    return {
        "connected": bool(current_user.google_refresh_token),
        "connected_at": current_user.google_calendar_connected_at,
    }


@router.delete("/google/calendar/disconnect", summary="Ngắt kết nối Google Calendar")
def google_calendar_disconnect(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    encrypted_refresh_token = current_user.google_refresh_token
    current_user.google_refresh_token = None
    current_user.google_calendar_connected_at = None
    db.commit()
    if encrypted_refresh_token:
        background_tasks.add_task(revoke_google_refresh_token, encrypted_refresh_token)
    return {"connected": False}


@router.get("/admin-only", summary="Kiểm tra quyền Admin")
def admin_only_route(current_user: User = Depends(require_role("admin"))):
    return {"status": "success", "message": f"Xin chào Admin {current_user.full_name}! Bạn có toàn quyền quản trị."}
````

## File: app/schemas/room.py
````python
import json
from typing import Optional, List, Union
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

# 1. Class cơ sở định nghĩa tất cả thuộc tính chung của Phòng
class RoomBase(BaseModel):
    name: str = Field(..., description="Tên phòng họp")
    capacity: int = Field(..., gt=0, description="Sức chứa (số người), phải lớn hơn 0")
    location: Optional[str] = Field(None, description="Vị trí/Tầng")
    description: Optional[str] = Field(None, description="Mô tả/Trang thiết bị phòng họp")
    amenities: Optional[Union[List[str], str]] = Field(default_factory=list, description="Danh sách tiện ích")
    is_active: bool = Field(True, description="Trạng thái: True (Hoạt động) / False (Bảo trì/Khóa)")

    @field_validator('amenities', mode='before')
    @classmethod
    def parse_amenities(cls, v):
        if v is None:
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v_str = v.strip()
            if not v_str:
                return []
            try:
                parsed = json.loads(v_str)
                if isinstance(parsed, list):
                    return [str(x).strip() for x in parsed if str(x).strip()]
            except Exception:
                pass
            return [s.strip() for s in v_str.split(',') if s.strip()]
        return []

# 2. Schema nhận dữ liệu khi Tạo phòng mới (POST)
class RoomCreate(RoomBase):
    pass

# 3. Schema nhận dữ liệu khi Cập nhật phòng (PUT)
class RoomUpdate(BaseModel):
    name: Optional[str] = None
    capacity: Optional[int] = Field(None, gt=0)
    location: Optional[str] = None
    description: Optional[str] = None
    amenities: Optional[Union[List[str], str]] = None
    is_active: Optional[bool] = None

# 4. Schema trả dữ liệu về cho Client (Response)
class RoomResponse(RoomBase):
    id: int
    amenities: Optional[List[str]] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RoomQRResponse(BaseModel):
    room_id: int
    room_name: str
    qr_token: str
````

## File: frontend/css/booking.css
````css
@import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap");
@import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap");

:root {
  font-family: "Inter", sans-serif;
  color: #111827;
  background: #f5f7fb;
  font-synthesis: none;
  --blue: #2563eb;
  --blue-dark: #1d4ed8;
  --blue-soft: #eff6ff;
  --gray-950: #111827;
  --gray-700: #374151;
  --gray-600: #4b5563;
  --gray-500: #6b7280;
  --gray-400: #9ca3af;
  --gray-300: #d1d5db;
  --gray-200: #e5e7eb;
  --gray-100: #f3f4f6;
  --white: #ffffff;
  --green: #059669;
  --amber: #b45309;
}

body {
  margin: 0;
  min-width: 320px;
  min-height: 100vh;
}

button,
input,
textarea {
  font: inherit;
}

button {
  cursor: pointer;
}

.page-shell {
  /* Fix cố định phủ kín toàn bộ màn hình */
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 9999;

  /* Căn giữa Form đặt phòng */
  display: none;
  /* Mặc định ẩn form; khi JS bật sẽ chuyển thành display: flex */
  align-items: center;
  justify-content: center;

  /* Nền mờ phía sau giúp nổi bật Modal */
  background: rgba(15, 23, 42, 0.45);
  /* Lớp phủ đen trong suốt */
  backdrop-filter: blur(4px);
  /* Làm mờ nhẹ nền trang web đằng sau */

  padding: 20px;
  overflow-y: auto;
  /* Cho phép cuộn nếu màn hình thiết bị quá nhỏ */
}

.ambient {
  position: absolute;
  border-radius: 999px;
  filter: blur(2px);
  opacity: 0.7;
  pointer-events: none;
}

.ambient-left {
  width: 240px;
  height: 240px;
  left: -100px;
  top: 8%;
  border: 1px solid rgba(37, 99, 235, 0.14);
}

.ambient-right {
  width: 330px;
  height: 330px;
  right: -180px;
  bottom: 2%;
  border: 1px solid rgba(99, 102, 241, 0.13);
}

.modal-card {
  width: 540px;
  max-width: 100%;
  max-height: min(92vh, 740px);
  margin: auto;
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 1;
  background: var(--white);
  border: 1px solid var(--gray-200);
  border-radius: 14px;
  box-shadow: 0 20px 60px rgba(15, 23, 42, 0.18), 0 4px 16px rgba(15, 23, 42, 0.06);
  padding: 0;
  overflow: hidden;
}

.modal-header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid var(--gray-200);
  background: var(--white);
}

.eyebrow {
  margin: 0 0 2px;
  color: var(--blue);
  font-size: 11px;
  line-height: 14px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.modal-title,
.empty-title {
  margin: 0;
  color: var(--gray-950);
  font-size: 18px;
  line-height: 24px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.icon-button {
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin: 0;
  padding: 0;
  color: var(--gray-500);
  background: transparent;
  border: 0;
  border-radius: 6px;
  transition: color 160ms ease, background 160ms ease;
}

.icon-button:hover {
  color: var(--gray-950);
  background: var(--gray-100);
}

.icon,
.select-chevron {
  width: 18px;
  height: 18px;
  flex: none;
}

.icon-small {
  width: 15px;
  height: 15px;
  flex: none;
}

.booking-form {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0;
  gap: 0;
}

.booking-form-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 14px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.booking-form-body::-webkit-scrollbar {
  width: 6px;
}

.booking-form-body::-webkit-scrollbar-track {
  background: #f1f5f9;
}

.booking-form-body::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

.booking-form-body::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.field-label,
.recurring-label {
  color: var(--gray-700);
  font-size: 12.5px;
  line-height: 16px;
  font-weight: 600;
}

.text-control,
.textarea-control,
.room-select,
.input-with-icon {
  width: 100%;
  box-sizing: border-box;
  color: var(--gray-950);
  background: var(--white);
  border: 1px solid var(--gray-300);
  border-radius: 7px;
  outline: none;
  transition: border-color 160ms ease, box-shadow 160ms ease;
}

.text-control {
  height: 38px;
  padding: 0 11px;
  font-size: 13px;
}

.textarea-control {
  min-height: 52px;
  height: 52px;
  padding: 7px 11px;
  line-height: 18px;
  font-size: 12.5px;
  resize: vertical;
}

.text-control::placeholder,
.textarea-control::placeholder {
  color: var(--gray-400);
}

.text-control:focus,
.textarea-control:focus,
.room-select:focus,
.room-select.is-open,
.input-with-icon:focus-within {
  border-color: var(--blue);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.room-field {
  position: relative;
}

.room-select {
  min-height: 46px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.room-select-main {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.room-name {
  display: block;
  color: var(--gray-950);
  font-size: 13.5px;
  line-height: 18px;
  font-weight: 600;
}

.room-meta {
  display: flex;
  align-items: center;
  gap: 5px;
  color: var(--gray-500);
  font-size: 12px;
  line-height: 17px;
  font-weight: 400;
}

.meta-divider {
  width: 3px;
  height: 3px;
  margin: 0 2px;
  background: var(--gray-300);
  border-radius: 99px;
}

.status-available {
  color: var(--green);
  font-weight: 500;
}

.status-busy {
  color: var(--amber);
  font-weight: 500;
}

.select-chevron {
  color: var(--gray-500);
  transition: transform 160ms ease;
}

.room-select.is-open .select-chevron {
  transform: rotate(180deg);
}

.room-menu {
  position: absolute;
  z-index: 5;
  top: calc(100% + 7px);
  left: 0;
  right: 0;
  max-height: 280px;
  overflow-y: auto;
  overscroll-behavior: contain;
  display: grid;
  gap: 6px;
  padding: 8px;
  background: var(--white);
  border: 1px solid var(--gray-200);
  border-radius: 10px;
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.13);
}

.room-option {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 42px;
  padding: 9px 11px;
  text-align: left;
  background: var(--white);
  border: 1px solid var(--gray-200);
  border-radius: 8px;
}

.room-option:hover,
.room-option.selected {
  background: var(--blue-soft);
  border-color: var(--blue);
}

.room-option>.icon-small {
  color: var(--blue);
}

.time-fieldset {
  min-width: 0;
  margin: 0;
  padding: 0;
  border: 0;
}

.time-fieldset>.field-label {
  margin-bottom: 8px;
}

.time-grid {
  display: grid;
  grid-template-columns: 1.18fr 1fr 1fr;
  gap: 10px;
}

.date-column,
.time-column {
  min-width: 0;
}

.mini-label {
  display: block;
  margin-bottom: 6px;
  color: var(--gray-500);
  font-size: 11px;
  line-height: 16px;
  font-weight: 500;
}

.input-with-icon {
  height: 42px;
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 0 10px;
  color: var(--gray-500);
}

.input-with-icon .icon {
  width: 17px;
  height: 17px;
}

.input-with-icon input {
  min-width: 0;
  width: 100%;
  padding: 0;
  color: var(--gray-700);
  background: transparent;
  border: 0;
  outline: 0;
  font-size: 12px;
  font-weight: 500;
}

.input-with-icon input::-webkit-calendar-picker-indicator {
  display: none;
}

.availability-button {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  margin-top: 10px;
  padding: 0;
  color: var(--blue);
  background: transparent;
  border: 0;
  font-size: 13px;
  line-height: 20px;
  font-weight: 600;
}

.availability-button:hover {
  color: var(--blue-dark);
}

.availability-button .icon {
  width: 17px;
  height: 17px;
}

.availability-button:disabled {
  cursor: wait;
  opacity: 0.65;
}

.availability-message {
  margin: 6px 0 0;
  color: var(--green);
  font-size: 12px;
  line-height: 18px;
}

.availability-message.is-error {
  color: #b91c1c;
}

.availability-results {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 7px;
}

.time-suggestion {
  min-height: 32px;
  padding: 5px 9px;
  color: var(--blue-dark);
  background: var(--blue-soft);
  border: 1px solid #bfdbfe;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}

.time-suggestion:hover,
.time-suggestion.selected {
  color: var(--white);
  background: var(--blue);
  border-color: var(--blue);
}

.recurring-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 13px 14px;
  background: #f9fafb;
  border: 1px solid var(--gray-200);
  border-radius: 9px;
}

.recurring-label {
  display: block;
  color: var(--gray-950);
  cursor: pointer;
}

.recurring-hint {
  margin: 2px 0 0;
  color: var(--gray-500);
  font-size: 12px;
  line-height: 17px;
}

.recurrence-select {
  width: min(220px, 52%);
  height: 40px;
  flex: none;
  padding: 0 10px;
  font-size: 12px;
}

.toggle {
  width: 40px;
  height: 24px;
  position: relative;
  flex: none;
  padding: 2px;
  background: var(--gray-300);
  border: 0;
  border-radius: 99px;
  transition: background 180ms ease;
}

.toggle-thumb {
  width: 20px;
  height: 20px;
  display: block;
  background: var(--white);
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.25);
  transition: transform 180ms ease;
}

.toggle-on {
  background: var(--blue);
}

.toggle-on .toggle-thumb {
  transform: translateX(16px);
}

.label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.optional {
  color: var(--gray-400);
  font-size: 11px;
  line-height: 16px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 20px;
  border-top: 1px solid var(--gray-100);
}

.button {
  min-height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 0 17px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 20px;
  font-weight: 600;
  transition: background 160ms ease, border-color 160ms ease, box-shadow 160ms ease, transform 120ms ease;
}

.button:active {
  transform: translateY(1px);
}

.button-primary {
  color: var(--white);
  background: var(--blue);
  border: 1px solid var(--blue);
  box-shadow: 0 1px 2px rgba(37, 99, 235, 0.18);
}

.button-primary:hover {
  background: var(--blue-dark);
  border-color: var(--blue-dark);
}

.button-secondary {
  color: var(--gray-700);
  background: var(--white);
  border: 1px solid var(--gray-300);
}

.button-secondary:hover {
  background: var(--gray-100);
  border-color: var(--gray-400);
}

.empty-state {
  width: 420px;
  max-width: 100%;
  padding: 40px;
  text-align: center;
  background: var(--white);
  border: 1px solid var(--gray-200);
  border-radius: 12px;
  box-shadow: 0 18px 50px rgba(15, 23, 42, 0.09);
}

.empty-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
  color: var(--blue);
  background: var(--blue-soft);
  border-radius: 12px;
}

.empty-icon .icon {
  width: 24px;
  height: 24px;
}

.empty-copy {
  margin: 8px 0 22px;
  color: var(--gray-500);
  font-size: 14px;
  line-height: 22px;
}

@media (max-width: 620px) {
  .page-shell {
    align-items: flex-start;
    padding: 14px;
  }

  .modal-card {
    padding: 20px;
  }

  .time-grid {
    grid-template-columns: 1fr 1fr;
  }

  .recurring-row {
    align-items: flex-start;
    gap: 12px;
  }

  .recurrence-select {
    width: 48%;
  }

  .date-column {
    grid-column: 1 / -1;
  }
}

@media (max-width: 420px) {
  .modal-card {
    padding: 18px;
  }

  .modal-footer {
    display: grid;
    grid-template-columns: 1fr 1.45fr;
  }

  .button {
    padding: 0 10px;
  }
}

@media (prefers-reduced-motion: reduce) {

  .icon-button,
  .text-control,
  .textarea-control,
  .room-select,
  .select-chevron,
  .toggle,
  .toggle-thumb,
  .button {
    transition: none;
  }
}

/* ============================================================
   DATE PICKER WRAPPER – nút chọn ngày kiểu badge đẹp
   ============================================================ */
.date-picker-wrapper {
  position: relative;
  height: 42px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 11px;
  background: var(--white);
  border: 1px solid var(--gray-300);
  border-radius: 7px;
  cursor: pointer;
  transition: border-color 160ms ease, box-shadow 160ms ease;
  user-select: none;
  box-sizing: border-box;
  width: 100%;
  color: var(--gray-500);
}

.date-picker-wrapper:hover {
  border-color: var(--blue);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.08);
}

.date-display-text {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--gray-700);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ============================================================
   TIME SELECT WRAPPER – dropdown giờ tiếng Việt
   ============================================================ */
.time-select-wrapper {
  position: relative;
  height: 42px;
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 0 10px;
  background: var(--white);
  border: 1px solid var(--gray-300);
  border-radius: 7px;
  box-sizing: border-box;
  width: 100%;
  color: var(--gray-500);
  transition: border-color 160ms ease, box-shadow 160ms ease;
}

.time-select-wrapper:focus-within {
  border-color: var(--blue);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.vi-time-select {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  color: var(--gray-700);
  font-size: 12px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  appearance: none;
  -webkit-appearance: none;
  padding: 0;
}

/* ============================================================
   EQUIPMENT BORROW SECTION – danh sách thiết bị mượn thêm
   ============================================================ */
.equipment-borrow-section {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 10px 12px 12px;
}

.equipment-section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 10px;
  gap: 8px;
}

.equipment-section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
}

.equipment-icon {
  font-size: 15px;
}

.equipment-badge {
  display: inline-block;
  background: #e0f2fe;
  color: #0369a1;
  font-size: 10px;
  font-weight: 600;
  padding: 1px 7px;
  border-radius: 999px;
  letter-spacing: 0.03em;
}

.equipment-hint {
  font-size: 11px;
  color: #64748b;
  text-align: right;
  flex-shrink: 0;
}

.equipment-list-container {
  display: flex;
  flex-direction: column;
  gap: 7px;
  max-height: 180px;
  overflow-y: auto;
  padding-right: 2px;
}

.equipment-list-container::-webkit-scrollbar {
  width: 5px;
}

.equipment-list-container::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 3px;
}

.equipment-list-container::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

.eq-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 9px 12px;
  transition: border-color 150ms ease, box-shadow 150ms ease;
}

.eq-card:hover {
  border-color: #93c5fd;
  box-shadow: 0 1px 4px rgba(37, 99, 235, 0.08);
}

.eq-label {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  flex: 1;
  min-width: 0;
}

.eq-label input[type="checkbox"] {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  accent-color: var(--blue);
  cursor: pointer;
}

.eq-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.eq-name {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.eq-stock {
  font-size: 11px;
  color: #64748b;
}

.eq-qty-group {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-shrink: 0;
}

.eq-qty-label {
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
}

.eq-qty-input {
  width: 52px;
  text-align: center;
  font-size: 13px;
  font-weight: 600;
  border: 1.5px solid #cbd5e1;
  border-radius: 6px;
  padding: 4px 0;
  background: #f1f5f9;
  color: #94a3b8;
  font-family: inherit;
  outline: none;
  transition: border-color 150ms, background 150ms, color 150ms;
}

.eq-qty-input:enabled {
  background: #ffffff;
  color: #0f172a;
  border-color: #93c5fd;
}

.eq-qty-input:enabled:focus {
  border-color: var(--blue);
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.12);
}

.equipment-empty {
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
  padding: 16px 0;
}

.equipment-loading {
  text-align: center;
  color: #94a3b8;
  font-size: 13px;
  padding: 14px 0;
}
````

## File: scripts/seed.py
````python
"""Create repeatable demo data for local feature testing."""

from datetime import datetime, time, timedelta
import json
from pathlib import Path
import os
import secrets
import sys

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from app.core.database import SessionLocal  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.equipment import Equipment, MeetingEquipment, RoomEquipment  # noqa: E402
from app.models.meeting import Meeting, MeetingParticipant  # noqa: E402
from app.models.notification import Notification  # noqa: E402
from app.models.room import Room  # noqa: E402
from app.models.user import User  # noqa: E402
import app.models  # noqa: E402,F401


DEMO_USERS = (
    ("demo.admin", "demo.admin@example.test", "Demo Admin", "admin", True),
    ("demo.alex", "demo.alex@example.test", "Alex Nguyen", "employee", True),
    ("demo.linh", "demo.linh@example.test", "Linh Tran", "employee", True),
    ("demo.inactive", "demo.inactive@example.test", "Inactive User", "employee", False),
    ("demo.manager", "demo.manager@example.test", "Quản lý Bùi Văn Nam", "manager", True),
    ("demo.tester1", "demo.tester1@example.test", "Tester Nguyễn Thu Hoa", "employee", True),
    ("demo.tester2", "demo.tester2@example.test", "Tester Trần Văn Bình", "employee", True),
)


DEMO_ROOMS = (
    {
        "name": "DEMO - Huddle Room",
        "location": "Tầng 2 - Tòa A",
        "capacity": 4,
        "description": "Phòng nhỏ dành cho nhóm dự án.",
        "amenities": ["Màn hình", "Bảng trắng"],
        "is_active": True,
    },
    {
        "name": "DEMO - Lotus Room",
        "location": "Tầng 3 - Tòa A",
        "capacity": 8,
        "description": "Phòng họp tiêu chuẩn.",
        "amenities": ["Máy chiếu", "Hội nghị trực tuyến"],
        "is_active": True,
    },
    {
        "name": "DEMO - Skyline Room",
        "location": "Tầng 8 - Tòa B",
        "capacity": 20,
        "description": "Phòng lớn cho buổi trình bày.",
        "amenities": ["Màn hình lớn", "Micro", "Bảng trắng"],
        "is_active": True,
    },
    {
        "name": "DEMO - Maintenance Room",
        "location": "Tầng 1 - Tòa B",
        "capacity": 6,
        "description": "Phòng mẫu đang bảo trì.",
        "amenities": [],
        "is_active": False,
    },
    {
        "name": "DEMO - Aurora Room",
        "location": "Tầng 2 - Tòa B",
        "capacity": 4,
        "description": "Phòng trao đổi nhanh cho nhóm nhỏ.",
        "amenities": ["Màn hình", "Bảng trắng"],
        "is_active": True,
    },
    {
        "name": "DEMO - Cedar Room",
        "location": "Tầng 4 - Tòa A",
        "capacity": 6,
        "description": "Phòng họp nhóm với thiết bị trình chiếu.",
        "amenities": ["Máy chiếu", "Bảng trắng"],
        "is_active": True,
    },
    {
        "name": "DEMO - River Room",
        "location": "Tầng 5 - Tòa B",
        "capacity": 10,
        "description": "Phòng họp nhóm liên phòng ban.",
        "amenities": ["Màn hình lớn", "Hội nghị trực tuyến"],
        "is_active": True,
    },
    {
        "name": "DEMO - Orion Room",
        "location": "Tầng 6 - Tòa A",
        "capacity": 14,
        "description": "Phòng họp rộng cho buổi lập kế hoạch.",
        "amenities": ["Máy chiếu", "Micro", "Bảng trắng"],
        "is_active": True,
    },
    {
        "name": "DEMO - Summit Room",
        "location": "Tầng 9 - Tòa B",
        "capacity": 30,
        "description": "Phòng hội thảo cho nhóm đông người.",
        "amenities": ["Màn hình lớn", "Micro", "Hội nghị trực tuyến"],
        "is_active": True,
    },
)

DEMO_EQUIPMENT = (
    ("DEMO-PROJECTOR", "Máy chiếu demo", "Presentation", 3, True),
    ("DEMO-MIC", "Micro hội nghị demo", "Audio", 8, True),
    ("DEMO-LAPTOP", "Laptop demo", "Computer", 5, True),
    ("DEMO-WEBCAM", "Webcam demo", "Video", 10, True),
    ("DEMO-WHITEBOARD", "Bảng di động demo", "Office", 2, True),
    ("DEMO-RETIRED", "Thiết bị ngừng hoạt động demo", "Office", 1, False),
)


def _get_or_create_user(db, username, email, full_name, role, is_active, password):
    user = db.query(User).filter(User.username == username).first()
    if user:
        return user, False

    user = User(
        username=username,
        email=email,
        full_name=full_name,
        hashed_password=hash_password(password),
        role=role,
        is_active=is_active,
    )
    db.add(user)
    db.flush()
    return user, True


def _get_or_create_meeting(db, title, room, organizer, start_time, end_time, **values):
    meeting = db.query(Meeting).filter(Meeting.title == title).first()
    if meeting:
        return meeting, False

    meeting = Meeting(
        title=title,
        room_id=room.id,
        organizer_id=organizer.id,
        start_time=start_time,
        end_time=end_time,
        **values,
    )
    db.add(meeting)
    db.flush()
    return meeting, True


def _add_participant(db, meeting, user):
    exists = (
        db.query(MeetingParticipant)
        .filter_by(meeting_id=meeting.id, user_id=user.id)
        .first()
    )
    if not exists:
        db.add(MeetingParticipant(meeting_id=meeting.id, user_id=user.id))


def _add_equipment(db, meeting, equipment, quantity, note):
    exists = (
        db.query(MeetingEquipment)
        .filter_by(meeting_id=meeting.id, equipment_id=equipment.id)
        .first()
    )
    if not exists:
        db.add(
            MeetingEquipment(
                meeting_id=meeting.id,
                equipment_id=equipment.id,
                quantity=quantity,
                note=note,
            )
        )


def _add_notification(db, user, title, content, is_read=False):
    exists = (
        db.query(Notification.id)
        .filter_by(user_id=user.id, title=title, content=content)
        .first()
    )
    if not exists:
        db.add(
            Notification(
                user_id=user.id,
                title=title,
                content=content,
                is_read=is_read,
            )
        )
    if not exists:
        db.add(
            Notification(
                user_id=user.id,
                title=title,
                content=content,
                is_read=is_read,
            )
        )


def seed() -> None:
    db = SessionLocal()
    created = {"users": 0, "rooms": 0, "equipment": 0, "meetings": 0}
    configured_admin_password = os.getenv("SEED_ADMIN_PASSWORD")
    configured_demo_password = (
        os.getenv("SEED_DEMO_PASSWORD") or configured_admin_password
    )
    generated_admin_password = configured_admin_password is None
    generated_demo_password = configured_demo_password is None
    admin_password = configured_admin_password or secrets.token_urlsafe(16)
    demo_password = configured_demo_password or secrets.token_urlsafe(16)
    demo_users_created = 0

    try:
        _, admin_created = _get_or_create_user(
            db,
            "admin",
            "admin@meeting.local",
            "Quản trị viên",
            "admin",
            True,
            admin_password,
        )
        if admin_created:
            created["users"] += 1

        users = {}
        for username, email, full_name, role, is_active in DEMO_USERS:
            user, was_created = _get_or_create_user(
                db, username, email, full_name, role, is_active, demo_password
            )
            users[username] = user
            created["users"] += int(was_created)
            demo_users_created += int(was_created)

        rooms = {}
        for room_data in DEMO_ROOMS:
            room = db.query(Room).filter(Room.name == room_data["name"]).first()
            if room is None:
                room = Room(
                    **{
                        **room_data,
                        "amenities": json.dumps(room_data["amenities"], ensure_ascii=False),
                    }
                )
                db.add(room)
                db.flush()
                created["rooms"] += 1
            rooms[room_data["name"]] = room

        equipment_by_code = {}
        for code, name, category, total_qty, is_active in DEMO_EQUIPMENT:
            equipment = db.query(Equipment).filter(Equipment.code == code).first()
            if equipment is None:
                equipment = Equipment(
                    code=code,
                    name=name,
                    category=category,
                    total_qty=total_qty,
                    description="Dữ liệu mẫu để kiểm thử quản lý và tồn kho thiết bị.",
                    is_active=is_active,
                )
                db.add(equipment)
                db.flush()
                created["equipment"] += 1
            equipment_by_code[code] = equipment

        room_equipment = {
            "DEMO - Huddle Room": {"DEMO-WHITEBOARD": 1, "DEMO-WEBCAM": 1},
            "DEMO - Lotus Room": {"DEMO-PROJECTOR": 1, "DEMO-MIC": 2},
            "DEMO - Skyline Room": {"DEMO-PROJECTOR": 1, "DEMO-MIC": 4},
        }
        for room_name, defaults in room_equipment.items():
            for code, quantity in defaults.items():
                equipment = equipment_by_code[code]
                exists = (
                    db.query(RoomEquipment)
                    .filter_by(room_id=rooms[room_name].id, equipment_id=equipment.id)
                    .first()
                )
                if not exists:
                    db.add(
                        RoomEquipment(
                            room_id=rooms[room_name].id,
                            equipment_id=equipment.id,
                            quantity=quantity,
                        )
                    )

        today = datetime.now().date()
        past_start = datetime.combine(today - timedelta(days=2), time(10, 0))
        future_start = datetime.combine(today + timedelta(days=1), time(9, 0))
        recurring_start = datetime.combine(today + timedelta(days=2), time(13, 0))

        past_meeting, was_created = _get_or_create_meeting(
            db,
            "[DEMO] Project review - completed",
            rooms["DEMO - Huddle Room"],
            users["demo.alex"],
            past_start,
            past_start + timedelta(hours=1),
            description="Lịch mẫu đã kết thúc để kiểm thử lịch sử cuộc họp.",
            status="completed",
        )
        created["meetings"] += int(was_created)
        _add_participant(db, past_meeting, users["demo.linh"])

        upcoming, was_created = _get_or_create_meeting(
            db,
            "[DEMO] Product planning",
            rooms["DEMO - Lotus Room"],
            users["demo.alex"],
            future_start,
            future_start + timedelta(hours=1),
            description="Lịch sắp tới có người tham dự và mượn thiết bị.",
            status="scheduled",
        )
        created["meetings"] += int(was_created)
        _add_participant(db, upcoming, users["demo.linh"])
        _add_participant(db, upcoming, users["demo.admin"])
        _add_equipment(
            db, upcoming, equipment_by_code["DEMO-PROJECTOR"], 1, "Trình chiếu kế hoạch"
        )
        _add_equipment(
            db, upcoming, equipment_by_code["DEMO-MIC"], 2, "Micro cho người tham dự"
        )

        for occurrence in range(1, 4):
            occurrence_start = recurring_start + timedelta(weeks=occurrence - 1)
            meeting, was_created = _get_or_create_meeting(
                db,
                f"[DEMO] Weekly planning {occurrence}/3",
                rooms["DEMO - Skyline Room"],
                users["demo.admin"],
                occurrence_start,
                occurrence_start + timedelta(minutes=45),
                description="Một buổi trong chuỗi họp định kỳ hàng tuần.",
                is_recurring=True,
                recurring_type="weekly",
                status="scheduled",
            )
            created["meetings"] += int(was_created)
            _add_participant(db, meeting, users["demo.alex"])
            _add_participant(db, meeting, users["demo.linh"])

        canceled_start = datetime.combine(today + timedelta(days=1), time(14, 0))
        canceled, was_created = _get_or_create_meeting(
            db,
            "[DEMO] Canceled meeting",
            rooms["DEMO - Huddle Room"],
            users["demo.linh"],
            canceled_start,
            canceled_start + timedelta(hours=1),
            description="Lịch mẫu đã hủy; phòng được xem là trống ở khung giờ này.",
            status="CANCELLED",
        )
        created["meetings"] += int(was_created)
        _add_participant(db, canceled, users["demo.alex"])

        _add_notification(
            db,
            users["demo.linh"],
            "Lời mời họp: Product planning",
            "Alex Nguyen đã mời bạn tham gia cuộc họp Product planning.",
            False,
        )
        _add_notification(
            db,
            users["demo.alex"],
            "Đặt phòng thành công",
            "Cuộc họp Product planning đã được lưu cùng các thiết bị yêu cầu.",
            True,
        )

        db.commit()
        print("Demo data ready:", ", ".join(f"{key}={value}" for key, value in created.items()))
        print("Login users: admin, demo.admin, demo.alex, demo.linh")
        if admin_created and generated_admin_password:
            print(f"One-time admin password: {admin_password}")
        if demo_users_created and generated_demo_password:
            print(f"One-time demo password: {demo_password}")
        else:
            print("Demo password: SEED_DEMO_PASSWORD or SEED_ADMIN_PASSWORD from .env")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
````

## File: frontend/index.html
````html
<!DOCTYPE html>
<html lang="vi">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Đăng nhập - RoomSync</title>
    <!-- Nhúng Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="css/style.css?v=10">
    <link rel="stylesheet" href="css/booking.css">
    <style>
        /* CSS tuỳ chỉnh hiệu ứng Focus đúng theo Style Figma */
        .custom-input:focus {
            border-color: #004CFF !important;
            box-shadow: 0 0 0 3px rgba(0, 76, 255, 0.08) !important;
        }
    </style>
</head>

<body class="bg-gray-50 lg:bg-white text-gray-900 antialiased font-sans min-h-screen">

    <div
        class="min-h-screen w-full flex flex-col items-center justify-center lg:flex-row lg:items-stretch lg:justify-start">

        <!-- KHUNG CHỨA FORM -->
        <div
            class="w-full flex-1 flex flex-col items-center justify-center px-5 py-12 lg:p-0 lg:w-[480px] lg:flex-none lg:border-r lg:border-gray-100 lg:bg-white">

            <!-- THẺ FORM ĐĂNG NHẬP -->
            <div
                class="w-full max-w-[390px] bg-white rounded-2xl px-8 py-10 shadow-[0_4px_24px_rgba(0,0,0,0.07)] lg:max-w-[360px] lg:rounded-none lg:shadow-none lg:p-0">

                <!-- LogoMark Component -->
                <div class="flex items-center gap-2.5 mb-8">
                    <div class="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
                        style="background-color: #004CFF;">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                            <rect x="3" y="4" width="18" height="16" rx="2" stroke="white" stroke-width="2" />
                            <path d="M8 2v4M16 2v4M3 10h18" stroke="white" stroke-width="2" stroke-linecap="round" />
                            <circle cx="8.5" cy="15" r="1.5" fill="white" />
                            <circle cx="12" cy="15" r="1.5" fill="white" />
                            <circle cx="15.5" cy="15" r="1.5" fill="white" />
                        </svg>
                    </div>
                    <span class="text-[15px] font-semibold text-gray-900 tracking-tight">RoomSync</span>
                </div>

                <!-- Tiêu đề -->
                <div class="mb-8">
                    <h1 class="text-[26px] leading-tight text-gray-900 tracking-tight font-bold">
                        Đăng nhập vào tài khoản
                    </h1>
                    <p class="mt-1.5 text-sm text-gray-500">
                        Chào mừng trở lại. Nhập thông tin đăng nhập để tiếp tục.
                    </p>
                </div>

                <!-- LoginForm Component -->
                <form id="loginForm" class="w-full">

                    <!-- Input Email / Username -->
                    <div class="mb-6">
                        <label for="username" class="block text-sm font-medium text-gray-700 mb-1.5">
                            Email công ty
                        </label>
                        <div class="relative">
                            <span
                                class="absolute inset-y-0 left-3.5 flex items-center text-gray-400 pointer-events-none">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                                    stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <path
                                        d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                                    <polyline points="22,6 12,13 2,6" />
                                </svg>
                            </span>
                            <input type="text" id="username" name="username" placeholder="ten@congty.com" required
                                class="custom-input w-full pl-10 pr-4 py-2.5 rounded-lg border border-gray-200 text-sm text-gray-900 placeholder-gray-400 bg-white transition-colors outline-none" />
                        </div>
                    </div>

                    <!-- Input Password -->
                    <div class="mb-6">
                        <label for="password" class="block text-sm font-medium text-gray-700 mb-1.5">
                            Mật khẩu
                        </label>
                        <div class="relative">
                            <span
                                class="absolute inset-y-0 left-3.5 flex items-center text-gray-400 pointer-events-none">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                                    stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                                    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                                </svg>
                            </span>
                            <input type="password" id="password" name="password" placeholder="••••••••" required
                                class="custom-input w-full pl-10 pr-11 py-2.5 rounded-lg border border-gray-200 text-sm text-gray-900 placeholder-gray-400 bg-white transition-colors outline-none" />
                            <button type="button" id="togglePassword"
                                class="absolute inset-y-0 right-3.5 flex items-center text-gray-400 hover:text-gray-600 transition-colors"
                                aria-label="Hiện mật khẩu">
                                <svg id="eyeIcon" width="18" height="18" viewBox="0 0 24 24" fill="none"
                                    stroke="currentColor" stroke-width="2" stroke-linecap="round"
                                    stroke-linejoin="round">
                                    <path
                                        d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
                                    <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
                                    <line x1="1" y1="1" x2="23" y2="23" />
                                </svg>
                            </button>
                        </div>
                    </div>

                    <!-- Ghi nhớ đăng nhập + Quên mật khẩu -->
                    <div class="flex items-center justify-between mb-6">
                        <label class="flex items-center gap-2 cursor-pointer select-none">
                            <div class="relative">
                                <input type="checkbox" id="rememberMe" class="sr-only" />
                                <div id="checkboxBox"
                                    class="w-4 h-4 rounded border flex items-center justify-center transition-colors border-gray-300 bg-white">
                                    <svg id="checkIcon" class="hidden" width="10" height="10" viewBox="0 0 10 10"
                                        fill="none">
                                        <path d="M2 5l2.5 2.5L8 3" stroke="white" stroke-width="1.5"
                                            stroke-linecap="round" stroke-linejoin="round" />
                                    </svg>
                                </div>
                            </div>
                            <span class="text-sm text-gray-600">Ghi nhớ đăng nhập</span>
                        </label>
                        <a href="#" class="text-sm font-medium transition-colors text-[#004CFF] hover:text-[#0038CC]">
                            Quên mật khẩu?
                        </a>
                    </div>

                    <!-- Khung hiển thị thông báo lỗi khi đăng nhập thất bại -->
                    <div id="errorAlert"
                        class="hidden mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm text-center">
                        Tài khoản hoặc mật khẩu không chính xác!
                    </div>

                    <!-- Nút Đăng nhập -->
                    <button type="submit"
                        class="w-full py-3 rounded-lg text-sm font-semibold text-white transition-all bg-[#004CFF] hover:bg-[#0038CC] focus:outline-none focus:ring-4 focus:ring-[#004CFF]/25">
                        Đăng Nhập
                    </button>

                    <div class="my-5 flex items-center gap-3 text-xs text-gray-400" aria-hidden="true">
                        <span class="h-px flex-1 bg-gray-200"></span>
                        <span>hoặc</span>
                        <span class="h-px flex-1 bg-gray-200"></span>
                    </div>

                    <button type="button" id="googleLoginButton"
                        class="w-full flex items-center justify-center gap-3 py-3 rounded-lg border border-gray-200 bg-white text-sm font-semibold text-gray-700 transition-colors hover:bg-gray-50 focus:outline-none focus:ring-4 focus:ring-blue-100">
                        <span class="text-lg font-bold text-[#4285F4]" aria-hidden="true">G</span>
                        Đăng nhập với Google
                    </button>

                    <p class="mt-6 text-xs text-center text-gray-400">
                        Chưa có tài khoản?
                        <a href="#" class="font-medium transition-colors text-[#004CFF] hover:text-[#0038CC]">
                            Liên hệ quản trị viên
                        </a>
                    </p>
                </form>

            </div>

            <!-- Dòng Copyright chuẩn giao diện Mobile Figma -->
            <p class="mt-6 text-center text-xs text-gray-400 lg:hidden">
                © 2026 RoomSync Inc. Bảo lưu mọi quyền.
            </p>

        </div>

        <!-- CỘT BÊN PHẢI: BANNER DESKTOP -->
        <div class="hidden lg:flex flex-1 relative overflow-hidden" style="background-color: #001A66;">
            <img src="https://images.unsplash.com/photo-1740933084056-078fac872bff?w=1200&h=900&fit=crop&auto=format"
                alt="Phòng họp doanh nghiệp hiện đại với bàn và ghế lớn"
                class="absolute inset-0 w-full h-full object-cover" style="opacity: 0.45;" />

            <div class="absolute inset-0"
                style="background: linear-gradient(135deg, rgba(0,76,255,0.35) 0%, rgba(0,10,60,0.7) 100%);"></div>

            <div class="absolute inset-0 flex flex-col justify-end p-14">
                <div class="flex flex-wrap gap-3 mb-10">
                    <span class="px-3 py-1.5 rounded-full text-xs font-medium text-white/80 border border-white/20"
                        style="background-color: rgba(255,255,255,0.08);">Đặt phòng họp</span>
                    <span class="px-3 py-1.5 rounded-full text-xs font-medium text-white/80 border border-white/20"
                        style="background-color: rgba(255,255,255,0.08);">Đồng bộ lịch</span>
                    <span class="px-3 py-1.5 rounded-full text-xs font-medium text-white/80 border border-white/20"
                        style="background-color: rgba(255,255,255,0.08);">Phân tích dữ liệu</span>
                    <span class="px-3 py-1.5 rounded-full text-xs font-medium text-white/80 border border-white/20"
                        style="background-color: rgba(255,255,255,0.08);">Hỗ trợ SSO</span>
                </div>

                <h2 class="text-3xl font-semibold text-white leading-snug mb-3 max-w-md">
                    Đặt đúng phòng họp,<br />mọi lúc bạn cần.
                </h2>
                <p class="text-sm text-white/60 max-w-sm leading-relaxed">
                    RoomSync giúp đội nhóm của bạn nắm rõ tình trạng toàn bộ phòng họp — đặt lịch, quản lý và tối ưu hoá
                    tại một nơi duy nhất.
                </p>

                <div class="flex gap-8 mt-8 pt-8 border-t border-white/10">
                    <div>
                        <div class="text-lg font-semibold text-white">2.400+</div>
                        <div class="text-xs text-white/50 mt-0.5">Phòng được quản lý</div>
                    </div>
                    <div>
                        <div class="text-lg font-semibold text-white">98,5%</div>
                        <div class="text-xs text-white/50 mt-0.5">Độ chính xác đặt phòng</div>
                    </div>
                    <div>
                        <div class="text-lg font-semibold text-white">340+</div>
                        <div class="text-xs text-white/50 mt-0.5">Khách hàng doanh nghiệp</div>
                    </div>
                </div>
            </div>
        </div>

    </div>

    <!-- Script xử lý UI (Giữ nguyên) -->
    <script>
        // 1. Tương tác Ẩn / Hiện Mật Khẩu
        const togglePasswordBtn = document.getElementById('togglePassword');
        const passwordInput = document.getElementById('password');
        const eyeIcon = document.getElementById('eyeIcon');

        const eyeOpenSVG = `<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle cx="12" cy="12" r="3" />`;
        const eyeClosedSVG = `<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" /><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" /><line x1="1" y1="1" x2="23" y2="23" />`;

        let isPasswordOpen = false;

        if (togglePasswordBtn && passwordInput) {
            togglePasswordBtn.addEventListener('click', () => {
                isPasswordOpen = !isPasswordOpen;
                passwordInput.type = isPasswordOpen ? 'text' : 'password';
                eyeIcon.innerHTML = isPasswordOpen ? eyeOpenSVG : eyeClosedSVG;
                togglePasswordBtn.setAttribute('aria-label', isPasswordOpen ? 'Ẩn mật khẩu' : 'Hiện mật khẩu');
            });
        }

        // 2. Tương tác Checkbox "Ghi nhớ đăng nhập"
        const rememberCheckbox = document.getElementById('rememberMe');
        const checkboxBox = document.getElementById('checkboxBox');
        const checkIcon = document.getElementById('checkIcon');

        if (rememberCheckbox) {
            rememberCheckbox.addEventListener('change', (e) => {
                if (e.target.checked) {
                    checkboxBox.style.backgroundColor = '#004CFF';
                    checkboxBox.style.borderColor = '#004CFF';
                    checkIcon.classList.remove('hidden');
                } else {
                    checkboxBox.style.backgroundColor = '#FFFFFF';
                    checkboxBox.style.borderColor = '#D1D5DB';
                    checkIcon.classList.add('hidden');
                }
            });
        }
    </script>

    <!-- Kết nối file JS xử lý gửi API Đăng nhập -->
    <script src="js/login.js?v=3"></script>
    <script src="js/auth.js?v=2"></script>
</body>

</html>
````

## File: frontend/login.html
````html
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Đăng nhập - RoomSync</title>
    <!-- Nhúng Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="css/style.css?v=10">
    <link rel="stylesheet" href="css/booking.css">
    <style>
        /* CSS tuỳ chỉnh hiệu ứng Focus đúng theo Style Figma */
        .custom-input:focus {
            border-color: #004CFF !important;
            box-shadow: 0 0 0 3px rgba(0, 76, 255, 0.08) !important;
        }
    </style>
</head>
<body class="bg-gray-50 lg:bg-white text-gray-900 antialiased font-sans min-h-screen">

    <div class="min-h-screen w-full flex flex-col items-center justify-center lg:flex-row lg:items-stretch lg:justify-start">

        <!-- KHUNG CHỨA FORM -->
        <div class="w-full flex-1 flex flex-col items-center justify-center px-5 py-12 lg:p-0 lg:w-[480px] lg:flex-none lg:border-r lg:border-gray-100 lg:bg-white">

            <!-- THẺ FORM ĐĂNG NHẬP -->
            <div class="w-full max-w-[390px] bg-white rounded-2xl px-8 py-10 shadow-[0_4px_24px_rgba(0,0,0,0.07)] lg:max-w-[360px] lg:rounded-none lg:shadow-none lg:p-0">

                <!-- LogoMark Component -->
                <div class="flex items-center gap-2.5 mb-8">
                    <div class="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0" style="background-color: #004CFF;">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                            <rect x="3" y="4" width="18" height="16" rx="2" stroke="white" stroke-width="2" />
                            <path d="M8 2v4M16 2v4M3 10h18" stroke="white" stroke-width="2" stroke-linecap="round" />
                            <circle cx="8.5" cy="15" r="1.5" fill="white" />
                            <circle cx="12" cy="15" r="1.5" fill="white" />
                            <circle cx="15.5" cy="15" r="1.5" fill="white" />
                        </svg>
                    </div>
                    <span class="text-[15px] font-semibold text-gray-900 tracking-tight">RoomSync</span>
                </div>

                <!-- Tiêu đề -->
                <div class="mb-8">
                    <h1 class="text-[26px] leading-tight text-gray-900 tracking-tight font-bold">
                        Đăng nhập vào tài khoản
                    </h1>
                    <p class="mt-1.5 text-sm text-gray-500">
                        Chào mừng trở lại. Nhập thông tin đăng nhập để tiếp tục.
                    </p>
                </div>

                <!-- LoginForm Component -->
                <form id="loginForm" class="w-full">

                    <!-- Input Email / Username -->
                    <div class="mb-6">
                        <label for="username" class="block text-sm font-medium text-gray-700 mb-1.5">
                            Email công ty
                        </label>
                        <div class="relative">
                            <span class="absolute inset-y-0 left-3.5 flex items-center text-gray-400 pointer-events-none">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
                                    <polyline points="22,6 12,13 2,6" />
                                </svg>
                            </span>
                            <input
                                type="text"
                                id="username"
                                name="username"
                                placeholder="ten@congty.com"
                                required
                                class="custom-input w-full pl-10 pr-4 py-2.5 rounded-lg border border-gray-200 text-sm text-gray-900 placeholder-gray-400 bg-white transition-colors outline-none"
                            />
                        </div>
                    </div>

                    <!-- Input Password -->
                    <div class="mb-6">
                        <label for="password" class="block text-sm font-medium text-gray-700 mb-1.5">
                            Mật khẩu
                        </label>
                        <div class="relative">
                            <span class="absolute inset-y-0 left-3.5 flex items-center text-gray-400 pointer-events-none">
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                                    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                                </svg>
                            </span>
                            <input
                                type="password"
                                id="password"
                                name="password"
                                placeholder="••••••••"
                                required
                                class="custom-input w-full pl-10 pr-11 py-2.5 rounded-lg border border-gray-200 text-sm text-gray-900 placeholder-gray-400 bg-white transition-colors outline-none"
                            />
                            <button
                                type="button"
                                id="togglePassword"
                                class="absolute inset-y-0 right-3.5 flex items-center text-gray-400 hover:text-gray-600 transition-colors"
                                aria-label="Hiện mật khẩu"
                            >
                                <svg id="eyeIcon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" />
                                    <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" />
                                    <line x1="1" y1="1" x2="23" y2="23" />
                                </svg>
                            </button>
                        </div>
                    </div>

                    <!-- Ghi nhớ đăng nhập + Quên mật khẩu -->
                    <div class="flex items-center justify-between mb-6">
                        <label class="flex items-center gap-2 cursor-pointer select-none">
                            <div class="relative">
                                <input type="checkbox" id="rememberMe" class="sr-only" />
                                <div id="checkboxBox" class="w-4 h-4 rounded border flex items-center justify-center transition-colors border-gray-300 bg-white">
                                    <svg id="checkIcon" class="hidden" width="10" height="10" viewBox="0 0 10 10" fill="none">
                                        <path d="M2 5l2.5 2.5L8 3" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
                                    </svg>
                                </div>
                            </div>
                            <span class="text-sm text-gray-600">Ghi nhớ đăng nhập</span>
                        </label>
                        <a
                            href="#"
                            class="text-sm font-medium transition-colors text-[#004CFF] hover:text-[#0038CC]"
                        >
                            Quên mật khẩu?
                        </a>
                    </div>

                    <!-- Khung hiển thị thông báo lỗi khi đăng nhập thất bại -->
                    <div id="errorAlert" class="hidden mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-600 text-sm text-center">
                        Tài khoản hoặc mật khẩu không chính xác!
                    </div>

                    <!-- Nút Đăng nhập -->
                    <button
                        type="submit"
                        class="w-full py-3 rounded-lg text-sm font-semibold text-white transition-all bg-[#004CFF] hover:bg-[#0038CC] focus:outline-none focus:ring-4 focus:ring-[#004CFF]/25"
                    >
                        Đăng Nhập
                    </button>

                    <div class="my-5 flex items-center gap-3 text-xs text-gray-400" aria-hidden="true">
                        <span class="h-px flex-1 bg-gray-200"></span>
                        <span>hoặc</span>
                        <span class="h-px flex-1 bg-gray-200"></span>
                    </div>

                    <button
                        type="button"
                        id="googleLoginButton"
                        class="w-full flex items-center justify-center gap-3 py-3 rounded-lg border border-gray-200 bg-white text-sm font-semibold text-gray-700 transition-colors hover:bg-gray-50 focus:outline-none focus:ring-4 focus:ring-blue-100"
                    >
                        <span class="text-lg font-bold text-[#4285F4]" aria-hidden="true">G</span>
                        Đăng nhập với Google
                    </button>

                    <p class="mt-6 text-xs text-center text-gray-400">
                        Chưa có tài khoản?
                        <a
                            href="#"
                            class="font-medium transition-colors text-[#004CFF] hover:text-[#0038CC]"
                        >
                            Liên hệ quản trị viên
                        </a>
                    </p>
                </form>

            </div>

            <!-- Dòng Copyright chuẩn giao diện Mobile Figma -->
            <p class="mt-6 text-center text-xs text-gray-400 lg:hidden">
                © 2026 RoomSync Inc. Bảo lưu mọi quyền.
            </p>

        </div>

        <!-- CỘT BÊN PHẢI: BANNER DESKTOP -->
        <div class="hidden lg:flex flex-1 relative overflow-hidden" style="background-color: #001A66;">
            <img
                src="https://images.unsplash.com/photo-1740933084056-078fac872bff?w=1200&h=900&fit=crop&auto=format"
                alt="Phòng họp doanh nghiệp hiện đại với bàn và ghế lớn"
                class="absolute inset-0 w-full h-full object-cover"
                style="opacity: 0.45;"
            />

            <div
                class="absolute inset-0"
                style="background: linear-gradient(135deg, rgba(0,76,255,0.35) 0%, rgba(0,10,60,0.7) 100%);"
            ></div>

            <div class="absolute inset-0 flex flex-col justify-end p-14">
                <div class="flex flex-wrap gap-3 mb-10">
                    <span class="px-3 py-1.5 rounded-full text-xs font-medium text-white/80 border border-white/20" style="background-color: rgba(255,255,255,0.08);">Đặt phòng họp</span>
                    <span class="px-3 py-1.5 rounded-full text-xs font-medium text-white/80 border border-white/20" style="background-color: rgba(255,255,255,0.08);">Đồng bộ lịch</span>
                    <span class="px-3 py-1.5 rounded-full text-xs font-medium text-white/80 border border-white/20" style="background-color: rgba(255,255,255,0.08);">Phân tích dữ liệu</span>
                    <span class="px-3 py-1.5 rounded-full text-xs font-medium text-white/80 border border-white/20" style="background-color: rgba(255,255,255,0.08);">Hỗ trợ SSO</span>
                </div>

                <h2 class="text-3xl font-semibold text-white leading-snug mb-3 max-w-md">
                    Đặt đúng phòng họp,<br />mọi lúc bạn cần.
                </h2>
                <p class="text-sm text-white/60 max-w-sm leading-relaxed">
                    RoomSync giúp đội nhóm của bạn nắm rõ tình trạng toàn bộ phòng họp — đặt lịch, quản lý và tối ưu hoá tại một nơi duy nhất.
                </p>

                <div class="flex gap-8 mt-8 pt-8 border-t border-white/10">
                    <div>
                        <div class="text-lg font-semibold text-white">2.400+</div>
                        <div class="text-xs text-white/50 mt-0.5">Phòng được quản lý</div>
                    </div>
                    <div>
                        <div class="text-lg font-semibold text-white">98,5%</div>
                        <div class="text-xs text-white/50 mt-0.5">Độ chính xác đặt phòng</div>
                    </div>
                    <div>
                        <div class="text-lg font-semibold text-white">340+</div>
                        <div class="text-xs text-white/50 mt-0.5">Khách hàng doanh nghiệp</div>
                    </div>
                </div>
            </div>
        </div>

    </div>

    <!-- Script xử lý UI -->
    <script>
        // 1. Tương tác Ẩn / Hiện Mật Khẩu
        const togglePasswordBtn = document.getElementById('togglePassword');
        const passwordInput = document.getElementById('password');
        const eyeIcon = document.getElementById('eyeIcon');

        const eyeOpenSVG = `<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" /><circle cx="12" cy="12" r="3" />`;
        const eyeClosedSVG = `<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94" /><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19" /><line x1="1" y1="1" x2="23" y2="23" />`;

        let isPasswordOpen = false;

        if (togglePasswordBtn && passwordInput) {
            togglePasswordBtn.addEventListener('click', () => {
                isPasswordOpen = !isPasswordOpen;
                passwordInput.type = isPasswordOpen ? 'text' : 'password';
                eyeIcon.innerHTML = isPasswordOpen ? eyeOpenSVG : eyeClosedSVG;
                togglePasswordBtn.setAttribute('aria-label', isPasswordOpen ? 'Ẩn mật khẩu' : 'Hiện mật khẩu');
            });
        }

        // 2. Tương tác Checkbox "Ghi nhớ đăng nhập"
        const rememberCheckbox = document.getElementById('rememberMe');
        const checkboxBox = document.getElementById('checkboxBox');
        const checkIcon = document.getElementById('checkIcon');

        if (rememberCheckbox) {
            rememberCheckbox.addEventListener('change', (e) => {
                if (e.target.checked) {
                    checkboxBox.style.backgroundColor = '#004CFF';
                    checkboxBox.style.borderColor = '#004CFF';
                    checkIcon.classList.remove('hidden');
                } else {
                    checkboxBox.style.backgroundColor = '#FFFFFF';
                    checkboxBox.style.borderColor = '#D1D5DB';
                    checkIcon.classList.add('hidden');
                }
            });
        }
    </script>

    <!-- Kết nối file JS xử lý gửi API Đăng nhập -->
    <script src="js/login.js?v=3"></script>
    <script src="js/auth.js?v=2"></script>
</body>
</html>
````

## File: app/routers/rooms.py
````python
import json
from datetime import datetime
from sqlalchemy import and_, func
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session


from app.core.database import get_db
from app.core.security import get_current_user, require_role
from app.models.room import Room
from app.models.meeting import Meeting
from app.models.user import User
from app.schemas.room import RoomCreate, RoomUpdate, RoomResponse, RoomQRResponse
from app.services import room_service
# Khởi tạo APIRouter (KHÔNG thêm prefix ở đây vì đã có prefix="/api/rooms" ở main.py)
router = APIRouter()


@router.get("/{room_id}/qr-code", response_model=RoomQRResponse, summary="Lấy mã QR phòng họp")
def get_room_qr_code(
    room_id: int,
    meeting_id: Optional[int] = Query(None, description="Cuộc họp do người tổ chức hiện tại chủ trì"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    role = str(current_user.role or "").strip().casefold()
    room = db.query(Room).filter(Room.id == room_id).first()
    if room is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy phòng họp")
    if role not in {"admin", "manager"}:
        if meeting_id is None:
            raise HTTPException(
                status_code=403,
                detail="Chỉ Admin, Manager hoặc chủ trì cuộc họp mới được lấy mã QR phòng.",
            )
        meeting = db.query(Meeting).filter(
            Meeting.id == meeting_id,
            Meeting.room_id == room_id,
            Meeting.organizer_id == current_user.id,
            func.upper(Meeting.status).in_(["SCHEDULED", "IN_PROGRESS"]),
        ).first()
        if meeting is None:
            raise HTTPException(
                status_code=403,
                detail="Bạn không có quyền lấy mã QR cho cuộc họp này.",
            )
    if not room.qr_token:
        room.generate_qr_token()
        db.commit()
        db.refresh(room)
    return RoomQRResponse(room_id=room.id, room_name=room.name, qr_token=room.qr_token)

# GET /api/rooms/: Lấy danh sách tất cả phòng
@router.get("/", response_model=List[RoomResponse], summary="Lấy danh sách tất cả phòng")
def get_all_rooms(db: Session = Depends(get_db)):
    # THÊM FILTER is_active == True
    return db.query(Room).filter(Room.is_active == True).all()


# GET /api/rooms/available: Tìm phòng trống theo khoảng thời gian
@router.get("/available", response_model=List[RoomResponse], summary="Tìm phòng trống")
def get_available_rooms(
    start_time: datetime,
    end_time: datetime,
    db: Session = Depends(get_db)
):
    # 1. Kiểm tra thời gian đầu vào hợp lệ
    if start_time >= end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thời gian kết thúc phải lớn hơn thời gian bắt đầu."
        )

    # 2. Tìm danh sách ID các phòng BỊ TRÙNG LỊCH 
    busy_rooms_query = db.query(Meeting.room_id).filter(
        func.upper(Meeting.status).notin_(
            ["CANCELLED", "CANCELLED_NO_SHOW", "COMPLETED"]
        ),
        Meeting.check_out_time.is_(None),
        and_(
            Meeting.start_time < end_time,
            Meeting.end_time > start_time
        )
    ).subquery()

    # 3. Lấy danh sách phòng ĐANG HOẠT ĐỘNG và KHÔNG BỊ TRÙNG LỊCH
    available_rooms = db.query(Room).filter(
        Room.is_active == True,
        Room.id.notin_(busy_rooms_query)
    ).all()

    return available_rooms


# POST /api/rooms/: Thêm phòng mới (Chỉ Admin)
@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED, summary="Thêm phòng mới (Admin)")
def create_room(
    room_in: RoomCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin"))
):
    # Kiểm tra xem tên phòng đã tồn tại chưa
    existing_room = db.query(Room).filter(Room.name == room_in.name).first()
    if existing_room:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tên phòng họp đã tồn tại!"
        )

    amenities_data = room_in.amenities
    if isinstance(amenities_data, list):
        amenities_json = json.dumps(amenities_data, ensure_ascii=False)
    elif isinstance(amenities_data, str) and amenities_data.strip():
        amenities_json = json.dumps([s.strip() for s in amenities_data.split(',') if s.strip()], ensure_ascii=False)
    else:
        amenities_json = None

    # Tạo phòng mới
    new_room = Room(
        name=room_in.name,
        capacity=room_in.capacity,
        location=room_in.location,
        description=room_in.description,
        amenities=amenities_json,
        is_active=room_in.is_active
    )
    db.add(new_room)
    db.commit()
    db.refresh(new_room)
    return new_room


# PUT /api/rooms/{room_id}: Cập nhật thông tin phòng (Chỉ Admin)
@router.put("/{room_id}", response_model=RoomResponse, status_code=status.HTTP_200_OK, summary="Cập nhật phòng (Admin)")
def update_room(
    room_id: int,
    room_in: RoomUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin"))
):
    # Tìm phòng
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Không tìm thấy phòng họp")

    # Cập nhật các trường có gửi lên
    update_data = room_in.model_dump(exclude_unset=True)
    if "amenities" in update_data:
        val = update_data["amenities"]
        if isinstance(val, list):
            update_data["amenities"] = json.dumps(val, ensure_ascii=False)
        elif isinstance(val, str) and val.strip():
            update_data["amenities"] = json.dumps([s.strip() for s in val.split(',') if s.strip()], ensure_ascii=False)
        else:
            update_data["amenities"] = None

    for key, value in update_data.items():
        setattr(room, key, value)

    db.commit()
    db.refresh(room)
    return room


# DELETE /api/rooms/{room_id}: Xóa (ẩn - soft delete) phòng (Chỉ Admin)
@router.delete("/{room_id}", status_code=status.HTTP_200_OK, summary="Xóa/Ẩn phòng (Admin)")
def delete_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(require_role("admin"))
):
    # Tìm phòng
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Không tìm thấy phòng họp")

    # Soft delete: Cập nhật trạng thái thành False thay vì xóa hẳn khỏi DB
    room.is_active = False
    db.commit()
    return {"status": "success", "message": f"Đã chuyển trạng thái phòng '{room.name}' thành ngưng hoạt động."}  
@router.get("/available/", response_model=List[RoomResponse])
def read_available_rooms(
    start_time: datetime = Query(..., description="Thời gian bắt đầu"),
    end_time: datetime = Query(..., description="Thời gian kết thúc"),
    min_capacity: Optional[int] = Query(0, description="Sức chứa tối thiểu"),
    db: Session = Depends(get_db),
):
    if start_time >= end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thời gian bắt đầu phải nhỏ hơn thời gian kết thúc!",
        )

    rooms = room_service.get_available_rooms(
        db=db,
        start_time=start_time,
        end_time=end_time,
        min_capacity=min_capacity,
    )

    return rooms
````

## File: frontend/js/login.js
````javascript
const API_URL = window.API_URL || 'http://localhost:8000/api';

document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('loginForm');
    const errorAlert = document.getElementById('errorAlert');

    if (!loginForm) return;

    loginForm.addEventListener('submit', async function (e) {
        e.preventDefault();

        if (errorAlert) errorAlert.classList.add('hidden');

        const usernameInput = document.getElementById('username') || document.getElementById('loginEmail');
        const passwordInput = document.getElementById('password') || document.getElementById('loginPassword');

        if (!usernameInput || !passwordInput) {
            console.error("Không tìm thấy input username/password!");
            return;
        }

        const username = usernameInput.value.trim();
        const password = passwordInput.value;

        try {
            const res = await fetch(`${API_URL}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    username: username,
                    password: password
                })
            });

            const result = await res.json();

            if (res.ok) {
                // Lưu Token vào LocalStorage[cite: 5]
                const token = result.access_token || result.token;
                localStorage.setItem('token', token);

                if (result.full_name) localStorage.setItem('user_name', result.full_name);
                const email = result.email || result.user?.email;
                if (email) localStorage.setItem('user_email', email);
                if (result.user_name) localStorage.setItem('user_name', result.user_name);
                if (result.role) localStorage.setItem('role', result.role);

                // 👉 LƯU THÊM EMAIL THẬT TỪ DATABASE VÀO LOCALSTORAGE
                localStorage.setItem('user_email', result.email || username);

                // Chuyển hướng sang trang Dashboard[cite: 5]
                window.location.href = 'dashboard.html';
            } else {
                if (errorAlert) {
                    // Xử lý an toàn để tránh hiện chữ [object Object] khi FastAPI trả về lỗi cấu trúc
                    let errorMessage = 'Tài khoản hoặc mật khẩu không chính xác!';
                    if (result.detail) {
                        if (typeof result.detail === 'string') {
                            errorMessage = result.detail;
                        } else if (Array.isArray(result.detail)) {
                            errorMessage = result.detail.map(err => err.msg || JSON.stringify(err)).join(', ');
                        } else if (typeof result.detail === 'object') {
                            errorMessage = result.detail.msg || JSON.stringify(result.detail);
                        }
                    }

                    errorAlert.textContent = errorMessage;
                    errorAlert.classList.remove('hidden');
                } else {
                    alert('Tài khoản hoặc mật khẩu không chính xác!');
                }
            }
        } catch (err) {
            console.error('Lỗi kết nối:', err);
            if (errorAlert) {
                errorAlert.textContent = 'Không thể kết nối đến máy chủ Backend!';
                errorAlert.classList.remove('hidden');
            }
        }
    });
});
````

## File: README.md
````markdown
# 🏢 Meeting Management System (Hệ thống Quản lý Phòng họp)

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-00000F?style=for-the-badge&logo=mysql&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71105?style=for-the-badge&logo=sqlalchemy&logoColor=white)

Hệ thống Quản lý và Đặt lịch Phòng họp trực tuyến dành cho doanh nghiệp và tổ chức. Dự án được phát triển bằng **FastAPI** (Python) và **MySQL**, hỗ trợ tối ưu hóa việc quản lý phòng, đăng ký lịch họp và phân quyền người dùng.

---

## 📌 1. Bảng Công nghệ (Tech Stack)

* **Backend Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Python 3.10+)
* **Database:** MySQL
* **ORM:** [SQLAlchemy 2.0](https://www.sqlalchemy.org/) & [PyMySQL](https://pymysql.readthedocs.io/)
* **Security & Auth:** PBKDF2-HMAC-SHA256 Password Hashing, JWT Token Authentication
* **Validation & Schemas:** Pydantic v2
* **Server Runner:** Uvicorn ASGI Server

## Docker (local development)

Set `MYSQL_ROOT_PASSWORD` in `.env` if you want to override the local default, then start the stack and apply database migrations:

```sh
docker compose up --build -d
docker compose exec web alembic upgrade head
```

Compose configures the backend to connect to the `roomsync_db` service and the `meeting_db` database; do not use `localhost` as the database host from inside the backend container. Check service health with `docker compose ps` and backend output with `docker compose logs web`.

## QR meeting check-in

Apply the Alembic migration with `alembic upgrade head` to add room QR tokens and meeting check-in fields. Admins and managers can retrieve the room QR payload from `GET /api/v1/rooms/{room_id}/qr-code`; display its `qr_token` value as the room's QR code. Organizers and accepted invitees can scan that code during the 15-minute check-in window using the dashboard's booking list. Check-in and check-out are available at `/api/v1/meetings/{meeting_id}/check-in` and `/api/v1/meetings/{meeting_id}/check-out`. The API process runs reminder, no-show cancellation, and automatic check-out jobs every minute. Configure the existing SMTP environment variables to send no-show emails.

## 🔐 Google OAuth 2.0

The project uses the existing `httpx` dependency for Google OAuth and Calendar API requests. Create a Google OAuth 2.0 Web client, enable Google Calendar API, and register `http://localhost:8000/api/auth/google/callback` as an authorized redirect URI. Set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `FRONTEND_LOGIN_URL`, and `BACKEND_PUBLIC_URL` in `.env` (see `.env.example`).

Users can connect or disconnect their own Google Calendar from the dashboard Settings page. Once connected, newly created meetings are added to the organizer's calendar and Google sends invitations to meeting invitees; connecting also syncs the user's existing meetings. Invitees may still receive a Calendar consent email so their own calendar can be synchronized. Configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and `SMTP_FROM_EMAIL` to send those emails. Generate a Fernet key for `GOOGLE_TOKEN_ENCRYPTION_KEY`; refresh tokens are encrypted at rest. Apply `migrations/007_google_calendar_invitees.sql` and `migrations/008_add_meeting_participant_response_status.sql` before deploying. Set `FRONTEND_DASHBOARD_URL` to the dashboard's public URL (defaults to `/static/dashboard.html`). For production, use HTTPS and the exact public callback/frontend URLs.

---

## 📁 2. Cấu trúc Dự án (Project Structure)

```text
MeetingManagement/
├── app/
│   ├── core/                  # Cấu hình kết nối Database và Bảo mật
│   │   ├── database.py        # Kết nối SQLAlchemy Engine & Session
│   │   └── security.py        # Hash mật khẩu & Xác thực bảo mật
│   ├── models/                # SQLAlchemy Models (ORM Mapping)
│   │   ├── user.py            # Bảng người dùng
│   │   ├── room.py            # Bảng phòng họp
│   │   └── meeting.py         # Bảng lịch họp
│   ├── routers/               # API Endpoints (Controllers)
│   │   └── auth.py            # API Đăng nhập / Xác thực
│   └── schemas/               # Pydantic Schemas (Request/Response Validation)
│       └── auth.py
│   └── main.py                # File khởi chạy chính của ứng dụng FastAPI
├── scripts/
│   └── seed.py                # Script khởi tạo dữ liệu mẫu (Admin, Rooms)
├── .env.example               # Mẫu cấu hình biến môi trường
├── .gitignore                 # Bỏ qua các file rác và tài nguyên nhạy cảm
├── README.md                  # Tài liệu hướng dẫn sử dụng
├── requirements.txt           # Thư viện phụ thuộc của dự án
└── schema.sql                 # Sơ đồ Cơ sở dữ liệu DDL
````

## File: app/models/meeting.py
````python
# app/models/meeting.py
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import relationship, synonym

from app.core.database import Base


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    # meeting_type: 'online' | 'offline' — online meetings do not require a room
    meeting_type = Column(String(20), nullable=False, default="offline", server_default="offline")
    meeting_link = Column(String(255), nullable=True)
    online_link = synonym("meeting_link")
    is_recurring = Column(Boolean, nullable=False, default=False, server_default="0")
    recurring_type = Column(String(20), nullable=True)
    # room_id is nullable: online meetings have no room
    room_id = Column(Integer, ForeignKey("rooms.id", ondelete="SET NULL"), nullable=True, index=True)
    organizer_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(String(20), nullable=False, default="scheduled")
    check_in_time = Column(DateTime, nullable=True)
    check_out_time = Column(DateTime, nullable=True)
    reminder_sent = Column(Boolean, nullable=False, default=False, server_default="0")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True, onupdate=func.now())

    # Relationships
    equipments = relationship("MeetingEquipment", back_populates="meeting", cascade="all, delete-orphan")
    room = relationship("Room", lazy="joined")
    organizer = relationship("User", lazy="joined")
    participants = relationship(
        "MeetingParticipant",
        back_populates="meeting",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Meeting id={self.id} title={self.title!r}>"


class MeetingParticipant(Base):
    __tablename__ = "meeting_participants"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    meeting_id = Column(
        Integer,
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    response_status = Column(String(20), nullable=False, default="pending", server_default="pending")
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    meeting = relationship("Meeting", back_populates="participants")
    user = relationship("User", lazy="joined")

    __table_args__ = (
        UniqueConstraint("meeting_id", "user_id", name="uq_meeting_participant"),
    )

    def __repr__(self) -> str:
        return f"<MeetingParticipant meeting_id={self.meeting_id} user_id={self.user_id}>"
````

## File: app/schemas/meeting.py
````python
from datetime import datetime
from typing import Any, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.schemas.equipment import MeetingEquipmentItemInput, MeetingEquipmentItemOutput


class MeetingParticipationResponse(BaseModel):
    response_status: Literal["accepted", "declined"]


class MeetingCheckInRequest(BaseModel):
    qr_token: str


class MeetingCheckOutRequest(BaseModel):
    qr_token: str


# 1. Schema cho dữ liệu gửi lên khi đặt lịch họp mới (Request)
class MeetingCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None
    # meeting_type: 'online' | 'offline'
    meeting_type: str = 'offline'
    meeting_link: Optional[str] = None
    # Retained for compatibility with existing clients and service code.
    online_link: Optional[str] = None
    # room_id: bắt buộc khi meeting_type='offline', phải NULL khi 'online'
    room_id: Optional[int] = None
    start_time: datetime
    end_time: datetime

    # Bổ sung các trường để hỗ trợ đặt lịch định kỳ
    is_recurring: Optional[bool] = False
    recurrence_type: Optional[str] = "none"  # "none", "weekly", "monthly", "until_changed"
    recurrence_end_date: Optional[datetime] = None

    # Thiết bị mượn kèm & Người tham dự
    equipments: Optional[List[MeetingEquipmentItemInput]] = []
    participant_ids: Optional[List[int]] = []

    @field_validator('meeting_type')
    @classmethod
    def validate_meeting_type(cls, v: str) -> str:
        if v not in ('online', 'offline'):
            raise ValueError("meeting_type phải là 'online' hoặc 'offline'")
        return v

    @model_validator(mode='after')
    def validate_meeting_mode(self) -> 'MeetingCreateRequest':
        link = (self.meeting_link or self.online_link or '').strip() or None
        self.meeting_link = link
        self.online_link = link
        return self


# 2. Schema phản hồi thông tin cuộc họp trả về cho Client (Response)
class MeetingResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    meeting_type: str = 'offline'
    meeting_link: Optional[str] = None
    online_link: Optional[str] = None
    room_id: Optional[int] = None
    organizer_id: Optional[int] = None
    start_time: datetime
    end_time: datetime
    is_recurring: bool = False
    recurring_type: Optional[str] = None
    status: str
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None
    equipments: Optional[List[MeetingEquipmentItemOutput]] = []
    participant_ids: Optional[List[int]] = []

    model_config = ConfigDict(from_attributes=True)

    @field_validator('equipments', mode='before')
    @classmethod
    def parse_equipments(cls, v: Any):
        if not v:
            return []
        res = []
        for item in v:
            if isinstance(item, dict):
                res.append(item)
            else:
                eq_name = getattr(getattr(item, 'equipment', None), 'name', 'Thiết bị')
                res.append({
                    'equipment_id': item.equipment_id,
                    'equipment_name': eq_name,
                    'quantity': item.quantity,
                    'note': getattr(item, 'note', None)
                })
        return res


# 3. Schema phản hồi người dùng thường xuyên họp
class FrequentUserResponse(BaseModel):
    id: int
    full_name: str
    email: str
    invite_count: int

    model_config = ConfigDict(from_attributes=True)


# 4. Schema phản hồi thông báo
class NotificationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    content: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# 5. Schema cho tính năng gợi ý khung giờ trống
class SuggestTimeRequest(BaseModel):
    participant_ids: List[int]
    date: str  # Định dạng: "YYYY-MM-DD"
    duration_minutes: int


class TimeSlot(BaseModel):
    start_time: str  # Định dạng ISO 8601: "YYYY-MM-DDTHH:MM:SS"
    end_time: str    # Định dạng ISO 8601: "YYYY-MM-DDTHH:MM:SS"


class SuggestTimeResponse(BaseModel):
    suggested_slots: List[TimeSlot]
````

## File: app/services/meeting_service.py
````python
from datetime import datetime, timedelta, timezone
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from fastapi import HTTPException, status

from app.models.room import Room
from app.models.meeting import Meeting, MeetingParticipant
from app.models.notification import Notification
from app.models.user import User
from app.schemas.meeting import MeetingCreateRequest

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class MeetingService:

    @staticmethod
    def check_in_meeting(
        db: Session,
        meeting_id: int,
        qr_token: str,
        current_user: User,
        now: datetime | None = None,
    ) -> Meeting:
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if meeting is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy cuộc họp.")
        if (meeting.status or "").casefold() != "scheduled":
            raise HTTPException(status_code=400, detail="Cuộc họp không ở trạng thái có thể check-in.")

        accepted_participant = any(
            participant.user_id == current_user.id
            and (participant.response_status or "").casefold() == "accepted"
            for participant in meeting.participants
        )
        if meeting.organizer_id != current_user.id and not accepted_participant:
            raise HTTPException(status_code=403, detail="Bạn không có quyền check-in cuộc họp này.")

        if meeting.room is None or not meeting.room.qr_token or meeting.room.qr_token != qr_token:
            raise HTTPException(status_code=400, detail="Mã QR phòng họp không hợp lệ.")

        current_time = now or _utc_now()
        if current_time < meeting.start_time - timedelta(minutes=15):
            raise HTTPException(
                status_code=400,
                detail="Chưa đến thời gian check-in (cho phép trước 15 phút)",
            )
        if current_time > meeting.start_time + timedelta(minutes=15):
            raise HTTPException(status_code=400, detail="Đã quá thời gian check-in")

        meeting.status = "IN_PROGRESS"
        meeting.check_in_time = current_time
        if meeting.organizer_id is not None:
            db.add(
                Notification(
                    user_id=meeting.organizer_id,
                    title="Check-in cuộc họp thành công",
                    content=(
                        f"Cuộc họp '{meeting.title}' đã check-in thành công và bắt đầu."
                    ),
                )
            )
        try:
            db.commit()
            db.refresh(meeting)
        except SQLAlchemyError as exc:
            db.rollback()
            logger.exception("Failed to check in meeting_id=%s", meeting_id)
            raise HTTPException(status_code=503, detail="Không thể lưu check-in cuộc họp.") from exc
        return meeting

    @staticmethod
    def check_out_meeting(
        db: Session,
        meeting_id: int,
        qr_token: str,
        current_user: User,
        now: datetime | None = None,
    ) -> Meeting:
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if meeting is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy cuộc họp.")
        if (meeting.status or "").casefold() != "in_progress":
            raise HTTPException(status_code=400, detail="Cuộc họp không ở trạng thái có thể check-out.")

        is_participant = any(
            participant.user_id == current_user.id for participant in meeting.participants
        )
        if meeting.organizer_id != current_user.id and not is_participant:
            raise HTTPException(status_code=403, detail="Bạn không thuộc cuộc họp này.")
        if meeting.room is None or not meeting.room.qr_token or meeting.room.qr_token != qr_token:
            raise HTTPException(status_code=400, detail="Mã QR phòng họp không hợp lệ.")

        meeting.status = "COMPLETED"
        meeting.check_out_time = now or _utc_now()
        try:
            db.commit()
            db.refresh(meeting)
        except SQLAlchemyError as exc:
            db.rollback()
            logger.exception("Failed to check out meeting_id=%s", meeting_id)
            raise HTTPException(status_code=503, detail="Không thể lưu check-out cuộc họp.") from exc
        return meeting

    @staticmethod
    def cancel_meeting(db: Session, meeting_id: int, current_user: User):
        """Cancel a meeting without deleting it or its participants."""
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Kh?ng t?m th?y cu?c h?p.",
            )

        is_admin = str(current_user.role or "").strip().casefold() == "admin"
        if meeting.organizer_id != current_user.id and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="B?n kh?ng c? quy?n h?y cu?c h?p n?y.",
            )

        # Idempotent: repeating the operation is a successful no-op.
        if meeting.status != "CANCELLED":
            meeting.status = "CANCELLED"
            try:
                db.commit()
                db.refresh(meeting)
            except SQLAlchemyError as exc:
                db.rollback()
                logger.exception(
                    "Failed to cancel meeting_id=%s for user_id=%s",
                    meeting_id,
                    current_user.id,
                )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Không thể hủy cuộc họp do lỗi cơ sở dữ liệu. "
                    "Vui lòng kiểm tra migration schema và thử lại.",
                ) from exc

        return meeting

    @staticmethod
    def get_all_active_rooms(db: Session):
        """VIỆC 1: Lấy danh sách tất cả phòng họp đang hoạt động"""
        return db.query(Room).filter(Room.is_active == True).all()

    @staticmethod
    def create_meeting(db: Session, payload: MeetingCreateRequest, organizer_id: int | None = None):
        """VIỆC 2 & 3: Đặt phòng đơn hoặc định kỳ + Chặn quá khứ + Kiểm tra chống trùng lịch toàn diện"""

        # 0. Kiểm tra thời gian bắt đầu không được ở trong quá khứ
        now = datetime.now()
        if payload.start_time < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể đặt lịch họp với thời gian bắt đầu nằm trong quá khứ!"
            )

        # 0b. Kiểm tra end_time phải sau start_time
        if payload.end_time <= payload.start_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Thời gian kết thúc phải sau thời gian bắt đầu!"
            )

        # 1. Xác định meeting_type và kiểm tra phòng (chỉ khi offline)
        meeting_type = getattr(payload, 'meeting_type', 'offline') or 'offline'
        meeting_link = (
            getattr(payload, 'meeting_link', None)
            or getattr(payload, 'online_link', None)
            or ''
        ).strip() or None
        room_id = payload.room_id

        if meeting_type == 'offline':
            if room_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Offline meetings require a room_id",
                )
            room = db.query(Room).filter(
                Room.id == room_id,
                Room.is_active == True
            ).first()
            if not room:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phòng họp không tồn tại hoặc đã ngưng hoạt động!"
                )
        elif meeting_type == 'online':
            if not meeting_link:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Online meetings require a meeting_link",
                )
            room_id = None
            room = None
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="meeting_type must be 'offline' or 'online'",
            )

        # 2. Xử lý danh sách các mốc thời gian (Hỗ trợ cả lịch đơn và lịch định kỳ tuần/tháng)
        meeting_dates = []
        start_date = payload.start_time
        end_date = payload.end_time
        
        # Lấy thông tin lặp lịch từ payload
        recurrence_type = getattr(payload, "recurrence_type", "none")
        recurrence_end_date = getattr(payload, "recurrence_end_date", None)

        if recurrence_type == "until_changed" and not recurrence_end_date:
            recurrence_end_date = start_date + timedelta(days=365)

        if not recurrence_type or recurrence_type == "none" or not recurrence_end_date:
            meeting_dates.append((start_date, end_date))
        else:
            # Vòng lặp sinh ra các khoảng thời gian lặp định kỳ
            current_start = start_date
            current_end = end_date
            while current_start <= recurrence_end_date:
                meeting_dates.append((current_start, current_end))
                if recurrence_type == "weekly":
                    current_start += timedelta(weeks=1)
                    current_end += timedelta(weeks=1)
                elif recurrence_type == "monthly":
                    current_start += timedelta(days=30)
                    current_end += timedelta(days=30)
                elif recurrence_type == "until_changed":
                    current_start += timedelta(days=30)
                    current_end += timedelta(days=30)
                else:
                    break

        # 3. Vòng lặp kiểm tra trùng phòng & quản lý Transaction (Rollback nếu dính bất kỳ ngày nào)
        try:
            created_meetings = []
            requested_equipments = getattr(payload, "equipments", []) or []

            # Kiểm tra tồn kho thiết bị cho từng khung giờ
            if requested_equipments:
                from app.services.equipment_service import check_equipment_availability
                for s_time, e_time in meeting_dates:
                    check_equipment_availability(db, s_time, e_time, requested_equipments)
            
            for s_time, e_time in meeting_dates:
                # Kiểm tra conflict phòng — chỉ áp dụng cho OFFLINE meeting
                if meeting_type == 'offline':
                    overlapping_meeting = db.query(Meeting).filter(
                        Meeting.room_id == room_id,
                        Meeting.status.notin_(["CANCELLED", "canceled", "CANCELLED_NO_SHOW"]),
                        and_(
                            Meeting.start_time < e_time,
                            Meeting.end_time > s_time
                        )
                    ).first()

                    if overlapping_meeting:
                        db.rollback()
                        date_str = s_time.strftime("%d/%m/%Y lúc %H:%M")
                        if not recurrence_type or recurrence_type == "none":
                            detail_msg = f"Phòng họp '{room.name}' đã có cuộc họp trong khung giờ này."
                        else:
                            detail_msg = f"Phòng họp '{room.name}' đã bị trùng lịch vào ngày {date_str}."
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=detail_msg
                        )

                # Tạo bản ghi cuộc họp
                new_meeting = Meeting(
                    title=payload.title,
                    description=payload.description,
                    meeting_type=meeting_type,
                    meeting_link=meeting_link,
                    room_id=room_id,
                    organizer_id=organizer_id,
                    start_time=s_time,
                    end_time=e_time,
                    is_recurring=recurrence_type not in (None, "none"),
                    recurring_type=recurrence_type if recurrence_type != "none" else None,
                    status="scheduled"
                )
                db.add(new_meeting)
                db.flush()

                # Lưu các thiết bị mượn kèm
                if requested_equipments:
                    from app.models.equipment import MeetingEquipment
                    for item in requested_equipments:
                        me = MeetingEquipment(
                            meeting_id=new_meeting.id,
                            equipment_id=item.equipment_id,
                            quantity=item.quantity,
                            note=getattr(item, 'note', None)
                        )
                        db.add(me)

                # Lưu participants — D2: skip organizer, atomic flush
                participant_ids_list = getattr(payload, 'participant_ids', []) or []
                for pid in participant_ids_list:
                    if pid == organizer_id:  # D2: organizer đã track qua organizer_id, skip
                        continue
                    mp = MeetingParticipant(meeting_id=new_meeting.id, user_id=pid)
                    db.add(mp)

                if participant_ids_list:
                    try:
                        db.flush()  # một flush duy nhất, atomic với transaction
                    except IntegrityError:
                        db.rollback()
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="participant_ids chứa user không tồn tại hoặc bị trùng lặp."
                        )

                created_meetings.append(new_meeting)

            # Tiến hành commit lưu tất cả vào database
            db.commit()
            for m in created_meetings:
                db.refresh(m)
                
            return created_meetings

        except Exception as e:
            db.rollback()
            raise e

    @staticmethod
    def calculate_suggested_times(db: Session, participant_ids: list[int], date_str: str, duration_minutes: int):
        """VIỆC CỦA LIÊM: Thuật toán truy vấn, so sánh lịch rảnh/bận để tìm khung giờ trống chung"""
        
        # KIỂM TRA: Đảm bảo tất cả user trong participant_ids phải tồn tại trong database
        existing_users = db.query(User).filter(User.id.in_(participant_ids)).all()
        existing_user_ids = {user.id for user in existing_users}
        missing_ids = [uid for uid in participant_ids if uid not in existing_user_ids]
        
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy người tham gia với ID: {missing_ids}"
            )

        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        
        # Khung giờ làm việc mặc định trong ngày: 08:00 - 12:00 và 13:00 - 17:00
        work_start1 = datetime.combine(target_date, datetime.strptime("08:00", "%H:%M").time())
        work_end1 = datetime.combine(target_date, datetime.strptime("12:00", "%H:%M").time())
        work_start2 = datetime.combine(target_date, datetime.strptime("13:00", "%H:%M").time())
        work_end2 = datetime.combine(target_date, datetime.strptime("17:00", "%H:%M").time())
        
        working_intervals = [(work_start1, work_end1), (work_start2, work_end2)]

        # Lấy toàn bộ cuộc họp trong ngày, loại trừ trạng thái 'canceled'
        day_start = datetime.combine(target_date, datetime.min.time())
        day_end = datetime.combine(target_date, datetime.max.time())
        
        meetings = db.query(Meeting).filter(
            Meeting.status.notin_(["CANCELLED", "canceled", "CANCELLED_NO_SHOW"]),
            Meeting.start_time <= day_end,
            Meeting.end_time >= day_start,
            Meeting.organizer_id.in_(participant_ids)
        ).all()

        # Thu thập các khoảng thời gian bận
        busy_intervals = [(m.start_time, m.end_time) for m in meetings]

        # Sắp xếp và gộp các khoảng bận bị chồng chéo
        busy_intervals.sort(key=lambda x: x[0])
        merged_busy = []
        for interval in busy_intervals:
            if not merged_busy or merged_busy[-1][1] <= interval[0]:
                merged_busy.append(interval)
            else:
                merged_busy[-1] = (merged_busy[-1][0], max(merged_busy[-1][1], interval[1]))

        # Tính toán khoảng thời gian rảnh bằng cách trừ khoảng bận khỏi giờ làm việc
        free_slots = []
        for w_start, w_end in working_intervals:
            current_start = w_start
            for b_start, b_end in merged_busy:
                if b_end <= current_start:
                    continue
                if b_start >= w_end:
                    break
                if b_start > current_start:
                    free_slots.append((current_start, b_start))
                current_start = max(current_start, b_end)
            if current_start < w_end:
                free_slots.append((current_start, w_end))

        # Lọc ra các khoảng rảnh có độ dài >= duration_minutes
        suggested_slots = []
        duration_delta = timedelta(minutes=duration_minutes)
        for f_start, f_end in free_slots:
            slot_start = f_start
            while slot_start + duration_delta <= f_end:
                slot_end = slot_start + duration_delta
                suggested_slots.append({
                    "start_time": slot_start.strftime("%Y-%m-%dT%H:%M:%S"),
                    "end_time": slot_end.strftime("%Y-%m-%dT%H:%M:%S")
                })
                slot_start += timedelta(minutes=30)  # Bước nhảy gợi ý mỗi 30 phút

        return {"suggested_slots": suggested_slots}

    @staticmethod
    def suggest_time(db: Session, payload):
        """Alias cho calculate_suggested_times — dùng bởi router /suggest-time."""
        return MeetingService.calculate_suggested_times(
            db=db,
            participant_ids=payload.participant_ids,
            date_str=payload.date,
            duration_minutes=payload.duration_minutes
        )
````

## File: frontend/css/style.css
````css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
}

body {
    background-color: #f4f6f9;
    color: #1e293b;
    font-size: 13px;
    min-height: 100vh;
}

.app-layout {
    display: flex;
    min-height: 100vh;
}

/* ==========================================
   1. SIDEBAR
   ========================================== */
.sidebar {
    width: 230px;
    background: #ffffff;
    border-right: 1px solid #e2e8f0;
    padding: 20px 16px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    position: fixed;
    height: 100vh;
    left: 0;
    top: 0;
    z-index: 100;
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.app-layout.collapsed .sidebar {
    transform: translateX(-100%);
}

.app-layout.collapsed .main-content {
    margin-left: 0 !important;
}

.sidebar-brand {
    display: flex;
    align-items: center;
    gap: 12px;
    font-weight: 700;
    font-size: 16px;
    color: #0f172a;
    cursor: pointer;
    padding-bottom: 12px;
    border-bottom: 1px solid #f1f5f9;
}

.logo-icon {
    background: #1d4ed8;
    color: #ffffff;
    padding: 6px 10px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 800;
}

.brand-name {
    font-size: 17px;
    font-weight: 800;
    color: #0f172a;
    letter-spacing: -0.3px;
}

.nav-menu {
    margin-top: 20px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    flex: 1;
}

.nav-item {
    text-decoration: none;
    color: #64748b;
    padding: 10px 14px;
    border-radius: 10px;
    font-weight: 500;
    font-size: 13.5px;
    display: flex;
    align-items: center;
    gap: 12px;
    transition: all 0.2s ease;
}

.nav-icon {
    width: 18px;
    height: 18px;
    flex-shrink: 0;
}

.nav-item:hover {
    background: #f8fafc;
    color: #0f172a;
}

.nav-item.active {
    background: #eff6ff;
    color: #1d4ed8;
    font-weight: 600;
}

.sidebar-user {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px;
    border-top: 1px solid #f1f5f9;
    cursor: pointer;
    border-radius: 10px;
    transition: background 0.2s ease;
}

.sidebar-user:hover { background: #f8fafc; }

.user-avatar {
    width: 36px;
    height: 36px;
    background: #1d4ed8;
    color: #ffffff;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 14px;
    flex-shrink: 0;
}

.user-info { display: flex; flex-direction: column; }
.user-name { font-size: 13px; font-weight: 600; color: #0f172a; }
.user-role { font-size: 11px; color: #94a3b8; }

/* ==========================================
   2. MAIN CONTENT & TOPBAR
   ========================================== */
.main-content {
    flex: 1;
    min-width: 0;
    margin-left: 230px;
    display: flex;
    flex-direction: column;
    transition: margin-left 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.topbar {
    background: #ffffff;
    padding: 12px 28px;
    border-bottom: 1px solid #e2e8f0;
    display: flex;
    justify-content: space-between;
    align-items: center;
    position: sticky;
    top: 0;
    z-index: 5;
}

.topbar-left { display: flex; align-items: center; gap: 16px; }

.btn-toggle-menu {
    background: #f1f5f9;
    border: 1px solid #e2e8f0;
    color: #334155;
    padding: 8px;
    border-radius: 8px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease;
}

.btn-toggle-menu:hover {
    background: #1d4ed8;
    color: #ffffff;
    border-color: #1d4ed8;
}

.search-box {
    display: flex;
    align-items: center;
    background: #f1f5f9;
    padding: 8px 16px;
    border-radius: 20px;
    width: 320px;
}

.search-icon {
    width: 15px;
    height: 15px;
    color: #94a3b8;
    margin-right: 10px;
}

.search-box input {
    border: none;
    background: transparent;
    outline: none;
    font-size: 12.5px;
    width: 100%;
}

.topbar-right { display: flex; align-items: center; gap: 14px; }
.notification-wrapper { position: relative; }
.icon-btn { background: transparent; border: none; cursor: pointer; color: #64748b; padding: 4px; display: flex; align-items: center; position: relative; }

/* Chấm đỏ nhấp nháy trên nút chuông */
.notification-dot {
    position: absolute;
    top: 2px;
    right: 2px;
    width: 9px;
    height: 9px;
    background-color: #ef4444;
    border-radius: 50%;
    border: 2px solid #ffffff;
    animation: notifPulse 1.5s ease-in-out infinite;
    z-index: 10;
}

@keyframes notifPulse {
    0%   { transform: scale(1);   opacity: 1; }
    50%  { transform: scale(1.35); opacity: 0.7; }
    100% { transform: scale(1);   opacity: 1; }
}

.notification-popup {
    position: absolute; right: 0; top: 36px; width: 280px; background: white; border: 1px solid #e2e8f0; border-radius: 12px; box-shadow: 0 10px 20px -5px rgba(0,0,0,0.1); padding: 14px; z-index: 20;
}
.notification-popup h4 { font-size: 13px; margin-bottom: 10px; }
.notification-popup ul { list-style: none; font-size: 12px; color: #475569; }
.notification-popup li { padding: 8px 0; border-bottom: 1px solid #f1f5f9; }

.header-avatar {
    width: 34px; height: 34px; background: #3b82f6; color: white; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 700; cursor: pointer;
}

/* ==========================================
   3. HERO BANNERS & STATS
   ========================================== */
.hero-banner-overview {
    position: relative;
    height: 360px;
    border-radius: 20px;
    overflow: hidden;
    margin-bottom: 28px;
    background: url('https://images.unsplash.com/photo-1497366216548-37526070297c') center/cover no-repeat;
    display: flex;
    align-items: center;
    padding: 0 48px;
    box-shadow: 0 12px 30px -10px rgba(15, 23, 42, 0.15);
}

.hero-overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(100deg, rgba(15, 23, 42, 0.92) 0%, rgba(15, 23, 42, 0.65) 60%, rgba(15, 23, 42, 0.2) 100%);
}

.hero-content {
    position: relative;
    z-index: 2;
    color: #ffffff;
    max-width: 680px;
}

.hero-badge {
    display: inline-block;
    background: rgba(59, 130, 246, 0.3);
    border: 1px solid rgba(147, 197, 253, 0.4);
    color: #93c5fd;
    font-size: 11px;
    padding: 4px 14px;
    border-radius: 20px;
    font-weight: 600;
    text-transform: uppercase;
    margin-bottom: 16px;
}

.hero-content h2 {
    font-size: 28px;
    font-weight: 800;
    line-height: 1.25;
    margin-bottom: 12px;
    color: #ffffff;
}

.hero-content p {
    font-size: 13.5px;
    line-height: 1.6;
    color: #cbd5e1;
    margin-bottom: 24px;
}

.hero-actions { display: flex; gap: 14px; }

.btn-hero-primary {
    background: #2563eb; color: #ffffff; border: none; padding: 11px 22px; border-radius: 10px; font-weight: 600; font-size: 13px; cursor: pointer; transition: all 0.2s ease;
}
.btn-hero-primary:hover { background: #1d4ed8; transform: translateY(-2px); }

.btn-hero-secondary {
    background: rgba(255, 255, 255, 0.12); color: #ffffff; border: 1px solid rgba(255, 255, 255, 0.25); padding: 11px 22px; border-radius: 10px; font-weight: 600; font-size: 13px; cursor: pointer; backdrop-filter: blur(6px); transition: all 0.2s ease;
}
.btn-hero-secondary:hover { background: rgba(255, 255, 255, 0.2); transform: translateY(-2px); }

.hero-banner-rooms {
    position: relative;
    height: 200px;
    border-radius: 16px;
    overflow: hidden;
    margin-bottom: 24px;
    background: url('https://images.unsplash.com/photo-1517502884422-41eaead166d4') center/cover no-repeat;
    display: flex;
    align-items: center;
    padding: 0 36px;
}
.hero-banner-rooms .hero-overlay { background: linear-gradient(90deg, rgba(30, 41, 59, 0.9) 0%, rgba(30, 41, 59, 0.5) 100%); }
.hero-banner-rooms h2 { font-size: 22px; font-weight: 700; color: white; margin-bottom: 6px; }
.hero-banner-rooms p { font-size: 13px; color: #94a3b8; }

.content-body { padding: 28px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { font-size: 20px; font-weight: 700; color: #0f172a; }
.subtitle { color: #94a3b8; font-size: 12px; margin-top: 2px; }

.btn-add-room { background: #1d4ed8; color: #ffffff; border: none; padding: 10px 18px; border-radius: 8px; font-weight: 600; font-size: 12px; cursor: pointer; }

.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 18px; margin-bottom: 24px; }
.stat-card { background: #ffffff; padding: 18px; border-radius: 12px; border: 1px solid #e2e8f0; }
.stat-title { font-size: 11.5px; color: #64748b; font-weight: 600; }
.stat-value { font-size: 24px; font-weight: 700; margin: 6px 0; }
.stat-sub { font-size: 11.5px; }

.text-orange { color: #d97706; }
.text-green { color: #16a34a; }
.text-purple { color: #7c3aed; }
.text-gray { color: #94a3b8; }

.filter-wrapper { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.filter-left { display: flex; align-items: center; gap: 8px; }
.btn-filter-date, .select-capacity { background: #ffffff; border: 1px solid #e2e8f0; padding: 8px 14px; border-radius: 8px; font-size: 12px; color: #334155; cursor: pointer; }

.filter-chips { display: flex; gap: 6px; margin-left: 8px; }
.chip { background: #ffffff; border: 1px solid #e2e8f0; padding: 8px 16px; border-radius: 8px; font-size: 12px; color: #64748b; cursor: pointer; }
.chip.active { background: #1d4ed8; color: #ffffff; border-color: #1d4ed8; }
.status-summary { font-size: 12.5px; color: #64748b; margin-left: 14px; }

.room-grid { display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px; }
.room-card { background: #ffffff; border-radius: 14px; border: 1px solid #e2e8f0; overflow: hidden; }
.card-image { position: relative; height: 170px; }
.card-image img { width: 100%; height: 100%; object-fit: cover; }
.status-badge { position: absolute; top: 12px; right: 12px; padding: 4px 12px; border-radius: 14px; font-size: 11px; font-weight: 600; }
.status-badge.has-qr-action { right: 12px; }
.status-green { background: #dcfce7; color: #15803d; }
.status-red { background: #fee2e2; color: #b91c1c; }
.room-qr-icon { position: absolute; top: 10px; left: 12px; display: inline-grid; place-items: center; width: 38px; height: 38px; padding: 8px; color: #1d4ed8; background: rgba(255, 255, 255, .96); border: 1px solid rgba(219, 234, 254, .95); border-radius: 50%; box-shadow: 0 2px 8px rgba(15, 23, 42, .18); cursor: pointer; transition: color 150ms ease, background-color 150ms ease, transform 150ms ease, box-shadow 150ms ease; }
.room-qr-icon svg { width: 21px; height: 21px; fill: currentColor; }
.room-qr-icon:hover, .room-qr-icon:focus-visible { color: #fff; background: #1d4ed8; transform: scale(1.08); box-shadow: 0 4px 12px rgba(29, 78, 216, .32); }
.room-qr-icon:focus-visible, .qr-icon-button:focus-visible, .qr-close-button:focus-visible { outline: 3px solid #93c5fd; outline-offset: 2px; }

.card-body { padding: 16px; }
.card-body h3 { font-size: 15px; font-weight: 700; color: #0f172a; }
.location { font-size: 12px; color: #94a3b8; margin: 4px 0 12px 0; }
.amenities-tags { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 16px; }
.tag { background: #f8fafc; border: 1px solid #f1f5f9; font-size: 11px; padding: 3px 8px; border-radius: 6px; color: #64748b; }

.card-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.btn-schedule { flex: 1; background: #ffffff; border: 1px solid #e2e8f0; color: #334155; padding: 9px; border-radius: 8px; font-weight: 600; font-size: 12px; cursor: pointer; }
.btn-book { flex: 1; background: #1d4ed8; color: #ffffff; border: none; padding: 9px; border-radius: 8px; font-weight: 600; font-size: 12px; cursor: pointer; }
.btn-admin-action { flex: 1; min-width: 52px; padding: 9px 8px; color: #334155; background: #fff; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 12px; font-weight: 600; cursor: pointer; }
.btn-admin-action:hover { background: #f1f5f9; }

/* TABLES & SETTINGS */
.table-card, .settings-card { background: white; border: 1px solid #e2e8f0; border-radius: 14px; padding: 24px; }
.data-table { width: 100%; border-collapse: collapse; text-align: left; }
.data-table th, .data-table td { padding: 14px; border-bottom: 1px solid #f1f5f9; }
.data-table th { font-size: 12px; color: #64748b; font-weight: 600; }
.my-bookings-scroll { overflow-x: auto; }
.my-bookings-table { min-width: 660px; table-layout: fixed; }
.my-bookings-table th:nth-child(1) { width: 27%; }
.my-bookings-table th:nth-child(2) { width: 35%; }
.my-bookings-table th:nth-child(3) { width: 18%; }
.my-bookings-table th:nth-child(4) { width: 20%; }
.my-bookings-table th, .my-bookings-table td { padding: 16px 14px; vertical-align: middle; }
.my-bookings-table th:last-child, .my-bookings-table td:last-child { text-align: right; }
.booking-room-cell { overflow-wrap: anywhere; }
.booking-room-name, .booking-meeting-title { display: block; }
.booking-room-name { color: #0f172a; font-size: 14px; font-weight: 700; }
.booking-meeting-title { margin-top: 4px; color: #64748b; font-size: 12px; line-height: 1.45; }
.booking-meeting-link { display: inline-block; margin-top: 6px; color: #1d4ed8; font-size: 12px; font-weight: 600; text-decoration: underline; text-underline-offset: 2px; }
.booking-meeting-link:hover { color: #1e40af; }
.booking-equipment-summary { margin-top: 7px; color: #64748b; font-size: 11px; line-height: 1.5; }
.booking-datetime { display: flex; flex-direction: column; gap: 4px; }
.booking-date { color: #64748b; font-size: 12px; }
.booking-time { color: #0f172a; font-size: 13px; white-space: nowrap; }
.booking-status { display: inline-flex; align-items: center; padding: 5px 9px; border-radius: 999px; font-size: 11px; font-weight: 600; white-space: nowrap; }
.booking-status-scheduled { color: #1d4ed8; background: #eff6ff; }
.booking-status-progress { color: #b45309; background: #fffbeb; }
.booking-status-completed { color: #15803d; background: #f0fdf4; }
.booking-status-canceled, .booking-status-unknown { color: #64748b; background: #f1f5f9; }
.booking-cancel-button { padding: 7px 11px; color: #b91c1c; background: #fff; border: 1px solid #fecaca; border-radius: 7px; font-size: 12px; font-weight: 600; cursor: pointer; }
.booking-cancel-button:hover { background: #fef2f2; border-color: #f87171; }
.table-empty-state { padding: 28px 14px !important; color: #64748b; text-align: center; }

.booking-tabs { display: flex; gap: 8px; margin: 0 0 18px; padding: 5px; width: fit-content; border-radius: 10px; background: #f1f5f9; }
.booking-tab { padding: 9px 16px; color: #64748b; background: transparent; border: 0; border-radius: 7px; font-size: 13px; font-weight: 600; cursor: pointer; }
.booking-tab.active { color: #1d4ed8; background: #fff; box-shadow: 0 1px 3px #0f172a1a; }
.booking-panel[hidden] { display: none; }
.booking-calendar-toolbar { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 14px; flex-wrap: wrap; }
.booking-calendar-nav, .booking-calendar-views { display: flex; align-items: center; gap: 8px; }
.booking-calendar-title { min-width: 180px; margin: 0 0 0 8px; color: #0f172a; font-size: 18px; font-weight: 700; }
.booking-calendar-button, .booking-calendar-views button { min-height: 36px; padding: 7px 11px; color: #475569; background: #fff; border: 1px solid #e2e8f0; border-radius: 7px; font-size: 12px; font-weight: 600; cursor: pointer; }
.booking-calendar-views button.active { color: #1d4ed8; border-color: #93c5fd; background: #eff6ff; }
.booking-calendar-grid { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); overflow: hidden; border: 1px solid #e2e8f0; border-radius: 12px; background: #fff; }
.booking-calendar-weekday { padding: 10px 6px; color: #64748b; background: #f8fafc; text-align: center; font-size: 11px; font-weight: 700; }
.booking-calendar-day { min-height: 100px; padding: 8px; border-top: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; cursor: pointer; }
.booking-calendar-day:nth-child(7n) { border-right: 0; }
.booking-calendar-day.outside { background: #f8fafc; color: #94a3b8; }
.booking-calendar-day.selected { outline: 2px solid #2563eb; outline-offset: -2px; background: #eff6ff; }
.booking-calendar-day.today .booking-calendar-day-number { color: #1d4ed8; font-weight: 800; }
.booking-calendar-day-number { display: inline-flex; align-items: center; justify-content: center; width: 26px; height: 26px; border-radius: 50%; font-size: 12px; }
.booking-calendar-event { display: block; overflow: hidden; margin-top: 5px; padding: 4px 5px; color: #1e40af; background: #dbeafe; border-radius: 4px; font-size: 10px; text-overflow: ellipsis; white-space: nowrap; }
.booking-calendar-more { margin-top: 4px; color: #64748b; font-size: 10px; }
.booking-day-agenda { margin-top: 18px; padding: 18px; border: 1px solid #e2e8f0; border-radius: 12px; background: #fff; }
.booking-day-agenda h3 { margin: 0 0 12px; color: #0f172a; font-size: 15px; font-weight: 700; }
.booking-agenda-item { display: grid; grid-template-columns: 92px 1fr; gap: 12px; padding: 12px 0; border-top: 1px solid #f1f5f9; }
.booking-agenda-time { color: #1d4ed8; font-size: 12px; font-weight: 700; }
.booking-agenda-details strong, .booking-agenda-details span { display: block; }
.booking-agenda-details strong { color: #0f172a; font-size: 13px; }
.booking-agenda-details span { margin-top: 3px; color: #64748b; font-size: 12px; }
.booking-list { display: grid; gap: 10px; }
.booking-list-card { overflow: hidden; border: 1px solid #e2e8f0; border-radius: 10px; background: #fff; }
.booking-list-row { display: grid; grid-template-columns: minmax(180px, 1.4fr) minmax(150px, 1fr) auto auto; align-items: center; gap: 14px; padding: 14px 16px; }
.booking-list-main { min-width: 0; }
.booking-list-main strong, .booking-list-main span { display: block; }
.booking-list-main strong { overflow: hidden; color: #0f172a; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }
.booking-list-main span, .booking-list-time { margin-top: 4px; color: #64748b; font-size: 12px; }
.booking-list-actions { display: flex; gap: 7px; justify-content: flex-end; }
.booking-guest-toggle, .booking-rsvp-button { padding: 7px 10px; color: #334155; background: #fff; border: 1px solid #cbd5e1; border-radius: 7px; font-size: 11px; font-weight: 600; cursor: pointer; }
.booking-guest-toggle:hover, .booking-rsvp-button:hover { background: #f8fafc; }
.booking-guest-list { padding: 12px 16px; border-top: 1px solid #f1f5f9; background: #f8fafc; }
.booking-guest { display: flex; justify-content: space-between; gap: 12px; padding: 6px 0; color: #334155; font-size: 12px; }
.booking-guest.pending { color: #94a3b8; }
.booking-guest-status.accepted { color: #15803d; font-weight: 700; }
.booking-guest-status.declined { color: #b91c1c; }
.booking-guest-status.pending { color: #94a3b8; }
.booking-list-empty { padding: 28px 16px; color: #64748b; border: 1px dashed #cbd5e1; border-radius: 10px; text-align: center; font-size: 13px; }

.booking-qr-button { min-height: 34px; padding: 7px 11px; color: #1d4ed8; background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 7px; font-size: 12px; font-weight: 600; }
.booking-qr-button:hover { background: #dbeafe; }
.qr-check-modal .modal-content { width: min(440px, calc(100vw - 32px)); }
.qr-reader { width: 100%; min-height: 220px; margin: 16px 0; overflow: hidden; border-radius: 8px; }
.qr-manual-label { display: block; margin-bottom: 6px; color: #4b5563; font-size: 12px; font-weight: 600; }
.qr-toast { position: fixed; z-index: 10001; right: 24px; bottom: 24px; max-width: min(420px, calc(100vw - 48px)); padding: 12px 16px; color: #fff; background: #047857; border-radius: 8px; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.2); opacity: 0; pointer-events: none; transform: translateY(8px); transition: opacity 160ms ease, transform 160ms ease; }
.qr-toast.is-visible { opacity: 1; transform: translateY(0); }
.qr-toast.is-error { background: #b91c1c; }

.qr-display-modal { z-index: 10000; }
.qr-display-modal .modal-content { width: min(440px, calc(100vw - 32px)); padding: 18px 20px; }
.qr-display-heading { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.qr-header-actions { display: flex; align-items: center; gap: 7px; flex: none; }
.qr-display-eyebrow { margin: 0 0 7px; color: #2563eb; font-size: 11px; font-weight: 800; letter-spacing: .12em; }
.qr-display-heading h3 { margin: 0; color: #0f172a; font-size: 21px; font-weight: 750; }
.qr-display-subtitle { margin: 6px 0 0; color: #64748b; font-size: 13px; }
.qr-close-button { display: inline-grid; place-items: center; width: 36px; height: 36px; flex: none; color: #64748b; background: #f1f5f9; border: 0; border-radius: 50%; font-size: 24px; line-height: 1; cursor: pointer; }
.qr-close-button:hover { color: #0f172a; background: #e2e8f0; }
.qr-icon-button { display: inline-grid; place-items: center; width: 36px; height: 36px; padding: 8px; color: #475569; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 50%; cursor: pointer; transition: color 150ms ease, background-color 150ms ease, transform 150ms ease; }
.qr-icon-button svg { width: 18px; height: 18px; fill: none; stroke: currentColor; stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
.qr-icon-button:hover { color: #1d4ed8; background: #eff6ff; transform: scale(1.06); }
.qr-image-frame { display: grid; place-items: center; margin: 12px auto 4px; background: #fff; }
.qr-image-room { width: 300px; max-width: 100%; min-height: 300px; padding: 8px; border: 1px solid #e2e8f0; border-radius: 12px; }
.qr-image-frame canvas, .qr-image-frame img { display: block; max-width: 100%; height: auto; }
.qr-display-actions { display: flex; justify-content: center; gap: 10px; flex-wrap: wrap; margin-top: 18px; }
.qr-secondary-button, .qr-primary-button { min-height: 42px; padding: 10px 16px; border-radius: 8px; font-size: 13px; font-weight: 700; cursor: pointer; }
.qr-secondary-button { color: #334155; background: #fff; border: 1px solid #cbd5e1; }
.qr-secondary-button:hover { background: #f8fafc; }
.qr-primary-button { color: #fff; background: #1d4ed8; border: 1px solid #1d4ed8; }
.qr-primary-button:hover { background: #1e40af; }
.qr-presenter-modal { z-index: 10000; overflow-y: auto; }
.qr-presenter-card { position: relative; display: flex; flex-direction: column; align-items: center; width: min(900px, calc(100vw - 32px)); max-height: calc(100vh - 32px); margin: auto; padding: 26px 28px; overflow-y: auto; color: #0f172a; background: #fff; border-radius: 18px; box-shadow: 0 24px 72px rgba(15, 23, 42, .25); text-align: center; }
.qr-presenter-info { width: 100%; padding: 0 40px; }
.qr-presenter-info h2 { margin: 0; color: #0f172a; font-size: clamp(22px, 3vw, 34px); font-weight: 800; }
.qr-presenter-room { margin: 8px 0 0; color: #334155; font-size: clamp(16px, 2vw, 22px); font-weight: 700; }
.qr-presenter-time { margin: 5px 0 0; color: #2563eb; font-size: clamp(15px, 2vw, 20px); font-weight: 700; }
.qr-image-presenter { width: min(560px, 38vh, calc(100vw - 64px)); height: min(560px, 38vh, calc(100vw - 64px)); padding: 10px; border: 1px solid #e2e8f0; border-radius: 14px; }
.qr-presenter-hint { margin: 0; color: #64748b; font-size: 14px; }
.qr-presenter-actions { margin-top: 18px; }
.qr-presenter-close { position: absolute; top: 16px; right: 16px; }
.qr-presenter-modal:fullscreen { display: flex !important; align-items: stretch; justify-content: center; padding: 0; background: #fff; backdrop-filter: none; }
.qr-presenter-modal:fullscreen .qr-presenter-card { width: 100%; max-height: none; justify-content: center; padding: 24px; border-radius: 0; box-shadow: none; }
.qr-presenter-modal:fullscreen .qr-image-presenter { width: min(52vh, 75vw, 900px); height: min(52vh, 75vw, 900px); margin: 16px auto; }

@media (max-width: 620px) {
    .qr-display-modal .modal-content { padding: 16px; }
    .qr-display-heading { align-items: center; }
    .qr-header-actions { gap: 5px; }
    .qr-icon-button, .qr-close-button { width: 34px; height: 34px; }
    .qr-presenter-card { padding: 56px 16px 20px; }
    .qr-image-presenter { width: min(76vw, 38vh); height: min(76vw, 38vh); }
}

@media (min-width: 768px) {
    .room-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (min-width: 1024px) {
    .room-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
}

@media (max-width: 767px) {
    .main-content { margin-left: 0; }
    .app-layout:not(.collapsed) .sidebar { transform: translateX(-100%); }
    .app-layout.collapsed .sidebar { transform: translateX(0); }
    .topbar { flex-wrap: wrap; padding: 12px 16px; }
    .topbar-left { flex: 1 1 100%; min-width: 0; }
    .search-box { flex: 1; min-width: 0; width: auto; }
    .topbar-right { justify-content: flex-end; }
    .stats-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
    .filter-wrapper { flex-direction: column; align-items: stretch; gap: 12px; }
    .filter-left { flex-wrap: wrap; }
    .filter-chips { width: 100%; margin-left: 0; overflow-x: auto; }
    .chip { flex: 0 0 auto; }
    .filter-right { display: flex; justify-content: flex-end; }
}

.equipment-availability-filters { display: grid; grid-template-columns: repeat(4, minmax(150px, 1fr)); gap: 12px; margin: 18px 0; }
.equipment-filter-field { display: flex; flex-direction: column; gap: 6px; color: #475569; font-size: 12px; font-weight: 600; }
.equipment-filter-field input { min-width: 0; height: 38px; padding: 0 10px; border: 1px solid #cbd5e1; border-radius: 6px; background: #fff; }

.equipment-status-badge { display: inline-flex; align-items: center; border-radius: 999px; padding: 4px 10px; font-size: 11px; font-weight: 600; }
.equipment-status-badge.available { background: #dcfce7; color: #166534; }
.equipment-status-badge.booked-out { background: #fee2e2; color: #991b1b; }
.equipment-status-badge.maintenance { background: #fef3c7; color: #854d0e; }

@media (max-width: 768px) {
    .booking-tabs { width: 100%; }
    .booking-tab { flex: 1; padding-right: 8px; padding-left: 8px; }
    .booking-calendar-day { min-height: 72px; padding: 4px; }
    .booking-calendar-event { font-size: 9px; }
    .booking-list-row { grid-template-columns: minmax(0, 1fr) auto; gap: 8px 12px; }
    .booking-list-time { grid-column: 1; }
    .booking-list-actions { grid-column: 2; grid-row: 1 / span 2; flex-direction: column; align-items: stretch; }
    .booking-agenda-item { grid-template-columns: 82px minmax(0, 1fr); }
}

/* ==========================================
   4. MODALS BASE & FIGMA BOOKING MODAL
   ========================================== */
.modal {
    position: fixed;
    inset: 0;
    background: rgba(15, 23, 42, 0.55);
    backdrop-filter: blur(4px);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 200;
    padding: 16px;
}

.modal-content {
    background: #ffffff;
    padding: 24px;
    border-radius: 16px;
    width: 100%;
    max-width: 460px;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
}

/* FIGMA CARD DESIGN IN BOOKING MODAL */
.modal-card {
    background: #ffffff;
    border-radius: 20px;
    width: 100%;
    max-width: 580px;
    max-height: 90vh;
    display: flex;
    flex-direction: column;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
    overflow: hidden;
    position: relative;
    z-index: 2;
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px 24px 16px 24px;
    border-bottom: 1px solid #f1f5f9;
}

.eyebrow { font-size: 0.75rem; color: #2563eb; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
.modal-title { font-size: 1.25rem; font-weight: 700; color: #0f172a; margin-top: 2px; }

.icon-button { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 50%; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; cursor: pointer; color: #64748b; }
.icon-button:hover { background: #fee2e2; color: #ef4444; }
.icon { width: 18px; height: 18px; }

.booking-form { display: flex; flex-direction: column; flex: 1; overflow: hidden; }
.booking-form-body { padding: 20px 24px; overflow-y: auto; display: flex; flex-direction: column; gap: 16px; }

.form-field { display: flex; flex-direction: column; gap: 6px; }
.field-label { font-size: 0.82rem; font-weight: 600; color: #334155; }
.text-control, .textarea-control { width: 100%; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 0.88rem; outline: none; transition: border-color 0.2s; }
.text-control:focus, .textarea-control:focus { border-color: #2563eb; }

/* ROOM SELECTOR */
.room-select {
    display: flex; justify-content: space-between; align-items: center; width: 100%; padding: 10px 14px; background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; cursor: pointer; text-align: left;
}
.room-name { font-weight: 600; color: #0f172a; display: block; font-size: 0.9rem; }
.room-meta { font-size: 0.78rem; color: #64748b; }

/* TIME FIELDSET & VI TIME SELECT */
.time-fieldset { border: 1px solid #e2e8f0; border-radius: 12px; padding: 14px; background: #fafafa; }
.time-grid { display: grid; grid-template-columns: 1.2fr 1fr 1fr; gap: 10px; margin-bottom: 12px; }
.mini-label { font-size: 0.75rem; font-weight: 600; color: #64748b; margin-bottom: 4px; display: block; }

.date-picker-wrapper, .time-select-wrapper {
    display: flex; align-items: center; gap: 8px; background: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 8px 10px; position: relative; cursor: pointer;
}
.date-display-text { font-size: 0.85rem; font-weight: 500; color: #0f172a; }
.vi-time-select { border: none; background: transparent; width: 100%; font-size: 0.85rem; outline: none; font-weight: 500; cursor: pointer; }

.availability-button {
    width: 100%; display: flex; align-items: center; justify-content: center; gap: 6px; padding: 8px; background: #eff6ff; border: 1px solid #bfdbfe; color: #1d4ed8; border-radius: 8px; font-size: 0.82rem; font-weight: 600; cursor: pointer;
}
.availability-button:hover { background: #dbeafe; }
.availability-results { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }

/* EQUIPMENT & PARTICIPANTS */
.equipment-borrow-section { border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px; background: #f8fafc; }
.equipment-section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.equipment-section-title { font-weight: 600; font-size: 0.85rem; display: flex; align-items: center; gap: 6px; }
.equipment-badge { background: #e0f2fe; color: #0369a1; font-size: 0.7rem; padding: 2px 6px; border-radius: 4px; }
.equipment-hint { font-size: 0.75rem; color: #64748b; }

.equipment-list-container, .participant-picker-list {
    max-height: 130px; overflow-y: auto; border: 1px solid #cbd5e1; border-radius: 8px; padding: 8px; background: #ffffff; display: flex; flex-direction: column; gap: 6px;
}

/* Ô nhập tên + gmail mời thủ công */
.invite-manual-wrapper {
    position: relative;
    margin-bottom: 8px;
}
.invite-manual-row {
    display: flex;
    gap: 8px;
    align-items: center;
}
.invite-input {
    flex: 1;
    height: 36px;
    padding: 0 10px;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    font-size: 0.82rem;
    color: #1e293b;
    background: #f8fafc;
    outline: none;
    transition: border-color 0.15s;
}
.invite-input:focus {
    border-color: #3b82f6;
    background: #fff;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.1);
}
.invite-add-btn {
    white-space: nowrap;
    height: 36px;
    padding: 0 14px;
    background: #2563eb;
    color: #fff;
    border: none;
    border-radius: 8px;
    font-size: 0.82rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s;
}
.invite-add-btn:hover { background: #1d4ed8; }

/* Dropdown gợi ý autocomplete */
.invite-suggestions {
    position: absolute;
    top: calc(100% + 2px);
    left: 0;
    right: 0;
    z-index: 999;
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    box-shadow: 0 8px 24px -4px rgba(0,0,0,0.12);
    list-style: none;
    padding: 4px 0;
    margin: 0;
    max-height: 200px;
    overflow-y: auto;
}
.invite-suggestions li {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 14px;
    cursor: pointer;
    font-size: 0.83rem;
    color: #1e293b;
    transition: background 0.1s;
}
.invite-suggestions li:hover,
.invite-suggestions li.active {
    background: #eff6ff;
}
.invite-suggestions li .sug-avatar {
    width: 28px; height: 28px;
    border-radius: 50%;
    background: #2563eb;
    color: #fff;
    font-weight: 700;
    font-size: 0.75rem;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
}
.invite-suggestions li .sug-info strong { display: block; font-size: 0.83rem; }
.invite-suggestions li .sug-info span  { font-size: 0.76rem; color: #64748b; }
.invite-suggestions li mark {
    background: #fef08a;
    color: inherit;
    border-radius: 2px;
    padding: 0 1px;
}

/* Danh sách người đã thêm thủ công */
.manual-guest-list {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 6px;
}
.manual-guest-tag {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 10px 3px 10px;
    background: #eff6ff;
    border: 1px solid #bfdbfe;
    border-radius: 999px;
    font-size: 0.78rem;
    color: #1d4ed8;
    font-weight: 500;
}
.manual-guest-tag button {
    background: none;
    border: none;
    cursor: pointer;
    color: #64748b;
    font-size: 0.85rem;
    line-height: 1;
    padding: 0;
    margin-left: 2px;
}
.manual-guest-tag button:hover { color: #ef4444; }

.modal-footer {
    padding: 16px 24px; border-top: 1px solid #f1f5f9; display: flex; justify-content: flex-end; gap: 10px; background: #ffffff;
}
.modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 18px;
}

.modal-actions button {
    min-height: 38px;
    padding: 0 16px;
    border: 1px solid transparent;
    border-radius: 8px;
    font: inherit;
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
    transition: background-color 160ms ease, border-color 160ms ease;
}

.modal-actions .btn-cancel {
    color: #475569;
    background: #ffffff;
    border-color: #cbd5e1;
}

.modal-actions .btn-cancel:hover {
    background: #f8fafc;
    border-color: #94a3b8;
}

.modal-actions .btn-save {
    color: #ffffff;
    background: #2563eb;
    border-color: #2563eb;
}

.modal-actions .btn-save:hover {
    background: #1d4ed8;
    border-color: #1d4ed8;
}
.button { padding: 9px 18px; border-radius: 8px; font-size: 0.85rem; font-weight: 600; cursor: pointer; border: none; }
.button-secondary { background: #f1f5f9; color: #475569; }
.button-secondary:hover { background: #e2e8f0; }
.button-primary { background: #2563eb; color: #ffffff; }
.button-primary:hover { background: #1d4ed8; }

.recurring-row { display: flex; justify-content: space-between; align-items: center; padding: 10px 12px; background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0; }
.recurring-label { font-size: 0.82rem; font-weight: 600; color: #334155; }
.recurring-hint { font-size: 0.72rem; color: #64748b; }
.recurrence-select { width: auto; padding: 4px 8px; font-size: 0.82rem; }

/* ==========================================
   ADMIN TOGGLE SWITCH & EQUIPMENT MODAL STYLES
   ========================================== */
.switch {
    position: relative;
    display: inline-block;
    width: 44px;
    height: 24px;
}

.switch input {
    opacity: 0;
    width: 0;
    height: 0;
}

.slider {
    position: absolute;
    cursor: pointer;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: #cbd5e1;
    transition: .3s;
    border-radius: 24px;
}

.slider:before {
    position: absolute;
    content: "";
    height: 18px;
    width: 18px;
    left: 3px;
    bottom: 3px;
    background-color: white;
    transition: .3s;
    border-radius: 50%;
}

input:checked + .slider {
    background-color: #16a34a;
}

input:checked + .slider:before {
    transform: translateX(20px);
}
/* ==========================================
   SỬA GIAO DIỆN FORM MODAL (THÊM / SỬA PHÒNG & THIẾT BỊ)
   ========================================== */
#roomModal .modal-content,
#equipmentModal .modal-content {
    background: #ffffff;
    padding: 28px;
    border-radius: 16px;
    width: 100%;
    max-width: 480px;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
}

#roomModal h3,
#equipmentModal h3 {
    font-size: 18px;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 20px;
    padding-bottom: 12px;
    border-bottom: 1px solid #f1f5f9;
}

.form-group {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-bottom: 16px;
}

.form-group label {
    font-size: 13px;
    font-weight: 600;
    color: #334155;
}

.form-control {
    width: 100%;
    height: 42px;
    padding: 0 12px;
    font-size: 13.5px;
    color: #0f172a;
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    outline: none;
    box-sizing: border-box;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.form-control:focus {
    border-color: #2563eb;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.form-control::placeholder {
    color: #94a3b8;
}
````

## File: requirements.txt
````
fastapi==0.115.0
fastapi-cli==0.0.32
google-auth==2.56.3
google-api-python-client>=2.150,<3.0
google-genai>=1.0.0
greenlet==3.5.5
h11==0.16.0
httpcore==1.0.9
httptools==0.8.0
httpx==0.28.1
idna==3.18
iniconfig==2.3.0
Jinja2==3.1.6
markdown-it-py==4.2.0
MarkupSafe==3.0.3
mdurl==0.1.2
orjson==3.12.0
packaging==26.3
passlib==1.7.4
pluggy==1.6.0
pyasn1==0.6.4
pyasn1_modules==0.4.2
pycparser==3.0
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
aiomysql==0.2.0
pymysql==1.1.0
pydantic==2.5.3
pydantic-settings==2.1.0
alembic==1.12.1
python-dotenv==1.0.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
openpyxl==3.1.2
reportlab==4.0.7
qrcode==7.4.2
pillow==10.1.0
requests==2.31.0
pytest==8.3.2
````

## File: app/routers/meetings.py
````python
# app/routers/meetings.py
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.meeting import Meeting, MeetingParticipant
from app.models.user import User
from app.schemas.meeting import (
    MeetingCheckInRequest,
    MeetingCheckOutRequest,
    MeetingCreateRequest,
    MeetingParticipationResponse,
    MeetingResponse,
    SuggestTimeRequest,
    SuggestTimeResponse,
)
from app.schemas.room import RoomResponse
from app.services.meeting_service import MeetingService
from app.services.notification_service import send_meeting_invitation_notifications
from app.services.calendar_email_service import request_calendar_access_for_invitees
from app.services.google_calendar_service import (
    delete_google_events_for_meeting,
    sync_user_meetings_to_google,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get(
    "",
    response_model=List[RoomResponse],
    summary="Lấy danh sách phòng họp",
    description="Trả về danh sách các phòng họp đang sẵn sàng cho người dùng chọn.",
)
def list_rooms(db: Session = Depends(get_db)):
    return MeetingService.get_all_active_rooms(db)


@router.post(
    "/book",
    response_model=List[MeetingResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Đặt lịch họp mới (Đơn & Định kỳ)",
    description="Tạo cuộc họp mới hoặc chuỗi lịch định kỳ (bao gồm mượn thiết bị). Hệ thống tự động kiểm tra trùng lịch, tồn kho thiết bị và rollback toàn bộ nếu có xung đột.",
)
def create_meeting(
    payload: MeetingCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. Gọi Service tạo cuộc họp
    created_meetings = MeetingService.create_meeting(
        db=db,
        payload=payload,
        organizer_id=current_user.id,
    )

    if current_user.google_refresh_token and created_meetings:
        background_tasks.add_task(sync_user_meetings_to_google, current_user.id)

    # 2. Gửi thông báo ngầm cho những người được mời tham dự
    # Filter organizer khỏi danh sách — organizer không nhận invitation notification
    if payload.participant_ids and created_meetings:
        first_meeting = created_meetings[0] if isinstance(created_meetings, list) else created_meetings
        start_str = first_meeting.start_time.strftime("%H:%M %d/%m/%Y")
        notify_ids = [pid for pid in payload.participant_ids if pid != current_user.id]
        if notify_ids:
            background_tasks.add_task(
                send_meeting_invitation_notifications,
                db=db,
                participant_ids=notify_ids,
                meeting_title=first_meeting.title,
                start_time_str=start_str,
            )
            background_tasks.add_task(
                request_calendar_access_for_invitees,
                user_ids=notify_ids,
                meeting_ids=[meeting.id for meeting in created_meetings],
            )

    return created_meetings


@router.post(
    "/suggest-time",
    response_model=SuggestTimeResponse,
    summary="Gợi ý khung giờ họp khả dụng",
    description="Tìm kiếm khung giờ họp phù hợp dựa trên danh sách người tham gia và phòng họp.",
)
def suggest_time(
    payload: SuggestTimeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return MeetingService.suggest_time(db=db, payload=payload)


@router.post("/{meeting_id}/check-in", response_model=MeetingResponse)
def check_in_meeting(
    meeting_id: int,
    payload: MeetingCheckInRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return MeetingService.check_in_meeting(db, meeting_id, payload.qr_token, current_user)


@router.post("/{meeting_id}/check-out", response_model=MeetingResponse)
def check_out_meeting(
    meeting_id: int,
    payload: MeetingCheckOutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return MeetingService.check_out_meeting(db, meeting_id, payload.qr_token, current_user)


@router.get(
    "/",
    response_model=List[MeetingResponse],
    summary="Lấy danh sách các cuộc họp",
    description="Lấy danh sách cuộc họp có hỗ trợ lọc theo phòng họp và khoảng thời gian.",
)
def get_meetings(
    room_id: Optional[int] = Query(None, description="Lọc theo phòng"),
    start_date: Optional[datetime] = Query(None, description="Lọc từ ngày"),
    end_date: Optional[datetime] = Query(None, description="Lọc đến ngày"),
    db: Session = Depends(get_db),
):
    query = db.query(Meeting).filter(
        Meeting.status.notin_(["CANCELLED", "canceled", "CANCELLED_NO_SHOW"])
    )

    if room_id:
        query = query.filter(Meeting.room_id == room_id)
    if start_date:
        query = query.filter(Meeting.start_time >= start_date)
    if end_date:
        query = query.filter(Meeting.end_time <= end_date)

    try:
        return query.all()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database error while listing meetings")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Không thể tải danh sách cuộc họp do lỗi cơ sở dữ liệu. "
            "Vui lòng kiểm tra schema/migration.",
        ) from exc


@router.get(
    "/mine",
    summary="Lịch họp của người dùng hiện tại",
    description="Trả về cuộc họp do người dùng chủ trì hoặc được mời, kèm trạng thái phản hồi của từng khách mời.",
)
def get_my_meetings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        meetings = (
            db.query(Meeting)
            .outerjoin(MeetingParticipant, MeetingParticipant.meeting_id == Meeting.id)
            .filter(
                (Meeting.organizer_id == current_user.id)
                | (MeetingParticipant.user_id == current_user.id)
            )
            .filter(
                Meeting.status.notin_(
                    ["CANCELLED", "canceled", "cancelled", "CANCELLED_NO_SHOW"]
                )
            )
            .distinct()
            .order_by(Meeting.start_time)
            .all()
        )

        results = []
        for meeting in meetings:
            item = MeetingResponse.model_validate(meeting).model_dump(mode="json")
            item["is_organizer"] = meeting.organizer_id == current_user.id
            item["organizer_name"] = (
                meeting.organizer.full_name or meeting.organizer.username
                if meeting.organizer
                else "Người tổ chức"
            )
            item["room_name"] = meeting.room.name if meeting.room else None
            item["my_response_status"] = next(
                (
                    participant.response_status
                    for participant in meeting.participants
                    if participant.user_id == current_user.id
                ),
                None,
            )
            item["participants"] = [
                {
                    "user_id": participant.user_id,
                    "name": (
                        participant.user.full_name or participant.user.username
                        if participant.user
                        else "Người tham dự"
                    ),
                    "email": participant.user.email if participant.user else None,
                    "response_status": participant.response_status,
                }
                for participant in meeting.participants
            ]
            results.append(item)
        return results
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database error while loading meetings for user_id=%s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Không thể tải lịch họp do lỗi cơ sở dữ liệu. "
            "Vui lòng kiểm tra schema/migration của meeting_participants.",
        ) from exc


@router.patch(
    "/{meeting_id}/response",
    summary="Phản hồi lời mời họp",
    description="Cho phép người được mời xác nhận tham gia hoặc từ chối; không cấp quyền hủy cuộc họp.",
)
def respond_to_meeting_invitation(
    meeting_id: int,
    payload: MeetingParticipationResponse,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        participant = (
            db.query(MeetingParticipant)
            .filter(
                MeetingParticipant.meeting_id == meeting_id,
                MeetingParticipant.user_id == current_user.id,
            )
            .first()
        )
        if participant is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy lời mời họp.")
        participant.response_status = payload.response_status
        db.commit()
        return {"meeting_id": meeting_id, "response_status": participant.response_status}
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception(
            "Database error while saving RSVP for meeting_id=%s user_id=%s",
            meeting_id,
            current_user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Không thể lưu phản hồi do lỗi cơ sở dữ liệu. "
            "Vui lòng kiểm tra schema/migration của meeting_participants.",
        ) from exc


@router.get(
    "/history",
    response_model=List[MeetingResponse],
    summary="Lịch sử cuộc họp",
    description="Chỉ trả về cuộc họp đã kết thúc mà người dùng tham gia (organizer hoặc participant), sắp xếp end_time giảm dần.",
)
def get_meeting_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.utcnow()

    participant_meeting_ids = (
        db.query(MeetingParticipant.meeting_id)
        .filter(MeetingParticipant.user_id == current_user.id)
        .subquery()
    )

    query = (
        db.query(Meeting)
        .filter(
            Meeting.end_time < now,
            Meeting.status.notin_(["CANCELLED", "canceled", "CANCELLED_NO_SHOW"]),
            (
                (Meeting.organizer_id == current_user.id)
                | Meeting.id.in_(participant_meeting_ids)
            ),
        )
        .distinct()
        .order_by(Meeting.end_time.desc())
    )

    try:
        return query.all()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database error while loading meeting history for user_id=%s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Không thể tải lịch sử cuộc họp do lỗi cơ sở dữ liệu. "
            "Vui lòng kiểm tra schema/migration.",
        ) from exc


@router.patch(
    "/{meeting_id}/cancel",
    response_model=MeetingResponse,
    status_code=status.HTTP_200_OK,
    summary="Hủy cuộc họp",
    description="Hủy cuộc họp theo ID. Chỉ người tổ chức (organizer) hoặc admin mới có quyền hủy.",
)
def cancel_meeting(
    meeting_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    meeting = MeetingService.cancel_meeting(db, meeting_id, current_user)
    background_tasks.add_task(delete_google_events_for_meeting, meeting.id)
    return meeting


@router.delete(
    "/{meeting_id}",
    response_model=MeetingResponse,
    status_code=status.HTTP_200_OK,
    summary="Hủy cuộc họp (Endpoint tương thích)",
    description="Endpoint tương thích ngược hỗ trợ hủy cuộc họp qua phương thức DELETE.",
)
def cancel_meeting_legacy(
    meeting_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    meeting = MeetingService.cancel_meeting(db, meeting_id, current_user)
    background_tasks.add_task(delete_google_events_for_meeting, meeting.id)
    return meeting
````

## File: frontend/dashboard.html
````html
<!DOCTYPE html>
<html lang="vi">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RoomSync - Quản Lý Đặt Phòng Họp</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="css/style.css?v=15">
    <link rel="stylesheet" href="css/booking.css?v=3">
    <link rel="stylesheet" href="css/create-meeting.css?v=1">
</head>

<body>
    <div class="app-layout" id="appLayout">
        <!-- SIDEBAR -->
        <aside class="sidebar" id="sidebar">
            <div class="sidebar-brand" onclick="switchToOverview()" title="Quay về Trang chủ">
                <span class="logo-icon">RS</span>
                <span class="brand-name">RoomSync</span>
            </div>

            <nav class="nav-menu">
                <a href="#" class="nav-item active" id="navOverview" onclick="switchMainTab('overview', this)">
                    <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="3" y="3" width="7" height="7"></rect>
                        <rect x="14" y="3" width="7" height="7"></rect>
                        <rect x="14" y="14" width="7" height="7"></rect>
                        <rect x="3" y="14" width="7" height="7"></rect>
                    </svg>
                    <span class="nav-text">Tổng quan</span>
                </a>
                <a href="#" class="nav-item" id="navRooms" onclick="switchMainTab('rooms', this)">
                    <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M3 21h18M3 7v14M21 7v14M6 3h12a2 2 0 0 1 2 2v2H4V5a2 2 0 0 1 2-2z"></path>
                    </svg>
                    <span class="nav-text">Phòng họp</span>
                </a>
                <a href="#" class="nav-item" id="navEquipments" onclick="switchMainTab('equipments', this)">
                    <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="4" y="4" width="16" height="16" rx="2"></rect>
                        <path d="M9 9h6v6H9zM9 2v2m6-2v2M9 20v2m6-2v2M2 9h2m-2 6h2m16-6h2m-2 6h2"></path>
                    </svg>
                    <span class="nav-text">Thiết bị</span>
                </a>
                <a href="#" class="nav-item" id="navMyBookings" onclick="switchMainTab('my-bookings', this)">
                    <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                        <line x1="16" y1="2" x2="16" y2="6"></line>
                        <line x1="8" y1="2" x2="8" y2="6"></line>
                        <line x1="3" y1="10" x2="21" y2="10"></line>
                    </svg>
                    <span class="nav-text">Đặt lịch của tôi</span>
                </a>
                <!-- TAB BÁO CÁO TRÊN NAVBAR -->
                <a href="#" class="nav-item" id="navReport" onclick="switchMainTab('report', this)">
                    <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M18 20V10M12 20V4M6 20v-6"></path>
                    </svg>
                    <span class="nav-text">Báo cáo sử dụng</span>
                </a>
                <a href="#" class="nav-item" id="navSettings" onclick="switchMainTab('settings', this)">
                    <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="3"></circle>
                        <path
                            d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z">
                        </path>
                    </svg>
                    <span class="nav-text">Cài đặt</span>
                </a>
            </nav>

            <div class="sidebar-user" onclick="navigateToSettings()" title="Cài đặt tài khoản">
                <div class="user-avatar" id="avatarText">N</div>
                <div class="user-info">
                    <span class="user-name" id="userNameDisplay">Nguyễn Minh Tuấn</span>
                    <span class="user-role" id="userRoleBadge">Quản trị viên</span>
                </div>
            </div>
        </aside>

        <!-- MAIN CONTENT -->
        <main class="main-content" id="mainContent">
            <!-- TOPBAR -->
            <header class="topbar">
                <div class="topbar-left">
                    <button class="btn-toggle-menu" onclick="toggleSidebar()" title="Ẩn / Hiện Menu">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                            stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <line x1="3" y1="12" x2="21" y2="12"></line>
                            <line x1="3" y1="6" x2="21" y2="6"></line>
                            <line x1="3" y1="18" x2="21" y2="18"></line>
                        </svg>
                    </button>

                    <div class="search-box" id="topbarSearchContainer">
                        <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="11" cy="11" r="8"></circle>
                            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                        </svg>
                        <input type="text" id="searchInput" placeholder="Tìm kiếm phòng họp, tầng, tiện ích..."
                            oninput="handleSearch()">
                    </div>
                </div>

                <div class="topbar-right">
                    <button type="button" class="cm-top-create" onclick="openCreateMeeting()">Tạo cuộc họp</button>
                    <div class="notification-wrapper">
                        <button class="icon-btn" id="notificationBellBtn" onclick="toggleNotificationPopup()"
                            title="Thông báo">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                                stroke-width="2">
                                <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
                                <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
                            </svg>
                            <span id="notificationDot" class="notification-dot" style="display: none;"></span>
                        </button>
                        <div id="notificationPopup" class="notification-popup" style="display: none;">
                            <h4>Thông báo mới</h4>
                            <ul>
                                <li>📌 Lịch họp Phòng Hội Đồng bắt đầu sau 15 phút.</li>
                                <li>✅ Bạn đã đặt thành công Phòng Sáng Tạo.</li>
                            </ul>
                        </div>
                    </div>

                    <div class="user-profile-header" onclick="navigateToSettings()" title="Bấm để vào Cài đặt">
                        <div class="header-avatar" id="headerAvatarText">N</div>
                    </div>
                </div>
            </header>

            <div class="content-body">
                <!-- VIEW 1: TỔNG QUAN -->
                <div id="viewOverview" class="tab-view">
                    <div class="hero-banner-overview">
                        <div class="hero-overlay"></div>
                        <div class="hero-content">
                            <span class="hero-badge">Hệ thống Quản lý Doanh nghiệp</span>
                            <h2>RS-RoomSync — Đặt Lịch Phòng Họp Trực Tuyến Thông Minh</h2>
                            <p>Giải pháp quản lý không gian họp hiện đại, tối ưu hóa công suất làm việc, giúp nhóm dự án
                                kết nối dễ dàng và nâng cao hiệu suất làm việc doanh nghiệp.</p>
                            <div class="hero-actions">
                                <button class="btn-hero-primary" onclick="openCreateMeeting()">Tạo cuộc họp</button>
                                <button class="btn-hero-secondary"
                                    onclick="alert('Tính năng hướng dẫn đang được cập nhật!')">Xem hướng dẫn</button>
                            </div>
                        </div>
                    </div>

                    <div class="page-header" id="roomsSection">
                        <div>
                            <h2>Phòng họp hiện có</h2>
                            <p class="subtitle" id="currentDateText">Đang tải...</p>
                        </div>
                        <button id="addRoomBtnOverview" class="btn-add-room" onclick="openRoomModal()"
                            style="display: none;">
                            + Thêm phòng họp
                        </button>
                    </div>

                    <div class="stats-grid">
                        <div class="stat-card">
                            <span class="stat-title">Tổng phòng họp</span>
                            <div class="stat-value" id="statTotal">0</div>
                            <span class="stat-sub text-gray">+2 so với tháng trước</span>
                        </div>
                        <div class="stat-card">
                            <span class="stat-title">Đang sử dụng</span>
                            <div class="stat-value text-orange" id="statInUse">0</div>
                            <span class="stat-sub text-orange" id="statCapacityText">0% công suất</span>
                        </div>
                        <div class="stat-card">
                            <span class="stat-title">Còn trống hôm nay</span>
                            <div class="stat-value text-green" id="statAvailable">0</div>
                            <span class="stat-sub text-gray" id="statRatioText">trong 0 phòng</span>
                        </div>
                        <div class="stat-card">
                            <span class="stat-title">Lượt đặt trong tuần</span>
                            <div class="stat-value text-purple" id="statBookings">142</div>
                            <span class="stat-sub text-gray">↑ 12% so với tuần trước</span>
                        </div>
                    </div>

                    <div class="filter-wrapper">
                        <div class="filter-left">
                            <button class="btn-filter-date" onclick="filterToday()">📅 Hôm nay — <span
                                    id="filterDateLabel">26/09/2026</span></button>
                            <select class="select-capacity" id="capacitySelect" onchange="applyFilters()">
                                <option value="all">Sức chứa ˅</option>
                                <option value="small">Nhỏ (1 - 5 người)</option>
                                <option value="medium">Vừa (6 - 12 người)</option>
                                <option value="large">Lớn (15+ người)</option>
                            </select>
                            <div class="filter-chips">
                                <button class="chip active" onclick="setFilter('all', this)">Tất cả</button>
                                <button class="chip" onclick="setFilter('Màn hình', this)">Màn hình</button>
                                <button class="chip" onclick="setFilter('Wifi', this)">Wifi</button>
                                <button class="chip" onclick="setFilter('Video', this)">Video</button>
                                <button class="chip" onclick="setFilter('Đồ uống', this)">Đồ uống</button>
                            </div>
                        </div>
                        <div class="filter-right">
                            <span class="status-summary"><strong id="summaryAvailable">0</strong> còn trống</span>
                            <span class="status-summary"><strong id="summaryInUse">0</strong> đã đặt</span>
                        </div>
                    </div>

                    <div class="room-grid" id="roomGridOverview"></div>
                </div>

                <!-- VIEW 2: PHÒNG HỌP -->
                <div id="viewRooms" class="tab-view" style="display: none;">
                    <div class="hero-banner-rooms">
                        <div class="hero-overlay"></div>
                        <div class="hero-content">
                            <span class="hero-badge">Không gian làm việc</span>
                            <h2>Danh Mục & Không Gian Phòng Họp</h2>
                            <p>Khám phá hệ thống phòng họp được trang bị đầy đủ thiết bị công nghệ hiện đại.</p>
                        </div>
                    </div>

                    <div class="page-header">
                        <h2>Tất cả phòng họp</h2>
                        <button id="addRoomBtnRooms" class="btn-add-room" onclick="openRoomModal()"
                            style="display: none;">
                            + Thêm phòng họp
                        </button>
                    </div>

                    <div class="room-grid" id="roomGridRooms"></div>
                </div>

                <!-- VIEW 3: TRẠNG THÁI THIẾT BỊ -->
                <div id="viewEquipments" class="tab-view" style="display: none;">
                    <div class="page-header">
                        <div>
                            <h2>Trạng thái và khả dụng thiết bị</h2>
                            <p class="subtitle">Số lượng khả dụng được tính theo khung thời gian đã chọn.</p>
                        </div>
                        <button id="addEquipmentBtn" class="btn-add-room" onclick="openEquipmentModal()"
                            style="display: none;">
                            + Thêm thiết bị mới
                        </button>
                    </div>
                    <div class="equipment-availability-filters">
                        <label class="equipment-filter-field">
                            <span>Bắt đầu</span>
                            <input id="equipmentStartTime" type="datetime-local"
                                onchange="fetchEquipmentAvailability()">
                        </label>
                        <label class="equipment-filter-field">
                            <span>Kết thúc</span>
                            <input id="equipmentEndTime" type="datetime-local" onchange="fetchEquipmentAvailability()">
                        </label>
                        <label class="equipment-filter-field">
                            <span>Phân loại</span>
                            <input id="equipmentCategoryFilter" type="search" placeholder="Tất cả phân loại"
                                oninput="scheduleEquipmentAvailabilityFetch()">
                        </label>
                        <label class="equipment-filter-field">
                            <span>Tìm thiết bị</span>
                            <input id="equipmentSearchFilter" type="search" placeholder="Tên hoặc mã thiết bị"
                                oninput="scheduleEquipmentAvailabilityFetch()">
                        </label>
                    </div>
                    <div class="table-card equipment-availability-table-wrap">
                        <table class="data-table equipment-availability-table">
                            <thead>
                                <tr>
                                    <th>Mã</th>
                                    <th>Tên</th>
                                    <th>Phân loại</th>
                                    <th>Tổng số</th>
                                    <th>Đã đặt</th>
                                    <th>Khả dụng</th>
                                    <th>Trạng thái</th>
                                </tr>
                            </thead>
                            <tbody id="equipmentAvailabilityTableBody">
                                <tr>
                                    <td colspan="7" class="equipment-table-message">Đang tải thiết bị...</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>

                    <!-- BẢNG DỮ LIỆU ADMIN (ADMIN TABLE) -->
                    <div id="adminEquipmentSection" style="display: none; margin-top: 28px;">
                        <div class="page-header" style="margin-bottom: 14px;">
                            <div>
                                <h3 style="font-size: 1.1rem; font-weight: 700; color: #0f172a;">Bảng Quản Lý Thiết Bị
                                    (Admin Table)</h3>
                                <p class="subtitle">Hiển thị toàn bộ thiết bị (gồm active và inactive), hỗ trợ toggle
                                    Bật/Tắt và Chỉnh sửa / Xóa.</p>
                            </div>
                        </div>
                        <div class="table-card equipment-availability-table-wrap">
                            <table class="data-table equipment-availability-table">
                                <thead>
                                    <tr>
                                        <th>Mã thiết bị</th>
                                        <th>Tên</th>
                                        <th>Phân loại</th>
                                        <th>Số lượng tổng</th>
                                        <th>Trạng thái (Bật/Tắt)</th>
                                        <th>Hành động</th>
                                    </tr>
                                </thead>
                                <tbody id="adminEquipmentTableBody">
                                    <tr>
                                        <td colspan="6" class="equipment-table-message">Đang tải danh sách Admin...</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- VIEW 4: ĐẶT LỊCH CỦA TÔI -->
                <div id="viewMyBookings" class="tab-view" style="display: none;">
                    <div class="page-header">
                        <h2>Lịch họp đã đặt của tôi</h2>
                    </div>
                    <div class="booking-tabs" role="tablist" aria-label="Các lịch họp của tôi">
                        <button class="booking-tab active" id="bookingTabCalendar" type="button" role="tab"
                            aria-selected="true" aria-controls="bookingPanelCalendar"
                            onclick="switchBookingTab('calendar')">Lịch họp</button>
                        <button class="booking-tab" id="bookingTabMine" type="button" role="tab"
                            aria-selected="false" aria-controls="bookingPanelMine"
                            onclick="switchBookingTab('mine')">Của tôi</button>
                        <button class="booking-tab" id="bookingTabInvited" type="button" role="tab"
                            aria-selected="false" aria-controls="bookingPanelInvited"
                            onclick="switchBookingTab('invited')">Được mời</button>
                    </div>

                    <section id="bookingPanelCalendar" class="booking-panel" role="tabpanel"
                        aria-labelledby="bookingTabCalendar">
                        <div class="booking-calendar-toolbar">
                            <div class="booking-calendar-nav">
                                <button type="button" class="booking-calendar-button" onclick="shiftBookingCalendar(-1)"
                                    aria-label="Khoảng thời gian trước">‹</button>
                                <button type="button" class="booking-calendar-button" onclick="goToBookingCalendarToday()">Hôm nay</button>
                                <button type="button" class="booking-calendar-button" onclick="shiftBookingCalendar(1)"
                                    aria-label="Khoảng thời gian sau">›</button>
                                <h3 id="bookingCalendarTitle" class="booking-calendar-title"></h3>
                            </div>
                            <div class="booking-calendar-views" role="group" aria-label="Chế độ xem lịch">
                                <button type="button" data-calendar-view="month" class="active"
                                    onclick="setBookingCalendarView('month')">Tháng</button>
                                <button type="button" data-calendar-view="week"
                                    onclick="setBookingCalendarView('week')">Tuần</button>
                                <button type="button" data-calendar-view="day"
                                    onclick="setBookingCalendarView('day')">Ngày</button>
                            </div>
                        </div>
                        <div id="bookingCalendarGrid" class="booking-calendar-grid"></div>
                        <div class="booking-day-agenda">
                            <h3 id="bookingAgendaTitle">Lịch trong ngày</h3>
                            <div id="bookingDayAgenda"></div>
                        </div>
                    </section>

                    <section id="bookingPanelMine" class="booking-panel" role="tabpanel"
                        aria-labelledby="bookingTabMine" hidden>
                        <div id="myBookingsTableBody" class="booking-list"></div>
                    </section>

                    <section id="bookingPanelInvited" class="booking-panel" role="tabpanel"
                        aria-labelledby="bookingTabInvited" hidden>
                        <div id="invitedBookingsList" class="booking-list"></div>
                    </section>
                </div>

                <!-- VIEW 5: BÁO CÁO SỬ DỤNG PHÒNG HỌP (TAB BÁO CÁO CHÍNH THỨC) -->
                <div id="viewReport" class="tab-view" style="display: none;">
                    <div class="page-header">
                        <h2>
                            <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                                stroke-width="2">
                                <line x1="18" y1="20" x2="18" y2="10"></line>
                                <line x1="12" y1="20" x2="12" y2="4"></line>
                                <line x1="6" y1="20" x2="6" y2="14"></line>
                                <line x1="3" y1="20" x2="21" y2="20"></line>
                            </svg>
                            Báo cáo & Thống kê Sử dụng Phòng họp
                        </h2>
                        <p class="subtitle">Cung cấp dữ liệu phân tích tỷ lệ lấp đầy và tổng số giờ họp của từng phòng.
                        </p>
                    </div>

                    <!-- Bộ lọc báo cáo -->
                    <div class="bg-white p-4 rounded-lg shadow mb-6 flex flex-wrap gap-4 items-end"
                        style="background: #fff; padding: 16px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 24px; display: flex; gap: 16px; align-items: flex-end;">
                        <div>
                            <label
                                style="display: block; font-size: 0.85rem; font-weight: 600; color: #475569; margin-bottom: 6px;">Từ
                                ngày:</label>
                            <input type="datetime-local" id="reportStartDate"
                                style="border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 12px; font-size: 0.9rem;">
                        </div>
                        <div>
                            <label
                                style="display: block; font-size: 0.85rem; font-weight: 600; color: #475569; margin-bottom: 6px;">Đến
                                ngày:</label>
                            <input type="datetime-local" id="reportEndDate"
                                style="border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 12px; font-size: 0.9rem;">
                        </div>
                        <div>
                            <label
                                style="display: block; font-size: 0.85rem; font-weight: 600; color: #475569; margin-bottom: 6px;">Phòng
                                họp:</label>
                            <select id="reportRoomIdSelect"
                                style="border: 1px solid #cbd5e1; border-radius: 6px; padding: 8px 12px; font-size: 0.9rem; background: #fff;">
                                <option value="">Tất cả các phòng</option>
                            </select>
                        </div>
                        <button onclick="fetchRoomUsageReport()"
                            style="background: #2563eb; color: #fff; border: none; padding: 9px 16px; border-radius: 6px; font-weight: 600; cursor: pointer;">
                            Xem Báo Cáo
                        </button>
                    </div>

                    <!-- Khối Tổng quan (Summary Cards) -->
                    <div class="stats-grid" style="margin-bottom: 24px;">
                        <div class="stat-card">
                            <span class="stat-title">Tổng số phòng</span>
                            <div class="stat-value" id="sumTotalRooms">-</div>
                        </div>
                        <div class="stat-card">
                            <span class="stat-title">Tổng số cuộc họp</span>
                            <div class="stat-value text-green" id="sumTotalMeetings">-</div>
                        </div>
                        <div class="stat-card">
                            <span class="stat-title">Tổng số giờ họp</span>
                            <div class="stat-value text-orange" id="sumTotalHours">-</div>
                        </div>
                        <div class="stat-card">
                            <span class="stat-title">Tỷ lệ lấp đầy TB</span>
                            <div class="stat-value text-purple" id="sumAvgOccupancy">-</div>
                        </div>
                    </div>

                    <!-- Bảng chi tiết -->
                    <div class="table-card">
                        <div style="padding: 16px; border-bottom: 1px solid #e2e8f0; font-weight: 700; color: #1e293b;">
                            Chi tiết theo từng phòng họp</div>
                        <div class="table-scroll">
                            <table class="data-table">
                                <thead>
                                    <tr>
                                        <th>ID</th>
                                        <th>Tên phòng</th>
                                        <th>Số cuộc họp</th>
                                        <th>Tổng số giờ</th>
                                        <th>Tỷ lệ lấp đầy (%)</th>
                                    </tr>
                                </thead>
                                <tbody id="roomDetailsTableBody">
                                    <tr>
                                        <td colspan="5" style="text-align: center; color: #94a3b8; padding: 24px;">Chưa
                                            có dữ liệu. Bấm "Xem Báo Cáo" để tải.</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- VIEW 6: CÀI ĐẶT -->
                <div id="viewSettings" class="tab-view max-w-4xl mx-auto py-6 px-4" style="display: none;">
                    <!-- Tiêu đề trang -->
                    <div class="mb-6">
                        <h1 class="text-2xl font-bold text-gray-900 tracking-tight">Cài đặt tài khoản</h1>
                        <p class="text-sm text-gray-500 mt-1">Quản lý thông tin cá nhân và bảo mật tài khoản của bạn.
                        </p>
                    </div>

                    <div class="space-y-6">
                        <!-- Thẻ 1: Thông tin hồ sơ -->
                        <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                            <div class="flex items-center gap-4 pb-6 border-b border-gray-100">
                                <div id="settingsAvatar"
                                    class="w-16 h-16 rounded-full bg-[#004CFF] text-white flex items-center justify-center text-2xl font-bold shadow-inner">
                                    Q
                                </div>
                                <div>
                                    <h3 id="settingsName" class="text-lg font-semibold text-gray-900">Quản trị viên</h3>
                                    <p id="settingsRole" class="text-sm text-gray-500">Quản trị viên</p>
                                </div>
                            </div>

                            <!-- Form cập nhật thông tin -->
                            <div class="mt-6 space-y-4">
                                <div>
                                    <label class="block text-sm font-medium text-gray-700 mb-1.5">Họ và tên</label>
                                    <input type="text" id="settingsInputName"
                                        class="w-full px-4 py-2.5 rounded-lg border border-gray-200 text-sm text-gray-900 focus:border-[#004CFF] focus:ring-2 focus:ring-[#004CFF]/20 outline-none transition-all" />
                                </div>

                                <div>
                                    <label class="block text-sm font-medium text-gray-700 mb-1.5">Email liên hệ</label>
                                    <input type="email" id="settingsInputEmail"
                                        class="w-full px-4 py-2.5 rounded-lg border border-gray-200 text-sm text-gray-900 focus:border-[#004CFF] focus:ring-2 focus:ring-[#004CFF]/20 outline-none transition-all" />
                                </div>

                                <div class="pt-2">
                                    <button type="button" onclick="updateUserSettings()"
                                        class="px-5 py-2.5 rounded-lg text-sm font-semibold text-white bg-[#004CFF] hover:bg-[#0038CC] transition-all shadow-sm focus:outline-none focus:ring-4 focus:ring-[#004CFF]/25">
                                        Lưu thay đổi
                                    </button>
                                </div>
                            </div>
                        </div>

                        <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                            <h3 class="text-base font-semibold text-gray-900 mb-1">Google Calendar</h3>
                            <p class="text-sm text-gray-500 mb-4">
                                Kết nối tài khoản Google để tự động đồng bộ cuộc họp và gửi lời mời cho người tham dự.
                            </p>
                            <div class="flex flex-wrap items-center gap-3">
                                <span id="googleCalendarStatus" class="text-sm text-gray-600" role="status"
                                    aria-live="polite">Đang kiểm tra kết nối...</span>
                                <button id="googleCalendarAction" type="button"
                                    class="px-4 py-2 rounded-lg text-sm font-medium text-white bg-[#004CFF] hover:bg-[#0038CC] transition-colors"
                                    onclick="handleGoogleCalendarAction()" disabled>
                                    Kết nối ngay
                                </button>
                            </div>
                        </div>

                        <!-- Thẻ 2: Phiên đăng nhập & Bảo mật -->
                        <div class="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
                            <h3 class="text-base font-semibold text-gray-900 mb-1">Phiên đăng nhập</h3>
                            <p class="text-sm text-gray-500 mb-4">Quản lý trạng thái kết nối của bạn trên hệ thống
                                RoomSync.</p>

                            <div class="pt-4 border-t border-gray-100 flex items-center justify-between">
                                <div>
                                    <span class="text-sm font-medium text-gray-900 block">Đăng xuất tài khoản</span>
                                    <span class="text-xs text-gray-500">Kết thúc phiên làm việc hiện tại trên thiết bị
                                        này.</span>
                                </div>
                                <button type="button" onclick="logout()"
                                    class="px-4 py-2 rounded-lg text-sm font-medium text-red-600 bg-red-50 hover:bg-red-100 border border-red-200 transition-colors">
                                    Đăng xuất
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    </div>

    <!-- MODAL XEM LỊCH TRÌNH -->
    <div id="scheduleModal" class="modal" style="display: none;">
        <div class="modal-content">
            <h3 id="scheduleRoomTitle">Lịch trình phòng họp</h3>
            <p class="subtitle" style="margin-bottom: 16px;">Danh sách khung giờ hoạt động trong ngày</p>
            <div id="timelineContainer" class="timeline-list"></div>
            <div class="modal-actions" style="margin-top: 20px;">
                <button type="button" onclick="closeScheduleModal()" class="btn-cancel">Đóng</button>
            </div>
        </div>
    </div>

    <div id="qrCheckModal" class="modal qr-check-modal" style="display: none;" role="dialog"
        aria-modal="true" aria-labelledby="qrCheckTitle">
        <div class="modal-content">
            <h3 id="qrCheckTitle">Quét mã QR phòng họp</h3>
            <p id="qrCheckDescription" class="subtitle">Đưa mã QR phòng họp vào khung quét.</p>
            <div id="qrReader" class="qr-reader"></div>
            <label class="qr-manual-label" for="qrTokenInput">Hoặc nhập mã QR</label>
            <input id="qrTokenInput" class="form-control" type="text" autocomplete="off"
                placeholder="Mã QR phòng họp">
            <div class="modal-actions" style="margin-top: 20px;">
                <button type="button" class="btn-cancel" onclick="closeQrCheckModal()">Đóng</button>
                <button type="button" class="btn-primary" onclick="submitQrCheck()">Xác nhận</button>
            </div>
        </div>
    </div>
    <div id="qrToast" class="qr-toast" role="status" aria-live="polite"></div>

    <div id="roomQrModal" class="modal qr-display-modal" style="display: none;" role="dialog"
        aria-modal="true" aria-labelledby="roomQrName">
        <div class="modal-content qr-display-card">
            <div class="qr-display-heading">
                <div>
                    <p class="qr-display-eyebrow">MÃ QR PHÒNG HỌP</p>
                    <h3 id="roomQrName">Phòng họp</h3>
                    <p id="roomQrLocation" class="qr-display-subtitle"></p>
                </div>
                <div class="qr-header-actions">
                    <button class="qr-icon-button" type="button" onclick="copyRoomQrToken()" title="Sao chép Token"
                        aria-label="Sao chép Token">
                        <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                            <rect x="8" y="8" width="12" height="12" rx="2"></rect>
                            <path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"></path>
                        </svg>
                    </button>
                    <button class="qr-icon-button" type="button" onclick="downloadRoomQrImage()" title="Tải ảnh QR"
                        aria-label="Tải ảnh QR">
                        <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                            <path d="M12 3v12m0 0 4-4m-4 4-4-4"></path>
                            <path d="M5 16v4a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-4"></path>
                        </svg>
                    </button>
                    <button class="qr-close-button" type="button" onclick="closeRoomQrModal()" title="Đóng"
                        aria-label="Đóng">×</button>
                </div>
            </div>
            <div id="roomQrImage" class="qr-image-frame qr-image-room"></div>
        </div>
    </div>

    <div id="presenterQRModal" class="modal qr-presenter-modal" style="display: none;" role="dialog"
        aria-modal="true" aria-labelledby="presenterQRTitle">
        <div class="qr-presenter-card">
            <button class="qr-close-button qr-presenter-close" type="button" onclick="closePresenterQrModal()"
                aria-label="Đóng">×</button>
            <div class="qr-presenter-info">
                <p class="qr-display-eyebrow">CHECK-IN CUỘC HỌP</p>
                <h2 id="presenterQRTitle">Cuộc họp</h2>
                <p id="presenterQRRoom" class="qr-presenter-room"></p>
                <p id="presenterQRTime" class="qr-presenter-time"></p>
            </div>
            <div id="presenterQRImage" class="qr-image-frame qr-image-presenter"></div>
            <p class="qr-presenter-hint">Mở camera điện thoại và quét mã để check-in</p>
            <div class="qr-display-actions qr-presenter-actions">
                <button id="presenterQRFullscreenButton" type="button" class="qr-secondary-button"
                    onclick="togglePresenterQrFullscreen()">Phóng to / Fullscreen</button>
                <button type="button" class="qr-primary-button" onclick="copyPresenterQrToken()">Sao chép Token</button>
            </div>
        </div>
    </div>

    <!-- MODAL QUẢN LÝ PHÒNG HỌP (ADMIN) -->
    <div id="roomModal" class="modal" style="display: none;">
        <div class="modal-content">
            <h3 id="modalTitle">Thêm Phòng Họp Mới</h3>
            <form id="roomForm" onsubmit="handleFormSubmit(event)">
                <input type="hidden" id="editRoomId">
                <div class="form-group">
                    <label>Tên phòng họp</label>
                    <input type="text" id="roomName" class="form-control" placeholder="Ví dụ: Phòng Sáng Tạo B"
                        required>
                </div>
                <div class="form-group">
                    <label>Vị trí (Tầng)</label>
                    <input type="text" id="roomLocation" class="form-control" placeholder="Ví dụ: Tầng 3" required>
                </div>
                <div class="form-group">
                    <label>Sức chứa</label>
                    <input type="text" id="roomCapacity" class="form-control" placeholder="Ví dụ: 8-10 người" required>
                </div>
                <div class="form-group">
                    <label>Tiện ích (phân cách bằng dấu phẩy)</label>
                    <input type="text" id="roomAmenities" class="form-control"
                        placeholder="Màn hình, Wifi, Video, Đồ uống">
                </div>
                <div class="modal-actions">
                    <button type="button" onclick="closeRoomModal()" class="btn-cancel">Hủy</button>
                    <button type="submit" class="btn-save">Lưu thông tin</button>
                </div>
            </form>
        </div>
    </div>

    <!-- MODAL QUẢN LÝ THIẾT BỊ (ADMIN - CRUD FORM) -->
    <div id="equipmentModal" class="modal" style="display: none;">
        <div class="modal-content">
            <h3 id="equipmentModalTitle">Thêm Thiết Bị Mới</h3>
            <form id="equipmentForm" onsubmit="handleEquipmentFormSubmit(event)">
                <input type="hidden" id="editEquipmentId">
                <div class="form-group">
                    <label>Tên thiết bị <span style="color:red;">*</span></label>
                    <input type="text" id="equipmentName" class="form-control" placeholder="Ví dụ: Micro không dây Sony"
                        required>
                </div>
                <div class="form-group">
                    <label>Mã thiết bị</label>
                    <input type="text" id="equipmentCode" class="form-control" placeholder="Ví dụ: MIC-001">
                </div>
                <div class="form-group">
                    <label>Phân loại</label>
                    <input type="text" id="equipmentCategory" class="form-control"
                        placeholder="Ví dụ: Audio, Visual, Cable">
                </div>
                <div class="form-group">
                    <label>Số lượng tổng (total_qty) <span style="color:red;">*</span></label>
                    <input type="number" id="equipmentTotalQty" class="form-control" min="1" value="1" required>
                </div>
                <div class="modal-actions">
                    <button type="button" onclick="closeEquipmentModal()" class="btn-cancel">Hủy</button>
                    <button type="submit" class="btn-save">Lưu thông tin</button>
                </div>
            </form>
        </div>
    </div>

    <!-- MODAL TẠO CUỘC HỌP -->
    <div id="createMeetingModal" class="cm-overlay" aria-hidden="true">
        <section id="cmDialog" class="cm-dialog" role="dialog" aria-modal="true" aria-labelledby="cmHeading">
            <header class="cm-header">
                <div>
                    <p class="cm-kicker">Cuộc họp</p>
                    <h1 id="cmHeading">Tạo cuộc họp</h1>
                </div>
                <button class="cm-icon-btn" type="button" aria-label="Đóng" onclick="closeCreateMeeting()">×</button>
            </header>

            <form id="createMeetingForm" class="cm-layout">
                <div class="cm-form-pane">
                    <section class="cm-section">
                        <div class="cm-section-head">
                            <p class="cm-section-title">Thông tin cuộc họp</p>
                            <p class="cm-help">Xác định cuộc họp và nội dung trước khi lựa chọn vị trí hoặc phòng.</p>
                        </div>
                        <label class="cm-label" for="cmTitle">Tên cuộc họp</label>
                        <input id="cmTitle" class="cm-title-input" name="title" maxlength="120"
                            placeholder="Ví dụ: Họp kế hoạch dự án tháng 10" autocomplete="off" />
                        <p id="cmTitleError" class="cm-field-error">Nhập tên cuộc họp trước khi tạo.</p>
                    </section>

                    <section class="cm-section">
                        <label class="cm-label" for="cmDescription">Mô tả ngắn</label>
                        <textarea id="cmDescription" class="cm-textarea" rows="3"
                            placeholder="Nội dung hoặc mục tiêu cuộc họp (không bắt buộc)"></textarea>
                    </section>

                    <section class="cm-section">
                        <div class="cm-section-head">
                            <p class="cm-section-title">Thời gian</p>
                            <p class="cm-help">Chọn ngày và khung giờ diễn ra để xác định thời điểm cuộc họp.</p>
                        </div>
                        <div class="cm-time-grid">
                            <label>
                                <span class="cm-mini-label">Ngày</span>
                                <input id="cmDate" class="cm-input" type="date" />
                            </label>
                            <label>
                                <span class="cm-mini-label">Giờ bắt đầu</span>
                                <select id="cmStart" class="cm-select"></select>
                            </label>
                            <label>
                                <span class="cm-mini-label">Giờ kết thúc</span>
                                <select id="cmEnd" class="cm-select"></select>
                            </label>
                        </div>
                        <div class="cm-seg" role="group" aria-label="Lặp lại">
                            <button type="button" id="cmRecNone" aria-pressed="true"
                                onclick="setRecurrence('none')">Không lặp</button>
                            <button type="button" id="cmRecWeekly" aria-pressed="false"
                                onclick="setRecurrence('weekly')">Hàng tuần</button>
                            <button type="button" id="cmRecMonthly" aria-pressed="false"
                                onclick="setRecurrence('monthly')">Hàng tháng</button>
                        </div>
                        <select id="cmRecurrence" class="cm-select" hidden>
                            <option value="none">Không lặp</option>
                            <option value="weekly">Hàng tuần</option>
                            <option value="monthly">Hàng tháng</option>
                        </select>
                        <div id="cmRecurringExtra" class="cm-recurring-extra">
                            <p id="cmRecurrenceNote" class="cm-help">Lặp vào thứ Hai hàng tuần</p>
                            <label>
                                <span class="cm-mini-label">Kết thúc vào ngày</span>
                                <input id="cmRecurrenceUntil" class="cm-input" type="date" />
                            </label>
                        </div>
                    </section>

                    <section class="cm-section">
                        <div class="cm-inline-actions">
                            <label class="cm-label" for="cmAttendeeSearch">Người tham dự</label>
                            <span id="cmAttendeeCount" class="cm-help">0 người tham dự</span>
                        </div>
                        <div class="cm-attendee-search">
                            <input id="cmAttendeeSearch" class="cm-search" type="search"
                                placeholder="Tìm người tham dự..." autocomplete="off" />
                            <ul id="cmAttendeeSuggest" class="cm-suggest"></ul>
                        </div>
                        <div id="cmAttendeeChips" class="cm-chips"></div>
                        <button type="button" class="cm-link-btn" onclick="addAllTeamMembers()">Thêm tất cả thành viên
                            nhóm</button>
                    </section>

                    <section class="cm-section">
                        <p class="cm-section-title">Vị trí</p>
                        <div class="cm-mode" role="group" aria-label="Hình thức cuộc họp"
                            aria-controls="cmOnlineBox cmResources">
                            <button type="button" id="cmModeOnline" aria-pressed="false"
                                onclick="setCreateMeetingMode('online')">🌐 Online</button>
                            <button type="button" id="cmModeOffline" aria-pressed="true"
                                onclick="setCreateMeetingMode('offline')">🏢 Offline</button>
                        </div>
                        <div id="cmOnlineBox" class="cm-online-box" aria-hidden="true">
                            <label class="cm-label" for="cmMeetingLink">Link cuộc họp</label>
                            <input id="cmMeetingLink" class="cm-input" type="url"
                                name="meeting_link" placeholder="https://meet.google.com/..." autocomplete="url" />
                            <button type="button" class="cm-btn cm-btn-secondary" onclick="generateMeetingLink()">Tạo
                                link</button>
                        </div>

                        <div id="cmResources" class="cm-resources is-open" aria-hidden="false">
                            <p class="cm-section-title">Yêu cầu phòng</p>
                            <div class="cm-fixed-requirements">
                                <span class="cm-label">Thiết bị cố định bắt buộc</span>
                                <p class="cm-help">Chọn các thiết bị/tiện nghi bắt buộc phòng họp phải có.</p>
                                <div id="cmFixedAmenityOptions" class="cm-amenity-options">
                                    <p class="cm-help">Đang tải tiện nghi phòng...</p>
                                </div>
                            </div>

                            <div class="cm-capacity">
                                <div>
                                    <span class="cm-help">Sức chứa cần thiết</span>
                                    <strong id="cmCapacityValue">1 người</strong>
                                    <span id="cmCapacityMin" class="cm-help">Phòng tối thiểu: 1 chỗ</span>
                                </div>
                                <button id="cmSearchRoomsBtn" type="button" class="cm-btn cm-btn-ghost"
                                    onclick="searchMatchingRooms()">Tìm phòng phù hợp</button>
                            </div>
                            <div id="cmRoomConflict" class="cm-alert cm-alert-warn" role="status"></div>
                            <div id="cmRoomResults" class="cm-room-list">
                                <div class="cm-empty">Chọn điều kiện phòng rồi bấm “Tìm phòng phù hợp”.</div>
                            </div>
                        </div>
                    </section>

                    <section id="cmEquipmentSection" class="cm-section" hidden>
                        <p class="cm-section-title">Thiết bị cần mượn thêm</p>
                        <p class="cm-help">Thiết bị di động được đặt riêng sau khi chọn phòng.</p>
                        <div id="cmBorrowEquipment" class="cm-borrow-eq"></div>
                        <div id="cmEquipConflict" class="cm-alert cm-alert-warn" role="status"></div>
                    </section>

                    <div id="cmFormError" class="cm-alert cm-alert-error" role="alert"></div>
                    <div id="cmApiError" class="cm-alert cm-alert-error" role="alert"></div>
                </div>

                <aside class="cm-summary-pane">
                    <div class="cm-summary-card">
                        <h2>Kiểm tra cuộc họp</h2>
                        <ul id="cmSummaryList" class="cm-summary-list"></ul>
                    </div>
                    <div id="cmSummaryStatus" class="cm-status is-ok">✓ Không có xung đột</div>
                    <div class="cm-summary-actions">
                        <button id="cmSubmit" class="cm-btn cm-btn-primary" type="submit">TẠO CUỘC HỌP</button>
                        <button class="cm-btn cm-btn-secondary" type="button"
                            onclick="closeCreateMeeting()">Hủy</button>
                    </div>
                </aside>
            </form>

            <div class="cm-success" role="status">
                <div class="cm-success-icon" aria-hidden="true">✓</div>
                <h2>Đã tạo cuộc họp</h2>
                <p class="cm-help">Cuộc họp đã được lưu. Người tham dự sẽ nhận thông tin theo cấu hình hệ thống.</p>
                <button type="button" class="cm-btn cm-btn-primary" onclick="openCreateMeeting()">Tạo cuộc họp
                    khác</button>
                <button type="button" class="cm-btn cm-btn-secondary" onclick="closeCreateMeeting()">Đóng</button>
            </div>
        </section>
    </div>

    <script src="https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
    <script src="js/app.js?v=15"></script>
    <script src="js/create-meeting.js?v=3"></script>
</body>

</html>
````

## File: app/main.py
````python
import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from fastapi import FastAPI, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, configure_mappers
from sqlalchemy import inspect

# 1. DB & Models
from app.db.session import Base
from app.core.database import engine, get_db, SessionLocal
from app.models.user import User
from app.models.room import Room
from app.models.meeting import Meeting
from app.models.equipment import Equipment, MeetingEquipment, RoomEquipment
from app.models.google_calendar_event import GoogleCalendarEvent

# 2. Routers & Security
from app.routers import auth, equipment, meetings, notifications, rooms, users
from app.core.security import authenticate_user
from app.routers.auth import issue_token
from app.schemas.auth import LoginRequest
from app.routers import auth, equipment, meetings, notifications, rooms, users
from app.routers import reports
from app.services.scheduler import (
    process_auto_checkouts,
    process_meeting_reminders,
    process_no_show_meetings,
)
# 3. Khởi tạo Mapper & Tạo bảng Database
try:
    configure_mappers()
except Exception as e:
    print(f"❌ Lỗi cấu hình ORM Models: {e}")

from sqlalchemy import text

Base.metadata.create_all(bind=engine)

# Tự động cập nhật các cột mới nếu các bảng đã tồn tại từ schema cũ
def _auto_migrate_schema():
    try:
        with engine.begin() as conn:
            if engine.dialect.name == "mysql":
                # 1. Kiểm tra bảng meetings
                cols_meetings = [row[0] for row in conn.execute(text("SHOW COLUMNS FROM meetings")).fetchall()]
                if "meeting_type" not in cols_meetings:
                    conn.execute(text("ALTER TABLE meetings ADD COLUMN meeting_type VARCHAR(20) NOT NULL DEFAULT 'offline' AFTER description"))
                    print("✅ Đã tự động thêm cột 'meeting_type' vào bảng meetings.")
                if "online_link" not in cols_meetings:
                    conn.execute(text("ALTER TABLE meetings ADD COLUMN online_link VARCHAR(500) DEFAULT NULL AFTER meeting_type"))
                    print("✅ Đã tự động thêm cột 'online_link' vào bảng meetings.")

                # Cho phép room_id nhận giá trị NULL (cho cuộc họp trực tuyến)
                room_id_col = conn.execute(text("SHOW COLUMNS FROM meetings LIKE 'room_id'")).fetchone()
                if room_id_col and room_id_col[2] == 'NO':
                    col_type = room_id_col[1]
                    conn.execute(text(f"ALTER TABLE meetings MODIFY COLUMN room_id {col_type} NULL"))
                    print("✅ Đã cập nhật cột 'room_id' cho phép NULL.")

                # 2. Kiểm tra bảng rooms
                cols_rooms = [row[0] for row in conn.execute(text("SHOW COLUMNS FROM rooms")).fetchall()]
                if "amenities" not in cols_rooms:
                    conn.execute(text("ALTER TABLE rooms ADD COLUMN amenities TEXT DEFAULT NULL AFTER description"))
                    print("✅ Đã tự động thêm cột 'amenities' vào bảng rooms.")

            if "meeting_participants" in inspect(conn).get_table_names():
                participant_columns = {
                    column["name"]
                    for column in inspect(conn).get_columns("meeting_participants")
                }
                if "response_status" not in participant_columns:
                    conn.execute(text(
                        "ALTER TABLE meeting_participants "
                        "ADD COLUMN response_status VARCHAR(20) NOT NULL DEFAULT 'pending'"
                    ))
                    print("✅ Đã tự động thêm cột 'response_status' vào bảng meeting_participants.")
    except Exception as e:
        print(f"⚠️ Thông báo cập nhật schema: {e}")

_auto_migrate_schema()


logger = logging.getLogger(__name__)


def _run_meeting_scheduler_cycle() -> None:
    for job in (
        process_meeting_reminders,
        process_no_show_meetings,
        process_auto_checkouts,
    ):
        db = SessionLocal()
        try:
            job(db)
        except Exception:
            db.rollback()
            logger.exception("Meeting scheduler job failed: %s", job.__name__)
        finally:
            db.close()


async def _meeting_scheduler_loop() -> None:
    while True:
        await asyncio.sleep(60)
        await asyncio.to_thread(_run_meeting_scheduler_cycle)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler_task = asyncio.create_task(_meeting_scheduler_loop())
    try:
        yield
    finally:
        scheduler_task.cancel()
        with suppress(asyncio.CancelledError):
            await scheduler_task


# 4. Khởi tạo ứng dụng FastAPI (Phải khởi tạo TRƯỚC khi gán Middleware/Router)
app = FastAPI(title="Meeting Management System API", version="1.0.0", lifespan=lifespan)

# 5. Cấu hình CORS Middleware (Cho phép Frontend port 3000 gọi sang Backend port 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 6. Cấu hình Static Files & Frontend
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
    assets_dir = FRONTEND_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

# 7. Đăng ký API Routers với Prefix chuẩn
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(rooms.router, prefix="/api/rooms", tags=["rooms"])
app.include_router(meetings.router, prefix="/api/meetings", tags=["meetings"])
# Versioned aliases for the QR check-in API.
app.include_router(rooms.router, prefix="/api/v1/rooms", tags=["rooms-v1"])
app.include_router(meetings.router, prefix="/api/v1/meetings", tags=["meetings-v1"])
app.include_router(equipment.router, prefix="/api/equipments", tags=["equipments"])
app.include_router(notifications.router, prefix="/api", tags=["notifications"])
app.include_router(users.router, prefix="/api", tags=["users"])
app.include_router(reports.router, prefix="/api/v1", tags=["reports"])
# 8. Endpoints Đăng nhập & Root
@app.post("/api/login", tags=["auth"])
def legacy_login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.username, payload.password)
    token_response = issue_token(user)
    return {
        **token_response.model_dump(),
        "user_name": token_response.full_name,
    }

@app.get("/", tags=["Root"])
def read_root():
    return {"status": "success", "message": "Meeting Management System API is running"}

@app.get("/dashboard", tags=["Web UI"])
def render_dashboard_page():
    path = FRONTEND_DIR / "dashboard.html"
    return FileResponse(path) if path.exists() else {"error": "Dashboard page not found"}

@app.get("/app", tags=["Web UI"])
def render_index_page():
    path = FRONTEND_DIR / "index.html"
    return FileResponse(path) if path.exists() else {"error": "Application page not found"}
````

## File: frontend/js/app.js
````javascript
/* ==========================================================================
   GLOBAL CONFIGURATION & STATE MANAGEMENT
   ========================================================================== */
const API_BASE = window.API_URL || "http://localhost:8000/api";
let allRooms = [];
let myBookings = [];
let bookingCalendarView = 'month';
let bookingCalendarDate = new Date();
let bookingSelectedDate = new Date();
let selectedRoomId = null;
let equipmentAvailabilityTimer = null;
let googleCalendarOAuthError = null;
let activeQrScanner = null;
let activeQrMeetingId = null;
let activeQrAction = null;
let qrSubmissionInProgress = false;
let qrToastTimer = null;
let activeRoomQrToken = '';
let activePresenterQrToken = '';

// Hàm bổ trợ lấy Auth Token
function getAuthToken() {
    return localStorage.getItem('token') || localStorage.getItem('access_token') || '';
}

// Xử lý Escape HTML an toàn
function escapeHtml(value) {
    if (!value) return '';
    return String(value).replace(/[&<>"']/g, character => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;',
    })[character]);
}

/* ==========================================================================
   INITIALIZATION & DOM LOAD
   ========================================================================== */
document.addEventListener('DOMContentLoaded', async () => {
    const token = getAuthToken();
    const isMeetingPreview = new URLSearchParams(location.search).get('preview') === 'meeting';
    if (!token && !isMeetingPreview) {
        window.location.href = 'index.html';
        return;
    }

    let userName = localStorage.getItem('user_name') || 'Người dùng';
    let userEmail = localStorage.getItem('user_email') || '';
    let role = localStorage.getItem('role') || 'user';

    // Gọi API lấy thông tin chuẩn từ Database trực tiếp
    try {
        const profileRes = await fetch(`${API_BASE}/users/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (profileRes.ok) {
            const userData = await profileRes.json();
            userName = userData.full_name || userName;
            userEmail = userData.email || userEmail;
            localStorage.setItem('user_name', userName);
            localStorage.setItem('user_email', userEmail);
        }
    } catch (e) {
        console.error("Không thể tải thông tin profile từ server", e);
    }

    const isAdmin = role === 'admin';

    // Cập nhật thông tin người dùng trên giao diện
    const nameDisplay = document.getElementById('userNameDisplay');
    if (nameDisplay) nameDisplay.innerText = userName;

    const settingsName = document.getElementById('settingsName');
    if (settingsName) settingsName.innerText = userName;

    const settingsInputName = document.getElementById('settingsInputName');
    if (settingsInputName) settingsInputName.value = userName;

    const settingsInputEmail = document.getElementById('settingsInputEmail');
    if (settingsInputEmail) {
        settingsInputEmail.value = userEmail;
        settingsInputEmail.removeAttribute('readonly'); // Cho phép sửa email
    }
    loadCurrentUserProfile();
    const initial = userName.charAt(0).toUpperCase();
    ['avatarText', 'headerAvatarText', 'settingsAvatar'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.innerText = initial;
    });

    const roleText = isAdmin ? 'Quản trị viên' : 'Nhân viên';
    const roleBadge = document.getElementById('userRoleBadge');
    if (roleBadge) roleBadge.innerText = roleText;

    const settingsRole = document.getElementById('settingsRole');
    if (settingsRole) settingsRole.innerText = roleText;

    // Hiển thị ngày tháng
    const now = new Date();
    const dateStr = `Thứ ${now.getDay() + 1}, ${now.getDate()} tháng ${now.getMonth() + 1} năm ${now.getFullYear()}`;
    const currentDateText = document.getElementById('currentDateText');
    if (currentDateText) currentDateText.innerText = `${dateStr} · Đang hiển thị danh sách phòng`;

    const filterDateLabel = document.getElementById('filterDateLabel');
    if (filterDateLabel) filterDateLabel.innerText = `${now.getDate()}/${now.getMonth() + 1}/${now.getFullYear()}`;

    // Cài đặt thời gian mặc định cho Modal
    setDefaultBookingTimes();

    // Hiển thị nút quản trị nếu là Admin
    if (isAdmin) {
        const btn1 = document.getElementById('addRoomBtnOverview');
        const btn2 = document.getElementById('addRoomBtnRooms');
        const addEqBtn = document.getElementById('addEquipmentBtn');
        const adminEqSection = document.getElementById('adminEquipmentSection');
        if (btn1) btn1.style.display = 'block';
        if (btn2) btn2.style.display = 'block';
        if (addEqBtn) addEqBtn.style.display = 'block';
        if (adminEqSection) adminEqSection.style.display = 'block';
    } else {
        const navReport = document.getElementById('navReport');
        if (navReport) navReport.style.display = 'none';
    }

    // Tải dữ liệu ban đầu
    fetchRooms(isAdmin).then(fetchMyBookings);
    setDefaultEquipmentAvailabilityTimes();
    if (isAdmin) {
        fetchAdminEquipments();
    }

    // Khởi tạo thời gian mặc định cho bộ lọc báo cáo
    const reportEnd = document.getElementById("reportEndDate");
    const reportStart = document.getElementById("reportStartDate");
    if (reportEnd && reportStart) {
        const thirtyDaysAgo = new Date(now.getTime() - (30 * 24 * 60 * 60 * 1000));
        reportEnd.value = now.toISOString().slice(0, 16);
        reportStart.value = thirtyDaysAgo.toISOString().slice(0, 16);
        loadRoomsForReportFilter();
    }

    const callbackQuery = new URLSearchParams(window.location.search);
    if (callbackQuery.has('calendar_connected') || callbackQuery.has('google_error')) {
        googleCalendarOAuthError = callbackQuery.get('google_error');
        const cleanUrl = new URL(window.location.href);
        cleanUrl.searchParams.delete('calendar_connected');
        cleanUrl.searchParams.delete('google_error');
        window.history.replaceState({}, document.title, `${cleanUrl.pathname}${cleanUrl.search}${cleanUrl.hash}`);
        switchMainTab('settings', document.getElementById('navSettings'));
    }
});

/* ==========================================================================
   NAVIGATION & UI CONTROLS
   ========================================================================== */
function toggleSidebar() {
    const layout = document.getElementById('appLayout');
    if (layout) layout.classList.toggle('collapsed');
}

function switchToOverview() {
    const overviewTab = document.getElementById('navOverview');
    switchMainTab('overview', overviewTab);
}

function switchMainTab(tabName, el) {
    document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
    if (el) el.classList.add('active');

    document.querySelectorAll('.tab-view').forEach(view => view.style.display = 'none');

    const searchContainer = document.getElementById('topbarSearchContainer');

    if (tabName === 'overview') {
        const view = document.getElementById('viewOverview');
        if (view) view.style.display = 'block';
        if (searchContainer) searchContainer.style.display = 'flex';
    } else if (tabName === 'rooms') {
        const view = document.getElementById('viewRooms');
        if (view) view.style.display = 'block';
        if (searchContainer) searchContainer.style.display = 'flex';
    } else if (tabName === 'equipments') {
        const view = document.getElementById('viewEquipments');
        if (view) view.style.display = 'block';
        if (searchContainer) searchContainer.style.display = 'none';
        fetchEquipmentAvailability();
        const role = localStorage.getItem('role') || 'user';
        if (role === 'admin') {
            fetchAdminEquipments();
        }
    } else if (tabName === 'my-bookings') {
        const view = document.getElementById('viewMyBookings');
        if (view) view.style.display = 'block';
        if (searchContainer) searchContainer.style.display = 'none';
        fetchMyBookings();
    } else if (tabName === 'report') {
        const view = document.getElementById('viewReport');
        if (view) view.style.display = 'block';
        if (searchContainer) searchContainer.style.display = 'none';
        fetchRoomUsageReport();
    } else if (tabName === 'settings') {
        const view = document.getElementById('viewSettings');
        if (view) view.style.display = 'block';
        if (searchContainer) searchContainer.style.display = 'none';
        loadCurrentUserProfile();
        loadGoogleCalendarStatus();
    }
}

async function loadGoogleCalendarStatus() {
    const statusElement = document.getElementById('googleCalendarStatus');
    const actionButton = document.getElementById('googleCalendarAction');
    if (!statusElement || !actionButton) return;

    actionButton.disabled = true;
    statusElement.textContent = 'Đang kiểm tra kết nối...';
    try {
        const response = await fetch(`${API_BASE}/auth/google/calendar/status`, {
            headers: { Authorization: `Bearer ${getAuthToken()}` },
        });
        if (!response.ok) throw new Error(`Không thể kiểm tra kết nối Google Calendar (${response.status})`);
        const result = await response.json();
        const connected = result.connected === true;
        const oauthErrorMessages = {
            calendar_permission_denied: 'Bạn chưa cấp quyền Google Calendar. Có thể kết nối lại bất cứ lúc nào.',
            oauth_failed: 'Không thể kết nối Google Calendar. Vui lòng thử lại.',
        };
        statusElement.textContent = connected
            ? 'Tài khoản Google Calendar đã được kết nối.'
            : oauthErrorMessages[googleCalendarOAuthError] || 'Chưa kết nối Google Calendar.';
        googleCalendarOAuthError = null;
        actionButton.textContent = connected ? 'Ngắt kết nối' : 'Kết nối ngay';
        actionButton.dataset.connected = String(connected);
        actionButton.disabled = false;
    } catch (error) {
        console.error('Không thể tải trạng thái Google Calendar:', error);
        statusElement.textContent = 'Không thể tải trạng thái Google Calendar. Vui lòng thử lại.';
    }
}

async function handleGoogleCalendarAction() {
    const statusElement = document.getElementById('googleCalendarStatus');
    const actionButton = document.getElementById('googleCalendarAction');
    if (!statusElement || !actionButton) return;

    actionButton.disabled = true;
    try {
        if (actionButton.dataset.connected === 'true') {
            const response = await fetch(`${API_BASE}/auth/google/calendar/disconnect`, {
                method: 'DELETE',
                headers: { Authorization: `Bearer ${getAuthToken()}` },
            });
            if (!response.ok) throw new Error(`Không thể ngắt kết nối Google Calendar (${response.status})`);
            await loadGoogleCalendarStatus();
            return;
        }

        const response = await fetch(`${API_BASE}/auth/google/calendar/authorize`, {
            credentials: 'include',
            headers: { Authorization: `Bearer ${getAuthToken()}` },
        });
        if (!response.ok) throw new Error(`Không thể bắt đầu kết nối Google Calendar (${response.status})`);
        const result = await response.json();
        if (!result.authorization_url) throw new Error('Máy chủ không trả về địa chỉ xác thực Google');
        window.location.assign(result.authorization_url);
    } catch (error) {
        console.error('Không thể cập nhật kết nối Google Calendar:', error);
        statusElement.textContent = error.message || 'Không thể cập nhật kết nối Google Calendar.';
        actionButton.disabled = false;
    }
}

async function loadCurrentUserProfile() {
    const emailInput = document.getElementById('settingsInputEmail');
    if (!emailInput) return;
    emailInput.disabled = false;
    emailInput.readOnly = false;

    let storedUser = {};
    try {
        const parsedUser = JSON.parse(localStorage.getItem('user') || '{}');
        if (parsedUser && typeof parsedUser === 'object') storedUser = parsedUser;
    } catch (error) {
        storedUser = {};
    }

    const getFallbackEmail = user => {
        const cachedEmail = localStorage.getItem('user_email') || storedUser.email || '';
        if (cachedEmail.trim()) return cachedEmail.trim();

        const username = String(
            user?.username || storedUser.username || localStorage.getItem('username') || '',
        ).trim();
        return username ? `${username.toLowerCase()}@congty.com` : '';
    };

    const setEmailValue = email => {
        emailInput.value = email;
        emailInput.defaultValue = email;
    };

    setEmailValue(getFallbackEmail());

    const token = getAuthToken();
    if (!token) return;

    try {
        const response = await fetch(`${API_BASE}/auth/me`, {
            headers: { Authorization: `Bearer ${token}` },
        });
        if (!response.ok) return;

        const user = await response.json();
        const actualEmail = typeof user.email === 'string' ? user.email.trim() : '';
        const email = actualEmail || getFallbackEmail(user);
        setEmailValue(email);
        if (actualEmail) localStorage.setItem('user_email', actualEmail);

        const fullName = user.full_name || user.username;
        if (fullName) {
            localStorage.setItem('user_name', fullName);
            const nameDisplay = document.getElementById('userNameDisplay');
            const settingsName = document.getElementById('settingsName');
            const settingsInputName = document.getElementById('settingsInputName');
            if (nameDisplay) nameDisplay.innerText = fullName;
            if (settingsName) settingsName.innerText = fullName;
            if (settingsInputName) settingsInputName.value = fullName;
        }
    } catch (error) {
        console.warn('Could not load the current user profile:', error);
    }
}

function navigateToSettings() {
    const settingsTab = document.getElementById('navSettings');
    switchMainTab('settings', settingsTab);
}

function scrollToRooms() {
    const elem = document.getElementById('roomsSection');
    if (elem) elem.scrollIntoView({ behavior: 'smooth' });
}

/* ==========================================================================
   UPDATE USER SETTINGS (LƯU THÔNG TIN CÁ NHÂN & EMAIL THẬT)
   ========================================================================== */
async function updateUserSettings() {
    const newName = document.getElementById('settingsInputName')?.value.trim();
    const newEmail = document.getElementById('settingsInputEmail')?.value.trim();
    const token = getAuthToken();

    if (!newEmail || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(newEmail)) {
        alert("Vui lòng nhập địa chỉ email hợp lệ!");
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/users/me`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                full_name: newName,
                email: newEmail
            })
        });

        if (res.ok) {
            const updatedUser = await res.json();

            localStorage.setItem('user_name', updatedUser.full_name || newName);
            localStorage.setItem('user_email', updatedUser.email || newEmail);

            const nameDisplay = document.getElementById('userNameDisplay');
            if (nameDisplay) nameDisplay.innerText = updatedUser.full_name || newName;
            const settingsName = document.getElementById('settingsName');
            if (settingsName) settingsName.innerText = updatedUser.full_name || newName;

            alert("Đã cập nhật thông tin thành công!");
        } else {
            const err = await res.json();
            alert(`Cập nhật thất bại: ${err.detail || 'Lỗi không xác định'}`);
        }
    } catch (error) {
        console.error("Lỗi cập nhật thông tin:", error);
        alert("Không thể kết nối máy chủ để lưu thông tin!");
    }
}

/* ==========================================================================
   NOTIFICATION MANAGEMENT
   ========================================================================== */
async function fetchNotifications() {
    const token = getAuthToken();
    if (!token) return;

    try {
        const res = await fetch(`${API_BASE}/notifications/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (res.ok) {
            const notifications = await res.json();
            renderNotifications(notifications);
        }
    } catch (err) {
        console.error("Lỗi lấy danh sách thông báo:", err);
    }
}

function renderNotifications(notifications) {
    const popup = document.getElementById('notificationPopup');
    if (!popup) return;

    if (!notifications || notifications.length === 0) {
        popup.innerHTML = '<div style="padding: 16px; color: #94a3b8; text-align: center; font-size: 0.85rem;">Không có thông báo nào.</div>';
        updateNotificationDot(0);
        return;
    }

    const unreadCount = notifications.filter(n => !n.is_read).length;
    const popupVisible = popup.style.display !== 'none';
    if (!popupVisible) {
        updateNotificationDot(unreadCount);
    }

    popup.innerHTML = `
        <div style="padding: 12px 16px; font-weight: 600; font-size: 0.9rem; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center;">
            <span>Thông báo</span>
            ${unreadCount > 0 ? `<span style="font-size: 0.75rem; background: #e0e7ff; color: #3730a3; padding: 2px 8px; border-radius: 9999px;">${unreadCount} chưa đọc</span>` : ''}
        </div>
        <div style="max-height: 320px; overflow-y: auto;">
            ${notifications.map(n => `
                <div style="padding: 12px 16px; border-bottom: 1px solid #f1f5f9; background-color: ${n.is_read ? '#ffffff' : '#f0fdf4'}; cursor: pointer;">
                    <div style="font-weight: 600; font-size: 0.85rem; color: #0f172a; margin-bottom: 4px;">${escapeHtml(n.title)}</div>
                    <div style="font-size: 0.8rem; color: #475569; line-height: 1.4;">${escapeHtml(n.content)}</div>
                </div>
            `).join('')}
        </div>
    `;
}

function updateNotificationDot(unreadCount) {
    const dot = document.getElementById('notificationDot');
    if (!dot) return;
    dot.style.display = unreadCount > 0 ? 'block' : 'none';
}

function toggleNotificationPopup() {
    const popup = document.getElementById('notificationPopup');
    if (!popup) return;

    const isHidden = popup.style.display === 'none' || !popup.style.display;
    popup.style.display = isHidden ? 'block' : 'none';

    if (isHidden) {
        updateNotificationDot(0);
        fetchNotifications();
    }
}

document.addEventListener('click', function (e) {
    const wrapper = document.querySelector('.notification-wrapper');
    const popup = document.getElementById('notificationPopup');
    if (!wrapper || !popup) return;
    if (!wrapper.contains(e.target) && popup.style.display !== 'none') {
        popup.style.display = 'none';
    }
});

window.fetchNotifications = fetchNotifications;
window.updateNotificationDot = updateNotificationDot;

/* ==========================================================================
   MANUAL GUEST INVITE
   ========================================================================== */
let _manualGuests = [];

function addManualGuest() {
    const nameInput = document.getElementById('inviteGuestName');
    const emailInput = document.getElementById('inviteGuestEmail');
    if (!nameInput || !emailInput) return;

    const name = nameInput.value.trim();
    const email = emailInput.value.trim();

    if (!name && !email) { nameInput.focus(); return; }
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        emailInput.style.borderColor = '#ef4444';
        emailInput.focus();
        setTimeout(() => emailInput.style.borderColor = '', 1500);
        return;
    }

    if (_manualGuests.find(g => g.email === email)) {
        emailInput.style.borderColor = '#f59e0b';
        setTimeout(() => emailInput.style.borderColor = '', 1500);
        return;
    }

    _manualGuests.push({ name, email });
    nameInput.value = '';
    emailInput.value = '';
    nameInput.focus();
    renderManualGuestList();
}

function removeManualGuest(email) {
    _manualGuests = _manualGuests.filter(g => g.email !== email);
    renderManualGuestList();
}

function renderManualGuestList() {
    const container = document.getElementById('manualGuestList');
    if (!container) return;
    if (_manualGuests.length === 0) { container.innerHTML = ''; return; }
    container.innerHTML = _manualGuests.map(g => `
        <span class="manual-guest-tag" title="${g.email}">
            ${g.name ? `<strong>${escapeHtml(g.name)}</strong>&nbsp;` : ''}
            <span style="opacity:0.75">${escapeHtml(g.email)}</span>
            <button type="button" onclick="removeManualGuest('${g.email}')" title="Xóa">✕</button>
        </span>
    `).join('');
}

function getManualGuests() { return [..._manualGuests]; }
function resetManualGuests() {
    _manualGuests = [];
    renderManualGuestList();
    const nameInput = document.getElementById('inviteGuestName');
    const emailInput = document.getElementById('inviteGuestEmail');
    if (nameInput) nameInput.value = '';
    if (emailInput) emailInput.value = '';
}

window.addManualGuest = addManualGuest;
window.removeManualGuest = removeManualGuest;
window.getManualGuests = getManualGuests;
window.resetManualGuests = resetManualGuests;

/* ==========================================================================
   DATE & TIME FORMATTING UTILITIES
   ========================================================================== */
function formatDateInput(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function formatTimeInput(date) {
    return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
}

function formatDateTimeLocal(date) {
    return `${formatDateInput(date)}T${formatTimeInput(date)}`;
}

function formatVietnameseTimeLabel(hour, minute) {
    const timeStr = `${String(hour).padStart(2, '0')}:${minute}`;
    let period = 'sáng';
    if (hour === 12) period = 'trưa';
    else if (hour > 12 && hour < 18) period = 'chiều';
    else if (hour >= 18) period = 'tối';

    const minText = minute === '00' ? '' : `${minute}`;
    return `${timeStr} (${hour}h${minText} ${period})`;
}

function buildViTimeOptions(selectEl, defaultTimeStr) {
    if (!selectEl) return;
    selectEl.innerHTML = '';

    for (let h = 7; h <= 21; h++) {
        for (let m of ['00', '30']) {
            if (h === 21 && m === '30') continue;
            const valueStr = `${String(h).padStart(2, '0')}:${m}`;
            const opt = document.createElement('option');
            opt.value = valueStr;
            opt.textContent = formatVietnameseTimeLabel(h, m);
            if (defaultTimeStr && valueStr === defaultTimeStr) {
                opt.selected = true;
            }
            selectEl.appendChild(opt);
        }
    }
}

function syncHiddenStartTime(selectEl) {
    const hiddenInput = document.getElementById('startTimeHidden');
    if (hiddenInput && selectEl) {
        hiddenInput.value = selectEl.value;
    }
}

function updateDateDisplay(dateVal) {
    const label = document.getElementById('dateDisplayLabel');
    if (!label || !dateVal) return;
    const [y, m, d] = dateVal.split('-');
    const days = ['CN', 'Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7'];
    const dt = new Date(parseInt(y), parseInt(m) - 1, parseInt(d));
    label.textContent = `${days[dt.getDay()]} ${d}/${m}/${y}`;
}

function setDefaultBookingTimes() {
    const now = new Date();
    let startHour = now.getHours();
    let startMin = now.getMinutes() < 30 ? '30' : '00';
    if (now.getMinutes() >= 30) startHour += 1;

    if (startHour < 7) startHour = 8;
    if (startHour > 20) startHour = 20;

    let endHour = startHour + 1;

    const startTimeStr = `${String(startHour).padStart(2, '0')}:${startMin}`;
    const endTimeStr = `${String(endHour).padStart(2, '0')}:${startMin}`;

    const dateInp = document.getElementById('meetingDateInput');
    if (dateInp) {
        dateInp.value = formatDateInput(now);
        updateDateDisplay(dateInp.value);
    }

    const startSel = document.getElementById('startTimeSelect');
    buildViTimeOptions(startSel, startTimeStr);

    const endSel = document.getElementById('endTimeSelect');
    buildViTimeOptions(endSel, endTimeStr);

    syncHiddenStartTime(startSel);
}

/* ==========================================================================
   ROOM MANAGEMENT & FETCHING
   ========================================================================== */
async function fetchRooms(isAdmin) {
    try {
        const token = getAuthToken();
        const res = await fetch(`${API_BASE}/rooms/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (res.ok) {
            allRooms = await res.json();
            renderRooms(allRooms, isAdmin);
            updateStats(allRooms);
        }
    } catch (err) {
        console.error("Lỗi lấy danh sách phòng:", err);
    }
}

function renderRooms(rooms, isAdmin) {
    const gridRooms = document.getElementById('roomGridRooms');
    renderDashboardRooms(rooms, isAdmin);
    if (!rooms || rooms.length === 0) {
        if (gridRooms) gridRooms.innerHTML = emptyRoomsMessage();
        return;
    }
    if (gridRooms) gridRooms.innerHTML = buildRoomCards(rooms, isAdmin);
}

function renderDashboardRooms(rooms, isAdmin) {
    const gridOverview = document.getElementById('roomGridOverview');
    if (!gridOverview) return;
    if (!rooms || rooms.length === 0) {
        gridOverview.innerHTML = emptyRoomsMessage();
        return;
    }
    gridOverview.innerHTML = buildRoomCards(rooms, isAdmin);
}

function emptyRoomsMessage() {
    return '<p class="text-muted" style="padding: 16px;">Chưa có phòng họp nào trong hệ thống.</p>';
}

function buildRoomCards(rooms, isAdmin) {
    const htmlContent = rooms.map(room => {
        const isAvailable = room.is_available !== false && room.is_active !== false;
        const statusClass = isAvailable ? 'status-green' : 'status-red';
        const statusText = isAvailable ? '• Còn trống' : '• Đã đặt';

        let amenitiesHTML = '';
        if (room.amenities) {
            let amenitiesList = room.amenities;
            if (typeof amenitiesList === 'string') {
                try { amenitiesList = JSON.parse(amenitiesList); }
                catch (e) { amenitiesList = [amenitiesList]; }
            }
            if (Array.isArray(amenitiesList)) {
                amenitiesHTML = amenitiesList.map(a => `<span class="tag">${getAmenityIcon(a)} ${escapeHtml(a)}</span>`).join(' ');
            }
        }

        let adminButtons = '';
        if (isAdmin) {
            adminButtons = `
                <button class="btn-admin-action btn-admin-edit" onclick="openEditModal(${room.id})">Sửa</button>
                <button class="btn-admin-action btn-admin-delete" onclick="deleteRoom(${room.id})">Xóa</button>
            `;
        }

        return `
            <div class="room-card">
                <div class="card-image">
                    <img src="${room.image_url || 'https://images.unsplash.com/photo-1497366216548-37526070297c'}" alt="${escapeHtml(room.name)}">
                    <span class="status-badge ${statusClass} ${isAdmin ? 'has-qr-action' : ''}">${statusText}</span>
                    ${isAdmin ? `<button class="room-qr-icon" type="button" onclick="openRoomQrModal(${room.id})" title="Xem mã QR phòng" aria-label="Xem mã QR phòng ${escapeHtml(room.name)}">
                        <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                            <path d="M3 3h8v8H3zM5.5 5.5v3h3v-3zM13 3h8v8h-8zM15.5 5.5v3h3v-3zM3 13h8v8H3zM5.5 15.5v3h3v-3zM13 13h3v3h-3zM18 13h3v3h-3zM13 18h3v3h-3zM18 18h3v3h-3z" />
                        </svg>
                    </button>` : ''}
                </div>
                <div class="card-body">
                    <h3>${escapeHtml(room.name)}</h3>
                    <p class="location">📍 ${escapeHtml(room.location || 'Tầng 1')} | 👥 ${room.capacity || '10'} người</p>
                    <div class="amenities-tags">${amenitiesHTML}</div>
                    <div class="card-actions">
                        <button class="btn-schedule" onclick="openScheduleModal(${room.id})">Xem lịch</button>
                        <button class="btn-book ${isAvailable ? '' : 'disabled'}" ${isAvailable ? `onclick="openCreateMeeting({ roomId: ${room.id} })"` : 'disabled'}>
                            ${isAvailable ? 'Tạo cuộc họp' : 'Hết chỗ'}
                        </button>
                        ${adminButtons}
                    </div>
                </div>
            </div>
        `;
    }).join('');
    return htmlContent;
}

function updateStats(rooms) {
    const total = rooms.length;
    const availableCount = rooms.filter(r => r.is_available !== false && r.is_active !== false).length;
    const inUseCount = total - availableCount;
    const capacityPercent = total > 0 ? Math.round((inUseCount / total) * 100) : 0;

    const setTxt = (id, val) => { const el = document.getElementById(id); if (el) el.innerText = val; };

    setTxt('statTotal', total);
    setTxt('statAvailable', availableCount);
    setTxt('statInUse', inUseCount);
    setTxt('statCapacityText', `${capacityPercent}% công suất`);
    setTxt('statRatioText', `trong ${total} phòng`);

    setTxt('summaryAvailable', availableCount);
    setTxt('summaryInUse', inUseCount);
}

function getAmenityIcon(name) {
    const lower = (name || '').toLowerCase();
    if (lower.includes('màn hình') || lower.includes('tv')) return '📺';
    if (lower.includes('wifi') || lower.includes('internet')) return '📶';
    if (lower.includes('video') || lower.includes('camera')) return '🎥';
    if (lower.includes('chiếu') || lower.includes('projector')) return '📽️';
    if (lower.includes('mic') || lower.includes('loa')) return '🎙️';
    if (lower.includes('đồ uống') || lower.includes('nước') || lower.includes('trà') || lower.includes('cà phê')) return '☕';
    return '✨';
}

/* ==========================================================================
   BOOKING & SCHEDULE MODALS
   ========================================================================== */
function openScheduleModal(roomId) {
    const room = allRooms.find(r => r.id === roomId);
    if (!room) return;

    const titleEl = document.getElementById('scheduleRoomTitle');
    if (titleEl) titleEl.innerText = `Lịch trình: ${room.name}`;

    const container = document.getElementById('timelineContainer');
    if (container) {
        const isAvail = room.is_available !== false;
        container.innerHTML = `
            <div class="timeline-item"><span>08:00 - 09:30</span><span class="time-free">Còn trống</span></div>
            <div class="timeline-item"><span>10:00 - 11:30</span><span class="${isAvail ? 'time-free' : 'time-busy'}">${isAvail ? 'Còn trống' : 'Đã có cuộc họp'}</span></div>
            <div class="timeline-item"><span>13:30 - 15:00</span><span class="time-free">Còn trống</span></div>
        `;
    }
    const modal = document.getElementById('scheduleModal');
    if (modal) modal.style.display = 'flex';
}

function closeScheduleModal() {
    const modal = document.getElementById('scheduleModal');
    if (modal) modal.style.display = 'none';
}

/* ==========================================================================
   MY BOOKINGS MANAGEMENT
   ========================================================================== */
async function cancelBooking(meetingId) {
    if (!confirm('Bạn có chắc chắn muốn hủy lịch họp này?')) return;
    try {
        const res = await fetch(`${API_BASE}/meetings/${meetingId}`, {
            method: 'DELETE',
            headers: { 'Authorization': 'Bearer ' + getAuthToken() }
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || 'Không thể hủy lịch họp!');
        }
        alert('Đã hủy lịch họp!');
        await fetchMyBookings();
        fetchRooms(localStorage.getItem('role') === 'admin');
    } catch (err) {
        alert(`Lỗi: ${err.message}`);
    }
}
async function fetchMyBookings() {
    if (!getAuthToken()) return;
    try {
        const res = await fetch(`${API_BASE}/meetings/mine`, {
            headers: { 'Authorization': 'Bearer ' + getAuthToken() }
        });
        if (!res.ok) throw new Error('Không thể tải danh sách lịch họp.');
        myBookings = await res.json();
        renderMyBookings();
    } catch (err) {
        console.error('Lỗi lấy danh sách lịch họp:', err);
        ['myBookingsTableBody', 'invitedBookingsList', 'bookingCalendarGrid'].forEach(id => {
            const element = document.getElementById(id);
            if (element) element.innerHTML = '<div class="booking-list-empty">Không thể tải lịch họp. Vui lòng thử lại.</div>';
        });
    }
}

function renderMyBookings() {
    renderOrganizerBookings(myBookings.filter(meeting => meeting.is_organizer));
    renderInvitedBookings(myBookings.filter(meeting => !meeting.is_organizer));
    renderBookingCalendar();
}

function bookingRoomName(meeting) {
    if (String(meeting.meeting_type || '').toLowerCase() === 'online') return 'Cuộc họp online';
    return meeting.room_name || allRooms.find(room => room.id === meeting.room_id)?.name
        || (meeting.room_id ? `Phòng ${meeting.room_id}` : 'Phòng chưa xác định');
}

function bookingDate(value) {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
}

function bookingTime(date) {
    return date.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', hour12: false });
}

function bookingDateKey(date) {
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function renderOrganizerBookings(meetings) {
    const container = document.getElementById('myBookingsTableBody');
    if (!container) return;
    if (!meetings.length) {
        container.innerHTML = '<div class="booking-list-empty">Bạn chưa chủ trì cuộc họp nào.</div>';
        return;
    }
    container.innerHTML = meetings.map(meeting => {
        const start = bookingDate(meeting.start_time);
        const end = bookingDate(meeting.end_time);
        const date = start ? start.toLocaleDateString('vi-VN') : 'Chưa có ngày';
        const time = start && end ? `${bookingTime(start)} – ${bookingTime(end)}` : 'Chưa có thời gian';
        const participants = (meeting.participants || []).filter(person => person.user_id !== meeting.organizer_id);
        const attendeeMarkup = participants.length ? participants.map(person => {
            const response = ['accepted', 'declined'].includes(person.response_status) ? person.response_status : 'pending';
            const label = response === 'accepted' ? 'Đã đồng ý' : response === 'declined' ? 'Đã từ chối' : 'Chưa phản hồi';
            return `<div class="booking-guest ${response === 'accepted' ? '' : 'pending'}"><span>${escapeHtml(person.name || person.email || 'Người tham dự')}</span><span class="booking-guest-status ${response}">${response === 'accepted' ? '✓ ' : ''}${label}</span></div>`;
        }).join('') : '<div class="booking-guest pending">Chưa có người được mời.</div>';
        const cancel = `<button class="booking-cancel-button" type="button" onclick="cancelBooking(${meeting.id})">Hủy lịch</button>`;
        const qrActions = meetingPresenterQrAction(meeting);
        let joinLink = '';
        try {
            const url = new URL(String(meeting.meeting_link || meeting.online_link || ''));
            if (url.protocol === 'http:' || url.protocol === 'https:') {
                joinLink = `<a class="booking-rsvp-button" href="${escapeHtml(url.href)}" target="_blank" rel="noopener noreferrer">Tham gia</a>`;
            }
        } catch (error) {
            joinLink = '';
        }
        return `<article class="booking-list-card"><div class="booking-list-row">
            <div class="booking-list-main"><strong>${escapeHtml(meeting.title || 'Cuộc họp')}</strong><span>${escapeHtml(bookingRoomName(meeting))} · ${escapeHtml(date)}</span></div>
            <div class="booking-list-time">${escapeHtml(time)}</div>
            <div class="booking-list-actions"><button class="booking-guest-toggle" type="button" aria-expanded="false" onclick="toggleBookingGuests(${meeting.id}, this)">Người được mời (${participants.length})</button>${joinLink}${qrActions}${cancel}</div>
        </div><div id="bookingGuests${meeting.id}" class="booking-guest-list" hidden>${attendeeMarkup}</div></article>`;
    }).join('');
}

function renderInvitedBookings(meetings) {
    const container = document.getElementById('invitedBookingsList');
    if (!container) return;
    if (!meetings.length) {
        container.innerHTML = '<div class="booking-list-empty">Bạn chưa được mời tham gia cuộc họp nào.</div>';
        return;
    }
    container.innerHTML = meetings.map(meeting => {
        const start = bookingDate(meeting.start_time);
        const end = bookingDate(meeting.end_time);
        const date = start ? start.toLocaleDateString('vi-VN') : 'Chưa có ngày';
        const time = start && end ? `${bookingTime(start)} – ${bookingTime(end)}` : 'Chưa có thời gian';
        const response = meeting.my_response_status || 'pending';
        const status = response === 'accepted' ? 'Đã xác nhận' : response === 'declined' ? 'Đã từ chối' : 'Chưa phản hồi';
        const adminCancel = String(localStorage.getItem('role') || '').trim().toLowerCase() === 'admin'
            ? `<button class="booking-cancel-button" type="button" onclick="cancelBooking(${meeting.id})">Hủy lịch</button>`
            : '';
        const qrActions = meetingQrActions(meeting, response === 'accepted');
        return `<article class="booking-list-card"><div class="booking-list-row">
            <div class="booking-list-main"><strong>${escapeHtml(meeting.title || 'Cuộc họp')}</strong><span>${escapeHtml(bookingRoomName(meeting))} · ${escapeHtml(date)}</span><span>Chủ trì: ${escapeHtml(meeting.organizer_name || 'Người tổ chức')}</span></div>
            <div class="booking-list-time">${escapeHtml(time)}<br>${escapeHtml(status)}</div>
            <div class="booking-list-actions"><button class="booking-rsvp-button" type="button" onclick="respondToMeeting(${meeting.id}, 'accepted')" ${response === 'accepted' ? 'disabled' : ''}>Xác nhận</button><button class="booking-rsvp-button" type="button" onclick="respondToMeeting(${meeting.id}, 'declined')" ${response === 'declined' ? 'disabled' : ''}>Từ chối</button>${qrActions}${adminCancel}</div>
        </div></article>`;
    }).join('');
}

function meetingQrActions(meeting, isEligible) {
    if (!isEligible || !meeting.room_id || String(meeting.meeting_type || 'offline').toLowerCase() === 'online') return '';
    const state = String(meeting.status || '').toUpperCase();
    if (state === 'SCHEDULED') {
        const start = bookingDate(meeting.start_time);
        const now = Date.now();
        if (!start || now < start.getTime() - 15 * 60 * 1000 || now > start.getTime() + 15 * 60 * 1000) return '';
        return `<button class="booking-qr-button" type="button" onclick="openQrCheckModal(${meeting.id}, 'check-in')">Check-in QR</button>`;
    }
    if (state === 'IN_PROGRESS') {
        return `<button class="booking-qr-button" type="button" onclick="openQrCheckModal(${meeting.id}, 'check-out')">Check-out QR</button>`;
    }
    return '';
}

function meetingPresenterQrAction(meeting) {
    if (!meeting.room_id || String(meeting.meeting_type || 'offline').toLowerCase() === 'online') return '';
    const state = String(meeting.status || '').toUpperCase();
    if (!['SCHEDULED', 'IN_PROGRESS'].includes(state)) return '';
    return `<button class="booking-qr-button" type="button" onclick="openPresenterQrModal(${meeting.id})"><span aria-hidden="true">▦</span> Mã QR Check-in</button>`;
}

function showQrToast(message, isError = false) {
    const toast = document.getElementById('qrToast');
    if (!toast) return;
    toast.textContent = message;
    toast.classList.toggle('is-error', isError);
    toast.classList.add('is-visible');
    if (qrToastTimer) clearTimeout(qrToastTimer);
    qrToastTimer = setTimeout(() => toast.classList.remove('is-visible'), 3500);
}

function buildQrCode(container, token, size) {
    if (typeof QRCode === 'undefined') {
        throw new Error('Không tải được thư viện tạo mã QR. Vui lòng tải lại trang.');
    }
    container.replaceChildren();
    new QRCode(container, {
        text: token,
        width: size,
        height: size,
        colorDark: '#0f172a',
        colorLight: '#ffffff',
        correctLevel: QRCode.CorrectLevel.H,
    });
}

async function fetchRoomQrToken(roomId, meetingId = null) {
    const meetingQuery = meetingId ? `?meeting_id=${encodeURIComponent(meetingId)}` : '';
    const response = await fetch(`${API_BASE}/rooms/${roomId}/qr-code${meetingQuery}`, {
        headers: { Authorization: `Bearer ${getAuthToken()}` },
    });
    const result = await response.json();
    if (!response.ok) {
        throw new Error(result.detail || 'Không thể tải mã QR phòng họp.');
    }
    return result;
}

async function openRoomQrModal(roomId) {
    const room = allRooms.find(item => item.id === roomId);
    const modal = document.getElementById('roomQrModal');
    const qrTarget = document.getElementById('roomQrImage');
    if (!room || !modal || !qrTarget) return;

    document.getElementById('roomQrName').textContent = room.name || 'Phòng họp';
    document.getElementById('roomQrLocation').textContent = room.location || 'Chưa cập nhật vị trí';
    qrTarget.replaceChildren();
    modal.style.display = 'flex';
    try {
        const data = await fetchRoomQrToken(roomId);
        activeRoomQrToken = data.qr_token;
        buildQrCode(qrTarget, activeRoomQrToken, 320);
    } catch (error) {
        modal.style.display = 'none';
        showQrToast(error.message || 'Không thể tải mã QR phòng.', true);
    }
}

function closeRoomQrModal() {
    const modal = document.getElementById('roomQrModal');
    if (modal) modal.style.display = 'none';
    activeRoomQrToken = '';
}

async function openPresenterQrModal(meetingId) {
    const meeting = myBookings.find(item => item.id === meetingId);
    const modal = document.getElementById('presenterQRModal');
    const qrTarget = document.getElementById('presenterQRImage');
    if (!meeting || !modal || !qrTarget) return;

    document.getElementById('presenterQRTitle').textContent = meeting.title || 'Cuộc họp';
    document.getElementById('presenterQRRoom').textContent = bookingRoomName(meeting);
    const start = bookingDate(meeting.start_time);
    const end = bookingDate(meeting.end_time);
    document.getElementById('presenterQRTime').textContent = start && end
        ? `${start.toLocaleDateString('vi-VN')} · ${bookingTime(start)} – ${bookingTime(end)}`
        : 'Chưa có thời gian';
    qrTarget.replaceChildren();
    modal.style.display = 'flex';
    try {
        const data = await fetchRoomQrToken(meeting.room_id, meeting.id);
        activePresenterQrToken = data.qr_token;
        buildQrCode(qrTarget, activePresenterQrToken, 560);
    } catch (error) {
        modal.style.display = 'none';
        showQrToast(error.message || 'Không thể tải mã QR check-in.', true);
    }
}

async function closePresenterQrModal() {
    const modal = document.getElementById('presenterQRModal');
    if (document.fullscreenElement === modal) {
        await document.exitFullscreen();
    }
    if (modal) modal.style.display = 'none';
    activePresenterQrToken = '';
}

async function togglePresenterQrFullscreen() {
    const modal = document.getElementById('presenterQRModal');
    if (!modal) return;
    try {
        if (document.fullscreenElement === modal) {
            await document.exitFullscreen();
        } else {
            await modal.requestFullscreen();
        }
    } catch (error) {
        showQrToast('Trình duyệt không cho phép mở chế độ toàn màn hình.', true);
    }
}

function syncPresenterFullscreenButton() {
    const button = document.getElementById('presenterQRFullscreenButton');
    const modal = document.getElementById('presenterQRModal');
    if (button) {
        button.textContent = document.fullscreenElement === modal ? 'Thoát toàn màn hình' : 'Phóng to / Fullscreen';
    }
}

async function copyQrToken(token) {
    if (!token) {
        showQrToast('Không có mã QR để sao chép.', true);
        return;
    }
    try {
        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(token);
        } else {
            const input = document.createElement('textarea');
            input.value = token;
            input.setAttribute('readonly', '');
            input.style.position = 'fixed';
            input.style.opacity = '0';
            document.body.appendChild(input);
            input.select();
            const copied = document.execCommand('copy');
            input.remove();
            if (!copied) throw new Error('Trình duyệt không thể sao chép mã QR.');
        }
        showQrToast('Đã sao chép token QR.');
    } catch (error) {
        showQrToast(error.message || 'Không thể sao chép token QR.', true);
    }
}

function downloadQrImage(containerId, fileName) {
    const canvas = document.querySelector(`#${containerId} canvas`);
    if (!canvas) {
        showQrToast('Ảnh QR chưa sẵn sàng để tải.', true);
        return;
    }
    try {
        const link = document.createElement('a');
        link.href = canvas.toDataURL('image/png');
        link.download = fileName;
        link.click();
        showQrToast('Đã tải ảnh QR PNG.');
    } catch (error) {
        showQrToast(error.message || 'Không thể tải ảnh QR.', true);
    }
}

function copyRoomQrToken() {
    return copyQrToken(activeRoomQrToken);
}

function downloadRoomQrImage() {
    const roomName = document.getElementById('roomQrName')?.textContent || 'phong-hop';
    const safeName = roomName.replace(/[^\w-]+/g, '-').replace(/^-|-$/g, '') || 'phong-hop';
    downloadQrImage('roomQrImage', `QR-${safeName}.png`);
}

function copyPresenterQrToken() {
    return copyQrToken(activePresenterQrToken);
}

document.addEventListener('fullscreenchange', syncPresenterFullscreenButton);

async function openQrCheckModal(meetingId, action) {
    activeQrMeetingId = meetingId;
    activeQrAction = action;
    qrSubmissionInProgress = false;
    const modal = document.getElementById('qrCheckModal');
    const input = document.getElementById('qrTokenInput');
    const description = document.getElementById('qrCheckDescription');
    if (!modal || !input) return;
    input.value = '';
    if (description) {
        description.textContent = action === 'check-in'
            ? 'Quét mã QR của phòng họp để check-in.'
            : 'Quét mã QR của phòng họp để check-out.';
    }
    modal.style.display = 'flex';
    if (typeof Html5Qrcode === 'undefined') {
        showQrToast('Không tải được trình quét QR. Bạn có thể nhập mã thủ công.', true);
        return;
    }
    try {
        activeQrScanner = new Html5Qrcode('qrReader');
        await activeQrScanner.start(
            { facingMode: 'environment' },
            { fps: 10, qrbox: { width: 240, height: 240 } },
            async (decodedText) => {
                input.value = decodedText;
                await stopQrScanner();
                await submitQrCheck();
            },
            () => {}
        );
    } catch (error) {
        console.warn('Không thể khởi động camera quét QR:', error);
        showQrToast('Không thể mở camera. Hãy nhập mã QR thủ công.', true);
    }
}

async function stopQrScanner() {
    if (!activeQrScanner) return;
    const scanner = activeQrScanner;
    activeQrScanner = null;
    try {
        if (scanner.isScanning) await scanner.stop();
        scanner.clear();
    } catch (error) {
        console.warn('Không thể dừng trình quét QR:', error);
    }
}

async function closeQrCheckModal() {
    await stopQrScanner();
    const modal = document.getElementById('qrCheckModal');
    if (modal) modal.style.display = 'none';
    activeQrMeetingId = null;
    activeQrAction = null;
    qrSubmissionInProgress = false;
}

async function submitQrCheck() {
    if (qrSubmissionInProgress || !activeQrMeetingId || !activeQrAction) return;
    const input = document.getElementById('qrTokenInput');
    const scannedValue = (input?.value || '').trim();
    if (!scannedValue) {
        showQrToast('Vui lòng quét hoặc nhập mã QR phòng họp.', true);
        return;
    }
    let qrToken = scannedValue;
    try {
        const parsed = JSON.parse(scannedValue);
        qrToken = parsed.qr_token || scannedValue;
    } catch (error) {
        // QR labels generated by RoomSync contain the token as plain text.
    }
    qrSubmissionInProgress = true;
    try {
        const response = await fetch(
            `${API_BASE}/v1/meetings/${activeQrMeetingId}/${activeQrAction}`,
            {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${getAuthToken()}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ qr_token: qrToken }),
            }
        );
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || 'Không thể cập nhật trạng thái check-in.');
        const successMessage = activeQrAction === 'check-in'
            ? 'Check-in thành công.'
            : 'Check-out thành công.';
        await closeQrCheckModal();
        showQrToast(successMessage);
        await fetchMyBookings();
    } catch (error) {
        qrSubmissionInProgress = false;
        showQrToast(error.message || 'Không thể gửi mã QR.', true);
    }
}

function toggleBookingGuests(meetingId, button) {
    const list = document.getElementById(`bookingGuests${meetingId}`);
    if (!list) return;
    list.hidden = !list.hidden;
    button.setAttribute('aria-expanded', String(!list.hidden));
}

function switchBookingTab(tab) {
    const tabs = { calendar: ['bookingTabCalendar', 'bookingPanelCalendar'], mine: ['bookingTabMine', 'bookingPanelMine'], invited: ['bookingTabInvited', 'bookingPanelInvited'] };
    Object.entries(tabs).forEach(([name, ids]) => {
        const active = name === tab;
        const button = document.getElementById(ids[0]);
        const panel = document.getElementById(ids[1]);
        if (button) {
            button.classList.toggle('active', active);
            button.setAttribute('aria-selected', String(active));
        }
        if (panel) panel.hidden = !active;
    });
    if (tab === 'calendar') renderBookingCalendar();
}

function shiftBookingCalendar(amount) {
    bookingCalendarDate = new Date(bookingCalendarDate);
    if (bookingCalendarView === 'month') bookingCalendarDate.setMonth(bookingCalendarDate.getMonth() + amount, 1);
    else bookingCalendarDate.setDate(bookingCalendarDate.getDate() + amount * (bookingCalendarView === 'week' ? 7 : 1));
    bookingSelectedDate = new Date(bookingCalendarDate);
    renderBookingCalendar();
}

function goToBookingCalendarToday() {
    bookingCalendarDate = new Date();
    bookingSelectedDate = new Date();
    renderBookingCalendar();
}

function setBookingCalendarView(view) {
    if (!['month', 'week', 'day'].includes(view)) return;
    bookingCalendarView = view;
    document.querySelectorAll('[data-calendar-view]').forEach(button => button.classList.toggle('active', button.dataset.calendarView === view));
    renderBookingCalendar();
}

function renderBookingCalendar() {
    const grid = document.getElementById('bookingCalendarGrid');
    if (!grid) return;
    const title = document.getElementById('bookingCalendarTitle');
    const selectedKey = bookingDateKey(bookingSelectedDate);
    let dates;
    if (bookingCalendarView === 'month') {
        const first = new Date(bookingCalendarDate.getFullYear(), bookingCalendarDate.getMonth(), 1);
        const start = new Date(first);
        start.setDate(1 - first.getDay());
        dates = Array.from({ length: 42 }, (_, index) => {
            const date = new Date(start);
            date.setDate(start.getDate() + index);
            return date;
        });
        if (title) title.textContent = bookingCalendarDate.toLocaleDateString('vi-VN', { month: 'long', year: 'numeric' });
    } else if (bookingCalendarView === 'week') {
        const start = new Date(bookingCalendarDate);
        start.setDate(start.getDate() - start.getDay());
        dates = Array.from({ length: 7 }, (_, index) => {
            const date = new Date(start);
            date.setDate(start.getDate() + index);
            return date;
        });
        if (title) title.textContent = `${dates[0].toLocaleDateString('vi-VN')} – ${dates[6].toLocaleDateString('vi-VN')}`;
    } else {
        dates = [new Date(bookingCalendarDate)];
        if (title) title.textContent = bookingCalendarDate.toLocaleDateString('vi-VN', { day: 'numeric', month: 'long', year: 'numeric' });
    }
    const weekdays = ['CN', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7'];
    const columns = bookingCalendarView === 'day' ? 1 : 7;
    grid.style.gridTemplateColumns = `repeat(${columns}, minmax(0, 1fr))`;
    grid.innerHTML = (bookingCalendarView === 'day' ? '' : weekdays.map(day => `<div class="booking-calendar-weekday">${day}</div>`).join(''))
        + dates.map(date => {
            const key = bookingDateKey(date);
            const events = myBookings.filter(meeting => {
                const start = bookingDate(meeting.start_time);
                return start && bookingDateKey(start) === key;
            }).sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
            const classes = [
                bookingCalendarView === 'month' && date.getMonth() !== bookingCalendarDate.getMonth() ? 'outside' : '',
                key === bookingDateKey(new Date()) ? 'today' : '',
                key === selectedKey ? 'selected' : '',
            ].filter(Boolean).join(' ');
            const preview = events.slice(0, bookingCalendarView === 'day' ? events.length : 3).map(meeting => {
                const start = bookingDate(meeting.start_time);
                return `<span class="booking-calendar-event">${start ? `${bookingTime(start)} ` : ''}${escapeHtml(meeting.title || 'Cuộc họp')}</span>`;
            }).join('');
            const more = events.length > 3 && bookingCalendarView !== 'day' ? `<div class="booking-calendar-more">+${events.length - 3} cuộc họp</div>` : '';
            return `<div class="booking-calendar-day ${classes}" role="button" tabindex="0" aria-label="${escapeHtml(date.toLocaleDateString('vi-VN'))}, ${events.length} cuộc họp" onclick="selectBookingCalendarDate('${key}')" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();selectBookingCalendarDate('${key}')}"><span class="booking-calendar-day-number">${date.getDate()}</span>${preview}${more}</div>`;
        }).join('');
    renderBookingAgenda();
}

function selectBookingCalendarDate(key) {
    const [year, month, day] = key.split('-').map(Number);
    bookingSelectedDate = new Date(year, month - 1, day);
    bookingCalendarDate = new Date(bookingSelectedDate);
    renderBookingCalendar();
}

function renderBookingAgenda() {
    const container = document.getElementById('bookingDayAgenda');
    const title = document.getElementById('bookingAgendaTitle');
    if (!container) return;
    if (title) title.textContent = `Lịch ngày ${bookingSelectedDate.toLocaleDateString('vi-VN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}`;
    const key = bookingDateKey(bookingSelectedDate);
    const events = myBookings.filter(meeting => {
        const start = bookingDate(meeting.start_time);
        return start && bookingDateKey(start) === key;
    }).sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
    container.innerHTML = events.length ? events.map(meeting => {
        const start = bookingDate(meeting.start_time);
        const end = bookingDate(meeting.end_time);
        const time = start && end ? `${bookingTime(start)} – ${bookingTime(end)}` : 'Chưa có thời gian';
        return `<div class="booking-agenda-item"><div class="booking-agenda-time">${escapeHtml(time)}</div><div class="booking-agenda-details"><strong>${escapeHtml(meeting.title || 'Cuộc họp')}</strong><span>${escapeHtml(bookingRoomName(meeting))}${meeting.organizer_name ? ` · ${escapeHtml(meeting.organizer_name)}` : ''}</span></div></div>`;
    }).join('') : '<div class="booking-list-empty">Không có cuộc họp trong ngày này.</div>';
}

async function respondToMeeting(meetingId, responseStatus) {
    try {
const res = await fetch(`${API_BASE}/meetings/${meetingId}/response`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getAuthToken() },
    body: JSON.stringify({ response_status: responseStatus }),
});
if (!res.ok) {
    const result = await res.json();
    throw new Error(result.detail || 'Không thể cập nhật phản hồi.');
}
await fetchMyBookings();
    } catch (error) {
alert(`Lỗi: ${error.message}`);
    }
}
/* ==========================================================================
   SEARCH & FILTERING
   ========================================================================== */
function handleSearch() { applyFilters(); }
function filterToday() { alert("Đã đồng bộ lịch họp hôm nay!"); }

function applyFilters() {
    const searchInput = document.getElementById('searchInput');
    const capSelect = document.getElementById('capacitySelect');

    const query = searchInput ? searchInput.value.toLowerCase() : '';
    const cap = capSelect ? capSelect.value : 'all';

    let filtered = allRooms.filter(r =>
        r.name.toLowerCase().includes(query) ||
        (r.location && r.location.toLowerCase().includes(query))
    );

    if (cap !== 'all') {
        filtered = filtered.filter(r => {
            const num = parseInt(r.capacity) || 10;
            if (cap === 'small') return num <= 5;
            if (cap === 'medium') return num > 5 && num <= 12;
            if (cap === 'large') return num > 12;
            return true;
        });
    }

    const role = localStorage.getItem('role') || 'user';
    renderRooms(filtered, role === 'admin');
}

function setFilter(amenity, btn) {
    document.querySelectorAll('.chip').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');

    const role = localStorage.getItem('role') || 'user';
    if (amenity === 'all') {
        renderRooms(allRooms, role === 'admin');
    } else {
        const filtered = allRooms.filter(r => {
            if (!r.amenities) return false;
            if (Array.isArray(r.amenities)) return r.amenities.includes(amenity);
            if (typeof r.amenities === 'string') return r.amenities.includes(amenity);
            return false;
        });
        renderRooms(filtered, role === 'admin');
    }
}

/* ==========================================================================
   ADMIN ACTIONS (ADD / EDIT / DELETE ROOMS)
   ========================================================================== */
function openRoomModal() {
    const modalTitle = document.getElementById('modalTitle');
    if (modalTitle) modalTitle.innerText = 'Thêm Phòng Họp Mới';
    document.getElementById('editRoomId').value = '';
    document.getElementById('roomForm').reset();
    document.getElementById('roomModal').style.display = 'flex';
}

function openEditModal(roomId) {
    const room = allRooms.find(r => r.id === roomId);
    if (!room) return;

    document.getElementById('modalTitle').innerText = 'Sửa Thông Tin Phòng Họp';
    document.getElementById('editRoomId').value = room.id;
    document.getElementById('roomName').value = room.name;
    document.getElementById('roomLocation').value = room.location || '';
    document.getElementById('roomCapacity').value = room.capacity || '';

    let amenitiesStr = '';
    if (room.amenities) {
        if (typeof room.amenities === 'string') {
            try {
                let parsed = JSON.parse(room.amenities);
                amenitiesStr = Array.isArray(parsed) ? parsed.join(', ') : room.amenities;
            } catch (e) { amenitiesStr = room.amenities; }
        } else if (Array.isArray(room.amenities)) {
            amenitiesStr = room.amenities.join(', ');
        }
    }
    document.getElementById('roomAmenities').value = amenitiesStr;
    document.getElementById('roomModal').style.display = 'flex';
}

function closeRoomModal() {
    document.getElementById('roomModal').style.display = 'none';
}

async function handleFormSubmit(e) {
    e.preventDefault();
    const token = getAuthToken();
    const editId = document.getElementById('editRoomId').value;

    const payload = {
        name: document.getElementById('roomName').value,
        location: document.getElementById('roomLocation').value,
        capacity: parseInt(document.getElementById('roomCapacity').value) || 0,
        amenities: document.getElementById('roomAmenities').value.split(',').map(s => s.trim()).filter(Boolean),
        is_active: true
    };

    const method = editId ? 'PUT' : 'POST';
    const url = editId ? `${API_BASE}/rooms/${editId}/` : `${API_BASE}/rooms/`;

    try {
        const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json', "Authorization": `Bearer ${token}` },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            closeRoomModal();
            fetchRooms(localStorage.getItem('role') === 'admin');
            alert(editId ? "Cập nhật phòng thành công!" : "Thêm phòng thành công!");
        } else {
            const err = await res.json();
            alert(err.detail || "Thao tác thất bại!");
        }
    } catch (err) { alert("Lỗi kết nối máy chủ!"); }
}

async function deleteRoom(roomId) {
    if (!confirm("Bạn có chắc chắn muốn xóa phòng này?")) return;
    const token = getAuthToken();
    try {
        const res = await fetch(`${API_BASE}/rooms/${roomId}/`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (res.ok) {
            allRooms = allRooms.filter(r => r.id !== roomId);
            renderRooms(allRooms, localStorage.getItem('role') === 'admin');
            updateStats(allRooms);
            alert("Xóa phòng thành công!");
        } else {
            const err = await res.json();
            alert(err.detail || "Thao tác thất bại!");
        }
    } catch (err) { alert("Lỗi máy chủ!"); }
}

function logout() {
    localStorage.clear();
    window.location.href = 'index.html';
}

/* ==========================================================================
   EQUIPMENT MANAGEMENT
   ========================================================================== */
function setDefaultEquipmentAvailabilityTimes() {
    const startInput = document.getElementById('equipmentStartTime');
    const endInput = document.getElementById('equipmentEndTime');
    if (!startInput || !endInput) return;
    const now = new Date();
    const end = new Date(now.getTime() + 60 * 60 * 1000);
    startInput.value = formatDateTimeLocal(now);
    endInput.value = formatDateTimeLocal(end);
}

function scheduleEquipmentAvailabilityFetch() {
    clearTimeout(equipmentAvailabilityTimer);
    equipmentAvailabilityTimer = setTimeout(fetchEquipmentAvailability, 250);
}

async function fetchEquipmentAvailability() {
    const tbody = document.getElementById('equipmentAvailabilityTableBody');
    if (!tbody) return;

    const params = new URLSearchParams();
    const startTime = document.getElementById('equipmentStartTime')?.value;
    const endTime = document.getElementById('equipmentEndTime')?.value;
    const category = document.getElementById('equipmentCategoryFilter')?.value.trim();
    const search = document.getElementById('equipmentSearchFilter')?.value.trim();

    if (startTime) params.set('start_time', `${startTime}:00`);
    if (endTime) params.set('end_time', `${endTime}:00`);
    if (category) params.set('category', category);
    if (search) params.set('search', search);

    tbody.innerHTML = '<tr><td colspan="7" class="equipment-table-message">Đang cập nhật...</td></tr>';
    try {
        const token = getAuthToken();
        const res = await fetch(`${API_BASE}/equipments/availability?${params.toString()}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) throw new Error('Không thể tải trạng thái thiết bị');

        const equipments = await res.json();
        if (!equipments.length) {
            tbody.innerHTML = '<tr><td colspan="7" class="equipment-table-message">Không tìm thấy thiết bị phù hợp.</td></tr>';
            return;
        }

        tbody.innerHTML = equipments.map(item => {
            const isInactive = item.is_active === false;
            const isAvailable = item.available_qty > 0;
            const badgeClass = isInactive ? 'maintenance' : (isAvailable ? 'available' : 'booked-out');
            const badgeText = isInactive ? 'Đang bảo trì' : (isAvailable ? 'Có sẵn' : 'Đã đặt hết');
            return `
                <tr>
                    <td>${escapeHtml(item.code || '—')}</td>
                    <td>${escapeHtml(item.name)}</td>
                    <td>${escapeHtml(item.category || '—')}</td>
                    <td>${item.total_qty}</td>
                    <td>${item.booked_qty}</td>
                    <td>${item.available_qty}</td>
                    <td><span class="equipment-status-badge ${badgeClass}">${badgeText}</span></td>
                </tr>
            `;
        }).join('');
    } catch (err) {
        tbody.innerHTML = '<tr><td colspan="7" class="equipment-table-message error">Không thể tải trạng thái thiết bị.</td></tr>';
    }
}

let adminEquipmentsCache = [];

async function fetchAdminEquipments() {
    const tbody = document.getElementById('adminEquipmentTableBody');
    if (!tbody) return;

    const token = getAuthToken();
    tbody.innerHTML = '<tr><td colspan="6" class="equipment-table-message">Đang tải danh sách Admin...</td></tr>';
    try {
        const res = await fetch(`${API_BASE}/equipments/?include_inactive=true`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) throw new Error();

        const equipments = await res.json();
        adminEquipmentsCache = equipments;

        if (!equipments.length) {
            tbody.innerHTML = '<tr><td colspan="6" class="equipment-table-message">Chưa có thiết bị nào.</td></tr>';
            return;
        }

        tbody.innerHTML = equipments.map(item => {
            const isChecked = item.is_active !== false;
            return `
                <tr>
                    <td>${escapeHtml(item.code || '—')}</td>
                    <td>${escapeHtml(item.name)}</td>
                    <td>${escapeHtml(item.category || '—')}</td>
                    <td><strong>${item.total_qty}</strong></td>
                    <td>
                        <label class="switch">
                            <input type="checkbox" ${isChecked ? 'checked' : ''} onchange="toggleEquipmentActive(${item.id}, this.checked)">
                            <span class="slider"></span>
                        </label>
                    </td>
                    <td>
                        <div style="display: flex; gap: 8px;">
                            <button type="button" onclick="openEditEquipmentModal(${item.id})" style="padding: 4px 10px; font-size: 0.78rem; background: #e0f2fe; color: #0369a1; border: none; border-radius: 6px; cursor: pointer; font-weight: 600;">Sửa</button>
                            <button type="button" onclick="deleteEquipment(${item.id})" style="padding: 4px 10px; font-size: 0.78rem; background: #fee2e2; color: #b91c1c; border: none; border-radius: 6px; cursor: pointer; font-weight: 600;">Xóa</button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    } catch (err) {
        tbody.innerHTML = '<tr><td colspan="6" class="equipment-table-message error">Không thể tải dữ liệu Admin.</td></tr>';
    }
}

async function toggleEquipmentActive(equipmentId, isActive) {
    const token = getAuthToken();
    try {
        await fetch(`${API_BASE}/equipments/${equipmentId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ is_active: isActive })
        });
        fetchAdminEquipments();
        fetchEquipmentAvailability();
    } catch (err) { alert(`Lỗi: ${err.message}`); }
}

function openEquipmentModal() {
    document.getElementById('editEquipmentId').value = '';
    document.getElementById('equipmentForm').reset();
    document.getElementById('equipmentModalTitle').innerText = 'Thêm Thiết Bị Mới';
    document.getElementById('equipmentModal').style.display = 'flex';
}

function openEditEquipmentModal(id) {
    const equip = adminEquipmentsCache.find(item => item.id === id);
    if (!equip) return;
    document.getElementById('editEquipmentId').value = equip.id;
    document.getElementById('equipmentName').value = equip.name || '';
    document.getElementById('equipmentCode').value = equip.code || '';
    document.getElementById('equipmentCategory').value = equip.category || '';
    document.getElementById('equipmentTotalQty').value = equip.total_qty || 1;
    document.getElementById('equipmentModalTitle').innerText = 'Sửa Thông Tin Thiết Bị';
    document.getElementById('equipmentModal').style.display = 'flex';
}

function closeEquipmentModal() {
    document.getElementById('equipmentModal').style.display = 'none';
}

async function handleEquipmentFormSubmit(event) {
    event.preventDefault();
    const token = getAuthToken();
    const editId = document.getElementById('editEquipmentId')?.value;
    const payload = {
        name: document.getElementById('equipmentName')?.value.trim(),
        code: document.getElementById('equipmentCode')?.value.trim() || null,
        category: document.getElementById('equipmentCategory')?.value.trim() || null,
        total_qty: parseInt(document.getElementById('equipmentTotalQty')?.value || '1', 10)
    };

    const isEdit = Boolean(editId);
    const url = isEdit ? `${API_BASE}/equipments/${editId}` : `${API_BASE}/equipments/`;

    try {
        const res = await fetch(url, {
            method: isEdit ? 'PUT' : 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error('Thao tác thất bại');
        closeEquipmentModal();
        fetchAdminEquipments();
        fetchEquipmentAvailability();
        alert(isEdit ? 'Cập nhật thiết bị thành công!' : 'Thêm thiết bị mới thành công!');
    } catch (err) { alert(`Lỗi: ${err.message}`); }
}

async function deleteEquipment(id) {
    if (!confirm('Bạn có chắc chắn muốn xóa thiết bị này?')) return;
    const token = getAuthToken();
    try {
        await fetch(`${API_BASE}/equipments/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        fetchAdminEquipments();
        fetchEquipmentAvailability();
    } catch (err) { alert(`Lỗi: ${err.message}`); }
}

/* ==========================================================================
   ROOM USAGE REPORT LOGIC
   ========================================================================== */
async function loadRoomsForReportFilter() {
    try {
        const response = await fetch(`${API_BASE}/rooms/`);
        if (response.ok) {
            const rooms = await response.json();
            const select = document.getElementById("reportRoomIdSelect");
            if (select) {
                select.innerHTML = '<option value="">Tất cả các phòng</option>';
                rooms.forEach(room => {
                    const option = document.createElement("option");
                    option.value = room.id;
                    option.textContent = room.name;
                    select.appendChild(option);
                });
            }
        }
    } catch (error) {
        console.error("Lỗi tải danh sách phòng cho bộ lọc báo cáo:", error);
    }
}

async function fetchRoomUsageReport() {
    const startDateVal = document.getElementById("reportStartDate").value;
    const endDateVal = document.getElementById("reportEndDate").value;
    const roomIdVal = document.getElementById("reportRoomIdSelect").value;
    const token = getAuthToken();

    let url = `${API_BASE}/v1/reports/room-usage?`;
    const params = new URLSearchParams();

    if (startDateVal) params.append("start_date", new Date(startDateVal).toISOString());
    if (endDateVal) params.append("end_date", new Date(endDateVal).toISOString());
    if (roomIdVal) params.append("room_id", roomIdVal);

    try {
        const response = await fetch(url + params.toString(), {
            method: "GET",
            headers: {
                "Authorization": `Bearer ${token}`,
                "Content-Type": "application/json"
            }
        });

        if (response.status === 401) {
            alert("Phiên đăng nhập hết hạn hoặc bạn không có quyền Quản trị viên (Admin)!");
            return;
        }

        if (response.status === 400) {
            const errData = await response.json();
            alert(`Lỗi tham số: ${errData.detail || "Khoảng thời gian không hợp lệ"}`);
            return;
        }

        if (!response.ok) {
            throw new Error("Không thể kết nối lấy dữ liệu báo cáo.");
        }

        const data = await response.json();
        renderReportDataToDashboard(data);

    } catch (error) {
        console.error("Lỗi gọi API báo cáo:", error);
        alert("Đã xảy ra lỗi khi tải dữ liệu báo cáo từ máy chủ.");
    }
}

function renderReportDataToDashboard(data) {
    document.getElementById("sumTotalRooms").textContent = data.summary.total_rooms;
    document.getElementById("sumTotalMeetings").textContent = data.summary.total_meetings;
    document.getElementById("sumTotalHours").textContent = `${data.summary.total_hours.toFixed(1)} h`;
    document.getElementById("sumAvgOccupancy").textContent = `${data.summary.average_occupancy_rate.toFixed(1)}%`;

    const tbody = document.getElementById("roomDetailsTableBody");
    tbody.innerHTML = "";

    if (!data.room_details || data.room_details.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: #94a3b8; padding: 24px;">Không có dữ liệu cuộc họp trong khoảng thời gian này.</td></tr>`;
        return;
    }

    data.room_details.forEach(room => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${room.room_id}</td>
            <td><strong>${escapeHtml(room.room_name)}</strong></td>
            <td>${room.total_meetings}</td>
            <td>${room.total_hours.toFixed(1)} h</td>
            <td>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="font-weight: 600;">${room.occupancy_rate.toFixed(1)}%</span>
                    <div style="width: 100px; background: #e2e8f0; border-radius: 9999px; height: 8px; overflow: hidden;">
                        <div style="background: #2563eb; height: 100%; width: ${Math.min(room.occupancy_rate, 100)}%;"></div>
                    </div>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

/* ==========================================================================
   GLOBAL EXPORTS (GẮN VÀO WINDOW CHO EVENT HANDLER)
   ========================================================================== */
window.toggleSidebar = toggleSidebar;
window.switchToOverview = switchToOverview;
window.switchMainTab = switchMainTab;
window.navigateToSettings = navigateToSettings;
window.scrollToRooms = scrollToRooms;
window.toggleNotificationPopup = toggleNotificationPopup;
window.openScheduleModal = openScheduleModal;
window.closeScheduleModal = closeScheduleModal;
window.openQrCheckModal = openQrCheckModal;
window.closeQrCheckModal = closeQrCheckModal;
window.submitQrCheck = submitQrCheck;
window.openRoomQrModal = openRoomQrModal;
window.closeRoomQrModal = closeRoomQrModal;
window.copyRoomQrToken = copyRoomQrToken;
window.downloadRoomQrImage = downloadRoomQrImage;
window.openPresenterQrModal = openPresenterQrModal;
window.closePresenterQrModal = closePresenterQrModal;
window.togglePresenterQrFullscreen = togglePresenterQrFullscreen;
window.copyPresenterQrToken = copyPresenterQrToken;
window.cancelBooking = cancelBooking;
window.handleSearch = handleSearch;
window.filterToday = filterToday;
window.applyFilters = applyFilters;
window.setFilter = setFilter;
window.openRoomModal = openRoomModal;
window.openEditModal = openEditModal;
window.closeRoomModal = closeRoomModal;
window.handleFormSubmit = handleFormSubmit;
window.deleteRoom = deleteRoom;
window.logout = logout;
window.fetchEquipmentAvailability = fetchEquipmentAvailability;
window.scheduleEquipmentAvailabilityFetch = scheduleEquipmentAvailabilityFetch;
window.fetchAdminEquipments = fetchAdminEquipments;
window.toggleEquipmentActive = toggleEquipmentActive;
window.openEquipmentModal = openEquipmentModal;
window.openEditEquipmentModal = openEditEquipmentModal;
window.closeEquipmentModal = closeEquipmentModal;
window.handleEquipmentFormSubmit = handleEquipmentFormSubmit;
window.deleteEquipment = deleteEquipment;
window.fetchRoomUsageReport = fetchRoomUsageReport;
window.loadRoomsForReportFilter = loadRoomsForReportFilter;
window.updateUserSettings = updateUserSettings;
````
