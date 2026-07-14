"""
Takes an ordered list of "timeline items" (each: a static image + an audio
clip, optionally with caption data) and produces the final video.

Root cause fix for audio silence: AAC encoding introduces a ~23ms encoder-delay
header per clip. Across 37 clips this accumulates to ~850ms of drift, causing
late-round clips to appear silent. Fix: encode each per-clip audio as MP3
(zero encoder delay), concat with stream-copy (no re-encode, no drift), then
re-encode audio exactly once to AAC in the final subtitle-burn pass.
"""
import os
import subprocess
import captions_builder

TEMP_DIR = "output/temp"


def _run(cmd: list, label: str = ""):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        tag = f" [{label}]" if label else ""
        raise RuntimeError(f"FFmpeg error{tag}:\n{result.stderr[-3000:]}")


def _get_duration(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    val = result.stdout.strip()
    if not val:
        raise RuntimeError(f"ffprobe could not read duration of: {path}")
    return float(val)


def _make_clip(image_path: str, audio_path: str, out_path: str) -> float:
    """
    Encodes one static-image + audio clip to MP4.
    Audio is encoded as MP3 (libmp3lame) — MP3 has zero encoder-delay header,
    so frame-accurate concat-copy is safe across any number of clips.
    Returns the audio duration in seconds.
    """
    duration = _get_duration(audio_path)
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-framerate", "30", "-i", image_path,
        "-i", audio_path,
        "-c:v", "libx264", "-tune", "stillimage",
        "-c:a", "libmp3lame", "-b:a", "320k",   # MP3: no encoder-delay
        "-pix_fmt", "yuv420p",
        "-t", str(duration),   # explicit duration — don't rely on -shortest
        out_path,
    ]
    _run(cmd, label=f"clip:{os.path.basename(out_path)}")
    return duration


def compose_video(timeline: list, final_out: str) -> str:
    """
    timeline: list of dicts, each:
      {"image": path, "audio": path,
       "caption": {"word_timings": [...], "anchor": str, "color_map": dict} or None}
    """
    os.makedirs(TEMP_DIR, exist_ok=True)
    clip_files = []
    ass_lines = captions_builder.new_ass_file()
    cumulative_time = 0.0

    for i, item in enumerate(timeline):
        clip_path = os.path.join(TEMP_DIR, f"clip_{i}.mp4")
        print(f"  Encoding clip {i + 1}/{len(timeline)}: {os.path.basename(item['audio'])}")
        duration = _make_clip(item["image"], item["audio"], clip_path)
        clip_files.append(clip_path)

        if item.get("caption"):
            cap = item["caption"]
            captions_builder.add_segment(
                ass_lines, cap["word_timings"], cumulative_time,
                cap["anchor"], cap.get("color_map", {}),
            )

        cumulative_time += duration

    # --- Concat all clips using stream-copy (no re-encode = no delay drift) ---
    concat_list = os.path.join(TEMP_DIR, "concat.txt")
    with open(concat_list, "w") as f:
        for cf in clip_files:
            f.write(f"file '{os.path.abspath(cf)}'\n")

    raw_video = os.path.join(TEMP_DIR, "raw.mp4")
    print("  Concatenating clips (stream-copy)...")
    _run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
        "-c", "copy",   # pure stream copy — zero re-encode, zero delay accumulation
        raw_video,
    ], label="concat")

    # --- Burn subtitles + re-encode audio to AAC exactly once ---
    ass_path = os.path.join(TEMP_DIR, "captions.ass")
    captions_builder.write_ass_file(ass_lines, ass_path)

    ass_escaped = os.path.abspath(ass_path).replace("\\", "/").replace(":", "\\:")
    print("  Burning subtitles and encoding final video...")
    _run([
        "ffmpeg", "-y", "-i", raw_video,
        "-vf", f"ass={ass_escaped}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",   # single AAC encode here, not per-clip
        "-af", "aresample=async=1000:min_hard_comp=0.100:first_pts=0",
        final_out,
    ], label="subtitle-burn")

    return final_out
