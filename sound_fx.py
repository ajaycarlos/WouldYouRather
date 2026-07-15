"""
SFX Generation (Zero external dependencies).
Generates sound effects entirely from math using FFmpeg lavfi filters.
Returns raw s16le PCM bytes matching the pipeline's master format (44100Hz, mono).
"""
import subprocess

RATE     = 44100
CHANNELS = 1
WIDTH    = 2
BYTES_PER_SEC = RATE * CHANNELS * WIDTH


def _lavfi_pcm(filtergraph: str, duration: float) -> bytes:
    """Renders a lavfi filtergraph to raw PCM bytes."""
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", filtergraph,
        "-ar", str(RATE), "-ac", str(CHANNELS),
        "-t", str(duration), "-f", "s16le", "pipe:1",
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"SFX synthesis failed:\n{result.stderr.decode()[-500:]}")
    
    pcm = result.stdout
    target = int(BYTES_PER_SEC * duration)
    if len(pcm) >= target:
        return pcm[:target]
    return pcm + bytes(target - len(pcm))


def generate_whoosh() -> bytes:
    """Fast, airy slide-in sound (white noise + phaser)."""
    graph = (
        "anoisesrc=c=white:a=0.5,"
        "lowpass=f=2000,"
        "aphaser=type=t,"
        "afade=t=in:st=0:d=0.05,"
        "afade=t=out:st=0.2:d=0.3"
    )
    return _lavfi_pcm(graph, 0.5)


def generate_boom() -> bytes:
    """Heavy cinematic drop sound (low sine wave + fast pitch/volume envelope)."""
    # 808-style boom.
    # aevalsrc simulates a sine wave sweeping from 100Hz down to 20Hz.
    graph = (
        "aevalsrc='0.8*sin(2*PI*t*(100-160*t))':d=0.5,"
        "afade=t=in:st=0:d=0.01,"
        "afade=t=out:st=0.1:d=0.4,"
        "compand=attacks=0:decays=0.3:points=-90/-900|-30/-9|0/-3" # compress to add harmonics
    )
    return _lavfi_pcm(graph, 0.5)


def generate_ding() -> bytes:
    """Bright percentage reveal sound (bell/cash register feel)."""
    # Mix of two high frequency sines with fast decay.
    graph = (
        "aevalsrc='0.4*sin(2*PI*1200*t)*exp(-8*t) + 0.3*sin(2*PI*2400*t)*exp(-12*t)':d=0.5,"
        "afade=t=in:st=0:d=0.01"
    )
    return _lavfi_pcm(graph, 0.5)


if __name__ == "__main__":
    import wave
    def test_write(name, pcm):
        with wave.open(f"{name}.wav", "wb") as w:
            w.setnchannels(CHANNELS)
            w.setsampwidth(WIDTH)
            w.setframerate(RATE)
            w.writeframes(pcm)
    
    test_write("output/test_whoosh", generate_whoosh())
    test_write("output/test_boom", generate_boom())
    test_write("output/test_ding", generate_ding())
    print("Wrote test SFX to output/")