"""
Builds .ass caption cues from Edge-TTS's exact word-level timing (voiceover.py).
Three anchor modes: "center" (plain background, e.g. "would you rather" line
and the pick/reason beat), "top_half" (anchored near the bottom of the top
image, for option A), "bottom_half" (anchored near the bottom of the bottom
image, for option B). Supports per-word color override for the "colored_words"
Gemini generates (e.g. "HOT" in red).

Because everything is built with explicit \\pos() overrides per line, no ASS
[Styles] margins are needed for positioning - only the base font/outline style.
"""
import config

COLOR_HEX = {  # ASS uses &HBBGGRR& (BGR order, not RGB)
    "red": "&H0000FF&",
    "blue": "&HFF0000&",
    "green": "&H00A000&",
    "yellow": "&H00FFFF&",
    "cyan": "&HFFFF00&",
    "orange": "&H00A5FF&",
    "pink": "&HB469FF&",
    "white": "&HFFFFFF&",
}
DEFAULT_COLOR = "&HFFFFFF&"  # white

ANCHOR_Y = {
    "center": 960,
    "top_half": 810,
    "bottom_half": 1770,
}

ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Poppins Bold,90,&HFFFFFF&,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,5,0,5,40,40,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _format_ass_timestamp(seconds: float) -> str:
    cs = int((seconds - int(seconds)) * 100)
    s = int(seconds) % 60
    m = (int(seconds) // 60) % 60
    h = int(seconds) // 3600
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def _clean_word(word: str) -> str:
    return word.strip().strip(".,!?\"'").lower()


def _colored_word_text(word: str, color_map: dict) -> str:
    clean = _clean_word(word)
    color = color_map.get(clean)
    display = word.strip().upper()
    if color and color in COLOR_HEX:
        return f"{{\\c{COLOR_HEX[color]}}}{display}{{\\c{DEFAULT_COLOR}}}"
    return display


def new_ass_file() -> list:
    return [ASS_HEADER]


def add_segment(
    lines: list, word_timings: list, global_offset: float, anchor: str,
    color_map: dict = None, words_per_cue: int = 3,
):
    """Appends dialogue cues for one audio segment to the growing `lines` list.
    word_timings: from voiceover.generate_voiceover(), times relative to this
    clip's own start (0.0) - global_offset shifts them into the full video's
    timeline (needed since clips are concatenated one after another)."""
    color_map = color_map or {}
    y = ANCHOR_Y.get(anchor, ANCHOR_Y["center"])

    for i in range(0, len(word_timings), words_per_cue):
        chunk = word_timings[i:i + words_per_cue]
        if not chunk:
            continue
        text = " ".join(_colored_word_text(w["word"], color_map) for w in chunk)
        start = _format_ass_timestamp(chunk[0]["start"] + global_offset)
        end = _format_ass_timestamp(chunk[-1]["end"] + global_offset)
        lines.append(
            f"Dialogue: 0,{start},{end},Default,,0,0,0,,{{\\pos(540,{y})\\fad(60,60)}}{text}\n"
        )


def write_ass_file(lines: list, out_path: str) -> str:
    with open(out_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return out_path
