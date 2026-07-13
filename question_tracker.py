"""
Tracks which "Would You Rather" question pairs have already been used, so the
same pair doesn't repeat across videos. Same rolling-window pattern as the
other channels' topic/matchup trackers.
"""
import os
import json

STATE_PATH = os.path.join("state", "used_questions.json")
MAX_HISTORY = 150


def _key(option_a_text: str, option_b_text: str) -> str:
    pair = sorted([option_a_text.strip().lower(), option_b_text.strip().lower()])
    return f"{pair[0]}::{pair[1]}"


def load_used_questions() -> list:
    if not os.path.exists(STATE_PATH):
        return []
    with open(STATE_PATH) as f:
        return json.load(f)


def save_used_question(option_a_text: str, option_b_text: str):
    used = load_used_questions()
    used.append(_key(option_a_text, option_b_text))
    used = used[-MAX_HISTORY:]
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump(used, f, indent=2)


def is_duplicate(option_a_text: str, option_b_text: str, used: list) -> bool:
    return _key(option_a_text, option_b_text) in used
