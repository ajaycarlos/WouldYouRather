"""
Orchestrator — 5-stage timeline-driven pipeline.

Stage 1  timeline_builder  → flat scene list (pure data, no audio)
Stage 2  audio_builder     → master.wav + master_timing.json
Stage 3  (timing embedded in Stage 2 output — no separate stage)
Stage 4  subtitle_builder  → master.ass
Stage 5  video_renderer    → final_video.mp4

Run with: python main.py
"""
import json
import os
import sys

import analytics
import config
import history
import question_tracker
import scheduler
import script_gen
import timeline_builder
import audio_builder
import subtitle_builder
import video_renderer
import youtube_upload


# ── Validation ────────────────────────────────────────────────────────────────

def _validate_scenes(scenes: list):
    """
    Hard abort if any required asset is missing before audio generation.
    Checks every frame image exists and is non-trivial.
    Subtitle/audio assets are validated by their respective stages.
    """
    print("  [validate] Checking frame images...")
    for i, scene in enumerate(scenes):
        path = scene.get("frame", "")
        if not os.path.isfile(path):
            raise RuntimeError(f"[VALIDATE] Missing frame for scene {i} "
                               f"({scene.get('id', '?')}): {path}")
        if os.path.getsize(path) < 512:
            raise RuntimeError(f"[VALIDATE] Frame too small (corrupt?): {path}")

    # Verify every narration-carrying scene has text
    for scene in scenes:
        if scene.get("narration") is not None and not scene["narration"].strip():
            raise RuntimeError(f"[VALIDATE] Empty narration in scene {scene['id']}")

    print(f"  [validate] ✓ {len(scenes)} scenes, all frames present.")


def _validate_timing(timing_json_path: str):
    """Verify master_timing.json is complete and monotonic."""
    with open(timing_json_path, encoding="utf-8") as f:
        data = json.load(f)

    scenes   = data["scenes"]
    prev_end = 0.0
    errors   = []

    for scene in scenes:
        gs = scene.get("global_start")
        ge = scene.get("global_end")
        if gs is None or ge is None:
            errors.append(f"  Scene {scene['id']} missing global timestamps")
            continue
        if ge < gs:
            errors.append(f"  Scene {scene['id']} has negative duration "
                          f"({gs:.3f} → {ge:.3f})")
        if gs < prev_end - 0.001:  # 1ms tolerance
            errors.append(f"  Scene {scene['id']} overlaps previous "
                          f"(gap {gs - prev_end:.4f}s)")
        prev_end = ge

    if errors:
        raise RuntimeError("[VALIDATE] Timing errors:\n" + "\n".join(errors))

    print(f"  [validate] ✓ Timing monotonic. Total: {data['total_duration']:.2f}s")


# ── Pipeline ──────────────────────────────────────────────────────────────────

def run_one(index: int):
    print(f"\n=== Video {index + 1} ===")
    out_dir = os.path.join(config.OUTPUT_DIR, f"video_{index}")
    os.makedirs(out_dir, exist_ok=True)

    # ── Analytics (non-blocking) ───────────────────────────────────────────────
    try:
        analytics.get_performance_notes()
    except Exception as e:
        print(f"  Analytics skipped ({e})")

    # ── Script generation (one Gemini call) ───────────────────────────────────
    print("Generating script (ONE Gemini call)...")
    used_questions = question_tracker.load_used_questions()
    script_data    = script_gen.generate_video_script(avoid_questions=used_questions)

    fresh_rounds = [
        r for r in script_data["rounds"]
        if not question_tracker.is_duplicate(
            r["option_a"]["text"], r["option_b"]["text"], used_questions
        )
    ]
    if len(fresh_rounds) < len(script_data["rounds"]):
        dropped = len(script_data["rounds"]) - len(fresh_rounds)
        print(f"  Dropped {dropped} duplicate round(s).")
    if not fresh_rounds:
        print("  All rounds are duplicates — aborting.")
        sys.exit(1)

    # Patch script_data with deduplicated rounds
    script_data["rounds"] = fresh_rounds

    # ── Stage 1: Timeline ──────────────────────────────────────────────────────
    print("\n[Stage 1] Building timeline (images + frames)...")
    timeline = timeline_builder.build_timeline(script_data, out_dir)
    scenes   = timeline["scenes"]

    # Save raw timeline for inspection/debugging
    timeline_path = os.path.join(out_dir, "timeline.json")
    with open(timeline_path, "w", encoding="utf-8") as f:
        json.dump(timeline, f, indent=2)

    _validate_scenes(scenes)

    # ── Stage 2: Master audio ──────────────────────────────────────────────────
    print("\n[Stage 2] Building master audio track...")
    timing_path = audio_builder.build_master_audio(scenes, out_dir)
    # Note: scenes list is mutated in-place with global_start/end/word_timings

    # ── Stage 3: Validate timing ───────────────────────────────────────────────
    print("\n[Stage 3] Validating timing...")
    _validate_timing(timing_path)

    # ── Stage 4: Subtitles ─────────────────────────────────────────────────────
    print("\n[Stage 4] Building subtitles...")
    ass_path = subtitle_builder.build_subtitles(timing_path, out_dir)

    # ── Stage 5: Render ────────────────────────────────────────────────────────
    print("\n[Stage 5] Rendering final video...")
    master_wav  = os.path.join(out_dir, "master.wav")
    final_video = os.path.join(out_dir, "final_video.mp4")
    video_renderer.render_video(timing_path, master_wav, ass_path, final_video)

    # ── Review gate ───────────────────────────────────────────────────────────
    if config.MANUAL_REVIEW_GATE:
        print(f"\nReview: {final_video}")
        print(f"Title:  {script_data['title']}")
        input("Press Enter to upload, Ctrl+C to abort...")

    # ── Upload ─────────────────────────────────────────────────────────────────
    print("\nScheduling and uploading...")
    publish_slot = scheduler.get_next_publish_slot()
    publish_iso  = publish_slot.strftime("%Y-%m-%dT%H:%M:%SZ")

    video_id = youtube_upload.upload_video(
        final_video, script_data["title"], script_data["description"],
        script_data["tags"], publish_iso,
    )

    for r in fresh_rounds:
        question_tracker.save_used_question(r["option_a"]["text"], r["option_b"]["text"])
    history.save_entry(
        video_id, "Would You Rather",
        fresh_rounds[0]["option_a"]["text"], script_data["title"], publish_iso,
    )
    print(f"\nDone! Uploaded: https://youtu.be/{video_id}  (scheduled {publish_iso})")


def main():
    for i in range(config.VIDEOS_PER_RUN):
        run_one(i)
    print("\nAll videos processed.")


if __name__ == "__main__":
    main()
