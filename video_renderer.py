"""
Stage 5 — Video Renderer

Single-pass FFmpeg render. No clip encoding. No concat demuxer.
No PTS discontinuities. No encoder-delay accumulation.

Inputs:
  - master_timing.json  (scene list with global_start / global_end per scene)
  - master.wav          (single continuous audio track)
  - master.ass          (single subtitle file with globally-correct timestamps)
  - PNG frames          (one per scene, referenced by scene["frame"])

Strategy:
  For each scene, loop its static image for exactly (global_end - global_start)
  seconds. Chain all image streams through FFmpeg's concat VIDEO FILTER
  (not the concat demuxer — the filter produces a single continuous PTS
  timeline with zero discontinuities). Map master.wav as the audio stream.
  Burn master.ass as a video filter INSIDE the filtergraph.

  The filter script is written to a temp file to avoid shell argument
  length limits for videos with many scenes.
"""
import json
import os
import subprocess


def _run(cmd: list, label: str = ""):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        tag = f" [{label}]" if label else ""
        raise RuntimeError(f"FFmpeg error{tag}:\n{result.stderr[-4000:]}")


def render_video(timing_json_path: str, master_wav: str, master_ass: str,
                 final_out: str) -> str:
    """
    Renders the final video in one FFmpeg pass.
    Returns path to final_out.
    """
    with open(timing_json_path, encoding="utf-8") as f:
        data = json.load(f)

    scenes   = data["scenes"]
    out_dir  = os.path.dirname(timing_json_path)
    n        = len(scenes)

    # ── Build FFmpeg inputs ────────────────────────────────────────────────────
    # One -loop 1 -t <dur> -i <frame> per scene, then master.wav last.
    # Identical frames can repeat (e.g. split_frame used by multiple scenes) —
    # FFmpeg handles this fine; they are separate input slots.
    cmd = ["ffmpeg", "-y"]
    for scene in scenes:
        dur = round(scene["global_end"] - scene["global_start"], 6)
        if dur <= 0:
            dur = 0.1   # guard against zero-duration scenes
        cmd += ["-loop", "1", "-framerate", "30", "-t", str(dur),
                "-i", os.path.abspath(scene["frame"])]
    cmd += ["-i", os.path.abspath(master_wav)]

    # ── Build filter_complex ───────────────────────────────────────────────────
    # Step 1: scale every input to exactly 1080×1920 (safety net for any
    #         frame that differs in size)
    scale_parts = []
    for i in range(n):
        scale_parts.append(
            f"[{i}:v]scale=1080:1920:force_original_aspect_ratio=decrease,"
            f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2[vs{i}]"
        )

    # Step 2: concat scaled streams
    concat_inputs = "".join(f"[vs{i}]" for i in range(n))
    concat_part   = f"{concat_inputs}concat=n={n}:v=1:a=0[vconcat]"

    # Step 3: burn subtitles (ASS path — colon must be escaped on all platforms)
    ass_abs     = os.path.abspath(master_ass)
    ass_escaped = ass_abs.replace("\\", "/").replace(":", "\\:")
    ass_part    = f"[vconcat]ass='{ass_escaped}'[vout]"

    filter_graph = ";\n".join(scale_parts + [concat_part, ass_part])

    # Write filter to file to avoid OS arg-length limits
    filter_file = os.path.join(out_dir, "filter_complex.txt")
    with open(filter_file, "w", encoding="utf-8") as f:
        f.write(filter_graph)

    # ── Assemble final command ─────────────────────────────────────────────────
    cmd += [
        "-filter_complex_script", filter_file,
        "-map", "[vout]",
        "-map", f"{n}:a",          # master.wav is input index n
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",  # web-friendly: moov atom at front
        final_out,
    ]

    print(f"  [render] Single-pass FFmpeg render ({n} scenes → {final_out})...")
    _run(cmd, label="render")
    print(f"  [render] Done: {final_out}")
    return final_out
