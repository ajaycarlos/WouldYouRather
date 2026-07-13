"""
Generates voiceover via Edge-TTS AND captures exact word-level timing from its
streaming "WordBoundary" events - this is more accurate than Whisper-guessing
after the fact, since we already know the exact text and get real generation
timing directly from the TTS engine itself.
"""
import asyncio
import edge_tts
import config
from retry_utils import retry


async def _generate_with_timing(text: str, out_path: str) -> list:
    communicate = edge_tts.Communicate(text, config.EDGE_TTS_VOICE)
    word_timings = []

    with open(out_path, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                # offset/duration are in 100-nanosecond units - convert to seconds
                word_timings.append({
                    "word": chunk["text"],
                    "start": chunk["offset"] / 10_000_000,
                    "end": (chunk["offset"] + chunk["duration"]) / 10_000_000,
                })

    return word_timings


@retry(times=3, delay=5, backoff=3)
def generate_voiceover(text: str, out_path: str) -> tuple:
    """Returns (audio_path, word_timings) where word_timings is a list of
    {"word": str, "start": float, "end": float} in seconds, relative to this
    clip's own start (0.0)."""
    word_timings = asyncio.run(_generate_with_timing(text, out_path))
    return out_path, word_timings


if __name__ == "__main__":
    path, timings = generate_voiceover("Would you rather be a genius, or be great at sports?", "output/test_voice.mp3")
    print(f"Saved {path}")
    for t in timings:
        print(t)
