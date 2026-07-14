"""
Takes an ordered list of "timeline items" (each: a static image + an audio
clip, optionally with caption data) and produces the final video. Tracks
cumulative elapsed time as it goes, so each item's captions land at the
correct GLOBAL timestamp in the final concatenated video, not just relative
to their own clip.
"""
import os
import subprocess
import captions_builder

TEMP_DIR = "output/temp"


def _run(cmd: list):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FFMPEG ERROR:\n{result.stderr}")
        result.check_returncode()


def _get_duration(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    return float(result.stdout.strip())


def _make_clip(image_path: str, audio_path: str, out_path: str) -> float:
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-framerate", "30", "-i", image_path,
        "-i", audio_path, "-c:v", "libx264", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p", "-shortest", out_path,
    ]
    _run(cmd)
    return _get_duration(audio_path)


def compose_video(timeline: list, final_out: str) -> str:
    """
    timeline: list of dicts, each:
      {"image": path, "audio": path, "caption": {"word_timings": [...], "anchor": str, "color_map": dict} or None}
    """
    os.makedirs(TEMP_DIR, exist_ok=True)
    clip_files = []
    ass_lines = captions_builder.new_ass_file()
    cumulative_time = 0.0

    for i, item in enumerate(timeline):
        clip_path = os.path.join(TEMP_DIR, f"clip_{i}.mp4")
        duration = _make_clip(item["image"], item["audio"], clip_path)
        clip_files.append(clip_path)

        if item.get("caption"):
            cap = item["caption"]
            captions_builder.add_segment(
                ass_lines, cap["word_timings"], cumulative_time,
                cap["anchor"], cap.get("color_map", {}),
            )

        cumulative_time += duration

    concat_list = os.path.join(TEMP_DIR, "concat.txt")
    with open(concat_list, "w") as f:
        for cf in clip_files:
            f.write(f"file '{os.path.abspath(cf)}'\n")

    raw_video = os.path.join(TEMP_DIR, "raw.mp4")
    # Re-encode audio (not copy) so AAC encoder-delay doesn't accumulate
    # across clip boundaries and cause silent gaps / muting.
    _run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-af", "aresample=async=1",
        raw_video,
    ])

    ass_path = os.path.join(TEMP_DIR, "captions.ass")
    captions_builder.write_ass_file(ass_lines, ass_path)

    ass_escaped = os.path.abspath(ass_path).replace("\\", "/").replace(":", "\\:")
    _run([
        "ffmpeg", "-y", "-i", raw_video, "-vf", f"ass={ass_escaped}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23", "-c:a", "copy", final_out,
    ])

    return final_out
