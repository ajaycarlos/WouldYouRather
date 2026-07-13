"""
Persists a local history log of every video uploaded: video ID, topic,
first-question text, title, and scheduled publish time. Used by analytics.py
to look up past video IDs for performance data.
"""
import os
import json

HISTORY_PATH = os.path.join("state", "history.json")


def save_entry(video_id: str, channel: str, first_question: str, title: str, publish_iso: str):
    entries = _load()
    entries.append({
        "video_id": video_id,
        "channel": channel,
        "first_question": first_question,
        "title": title,
        "published_at": publish_iso,
    })
    _save(entries)
    print(f"  History saved: {video_id}")


def load_all() -> list:
    return _load()


def _load() -> list:
    if not os.path.exists(HISTORY_PATH):
        return []
    with open(HISTORY_PATH) as f:
        return json.load(f)


def _save(entries: list):
    os.makedirs(os.path.dirname(HISTORY_PATH), exist_ok=True)
    with open(HISTORY_PATH, "w") as f:
        json.dump(entries, f, indent=2)
