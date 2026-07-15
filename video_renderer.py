"""
Stage 5 — Video Renderer (with Dynamic Transitions)

Single-pass FFmpeg render with xfade transitions between scene groups.

Transition strategy (CPU-efficient — no zoompan):
  - Consecutive scenes sharing the same frame are merged into one segment.
    This reduces 19 individual clips to ~10 grouped segments.
  - xfade transitions are applied between segments where the frame changes:
      plain  → split  : "fade"       0.20s  (split screen appears)
      split  → reveal : "fadewhite"  0.15s  (flash then percentages revealed)
      reveal → plain  : "fadeblack"  0.20s  (clean break between rounds)
  - "fade", "fadeblack", "fadewhite" are the lightest xfade modes — pure
    alpha blend, no pixel remapping. Negligible CPU overhead.

Audio stays as master.wav (unchanged). The total transition duration borrowed
(~1.5s) means the last frame holds for that long after audio ends — on a
looping Short this is invisible.
"""
import json
import os
import subprocess


def _run(cmd: list, label: str = ""):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        tag = f" [{label}]" if label else ""
        raise RuntimeError(f"FFmpeg error{tag}:\n{result.stderr[-4000:]}")


def _pick_transition(from_id: str, to_id: str) -> tuple:
    """
    Returns (xfade_name, duration_seconds) for the boundary between two scenes.
    Kept to 3 fast alpha-blend modes only — no pixel-remap filters.
    """
    from_reveal = "reveal" in from_id
    from_plain  = ("wyr" in from_id) or ("outro" in from_id)
    to_split    = "option" in to_id or "or" in to_id or "tick" in to_id
    to_reveal   = "reveal" in to_id
    to_plain    = ("wyr" in to_id) or ("outro" in to_id)

    if from_plain and to_split:
        return "fade", 0.20           # split screen appears
    if to_reveal:
        return "fadewhite", 0.15      # white flash → reveal percentages
    if to_plain or from_reveal:
        return "fadeblack", 0.20      # dark cut between rounds
    return "fade", 0.15               # fallback


def _group_scenes(scenes: list) -> list:
    """
    Merge consecutive scenes that share the same frame into one segment.
    Each segment: {frame, duration, first_id, last_id, scenes[]}.
    """
    groups = []
    for scene in scenes:
        dur = round(scene["global_end"] - scene["global_start"], 6)
        if dur <= 0:
            dur = 0.05
        if groups and groups[-1]["frame"] == scene["frame"]:
            groups[-1]["duration"]  = round(groups[-1]["duration"] + dur, 6)
            groups[-1]["last_id"]   = scene["id"]
            groups[-1]["scenes"].append(scene)
        else:
            groups.append({
                "frame":    scene["frame"],
                "duration": dur,
                "first_id": scene["id"],
                "last_id":  scene["id"],
                "scenes":   [scene],
            })
    return groups


def _build_filtergraph(groups: list, ass_escaped: str,
                        fonts_escaped: str = "") -> str:
    """
    Builds the filter_complex string:
      1. Scale each group's input to 1080×1920.
      2. Chain xfade between every consecutive group pair.
      3. Burn ASS subtitles on the combined stream.

    xfade offset math:
      After each xfade, the output timeline grows by (seg_duration - xf_dur).
      The NEXT xfade's offset = current accumulated output length - next xf_dur.
    """
    n      = len(groups)
    lines  = []

    # Step 1 — scale all inputs
    for i in range(n):
        lines.append(
            f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
            f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[vs{i}]"
        )

    if n == 1:
        fd = f":fontsdir='{fonts_escaped}'" if fonts_escaped else ""
        lines.append(f"[vs0]ass='{ass_escaped}'{fd}[vout]")
        return ";\n".join(lines)

    # Step 2 — chain xfades
    # timeline_end tracks where the OUTPUT stream currently ends
    timeline_end = groups[0]["duration"]
    prev_label   = "vs0"

    for k in range(1, n):
        xf_name, xf_dur = _pick_transition(groups[k-1]["last_id"],
                                            groups[k]["first_id"])
        # Clamp so transition never exceeds 80% of the shorter segment
        xf_dur = min(xf_dur,
                     groups[k-1]["duration"] * 0.8,
                     groups[k]["duration"]   * 0.8)
        offset    = max(0.0, round(timeline_end - xf_dur, 6))
        out_label = f"xf{k}" if k < n - 1 else "vcombined"

        lines.append(
            f"[{prev_label}][vs{k}]xfade=transition={xf_name}:"
            f"duration={xf_dur:.4f}:offset={offset:.4f}[{out_label}]"
        )
        timeline_end += groups[k]["duration"] - xf_dur
        prev_label    = out_label

    # Step 3 — burn subtitles with fontsdir so libass finds bundled font
    fd = f":fontsdir='{fonts_escaped}'" if fonts_escaped else ""
    lines.append(f"[vcombined]ass='{ass_escaped}'{fd}[vout]")
    return ";\n".join(lines)


def render_video(timing_json_path: str, master_wav: str, master_ass: str,
                 final_out: str) -> str:
    """Renders the final video. Returns path to final_out."""
    with open(timing_json_path, encoding="utf-8") as f:
        data = json.load(f)

    scenes  = data["scenes"]
    out_dir = os.path.dirname(timing_json_path)
    groups  = _group_scenes(scenes)
    n       = len(groups)

    print(f"  [render] {len(scenes)} scenes → {n} segments "
          f"(merged same-frame) + {n-1} xfade transitions")

    # ── FFmpeg inputs: one per SEGMENT (not per scene) ────────────────────────
    cmd = ["ffmpeg", "-y"]
    for grp in groups:
        cmd += ["-loop", "1", "-framerate", "30",
                "-t", str(grp["duration"]),
                "-i", os.path.abspath(grp["frame"])]
    cmd += ["-i", os.path.abspath(master_wav)]

    # ── Filtergraph ────────────────────────────────────────────────────────────
    # ASS filter with fontsdir so libass finds our bundled Fredoka font
    # without requiring it to be installed system-wide.
    ass_abs     = os.path.abspath(master_ass)
    fonts_dir   = os.path.dirname(os.path.abspath(master_ass))
    # On Linux: colons in path need escaping for ffmpeg filter options
    ass_escaped   = ass_abs.replace("\\", "/").replace(":", "\\:")
    fonts_escaped = fonts_dir.replace("\\", "/").replace(":", "\\:")
    filter_graph  = _build_filtergraph(groups, ass_escaped, fonts_escaped)

    filter_file = os.path.join(out_dir, "filter_complex.txt")
    with open(filter_file, "w", encoding="utf-8") as f:
        f.write(filter_graph)

    # ── Encode ────────────────────────────────────────────────────────────────
    cmd += [
        "-filter_complex_script", filter_file,
        "-map", "[vout]",
        "-map", f"{n}:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        final_out,
    ]

    print(f"  [render] Rendering with transitions → {final_out}...")
    _run(cmd, label="render")
    print(f"  [render] Done: {final_out}")
    return final_out
