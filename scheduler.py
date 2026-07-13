"""
Scheduler: determines the next upload slot for the Would You Rather channel.
Publishes daily at PUBLISH_HOUR_UTC (default 16:00 UTC = 21:30 IST).
If that slot today has already passed, returns the same slot for tomorrow.
"""
import config
from datetime import datetime, timezone, timedelta


def get_next_publish_slot() -> datetime:
    """Returns a UTC datetime for the next available publish slot."""
    now = datetime.now(timezone.utc)
    candidate = now.replace(
        hour=config.PUBLISH_HOUR_UTC,
        minute=0,
        second=0,
        microsecond=0,
    )
    # If today's slot has already passed (or is < 5 min away), push to tomorrow
    if candidate <= now + timedelta(minutes=5):
        candidate += timedelta(days=1)
    return candidate
