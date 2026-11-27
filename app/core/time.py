"""Time helpers: store in UTC, display in India Standard Time."""

from datetime import UTC, datetime, timedelta, timezone

# India has no daylight saving, so a fixed offset is exact and needs no tz database.
IST = timezone(timedelta(hours=5, minutes=30), "IST")


def utc_now() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(UTC)


def to_ist(moment: datetime) -> datetime:
    """Convert an aware datetime to India Standard Time for display."""
    if moment.tzinfo is None:
        raise ValueError("to_ist needs a timezone-aware datetime; naive values are ambiguous")
    return moment.astimezone(IST)
