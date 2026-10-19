import logging
from collections.abc import Callable, Sequence

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.models.meeting import Meeting
from app.models.user import User
from app.services.calendar_email_service import request_calendar_access_for_invitees
from app.services.email_service import send_meeting_invitation_email
from app.services.google_calendar_service import sync_user_meetings_to_google
from app.services.notification_service import send_meeting_invitation_notifications

logger = logging.getLogger(__name__)
InvitationEmailSender = Callable[..., None]
InvitationCalendarSync = Callable[..., None]


def schedule_meeting_invitations(
    background_tasks: BackgroundTasks,
    db: Session,
    meetings: Sequence[Meeting],
    participant_ids: Sequence[int],
    organizer: User,
    *,
    calendar_sync: InvitationCalendarSync | None = None,
    calendar_access_request: InvitationCalendarSync | None = None,
    email_sender: InvitationEmailSender | None = None,
) -> None:
    if not meetings:
        return

    if organizer.google_refresh_token:
        background_tasks.add_task(
            calendar_sync or sync_user_meetings_to_google,
            organizer.id,
        )

    first_meeting = meetings[0]
    notify_ids = sorted(
        {participant_id for participant_id in participant_ids if participant_id != organizer.id}
    )
    if not notify_ids:
        return

    start_str = first_meeting.start_time.strftime("%H:%M %d/%m/%Y")
    background_tasks.add_task(
        send_meeting_invitation_notifications,
        db=db,
        participant_ids=notify_ids,
        meeting_title=first_meeting.title,
        start_time_str=start_str,
        meeting_id=first_meeting.id,
    )
    background_tasks.add_task(
        calendar_access_request or request_calendar_access_for_invitees,
        user_ids=notify_ids,
        meeting_ids=[meeting.id for meeting in meetings],
    )

    if first_meeting.room is not None:
        location = f"Phòng {first_meeting.room.name}"
    elif first_meeting.meeting_link:
        location = f"Trực tuyến ({first_meeting.meeting_link})"
    else:
        location = "Trực tuyến"

    invitees = db.query(User).filter(User.id.in_(notify_ids)).all()
    for invitee in invitees:
        if not invitee.email:
            logger.warning(
                "Meeting invitation email skipped: user_id=%s has no email",
                invitee.id,
            )
            continue
        background_tasks.add_task(
            email_sender or send_meeting_invitation_email,
            to_email=invitee.email,
            user_name=invitee.full_name or invitee.username,
            meeting_title=first_meeting.title,
            start_time_str=start_str,
            location_str=location,
            meeting_link=first_meeting.meeting_link,
            meeting_id=first_meeting.id,
            start_time=first_meeting.start_time,
            end_time=first_meeting.end_time,
            organizer_email=organizer.email,
            organizer_name=organizer.full_name or organizer.username,
        )
