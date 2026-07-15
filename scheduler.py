"""
Scheduler: determines the next upload slot for the Would You Rather channel.
Publishes daily at PUBLISH_HOUR_UTC.
If multiple videos are queued, it schedules them sequentially one day apart.
"""
import config
import history
from datetime import datetime, timezone, timedelta


def get_next_publish_slot() -> datetime:
    """Returns a UTC datetime for the next available publish slot."""
    now = datetime.now(timezone.utc)
    
    # 1. Calculate the base candidate based on current time
    candidate = now.replace(
        hour=config.PUBLISH_HOUR_UTC,
        minute=0,
        second=0,
        microsecond=0,
    )
    if candidate <= now + timedelta(minutes=5):
        candidate += timedelta(days=1)
        
    # 2. Check history to ensure we queue videos day-by-day
    entries = history.load_all()
    latest_future_dt = None
    
    for entry in entries:
        if "published_at" in entry:
            try:
                dt_str = entry["published_at"]
                if dt_str.endswith("Z"):
                    dt_str = dt_str[:-1] + "+00:00"
                dt = datetime.fromisoformat(dt_str)
                # Ensure timezone aware UTC
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if latest_future_dt is None or dt > latest_future_dt:
                    latest_future_dt = dt
            except Exception:
                pass
                
    # If a video is already queued for the candidate slot or later, push it forward
    if latest_future_dt and latest_future_dt >= candidate:
        return latest_future_dt + timedelta(days=1)

    return candidate
