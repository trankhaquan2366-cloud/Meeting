from datetime import datetime, timedelta, timezone


VIETNAM_TZ = timezone(timedelta(hours=7))


def normalize_to_utc_naive(value: datetime) -> datetime:
    """Normalize timestamps for storage in timezone-naive UTC database columns."""
    localized = value.replace(tzinfo=VIETNAM_TZ) if value.tzinfo is None else value
    return localized.astimezone(timezone.utc).replace(tzinfo=None)


def as_utc_aware(value: datetime) -> datetime:
    """Mark naive database timestamps as UTC for API serialization."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
