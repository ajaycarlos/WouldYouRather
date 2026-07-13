"""
Generates a simple repeating "tick... tick... tick" countdown sound using
ffmpeg's built-in sine wave generator - no external sound effect library or
license needed, since nothing is sourced from anywhere; it's synthesized.

Bug fix over original: each sine input is fed in as a lavfi source, then
adelay is applied via the filter_complex graph. The apad filter then extends
the final mix to exactly `duration` seconds so the clip never ends early when
muxed with -shortest.
"""
import subprocess
import config


def generate_tick_sound(out_path: str, duration: float = None) -> str:
    duration = duration or config.TIMER_SECONDS
    tick_interval = 1.0
    num_ticks = max(1, int(duration / tick_interval))

    # Each input is a raw 0.08s sine burst. We route each through adelay in
    # the filter graph to stagger them 1 second apart, mix them, then pad
    # the combined audio to exactly `duration` seconds with silence.
    inputs = []
    for _ in range(num_ticks):
        inputs += ["-f", "lavfi", "-i", "sine=frequency=1200:duration=0.08:sample_rate=44100"]

    # Build adelay + label for each input stream
    delay_filters = []
    for i in range(num_ticks):
        delay_ms = int(i * tick_interval * 1000)
        delay_filters.append(f"[{i}:a]adelay={delay_ms}|{delay_ms}[t{i}]")

    mix_inputs = "".join(f"[t{i}]" for i in range(num_ticks))

    filter_complex = (
        ";".join(delay_filters)
        + f";{mix_inputs}amix=inputs={num_ticks}:duration=longest[mixed]"
        + f";[mixed]apad=whole_dur={duration}[out]"
    )

    cmd = (
        ["ffmpeg", "-y"]
        + inputs
        + [
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-t", str(duration),
            out_path,
        ]
    )
    subprocess.run(cmd, check=True, capture_output=True)
    return out_path


if __name__ == "__main__":
    import os
    os.makedirs("output", exist_ok=True)
    generate_tick_sound("output/test_tick.mp3", 3.0)
    print("Saved output/test_tick.mp3")