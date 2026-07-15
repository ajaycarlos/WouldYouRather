"""
Stage 4 — Subtitle Builder

Reads the timed scene list from master_timing.json.
Writes ONE master.ass covering the complete video.

Smart chunking replaces the old fixed-word-count chunking.
Words are grouped by natural sentence breaks, punctuation, and
inter-word pause gaps — not arbitrary word counts.
This prevents "WOULD YOU" / "RATHER..." fragmentation and makes
long host opinions readable as phrases instead of word debris.

Subtitle Y positions are placed in the COLOUR STRIPS (above/below
the image box), not at the image mid-point.
"""
import json
import os
import shutil

# ── ASS constants ──────────────────────────────────────────────────────────────
COLOR_HEX = {   # ASS BGR order (\&HBBGGRR\&)
    "red":    "&H0000FF&",
    "blue":   "&HFF0000&",
    "green":  "&H00A000&",
    "yellow": "&H00FFFF&",
    "cyan":   "&HFFFF00&",
    "orange": "&H00A5FF&",
    "pink":   "&HB469FF&",
    "white":  "&HFFFFFF&",
}
DEFAULT_COLOR = "&HFFFFFF&"
HIGHLIGHT_COLOR = "&H00FFFF&"  # standard yellow

# visual_gen canvas: 1080×1920, HALF_H=960, IMG_H=480, IMG_PAD_V=240
# Top colour strip:    y ∈ [0,   240]  → centre y = 120
# Top image:           y ∈ [240, 720]
# Divider / OR badge:  y = 960
# Bottom image:        y ∈ [1200,1680]
# Bottom colour strip: y ∈ [1680,1920] → centre y = 1800
ANCHOR_Y = {
    "center":      960,   # plain dark background — dead centre
    "top_half":    120,   # colour strip above Option A image
    "bottom_half": 1800,  # colour strip below Option B image
}
ANCHOR_FS = {
    "center":      150,   # big impact on plain dark screen
    "top_half":    115,   # punchy inside colour strip
    "bottom_half": 115,
}
# Group subtitles according to natural speech (Issue 5 fix)
ANCHOR_MAX_WORDS = {
    "center":      5,
    "top_half":    5,
    "bottom_half": 5,
}

ASS_HEADER = """\
[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Lilita One,110,&HFFFFFF&,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,3,0,5,40,40,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


# ── Helpers ────────────────────────────────────────────────────────────────────

def _ts(seconds: float) -> str:
    cs  = int((seconds % 1) * 100)
    s   = int(seconds) % 60
    m   = (int(seconds) // 60) % 60
    h   = int(seconds) // 3600
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _clean(word: str) -> str:
    return word.strip().strip('.,!?"\'').lower()


def _clean(word: str) -> str:
    return word.strip().strip('.,!?"\'').lower()


def _smart_chunk(word_timings: list, max_words: int,
                 gap_threshold: float = 0.18) -> list:
    """
    Groups word_timings into cue-chunks by natural sentence structure.

    Break rules (evaluated in priority order):
      1. After a sentence-ending word (ends with . ! ?)
      2. After a clause-ending word (ends with ,) when chunk is ≥ 3 words
      3. When the gap to the next word exceeds gap_threshold seconds
      4. When max_words is reached

    This keeps "Would you rather..." as ONE cue instead of splitting it,
    and keeps host opinions as readable phrases.
    """
    if not word_timings:
        return []

    chunks, current = [], [word_timings[0]]

    for i in range(1, len(word_timings)):
        prev = word_timings[i - 1]
        curr = word_timings[i]
        pw   = prev["word"].rstrip()

        ends_sentence = pw.endswith((".", "!", "?"))
        ends_clause   = pw.endswith(",") and len(current) >= 3
        gap_break     = (curr["start"] - prev["end"]) > gap_threshold
        word_limit    = len(current) >= max_words

        if ends_sentence or ends_clause or gap_break or word_limit:
            chunks.append(current)
            current = [curr]
        else:
            current.append(curr)

    if current:
        chunks.append(current)

    return chunks


def _cue(y: int, fs: int, start: float, end: float,
         words: list, color_map: dict) -> str:
    
    # Ensure cue is long enough for the animation to play out (min 0.20s total)
    if end - start < 0.20:
        end = start + 0.20

    # Pop animation with spring back (Issue 7 and 4 fix)
    # Total animation shouldn't exceed half the cue's duration (so it reaches 100% scale quickly)
    cue_dur_ms = int((end - start) * 1000)
    anim_time = min(150, int(cue_dur_ms * 0.5))
    t1 = int(anim_time * 0.4)
    t2 = anim_time
    # scale starts at 40%, jumps to 110%, settles at 100%
    pop = f"{{\\fscx40\\fscy40\\t(0,{t1},\\fscx110\\fscy110)\\t({t1},{t2},\\fscx100\\fscy100)}}"

    parts = []
    for w in words:
        w_start_ms = max(0, int((w["start"] - start) * 1000))
        w_end_ms   = max(0, int((w["end"] - start) * 1000))

        # Check if the word has a special static color
        clean = _clean(w["word"])
        special_color = color_map.get(clean)
        display = w["word"].strip().upper()

        if special_color and special_color in COLOR_HEX:
            target_color = COLOR_HEX[special_color]
        else:
            target_color = HIGHLIGHT_COLOR # yellow default highlight

        # Word-level highlight: turn target color when spoken, back to white when done
        # A smooth 50ms fade feels much more premium
        fade_in_end = min(w_start_ms + 50, w_end_ms)
        fade_out_end = w_end_ms + 50
        
        highlight = f"{{\\c{DEFAULT_COLOR}\\t({w_start_ms},{fade_in_end},\\c{target_color})\\t({w_end_ms},{fade_out_end},\\c{DEFAULT_COLOR})}}"
        parts.append(f"{highlight}{display}")

    text = " ".join(parts)
    return (
        f"Dialogue: 0,{_ts(start)},{_ts(end)},Default,,0,0,0,,"
        f"{{\\an5\\pos(540,{y})\\fs{fs}}}{pop}{text}\n"
    )


# ── Public API ─────────────────────────────────────────────────────────────────

def build_subtitles(timing_json_path: str, out_dir: str) -> str:
    """
    Reads master_timing.json. Writes master.ass.
    Returns path to master.ass.
    """
    with open(timing_json_path, encoding="utf-8") as f:
        data = json.load(f)

    scenes    = data["scenes"]
    ass_lines = [ASS_HEADER]

    for scene in scenes:
        anchor = scene.get("subtitle_anchor")
        if not anchor:
            continue

        word_timings = scene.get("word_timings", [])
        if not word_timings:
            continue

        y         = ANCHOR_Y[anchor]
        fs        = ANCHOR_FS[anchor]
        max_w     = ANCHOR_MAX_WORDS[anchor]
        color_map = scene.get("color_map", {})

        chunks = _smart_chunk(word_timings, max_words=max_w)

        for chunk in chunks:
            start = chunk[0]["start"]
            end   = chunk[-1]["end"]
            ass_lines.append(_cue(y, fs, start, end, chunk, color_map))

    ass_path = os.path.join(out_dir, "master.ass")
    with open(ass_path, "w", encoding="utf-8") as f:
        f.writelines(ass_lines)

    # Copy the Fredoka font into out_dir so fontsdir always resolves it
    import config as _cfg
    font_src  = _cfg.FONT_PATH
    font_dest = os.path.join(out_dir, os.path.basename(font_src))
    if not os.path.isfile(font_dest):
        shutil.copy2(font_src, font_dest)

    cue_count = sum(1 for l in ass_lines if l.startswith("Dialogue"))
    print(f"  [subtitles] master.ass written ({cue_count} cues)")
    return ass_path


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python subtitle_builder.py <master_timing.json> <out_dir>")
    else:
        build_subtitles(sys.argv[1], sys.argv[2])
