"""
Builds .ass caption cues from Edge-TTS word-level timing (voiceover.py).

Anchor modes:
  "center"      — plain dark background (WYR intro + pick/reason beat).
                  Uses a large \\fs override so "WOULD YOU RATHER" fills
                  the screen in 2 words at a time.
  "top_half"    — mid-way of the top image box (option A).
  "bottom_half" — mid-way of the bottom image box (option B).

All cues use explicit \\pos() so ASS [Styles] margins don't matter.
"""
import config

COLOR_HEX = {  # ASS uses &HBBGGRR& (BGR order, not RGB)
    "red":    "&H0000FF&",
    "blue":   "&HFF0000&",
    "green":  "&H00A000&",
    "yellow": "&H00FFFF&",
    "cyan":   "&HFFFF00&",
    "orange": "&H00A5FF&",
    "pink":   "&HB469FF&",
    "white":  "&HFFFFFF&",
}
DEFAULT_COLOR = "&HFFFFFF&"  # white

ANCHOR_Y = {
    # Vertical centre of the plain dark frame — WYR intro & pick/reason
    "center":      960,
    # Mid-way inside the top image box (clear of the OR badge at y=960)
    "top_half":    480,
    # Mid-way inside the bottom image box
    "bottom_half": 1440,
}

# Font sizes per anchor (injected as \fs ASS inline override)
ANCHOR_FS = {
    "center":      130,   # big, fills the dark screen
    "top_half":    90,    # readable but doesn't cover the whole image
    "bottom_half": 90,
}

# Words shown at once per anchor
ANCHOR_WPC = {
    "center":      2,   # 2 words at a time — impactful on the plain bg
    "top_half":    3,
    "bottom_half": 3,
}

ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Poppins Bold,110,&HFFFFFF&,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,0,5,40,40,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _format_ass_timestamp(seconds: float) -> str:
    cs = int((seconds - int(seconds)) * 100)
    s  = int(seconds) % 60
    m  = (int(seconds) // 60) % 60
    h  = int(seconds) // 3600
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def _clean_word(word: str) -> str:
    return word.strip().strip(".,!?\"'").lower()


def _colored_word_text(word: str, color_map: dict) -> str:
    clean   = _clean_word(word)
    color   = color_map.get(clean)
    display = word.strip().upper()
    if color and color in COLOR_HEX:
        return f"{{\\c{COLOR_HEX[color]}}}{display}{{\\c{DEFAULT_COLOR}}}"
    return display


def new_ass_file() -> list:
    return [ASS_HEADER]


def add_segment(
    lines: list, word_timings: list, global_offset: float, anchor: str,
    color_map: dict = None, words_per_cue: int = None,
):
    """Appends dialogue cues for one audio segment to `lines`.

    word_timings: list of {"word", "start", "end"} relative to this clip's
    own t=0.  global_offset shifts them into the full concatenated timeline.
    """
    color_map    = color_map or {}
    y            = ANCHOR_Y.get(anchor, ANCHOR_Y["center"])
    fs           = ANCHOR_FS.get(anchor, 110)
    wpc          = words_per_cue or ANCHOR_WPC.get(anchor, 3)

    for i in range(0, len(word_timings), wpc):
        chunk = word_timings[i:i + wpc]
        if not chunk:
            continue
        text  = " ".join(_colored_word_text(w["word"], color_map) for w in chunk)
        start = _format_ass_timestamp(chunk[0]["start"] + global_offset)
        end   = _format_ass_timestamp(chunk[-1]["end"]  + global_offset)
        # \\fs overrides the style font size per cue; \\fad adds a 60 ms fade
        lines.append(
            f"Dialogue: 0,{start},{end},Default,,0,0,0,,"
            f"{{\\pos(540,{y})\\fs{fs}\\fad(60,60)}}{text}\n"
        )


def write_ass_file(lines: list, out_path: str) -> str:
    with open(out_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return out_path
