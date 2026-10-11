from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.models.meeting_reminder import MeetingReminder
from app.models.notification import Notification
from app.services.reminder_service import check_and_send_meeting_reminders
from tests.helpers import (
    _add_participant,
    _create_meeting,
    _create_room,
    _create_user,
)


def test_scheduler_sends_only_for_accepted_users_and_is_idempotent(db_session):
    organizer = _create_user(db_session, "org_reminder")
    accepted = _create_user(db_session, "accepted_user")
    rejected = _create_user(db_session, "rejected_user")
    pending = _create_user(db_session, "pending_user")
    room = _create_room(db_session, "Room Reminder")

    now = datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).replace(tzinfo=None)
    plus_30_min = _create_meeting(
        db_session,
        room,
        organizer,
        now + timedelta(minutes=29),
        now + timedelta(minutes=59),
    )
    plus_15_min = _create_meeting(
        db_session,
        room,
        organizer,
        now + timedelta(minutes=14),
        now + timedelta(minutes=44),
    )
    plus_one_day = _create_meeting(
        db_session,
        room,
        organizer,
        now + timedelta(hours=23, minutes=30),
        now + timedelta(hours=24, minutes=30),
    )

    accepted_30_min = _add_participant(db_session, plus_30_min, accepted)
    accepted_30_min.response_status = "accepted"

    rejected_30_min = _add_participant(db_session, plus_30_min, rejected)
    rejected_30_min.response_status = "rejected"

    pending_30_min = _add_participant(db_session, plus_30_min, pending)
    pending_30_min.response_status = "pending"

    accepted_15_min = _add_participant(db_session, plus_15_min, accepted)
    accepted_15_min.response_status = "accepted"

    rejected_15_min = _add_participant(db_session, plus_15_min, rejected)
    rejected_15_min.response_status = "rejected"

    accepted_one_day = _add_participant(db_session, plus_one_day, accepted)
    accepted_one_day.response_status = "accepted"

    rejected_one_day = _add_participant(db_session, plus_one_day, rejected)
    rejected_one_day.response_status = "rejected"

    pending_one_day = _add_participant(db_session, plus_one_day, pending)
    pending_one_day.response_status = "pending"

    db_session.commit()

    results = check_and_send_meeting_reminders()

    assert results["processed_meetings"] == 3
    assert results["reminders_sent"] == 6

    sent = db_session.query(MeetingReminder).all()
    assert len(sent) == 6
    assert {item.reminder_type for item in sent} == {"1_day", "30_mins", "15_mins"}
    assert {item.user_id for item in sent} == {organizer.id, accepted.id}
    assert {item.meeting_id for item in sent if item.reminder_type == "1_day"} == {plus_one_day.id}
    assert {item.meeting_id for item in sent if item.reminder_type == "30_mins"} == {plus_30_min.id}
    assert {item.meeting_id for item in sent if item.reminder_type == "15_mins"} == {plus_15_min.id}

    reminder_notifications = (
        db_session.query(Notification)
        .filter(Notification.meeting_id.in_([plus_one_day.id, plus_30_min.id, plus_15_min.id]))
        .all()
    )
    assert len(reminder_notifications) == 6
    assert {item.user_id for item in reminder_notifications} == {organizer.id, accepted.id}

    second_run = check_and_send_meeting_reminders()
    assert second_run["reminders_sent"] == 0
    assert db_session.query(MeetingReminder).count() == 6


def test_scheduler_does_not_send_reminders_for_cancelled_meetings(db_session):
    organizer = _create_user(db_session, "org_cancelled_reminder")
    invitee = _create_user(db_session, "accepted_cancelled_meeting")
    room = _create_room(db_session, "Room Cancelled Reminder")

    local_now = (
        datetime.now(timezone.utc)
        .astimezone(ZoneInfo("Asia/Ho_Chi_Minh"))
        .replace(tzinfo=None)
    )
    meeting = _create_meeting(
        db_session,
        room,
        organizer,
        local_now + timedelta(minutes=20),
        local_now + timedelta(minutes=50),
        status="CANCELLED",
    )
    participant = _add_participant(db_session, meeting, invitee)
    participant.response_status = "accepted"
    db_session.commit()

    result = check_and_send_meeting_reminders()

    assert result["reminders_sent"] == 0
    assert db_session.query(MeetingReminder).filter_by(meeting_id=meeting.id).count() == 0
    assert db_session.query(Notification).filter_by(meeting_id=meeting.id).count() == 0
