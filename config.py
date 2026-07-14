import os
import urllib.request
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

EDGE_TTS_VOICE = os.getenv("EDGE_TTS_VOICE", "en-US-AndrewNeural")

# Pexels free API key - sign up at pexels.com/api, free, no cost, no commercial restriction
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

YT_CLIENT_SECRETS_FILE = os.getenv("YT_CLIENT_SECRETS_FILE", "client_secret.json")
YT_TOKEN_FILE          = os.getenv("YT_TOKEN_FILE", "yt_token.json")

ROUNDS_PER_VIDEO  = int(os.getenv("ROUNDS_PER_VIDEO", "3"))
VIDEOS_PER_RUN    = int(os.getenv("VIDEOS_PER_RUN", "1"))
MANUAL_REVIEW_GATE = os.getenv("MANUAL_REVIEW_GATE", "False").lower() == "true"

# Offset from channel 1 (08:00 UTC) and channel 2 (12:00 UTC) so all three
# don't contend for CPU/network if their runs overlap.
PUBLISH_HOUR_UTC = int(os.getenv("PUBLISH_HOUR_UTC", "16"))

TIMER_SECONDS = float(os.getenv("TIMER_SECONDS", "3.0"))

OUTPUT_DIR = "output"

# Percentage split range - never exactly 50/50 (less satisfying reveal), and
# never a total blowout (keeps the "which would you pick" tension real)
PERCENT_SPLIT_MIN = int(os.getenv("PERCENT_SPLIT_MIN", "55"))  # winning side's floor
PERCENT_SPLIT_MAX = int(os.getenv("PERCENT_SPLIT_MAX", "82"))  # winning side's ceiling


# ── Font resolution ───────────────────────────────────────────────────────────
# Try the user-configured path first, then common system locations, then
# download Poppins-Bold from the Google Fonts GitHub mirror as a last resort.
# A missing font causes PIL to fall back to an 8px bitmap that ignores size and
# stroke — the root cause of the invisible/tiny percentage text bug.

_FONT_SEARCH_PATHS = [
    os.path.expanduser(os.getenv("FONT_PATH", "~/.fonts/Poppins-Bold.ttf")),
    "/usr/share/fonts/truetype/poppins/Poppins-Bold.ttf",
    "/usr/share/fonts/poppins/Poppins-Bold.ttf",
    os.path.join(os.path.dirname(__file__), "Poppins-Bold.ttf"),
]

_POPPINS_URL = (
    "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-Bold.ttf"
)


def _resolve_font() -> str:
    # 1. Try known paths
    for path in _FONT_SEARCH_PATHS:
        if path and os.path.isfile(path):
            return path

    # 2. Auto-download to project root
    local_path = os.path.join(os.path.dirname(__file__), "Poppins-Bold.ttf")
    print(f"[config] Poppins-Bold.ttf not found — downloading from Google Fonts...")
    try:
        urllib.request.urlretrieve(_POPPINS_URL, local_path)
        if os.path.isfile(local_path) and os.path.getsize(local_path) > 10_000:
            print(f"[config] Font saved to {local_path}")
            return local_path
    except Exception as e:
        pass  # fall through to error below

    raise RuntimeError(
        "Could not locate or download Poppins-Bold.ttf.\n"
        "Fix: run  mkdir -p ~/.fonts && cp /path/to/Poppins-Bold.ttf ~/.fonts/\n"
        "     or set FONT_PATH=/absolute/path/to/any-bold.ttf in your .env"
    )


FONT_PATH = _resolve_font()
