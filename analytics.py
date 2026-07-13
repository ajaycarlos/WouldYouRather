"""
Analytics: fetches performance data (views, likes, watch time) for past
uploaded videos using the YouTube Analytics API. Used by main.py to pass
lightweight performance notes into the script_gen prompt so Gemini can
(lightly) steer toward what's working.

On first run, or if analytics aren't available yet (e.g., channel too new,
no videos yet), it returns an empty string gracefully rather than crashing.
"""
import os
import config
import history
from datetime import datetime, timezone, timedelta

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    ANALYTICS_SCOPES = ["https://www.googleapis.com/auth/yt-analytics.readonly"]

    def _get_analytics_service():
        if not os.path.exists(config.YT_TOKEN_FILE):
            return None
        creds = Credentials.from_authorized_user_file(
            config.YT_TOKEN_FILE,
            scopes=ANALYTICS_SCOPES + ["https://www.googleapis.com/auth/youtube.upload"],
        )
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        return build("youtubeAnalytics", "v2", credentials=creds)

except ImportError:
    def _get_analytics_service():
        return None


def get_performance_notes(lookback_days: int = 30, top_n: int = 3) -> str:
    """
    Returns a short human-readable string describing recent video performance,
    e.g. "Top performing themes in last 30 days: food choices, superpowers"
    Returns "" if analytics aren't available yet.
    """
    try:
        service = _get_analytics_service()
        if not service:
            return ""

        past = history.load_all()
        if not past:
            return ""

        recent = [
            e for e in past
            if _days_ago(e.get("published_at", "")) <= lookback_days
        ]
        if not recent:
            return ""

        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        start_date = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

        ids_csv = ",".join(e["video_id"] for e in recent[:20])  # API cap
        response = service.reports().query(
            ids="channel==MINE",
            startDate=start_date,
            endDate=end_date,
            metrics="views,averageViewDuration",
            dimensions="video",
            filters=f"video=={ids_csv}",
            sort="-views",
        ).execute()

        rows = response.get("rows", [])
        if not rows:
            return ""

        id_to_entry = {e["video_id"]: e for e in recent}
        top = []
        for row in rows[:top_n]:
            vid_id = row[0]
            if vid_id in id_to_entry:
                top.append(id_to_entry[vid_id].get("first_question", vid_id))

        if top:
            return f"Recent high-performing question themes: {'; '.join(top)}. Try similar energy/style."
        return ""

    except Exception as e:
        # Analytics failure is non-fatal - the pipeline continues without notes
        print(f"  Analytics skipped ({e})")
        return ""


def _days_ago(iso_str: str) -> int:
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days
    except Exception:
        return 9999
