"""Time and timestamp helpers.

All helpers operate on timezone-aware UTC datetimes and ISO 8601 strings.
"""

from __future__ import annotations

from datetime import datetime, timezone


def now_utc() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


def parse_iso(ts: str | datetime) -> datetime:
    """Parse an ISO 8601 string (or passthrough a datetime) into aware UTC."""
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)
    parsed = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def to_iso(dt: datetime) -> str:
    """Serialize a datetime to an ISO 8601 UTC string."""
    aware = dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)
    return aware.astimezone(timezone.utc).isoformat()


def since_now(dt: datetime) -> float:
    """Return seconds elapsed between ``dt`` and now (positive when in past)."""
    return (now_utc() - parse_iso(dt)).total_seconds()