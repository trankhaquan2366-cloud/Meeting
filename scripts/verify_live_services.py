"""Verify live SMTP delivery and measure a real calendar event sync."""

import argparse
import logging
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from app.core.database import SessionLocal  # noqa: E402
from app.core.meeting_events import (  # noqa: E402
    EVENT_MEETING_CREATED,
    EVENT_MEETING_UPDATED,
)
from app.models.calendar import UserCalendarToken  # noqa: E402
from app.models.meeting import Meeting, MeetingParticipant  # noqa: E402
from app.services import calendar_sync_service, email_service  # noqa: E402
from app.models.user import User  # noqa: E402


_SLA_SECONDS = 5.0


def _verify_smtp(recipient: str) -> bool:
    try:
        settings = email_service.get_smtp_settings()
        if settings is None:
            raise ValueError("SMTP settings are missing from .env")
        email_service.send_email(
            recipient,
            "RoomSync live SMTP verification",
            "This is a live SMTP configuration test from RoomSync.",
            settings,
        )
    except Exception as exc:
        print(f"SMTP: FAIL ({type(exc).__name__}: {exc})")
        return False

    print(f"SMTP: PASS (test message accepted for {recipient})")
    return True


def _connected_calendar_count(meeting_id: int) -> int:
    db = SessionLocal()
    try:
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).one_or_none()
        if meeting is None:
            raise ValueError(f"Meeting {meeting_id} was not found")

        recipient_ids = {meeting.organizer_id}
        recipient_ids.update(
            user_id
            for (user_id,) in (
                db.query(MeetingParticipant.user_id)
                .filter(MeetingParticipant.meeting_id == meeting_id)
                .all()
            )
        )
        return (
            db.query(UserCalendarToken)
            .join(User, User.id == UserCalendarToken.user_id)
            .filter(
                UserCalendarToken.user_id.in_(recipient_ids),
                UserCalendarToken.is_active.is_(True),
                User.is_active.is_(True),
            )
            .count()
        )
    finally:
        db.close()


def _verify_calendar(meeting_id: int, event_type: str) -> bool:
    try:
        linked_calendars = _connected_calendar_count(meeting_id)
        if linked_calendars == 0:
            raise ValueError(
                "No active Google/Outlook calendar is connected to a meeting "
                "organizer or participant"
            )
    except Exception as exc:
        print(f"Calendar preflight: FAIL ({type(exc).__name__}: {exc})")
        return False

    provider_calls: list[tuple[str, float, str | None]] = []
    original_request = calendar_sync_service._provider_event_request

    def timed_provider_request(provider, access_token, method, **kwargs):
        started_at = time.perf_counter()
        try:
            result = original_request(
                provider,
                access_token,
                method,
                **kwargs,
            )
        except Exception as exc:
            provider_calls.append(
                (f"{provider} {method}", time.perf_counter() - started_at, str(exc))
            )
            raise
        provider_calls.append(
            (f"{provider} {method}", time.perf_counter() - started_at, None)
        )
        return result

    calendar_sync_service._provider_event_request = timed_provider_request
    started_at = time.perf_counter()
    try:
        calendar_sync_service.sync_event_task(meeting_id, event_type)
    except Exception as exc:
        print(f"Calendar sync: FAIL ({type(exc).__name__}: {exc})")
        return False
    finally:
        elapsed = time.perf_counter() - started_at
        calendar_sync_service._provider_event_request = original_request

    for label, seconds, error in provider_calls:
        result = "PASS" if error is None and seconds < _SLA_SECONDS else "FAIL"
        detail = f"; error={error}" if error else ""
        print(f"{label}: {seconds * 1000:.1f} ms ({result}{detail})")

    total_ms = elapsed * 1000
    success = bool(provider_calls) and all(
        error is None and seconds < _SLA_SECONDS
        for _, seconds, error in provider_calls
    )
    success = success and elapsed < _SLA_SECONDS
    print(
        f"Calendar sync total: {total_ms:.1f} ms; "
        f"provider calls={len(provider_calls)}; "
        f"connected calendars={linked_calendars}; "
        f"SLA < 5000 ms: {'PASS' if success else 'FAIL'}"
    )
    if not provider_calls:
        print("Calendar sync: FAIL (no provider API request was made)")
    return success


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(
        description="Send a live SMTP test and measure calendar provider sync latency."
    )
    parser.add_argument(
        "--email",
        required=True,
        help="Mailbox that should receive the live SMTP verification message",
    )
    parser.add_argument(
        "--meeting-id",
        type=int,
        required=True,
        help="Existing meeting with at least one connected calendar account",
    )
    parser.add_argument(
        "--event",
        choices=("create", "update"),
        default="update",
        help="Calendar operation to run (default: update)",
    )
    args = parser.parse_args()
    event_type = (
        EVENT_MEETING_CREATED if args.event == "create" else EVENT_MEETING_UPDATED
    )

    smtp_ok = _verify_smtp(args.email)
    calendar_ok = _verify_calendar(args.meeting_id, event_type)
    return 0 if smtp_ok and calendar_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
