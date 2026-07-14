import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

EDGE_TTS_VOICE = os.getenv("EDGE_TTS_VOICE", "en-US-AndrewNeural")

# Pexels free API key - sign up at pexels.com/api, free, no cost, no commercial restriction
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

YT_CLIENT_SECRETS_FILE = os.getenv("YT_CLIENT_SECRETS_FILE", "client_secret.json")
YT_TOKEN_FILE = os.getenv("YT_TOKEN_FILE", "yt_token.json")

ROUNDS_PER_VIDEO = int(os.getenv("ROUNDS_PER_VIDEO", "3"))
VIDEOS_PER_RUN = int(os.getenv("VIDEOS_PER_RUN", "1"))
MANUAL_REVIEW_GATE = os.getenv("MANUAL_REVIEW_GATE", "False").lower() == "true"

# Offset from channel 1 (08:00 UTC) and channel 2 (12:00 UTC) so all three
# don't contend for CPU/network if their runs overlap.
PUBLISH_HOUR_UTC = int(os.getenv("PUBLISH_HOUR_UTC", "16"))

TIMER_SECONDS = float(os.getenv("TIMER_SECONDS", "3.0"))
FONT_PATH = os.path.expanduser(os.getenv("FONT_PATH", "~/.fonts/Poppins-Bold.ttf"))

OUTPUT_DIR = "output"

# Percentage split range - never exactly 50/50 (less satisfying reveal), and
# never a total blowout (keeps the "which would you pick" tension real)
PERCENT_SPLIT_MIN = int(os.getenv("PERCENT_SPLIT_MIN", "55"))  # winning side's floor
PERCENT_SPLIT_MAX = int(os.getenv("PERCENT_SPLIT_MAX", "82"))  # winning side's ceiling
