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
# Fredoka One: rounded, bold, perfect for YouTube Shorts punch-text style.
# Falls back to Poppins-Bold if already present, then auto-downloads Fredoka.

_FONT_SEARCH_PATHS = [
    os.path.join(os.path.dirname(__file__), "FredokaOne-Regular.ttf"),
    os.path.expanduser("~/.fonts/FredokaOne-Regular.ttf"),
    # Poppins fallback (already downloaded in a previous session)
    os.path.expanduser(os.getenv("FONT_PATH", "~/.fonts/Poppins-Bold.ttf")),
    os.path.join(os.path.dirname(__file__), "Poppins-Bold.ttf"),
]

_FREDOKA_URL = (
    "https://github.com/google/fonts/raw/main/ofl/fredokaone/FredokaOne-Regular.ttf"
)


def _resolve_font() -> str:
    # 1. Try known paths (Fredoka One first, Poppins as fallback)
    for path in _FONT_SEARCH_PATHS:
        if path and os.path.isfile(path):
            print(f"[config] Font: {os.path.basename(path)}")
            return path

    # 2. Auto-download Fredoka One to project root
    local_path = os.path.join(os.path.dirname(__file__), "FredokaOne-Regular.ttf")
    print("[config] FredokaOne-Regular.ttf not found — downloading from Google Fonts...")
    try:
        urllib.request.urlretrieve(_FREDOKA_URL, local_path)
        if os.path.isfile(local_path) and os.path.getsize(local_path) > 10_000:
            print(f"[config] Font saved to {local_path}")
            return local_path
    except Exception:
        pass

    raise RuntimeError(
        "Could not locate or download FredokaOne-Regular.ttf.\n"
        "Fix: place FredokaOne-Regular.ttf in the project directory\n"
        "     or set FONT_PATH=/absolute/path/to/any-bold.ttf in your .env"
    )


FONT_PATH = _resolve_font()
