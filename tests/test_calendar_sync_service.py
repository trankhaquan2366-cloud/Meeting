from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet
import pytest
from sqlalchemy.orm import sessionmaker

from app.core.meeting_events import (
    EVENT_MEETING_CANCELLED,
    EVENT_MEETING_CREATED,
    EVENT_MEETING_UPDATED,
)
from app.models.calendar import UserCalendarEvent, UserCalendarToken
from app.models.meeting import Meeting, MeetingParticipant
from app.models.notification import Notification
from app.models.user import User
from app.routers import meetings as meetings_router
from app.schemas.meeting import MeetingCreateRequest
from app.services import calendar_sync_service, reminder_service
from app.services.meeting_service import MeetingService
from tests.helpers import _auth_header, _create_room, _create_user, _make_token


def _create_calendar_user(db_session, username="calendar-user") -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        hashed_password="unused",
    )
    db_session.add(user)
    db_session.commit()
    return user


def _set_encryption_key(monkeypatch):
    monkeypatch.setenv(
        "CALENDAR_TOKEN_ENCRYPTION_KEY",
        Fernet.generate_key().decode("ascii"),
    )


def test_stores_oauth_tokens_encrypted_and_updates_existing_connection(
    db_session,
    monkeypatch,
):
    _set_encryption_key(monkeypatch)
    user = _create_calendar_user(db_session)

    saved = calendar_sync_service.store_authorized_tokens(
        db_session,
        user.id,
        "google",
        {
            "access_token": "initial-access",
            "refresh_token": "initial-refresh",
            "expires_in": 3600,
        },
    )
    original_id = saved.id

    assert saved.access_token != "initial-access"
    assert saved.refresh_token != "initial-refresh"
    assert calendar_sync_service._decrypt_token(saved.access_token) == "initial-access"
    assert calendar_sync_service._decrypt_token(saved.refresh_token) == "initial-refresh"
    assert saved.expires_at is not None

    updated = calendar_sync_service.store_authorized_tokens(
        db_session,
        user.id,
        "google",
        {"access_token": "updated-access", "expires_in": 1800},
    )

    assert updated.id == original_id
    assert calendar_sync_service._decrypt_token(updated.access_token) == "updated-access"
    assert calendar_sync_service._decrypt_token(updated.refresh_token) == "initial-refresh"


def test_returns_current_access_token_without_refresh(db_session, monkeypatch):
    _set_encryption_key(monkeypatch)
    user = _create_calendar_user(db_session)
    token = UserCalendarToken(
        user_id=user.id,
        provider="google",
        access_token=calendar_sync_service._encrypt_token("usable-access"),
        refresh_token=None,
        expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1),
        is_active=True,
    )
    db_session.add(token)
    db_session.commit()

    assert calendar_sync_service.get_valid_access_token(user.id, "google") == "usable-access"


def test_refreshes_expired_access_token(db_session, monkeypatch):
    _set_encryption_key(monkeypatch)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-secret")
    user = _create_calendar_user(db_session)
    token = UserCalendarToken(
        user_id=user.id,
        provider="google",
        access_token=calendar_sync_service._encrypt_token("expired-access"),
        refresh_token=calendar_sync_service._encrypt_token("refresh-value"),
        expires_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1),
        is_active=True,
    )
    db_session.add(token)
    db_session.commit()
    request_payload = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"access_token": "new-access", "expires_in": 3600}

    def fake_post(url, data, timeout):
        request_payload.update({"url": url, "data": data, "timeout": timeout})
        return FakeResponse()

    monkeypatch.setattr(calendar_sync_service.httpx, "post", fake_post)

    assert calendar_sync_service.get_valid_access_token(user.id, "google") == "new-access"
    assert request_payload["url"] == "https://oauth2.googleapis.com/token"
    assert request_payload["data"]["refresh_token"] == "refresh-value"
    assert request_payload["timeout"] == 15.0

    db_session.refresh(token)
    assert calendar_sync_service._decrypt_token(token.access_token) == "new-access"


def test_create_update_and_delete_provider_event(db_session, monkeypatch):
    _set_encryption_key(monkeypatch)
    user = _create_calendar_user(db_session)
    meeting = Meeting(
        title="Calendar sync",
        organizer_id=user.id,
        start_time=datetime(2030, 1, 1, 13),
        end_time=datetime(2030, 1, 1, 14),
        status="CONFIRMED",
    )
    db_session.add(meeting)
    db_session.add(
        UserCalendarToken(
            user_id=user.id,
            provider="google",
            access_token=calendar_sync_service._encrypt_token("access-value"),
            is_active=True,
        )
    )
    db_session.commit()

    monkeypatch.setattr(
        calendar_sync_service,
        "SessionLocal",
        sessionmaker(bind=db_session.get_bind()),
    )
    monkeypatch.setattr(
        calendar_sync_service,
        "get_valid_access_token",
        lambda user_id, provider: f"access-{user_id}-{provider}",
    )
    requests = []

    def fake_provider_request(provider, access_token, method, event_id=None, payload=None):
        requests.append((provider, access_token, method, event_id, payload))
        return "google-event-id" if method == "POST" else event_id

    monkeypatch.setattr(
        calendar_sync_service,
        "_provider_event_request",
        fake_provider_request,
    )

    calendar_sync_service.sync_create_event(meeting.id)
    link = db_session.query(UserCalendarEvent).filter_by(meeting_id=meeting.id).one()
    assert link.external_event_id == "google-event-id"
    assert requests[0][1] == f"access-{user.id}-google"
    assert requests[0][2] == "POST"
    assert requests[0][4]["start"]["dateTime"] == "2030-01-01T13:00:00+00:00"

    calendar_sync_service.sync_update_event(meeting.id)
    assert requests[1][2] == "PATCH"
    assert requests[1][3] == "google-event-id"

    calendar_sync_service.sync_delete_event(meeting.id)
    assert requests[2][2] == "DELETE"
    assert db_session.query(UserCalendarEvent).filter_by(meeting_id=meeting.id).count() == 0


def test_recurring_event_payload_matches_google_and_outlook_contract(db_session):
    meeting = Meeting(
        title="Weekly review",
        start_time=datetime(2030, 1, 7, 13),
        end_time=datetime(2030, 1, 7, 14),
        is_recurring=True,
        recurring_type="weekly",
    )

    google_payload = calendar_sync_service._meeting_event_payload(
        meeting,
        "google",
        recurrence_count=4,
    )
    outlook_payload = calendar_sync_service._meeting_event_payload(
        meeting,
        "outlook",
        recurrence_count=4,
    )

    assert google_payload["recurrence"] == ["RRULE:FREQ=WEEKLY;COUNT=4"]
    assert outlook_payload["recurrence"]["pattern"] == {
        "type": "weekly",
        "interval": 1,
        "daysOfWeek": ["monday"],
        "firstDayOfWeek": "sunday",
    }
    assert outlook_payload["recurrence"]["range"]["numberOfOccurrences"] == 4


def test_weekly_recurrence_requires_end_date():
    with pytest.raises(ValueError, match="recurrence_end_date"):
        MeetingCreateRequest(
            title="Missing recurrence end",
            meeting_type="online",
            online_link="https://meet.example.com",
            start_time=datetime(2030, 1, 7, 13),
            end_time=datetime(2030, 1, 7, 14),
            recurrence_type="weekly",
        )


def test_update_removes_event_from_removed_participant_calendar(
    db_session,
    monkeypatch,
):
    _set_encryption_key(monkeypatch)
    organizer = _create_calendar_user(db_session)
    participant = _create_calendar_user(db_session, "calendar-participant")
    meeting = Meeting(
        title="Participant removal",
        organizer_id=organizer.id,
        start_time=datetime(2030, 1, 1, 13),
        end_time=datetime(2030, 1, 1, 14),
        status="CONFIRMED",
        participants=[MeetingParticipant(user_id=participant.id)],
    )
    db_session.add(meeting)
    db_session.add(
        UserCalendarToken(
            user_id=participant.id,
            provider="google",
            access_token=calendar_sync_service._encrypt_token("access-value"),
            is_active=True,
        )
    )
    db_session.commit()
    db_session.add(
        UserCalendarEvent(
            meeting_id=meeting.id,
            user_id=participant.id,
            provider="google",
            external_event_id="participant-event-id",
        )
    )
    db_session.commit()
    db_session.delete(meeting.participants[0])
    db_session.commit()

    monkeypatch.setattr(
        calendar_sync_service,
        "SessionLocal",
        sessionmaker(bind=db_session.get_bind()),
    )
    monkeypatch.setattr(
        calendar_sync_service,
        "get_valid_access_token",
        lambda user_id, provider: f"access-{user_id}-{provider}",
    )
    requests = []

    def fake_provider_request(provider, access_token, method, event_id=None, payload=None):
        requests.append((provider, method, event_id))
        return event_id

    monkeypatch.setattr(
        calendar_sync_service,
        "_provider_event_request",
        fake_provider_request,
    )

    calendar_sync_service.sync_update_event(meeting.id)

    assert requests == [("google", "DELETE", "participant-event-id")]
    assert db_session.query(UserCalendarEvent).filter_by(meeting_id=meeting.id).count() == 0


def test_recurring_series_creates_one_provider_series_and_maps_occurrences(
    db_session,
    monkeypatch,
):
    _set_encryption_key(monkeypatch)
    user = _create_calendar_user(db_session, "recurring-calendar-user")
    series_id = "be260f40-bd34-4c10-9f1f-823ef0a94cec"
    meetings = [
        Meeting(
            title="Weekly planning",
            organizer_id=user.id,
            start_time=datetime(2030, 1, 7, 13) + timedelta(days=7 * index),
            end_time=datetime(2030, 1, 7, 14) + timedelta(days=7 * index),
            status="CONFIRMED",
            is_recurring=True,
            recurring_type="weekly",
            recurring_series_id=series_id,
            recurrence_original_start=datetime(2030, 1, 7, 13)
            + timedelta(days=7 * index),
        )
        for index in range(3)
    ]
    db_session.add_all(meetings)
    db_session.add(
        UserCalendarToken(
            user_id=user.id,
            provider="google",
            access_token=calendar_sync_service._encrypt_token("access-value"),
            is_active=True,
        )
    )
    db_session.commit()
    meeting_ids = [meeting.id for meeting in meetings]

    monkeypatch.setattr(
        calendar_sync_service,
        "SessionLocal",
        sessionmaker(bind=db_session.get_bind()),
    )
    monkeypatch.setattr(
        calendar_sync_service,
        "get_valid_access_token",
        lambda user_id, provider: "access-value",
    )
    requests = []

    def fake_provider_request(provider, access_token, method, event_id=None, payload=None):
        requests.append((provider, method, event_id, payload))
        return "google-series-event" if method == "POST" else event_id

    monkeypatch.setattr(
        calendar_sync_service,
        "_provider_event_request",
        fake_provider_request,
    )

    for meeting_id in meeting_ids:
        calendar_sync_service.sync_create_event(meeting_id)

    assert len(requests) == 1
    assert requests[0][1] == "POST"
    assert requests[0][3]["recurrence"] == ["RRULE:FREQ=WEEKLY;COUNT=3"]
    links = (
        db_session.query(UserCalendarEvent)
        .filter(UserCalendarEvent.meeting_id.in_(meeting_ids))
        .order_by(UserCalendarEvent.meeting_id)
        .all()
    )
    assert len(links) == 3
    assert {link.external_event_id for link in links} == {"google-series-event"}


def test_monthly_meeting_series_matches_monthly_calendar_recurrence(db_session):
    user = _create_calendar_user(db_session, "monthly-series-user")
    room = _create_room(db_session, "Monthly series room")
    payload = MeetingCreateRequest(
        title="Month-end review",
        room_id=room.id,
        start_time=datetime(2035, 1, 31, 9),
        end_time=datetime(2035, 1, 31, 10),
        recurrence_type="monthly",
        recurrence_end_date=datetime(2035, 3, 31, 23, 59),
    )

    meetings = MeetingService.create_meeting(
        db_session,
        payload,
        organizer_id=user.id,
    )

    assert [meeting.start_time.date().isoformat() for meeting in meetings] == [
        "2035-01-31",
        "2035-03-31",
    ]
    assert len({meeting.recurring_series_id for meeting in meetings}) == 1
    assert all(meeting.recurrence_original_start for meeting in meetings)


def test_recurring_occurrence_update_and_cancel_use_instance_id(
    db_session,
    monkeypatch,
):
    _set_encryption_key(monkeypatch)
    user = _create_calendar_user(db_session, "recurring-instance-user")
    series_id = "be260f40-bd34-4c10-9f1f-823ef0a94ced"
    meeting = Meeting(
        title="Weekly planning",
        organizer_id=user.id,
        start_time=datetime(2030, 1, 14, 13),
        end_time=datetime(2030, 1, 14, 14),
        status="CONFIRMED",
        is_recurring=True,
        recurring_type="weekly",
        recurring_series_id=series_id,
        recurrence_original_start=datetime(2030, 1, 14, 13),
    )
    db_session.add(meeting)
    db_session.add(
        UserCalendarToken(
            user_id=user.id,
            provider="google",
            access_token=calendar_sync_service._encrypt_token("access-value"),
            is_active=True,
        )
    )
    db_session.commit()
    link = UserCalendarEvent(
        meeting_id=meeting.id,
        user_id=user.id,
        provider="google",
        external_event_id="google-series-event",
    )
    db_session.add(link)
    db_session.commit()

    monkeypatch.setattr(
        calendar_sync_service,
        "SessionLocal",
        sessionmaker(bind=db_session.get_bind()),
    )
    monkeypatch.setattr(
        calendar_sync_service,
        "get_valid_access_token",
        lambda user_id, provider: "access-value",
    )

    class FakeInstancesResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "items": [
                    {
                        "id": "google-occurrence-event",
                        "originalStartTime": {
                            "dateTime": "2030-01-14T13:00:00Z"
                        },
                    }
                ]
            }

    monkeypatch.setattr(
        calendar_sync_service.httpx,
        "get",
        lambda *args, **kwargs: FakeInstancesResponse(),
    )
    requests = []

    def fake_provider_request(provider, access_token, method, event_id=None, payload=None):
        requests.append((method, event_id, payload))
        return event_id

    monkeypatch.setattr(
        calendar_sync_service,
        "_provider_event_request",
        fake_provider_request,
    )

    calendar_sync_service.sync_update_event(meeting.id)
    assert requests[0][0:2] == ("PATCH", "google-occurrence-event")
    assert "recurrence" not in requests[0][2]

    calendar_sync_service.sync_delete_event(meeting.id)
    assert requests[1] == ("DELETE", "google-occurrence-event", None)
    assert (
        db_session.query(UserCalendarEvent)
        .filter_by(meeting_id=meeting.id)
        .count()
        == 0
    )


def test_moved_recurring_occurrence_becomes_standalone_event(
    db_session,
    monkeypatch,
):
    _set_encryption_key(monkeypatch)
    user = _create_calendar_user(db_session, "detached-instance-user")
    series_id = "be260f40-bd34-4c10-9f1f-823ef0a94cee"
    original_start = datetime(2030, 1, 14, 13)
    meeting = Meeting(
        title="Moved planning session",
        organizer_id=user.id,
        start_time=datetime(2030, 1, 14, 15),
        end_time=datetime(2030, 1, 14, 16),
        status="CONFIRMED",
        is_recurring=True,
        recurring_type="weekly",
        recurring_series_id=series_id,
        recurrence_original_start=original_start,
        recurrence_is_detached=True,
    )
    db_session.add(meeting)
    db_session.add(
        UserCalendarToken(
            user_id=user.id,
            provider="google",
            access_token=calendar_sync_service._encrypt_token("access-value"),
            is_active=True,
        )
    )
    db_session.commit()
    link = UserCalendarEvent(
        meeting_id=meeting.id,
        user_id=user.id,
        provider="google",
        external_event_id="google-series-event",
        external_series_event_id="google-series-event",
    )
    db_session.add(link)
    db_session.commit()

    monkeypatch.setattr(
        calendar_sync_service,
        "SessionLocal",
        sessionmaker(bind=db_session.get_bind()),
    )
    monkeypatch.setattr(
        calendar_sync_service,
        "get_valid_access_token",
        lambda user_id, provider: "access-value",
    )

    class FakeInstancesResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "items": [
                    {
                        "id": "google-original-occurrence",
                        "originalStartTime": {
                            "dateTime": "2030-01-14T13:00:00Z"
                        },
                    }
                ]
            }

    monkeypatch.setattr(
        calendar_sync_service.httpx,
        "get",
        lambda *args, **kwargs: FakeInstancesResponse(),
    )
    requests = []

    def fake_provider_request(provider, access_token, method, event_id=None, payload=None):
        requests.append((method, event_id, payload))
        return "google-standalone-event" if method == "POST" else event_id

    monkeypatch.setattr(
        calendar_sync_service,
        "_provider_event_request",
        fake_provider_request,
    )

    calendar_sync_service.sync_update_event(meeting.id)

    assert [request[0:2] for request in requests] == [
        ("POST", None),
        ("DELETE", "google-original-occurrence"),
    ]
    assert "recurrence" not in requests[0][2]
    db_session.refresh(link)
    assert link.external_event_id == "google-standalone-event"
    assert link.external_series_event_id == "google-series-event"
    assert link.external_occurrence_id is None

    calendar_sync_service.sync_update_event(meeting.id)
    assert requests[-1][0:2] == ("PATCH", "google-standalone-event")

    calendar_sync_service.sync_delete_event(meeting.id)
    assert requests[-1][0:2] == ("DELETE", "google-standalone-event")


def test_create_and_cancel_queue_calendar_background_hook(client, db_session, monkeypatch):
    user = _create_user(db_session, "calendar-hook-organizer")
    room = _create_room(db_session, "Calendar Hook Room")
    queued_actions = []
    monkeypatch.setattr(
        meetings_router,
        "sync_event_task",
        lambda meeting_id, event_type, reason=None: queued_actions.append(
            (meeting_id, event_type, reason)
        ),
    )
    headers = _auth_header(_make_token(user))
    start = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=3)

    response = client.post(
        "/api/meetings/book",
        headers=headers,
        json={
            "title": "Calendar hook",
            "room_id": room.id,
            "start_time": start.isoformat(),
            "end_time": (start + timedelta(hours=1)).isoformat(),
        },
    )

    assert response.status_code == 201
    meeting_id = response.json()[0]["id"]
    assert response.json()[0]["status"] == "CONFIRMED"
    assert queued_actions == [(meeting_id, EVENT_MEETING_CREATED, None)]

    response = client.patch(
        f"/api/meetings/{meeting_id}",
        headers=headers,
        json={"title": "Updated calendar hook"},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated calendar hook"
    assert queued_actions == [
        (meeting_id, EVENT_MEETING_CREATED, None),
        (meeting_id, EVENT_MEETING_UPDATED, None),
    ]

    response = client.patch(
        f"/api/meetings/{meeting_id}/cancel",
        headers=headers,
        params={"reason": "Phòng họp không còn khả dụng"},
    )

    assert response.status_code == 200
    assert queued_actions == [
        (meeting_id, EVENT_MEETING_CREATED, None),
        (meeting_id, EVENT_MEETING_UPDATED, None),
        (
            meeting_id,
            EVENT_MEETING_CANCELLED,
            "Phòng họp không còn khả dụng",
        ),
    ]
    cancellation_notice = (
        db_session.query(Notification)
        .filter(Notification.title == "Cuộc họp đã bị hủy")
        .one()
    )
    assert "Phòng họp không còn khả dụng" in cancellation_notice.content
    assert "xin lỗi" in cancellation_notice.content


def test_moving_recurring_occurrence_marks_it_for_detachment(
    client,
    db_session,
    monkeypatch,
):
    user = _create_user(db_session, "calendar-recurring-update")
    old_start = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=5)
    meeting = Meeting(
        title="Recurring session",
        meeting_type="online",
        online_link="https://meet.example.com/recurring",
        organizer_id=user.id,
        start_time=old_start,
        end_time=old_start + timedelta(hours=1),
        status="CONFIRMED",
        is_recurring=True,
        recurring_type="weekly",
        recurring_series_id="be260f40-bd34-4c10-9f1f-823ef0a94cef",
        recurrence_original_start=old_start,
    )
    db_session.add(meeting)
    db_session.commit()
    meeting_id = meeting.id
    queued_actions = []
    monkeypatch.setattr(
        meetings_router,
        "sync_event_task",
        lambda requested_id, action: queued_actions.append((requested_id, action)),
    )

    response = client.patch(
        f"/api/meetings/{meeting_id}",
        headers=_auth_header(_make_token(user)),
        json={
            "meeting_type": "online",
            "online_link": "https://meet.example.com/recurring",
            "room_id": None,
            "start_time": (old_start + timedelta(hours=2)).isoformat(),
            "end_time": (old_start + timedelta(hours=3)).isoformat(),
        },
    )

    assert response.status_code == 200
    db_session.refresh(meeting)
    assert meeting.recurrence_is_detached is True
    assert meeting.recurrence_original_start == old_start
    assert queued_actions == [(meeting_id, EVENT_MEETING_UPDATED)]


def test_meeting_detail_is_visible_to_organizer_and_participant_only(
    client,
    db_session,
):
    organizer = _create_calendar_user(db_session, "meeting-detail-organizer")
    participant = _create_calendar_user(db_session, "meeting-detail-participant")
    outsider = _create_calendar_user(db_session, "meeting-detail-outsider")
    start_time = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=1)
    meeting = Meeting(
        title="Private meeting details",
        meeting_type="online",
        online_link="https://meet.example.com/private",
        organizer_id=organizer.id,
        start_time=start_time,
        end_time=start_time + timedelta(hours=1),
        status="CONFIRMED",
    )
    meeting.participants.append(MeetingParticipant(user_id=participant.id))
    db_session.add(meeting)
    db_session.commit()

    organizer_response = client.get(
        f"/api/meetings/{meeting.id}",
        headers=_auth_header(_make_token(organizer)),
    )
    participant_response = client.get(
        f"/api/meetings/{meeting.id}",
        headers=_auth_header(_make_token(participant)),
    )
    outsider_response = client.get(
        f"/api/meetings/{meeting.id}",
        headers=_auth_header(_make_token(outsider)),
    )

    assert organizer_response.status_code == 200
    assert organizer_response.json()["id"] == meeting.id
    assert participant_response.status_code == 200
    assert outsider_response.status_code == 403


def test_reschedule_meeting_resets_reminders_and_sends_again_at_new_24h_window(
    client,
    db_session,
    monkeypatch,
):
    user = _create_calendar_user(db_session, "reschedule-reminder")
    room = _create_room(db_session, "Reschedule Room")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    old_start = now + timedelta(hours=72)
    new_start = now + timedelta(hours=48)
    meeting = Meeting(
        title="Rescheduled meeting",
        room_id=room.id,
        organizer_id=user.id,
        start_time=old_start,
        end_time=old_start + timedelta(hours=1),
        status="CONFIRMED",
        is_reminded_24h=True,
        is_reminded_15m=True,
    )
    db_session.add(meeting)
    db_session.commit()
    meeting_id = meeting.id
    monkeypatch.setattr(meetings_router, "sync_event_task", lambda *args: None)
    monkeypatch.setattr(
        meetings_router,
        "send_meeting_notification_task",
        lambda *args: None,
    )

    response = client.patch(
        f"/api/meetings/{meeting_id}",
        headers=_auth_header(_make_token(user)),
        json={
            "start_time": new_start.replace(tzinfo=timezone.utc).isoformat(),
            "end_time": (new_start + timedelta(hours=1))
            .replace(tzinfo=timezone.utc)
            .isoformat(),
        },
    )

    assert response.status_code == 200
    db_session.refresh(meeting)
    assert meeting.is_reminded_24h is False
    assert meeting.is_reminded_15m is False

    reminder_now = new_start - timedelta(hours=24) + timedelta(seconds=30)
    assert (
        reminder_service.process_due_meeting_reminders(db_session, reminder_now)
        == 1
    )
    db_session.refresh(meeting)
    assert meeting.is_reminded_24h is True
    assert db_session.query(Notification).filter_by(
        meeting_id=meeting_id,
        user_id=user.id,
    ).count() == 1


def test_reschedule_within_24_hours_skips_the_missed_24h_reminder(
    client,
    db_session,
    monkeypatch,
):
    user = _create_calendar_user(db_session, "reschedule-near")
    room = _create_room(db_session, "Reschedule Near Room")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    old_start = now + timedelta(days=2)
    new_start = now + timedelta(hours=12)
    meeting = Meeting(
        title="Near rescheduled meeting",
        room_id=room.id,
        organizer_id=user.id,
        start_time=old_start,
        end_time=old_start + timedelta(hours=1),
        status="CONFIRMED",
        is_reminded_24h=True,
        is_reminded_15m=True,
    )
    db_session.add(meeting)
    db_session.commit()
    monkeypatch.setattr(meetings_router, "sync_event_task", lambda *args: None)
    monkeypatch.setattr(
        meetings_router,
        "send_meeting_notification_task",
        lambda *args: None,
    )

    response = client.patch(
        f"/api/meetings/{meeting.id}",
        headers=_auth_header(_make_token(user)),
        json={
            "start_time": new_start.replace(tzinfo=timezone.utc).isoformat(),
            "end_time": (new_start + timedelta(hours=1))
            .replace(tzinfo=timezone.utc)
            .isoformat(),
        },
    )

    assert response.status_code == 200
    db_session.refresh(meeting)
    assert meeting.is_reminded_24h is True
    assert meeting.is_reminded_15m is False
