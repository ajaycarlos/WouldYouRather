"""
Stage 2 — Audio Builder

Reads the flat scene list from timeline.json.
Generates all TTS narration and tick sound effects IN MEMORY.
Concatenates all PCM into ONE master.wav — no intermediate files,
no clip concatenation, no encoder-delay artifacts.

The PCM byte cursor is the single source of truth for all timestamps.
Every scene gets global_start, global_end, word_timings written back
into the scene dict and saved as master_timing.json.

Sample format throughout: 44100 Hz, mono, 16-bit signed little-endian.
"""
import asyncio
import json
import os
import subprocess
import wave

import edge_tts
import config
from retry_utils import retry
import array
import sound_fx

# ── PCM constants ─────────────────────────────────────────────────────────────
RATE     = 44100   # Hz
CHANNELS = 1
WIDTH    = 2       # bytes per sample (16-bit)
BYTES_PER_SEC = RATE * CHANNELS * WIDTH


# ── Low-level PCM helpers ──────────────────────────────────────────────────────

def _mp3_bytes_to_pcm(mp3_bytes: bytes) -> bytes:
    """Decode MP3 bytes → raw s16le PCM via ffmpeg pipe. No temp files."""
    result = subprocess.run(
        ["ffmpeg", "-y", "-f", "mp3", "-i", "pipe:0",
         "-ar", str(RATE), "-ac", str(CHANNELS), "-f", "s16le", "pipe:1"],
        input=mp3_bytes, capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"PCM decode failed:\n{result.stderr.decode()[-800:]}")
    return result.stdout


def _pcm_duration(pcm: bytes) -> float:
    return len(pcm) / BYTES_PER_SEC


def _silence(duration: float) -> bytes:
    return bytes(int(BYTES_PER_SEC * duration))


def _write_wav(pcm: bytes, path: str):
    with wave.open(path, "wb") as w:
        w.setnchannels(CHANNELS)
        w.setsampwidth(WIDTH)
        w.setframerate(RATE)
        w.writeframes(pcm)


def _trim_or_pad_pcm(pcm: bytes, target_seconds: float) -> bytes:
    target = int(BYTES_PER_SEC * target_seconds)
    if len(pcm) >= target:
        return pcm[:target]
    return pcm + bytes(target - len(pcm))


def _mix_pcm(target: bytearray, src: bytes, offset_sec: float):
    """Mathematically adds src PCM into target bytearray at offset_sec."""
    offset_bytes = int(offset_sec * BYTES_PER_SEC)
    # Ensure even alignment for 16-bit
    if offset_bytes % 2 != 0:
        offset_bytes -= 1
        
    end_bytes = offset_bytes + len(src)
    
    # Pad target if src extends beyond it
    if end_bytes > len(target):
        target.extend(bytes(end_bytes - len(target)))
        
    # Read as 16-bit signed integers
    target_arr = array.array('h', target[offset_bytes:end_bytes])
    src_arr    = array.array('h', src)
    
    # Mix and clip
    for i in range(len(target_arr)):
        val = target_arr[i] + src_arr[i]
        target_arr[i] = max(-32768, min(32767, val))
        
    # Write back
    target[offset_bytes:end_bytes] = target_arr.tobytes()


# ── TTS ────────────────────────────────────────────────────────────────────────

async def _tts_stream(text: str) -> tuple:
    """Returns (mp3_bytes, word_timings_relative)."""
    communicate = edge_tts.Communicate(text, config.EDGE_TTS_VOICE)
    chunks, timings = [], []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            chunks.append(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            timings.append({
                "word":  chunk["text"],
                "start": round(chunk["offset"] / 10_000_000, 4),
                "end":   round((chunk["offset"] + chunk["duration"]) / 10_000_000, 4),
            })
    return b"".join(chunks), timings


@retry(times=3, delay=5, backoff=3)
def _tts(text: str) -> tuple:
    return asyncio.run(_tts_stream(text))


def _synthetic_timings(text: str, duration: float) -> list:
    """Even distribution fallback when TTS fires no WordBoundary events."""
    words = text.split()
    if not words:
        return []
    lead    = min(0.1, duration * 0.05)
    usable  = max(0.0, duration - lead * 2)
    slot    = usable / len(words)
    result  = []
    for i, word in enumerate(words):
        s = lead + i * slot
        e = s + slot * 0.88
        result.append({"word": word, "start": round(s, 4), "end": round(e, 4)})
    return result


# ── Tick SFX ──────────────────────────────────────────────────────────────────

def _tick_pcm(duration: float) -> bytes:
    """Generate rhythmic tick sound as raw PCM bytes."""
    interval  = 1.0
    num_ticks = max(1, int(duration / interval))
    inputs    = []
    for _ in range(num_ticks):
        inputs += ["-f", "lavfi", "-i",
                   f"sine=frequency=1200:duration=0.08:sample_rate={RATE}"]

    delay_parts  = [f"[{i}:a]adelay={int(i*interval*1000)}|{int(i*interval*1000)}[t{i}]"
                    for i in range(num_ticks)]
    mix_in       = "".join(f"[t{i}]" for i in range(num_ticks))
    filter_graph = (
        ";".join(delay_parts)
        + f";{mix_in}amix=inputs={num_ticks}:duration=longest[mx]"
        + f";[mx]apad=whole_dur={duration}[out]"
    )
    result = subprocess.run(
        ["ffmpeg", "-y"] + inputs + [
            "-filter_complex", filter_graph,
            "-map", "[out]",
            "-ar", str(RATE), "-ac", str(CHANNELS),
            "-t", str(duration), "-f", "s16le", "pipe:1",
        ],
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Tick SFX failed:\n{result.stderr.decode()[-500:]}")
    return _trim_or_pad_pcm(result.stdout, duration)


# ── Main builder ──────────────────────────────────────────────────────────────

def build_master_audio(scenes: list, out_dir: str) -> str:
    """
    Iterates scenes in order. Generates audio for each. Concatenates all PCM.
    Writes master.wav and master_timing.json.
    Returns path to master_timing.json.

    Each scene dict is mutated in-place with:
      global_start  (float, seconds)
      global_end    (float, seconds)
      word_timings  (list of {word, start, end} — globally offset)
    """
    os.makedirs(out_dir, exist_ok=True)
    master_pcm = bytearray()
    cursor     = 0.0
    
    # Queue of (sfx_func, offset_seconds) to mix in after building the base track
    sfx_queue = []

    for scene in scenes:
        scene_start = cursor
        scene_id = scene.get("id", "")

        if scene.get("narration"):
            text = scene["narration"]
            print(f"  [audio] {scene['id']}: TTS \"{text[:55]}{'...' if len(text)>55 else ''}\"")

            mp3_bytes, rel_timings = _tts(text)
            pcm      = _mp3_bytes_to_pcm(mp3_bytes)
            duration = _pcm_duration(pcm)

            if not rel_timings:
                rel_timings = _synthetic_timings(text, duration)

            # Shift to global timeline
            global_timings = [
                {"word": wt["word"],
                 "start": round(wt["start"] + cursor, 4),
                 "end":   round(wt["end"]   + cursor, 4)}
                for wt in rel_timings
            ]

            master_pcm.extend(pcm)
            
            # Queue SFX based on scene type
            if "option_a" in scene_id or "option_b" in scene_id:
                sfx_queue.append((sound_fx.generate_whoosh, cursor))
            elif "or" in scene_id:
                sfx_queue.append((sound_fx.generate_boom, cursor))
            elif "reveal" in scene_id:
                sfx_queue.append((sound_fx.generate_ding, cursor))

            cursor += duration

        elif scene.get("sfx") == "tick":
            dur = float(scene.get("sfx_duration", config.TIMER_SECONDS))
            print(f"  [audio] {scene['id']}: tick SFX {dur}s")
            pcm         = _tick_pcm(dur)
            master_pcm.extend(pcm)
            cursor     += dur
            global_timings = []

        else:
            global_timings = []

        scene["global_start"] = round(scene_start, 6)
        scene["global_end"]   = round(cursor,       6)
        scene["word_timings"] = global_timings

    # Mix queued SFX over the voice/tick track
    if sfx_queue:
        print(f"  [audio] Mixing {len(sfx_queue)} sound effects into master track...")
        # cache generated SFX to save FFmpeg calls (whoosh, boom, ding are identical every time)
        sfx_cache = {}
        for sfx_func, offset in sfx_queue:
            if sfx_func not in sfx_cache:
                sfx_cache[sfx_func] = sfx_func()
            _mix_pcm(master_pcm, sfx_cache[sfx_func], offset)

    # Write master audio
    wav_path = os.path.join(out_dir, "master.wav")
    _write_wav(master_pcm, wav_path)
    print(f"  [audio] master.wav written ({cursor:.2f}s, "
          f"{len(master_pcm)//1024} KB)")

    # Write timing JSON (scenes now carry global timestamps)
    timing_path = os.path.join(out_dir, "master_timing.json")
    with open(timing_path, "w", encoding="utf-8") as f:
        json.dump({"total_duration": round(cursor, 6), "scenes": scenes}, f, indent=2)

    print(f"  [audio] master_timing.json written ({len(scenes)} scenes)")
    return timing_path
