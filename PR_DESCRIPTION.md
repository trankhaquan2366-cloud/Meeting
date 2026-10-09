# Pull Request: Calendar sync and meeting reminders

## Summary

- Added Google and Outlook OAuth connection flows with encrypted token storage,
  refresh support, and background calendar event create/update/delete sync.
- Added in-app and optional SMTP meeting reminders 24 hours and 15 minutes
  before meetings, including catch-up scanning and a persistent email retry queue.
- Added a MySQL named lock with a cross-process file-lock fallback on the same host.
- Normalized meeting lifecycle values to `CONFIRMED`, `COMPLETED`, and
  `CANCELLED`, and normalized meeting timestamps to UTC.
- Added recurrence series identity and provider-specific recurring calendar sync.
- Added migrations `001` through `013`; apply them in numeric order as described
  in `README.md`.

## Technical Exception Note for Core Team (Group A)

This branch touches the core meeting files to connect the independent
notification/calendar services to the meeting lifecycle:

- `app/routers/meetings.py` schedules lifecycle hooks using FastAPI
  `BackgroundTasks` after database changes succeed.
- `app/services/meeting_service.py` creates meetings with the shared
  `CONFIRMED` status and maintains recurring-meeting identity.
- `app/models/meeting.py` adds `series_id` and occurrence identity needed to
  synchronize recurring meetings and individual occurrences correctly.

These changes are required for reminder/calendar behavior and recurrence
mapping. Please review and preserve the hook, status, and series identity changes
when merging this branch into `dev`; resolve conflicts together with the feature
owner rather than dropping the inserted lines.

## QA: local E2E environment

1. Copy `.env.example` to `.env`; keep `.env` out of source control.
2. Configure SMTP with a test mailbox/provider:
   `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME` (or `SMTP_USER`),
   `SMTP_PASSWORD`, and `SMTP_FROM_EMAIL`. For Gmail, use an App Password,
   not the account login password.
3. Register Google and/or Microsoft Entra OAuth applications and set
   `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`,
   `OUTLOOK_CLIENT_ID`, `OUTLOOK_CLIENT_SECRET`, and `OUTLOOK_REDIRECT_URI`.
   Register the same callback URL configured in the app.
4. Generate `CALENDAR_TOKEN_ENCRYPTION_KEY` with Fernet and retain the same key
   across restarts; changing it makes existing stored tokens unreadable.
5. Apply database migrations `001` through `013` in order with
   `python scripts/apply_db_migrations.py` on MySQL. This command also tests the
   named lock. On SQLite or another non-MySQL database, the scheduler uses a
   host-local file lock; it does not coordinate between different hosts.
6. Connect a test account through the dashboard and run
   `python scripts/verify_live_services.py --email qa@example.com --meeting-id 123`.
   This sends one real SMTP test message and measures live calendar API response
   times. Verify event create/update/cancel separately in the provider account.

Do not paste credentials into the PR or commit `.env`. Live provider and SMTP
E2E results must be recorded by QA after running with approved test credentials;
automated tests use mocked provider and SMTP responses.

## Verification

- Automated tests cover lifecycle hooks, calendar sync, reminder catch-up,
  email retry queue behavior, and local scheduler locking.
- Confirm the complete test suite and migration application in CI/staging before
  merge.
