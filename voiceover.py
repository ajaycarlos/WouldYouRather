"""
Generates voiceover via Edge-TTS AND captures exact word-level timing from its
streaming "WordBoundary" events.

Fallback synthetic timing: some voices (e.g. en-US-AndrewNeural) do not fire
WordBoundary events for short phrases. In that case we measure the actual audio
duration with ffprobe and distribute words evenly across it. This guarantees
non-empty timings for every clip, which the caption system requires.
"""
import asyncio
import subprocess
import edge_tts
import config
from retry_utils import retry


def _get_audio_duration(path: str) -> float:
    """Returns duration in seconds using ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    val = result.stdout.strip()
    return float(val) if val else 0.0


def _synthetic_timings(text: str, duration: float) -> list:
    """
    Distribute words evenly across `duration` seconds.
    Used as a fallback when Edge-TTS returns no WordBoundary events.
    Adds a small leading silence offset (0.05s) to avoid cues starting at t=0.
    """
    words = text.split()
    if not words:
        return []
    usable = max(0.0, duration - 0.05)
    slot = usable / len(words)
    timings = []
    for i, word in enumerate(words):
        start = 0.05 + i * slot
        end   = start + slot * 0.9   # 90 % of slot; tiny gap between words
        timings.append({"word": word, "start": round(start, 4), "end": round(end, 4)})
    return timings


async def _generate_with_timing(text: str, out_path: str) -> list:
    communicate = edge_tts.Communicate(text, config.EDGE_TTS_VOICE)
    word_timings = []

    with open(out_path, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                # offset/duration are in 100-nanosecond units → convert to seconds
                word_timings.append({
                    "word":  chunk["text"],
                    "start": chunk["offset"] / 10_000_000,
                    "end":   (chunk["offset"] + chunk["duration"]) / 10_000_000,
                })

    # Fallback: if the voice fired no WordBoundary events, synthesise timing
    # from the actual audio duration so captions are always generated.
    if not word_timings:
        duration = _get_audio_duration(out_path)
        word_timings = _synthetic_timings(text, duration)

    return word_timings


@retry(times=3, delay=5, backoff=3)
def generate_voiceover(text: str, out_path: str) -> tuple:
    """Returns (audio_path, word_timings) where word_timings is a list of
    {"word": str, "start": float, "end": float} in seconds relative to this
    clip's own start (0.0). Never returns empty timings."""
    word_timings = asyncio.run(_generate_with_timing(text, out_path))
    return out_path, word_timings


if __name__ == "__main__":
    path, timings = generate_voiceover(
        "Would you rather be a genius, or be great at sports?",
        "output/test_voice.mp3",
    )
    print(f"Saved {path}")
    for t in timings:
        print(t)
