"""
Full pipeline: ONE Gemini call for the whole video -> per round, fetch images,
generate percentage split, build all audio/caption segments, assemble the
timeline -> compose final video -> upload with scheduling.

Run with: python main.py
"""
import os
import sys
import config
import script_gen
import percentage_gen
import image_fetch
import voiceover
import visual_gen
import sound_fx
import video_composer
import question_tracker
import scheduler
import youtube_upload
import history
import analytics


def _color_map(colored_words: list) -> dict:
    return {cw["word"].strip().lower(): cw["color"] for cw in colored_words}


def build_round_timeline(round_data: dict, round_number: int, out_dir: str) -> list:
    base = os.path.join(out_dir, f"round_{round_number}")
    timeline = []

    option_a, option_b = round_data["option_a"], round_data["option_b"]

    # 1. "Would you rather" - plain background
    plain_img = visual_gen.build_plain_frame(f"{base}_plain.png")
    wyr_audio, wyr_timings = voiceover.generate_voiceover("Would you rather...", f"{base}_wyr.mp3")
    timeline.append({
        "image": plain_img, "audio": wyr_audio,
        "caption": {"word_timings": wyr_timings, "anchor": "center", "color_map": {}},
    })

    # Fetch both images, build the split frame (reused across the next few clips)
    img_a_path = image_fetch.fetch_image(option_a["image_query"], f"{base}_img_a.jpg")
    img_b_path = image_fetch.fetch_image(option_b["image_query"], f"{base}_img_b.jpg")
    split_frame, color_pair = visual_gen.build_split_frame(img_a_path, img_b_path, f"{base}_split.png")

    # 2. Option A - captions anchored to top half
    a_audio, a_timings = voiceover.generate_voiceover(option_a["text"], f"{base}_a.mp3")
    timeline.append({
        "image": split_frame, "audio": a_audio,
        "caption": {"word_timings": a_timings, "anchor": "top_half", "color_map": _color_map(option_a["colored_words"])},
    })

    # "or" bridge - no caption, visual "OR" badge already on screen
    or_audio, _ = voiceover.generate_voiceover("or", f"{base}_or.mp3")
    timeline.append({"image": split_frame, "audio": or_audio, "caption": None})

    # 3. Option B - captions anchored to bottom half
    b_audio, b_timings = voiceover.generate_voiceover(option_b["text"], f"{base}_b.mp3")
    timeline.append({
        "image": split_frame, "audio": b_audio,
        "caption": {"word_timings": b_timings, "anchor": "bottom_half", "color_map": _color_map(option_b["colored_words"])},
    })

    # 4. Timer - tick sound over the same split frame, no caption
    tick_audio = sound_fx.generate_tick_sound(f"{base}_tick.mp3")
    timeline.append({"image": split_frame, "audio": tick_audio, "caption": None})

    # 5. Reveal - percentages baked into the frame, pick + reason spoken over it
    split = percentage_gen.generate_split()
    reveal_frame = visual_gen.build_reveal_frame(img_a_path, img_b_path, split, f"{base}_reveal.png", color_pair=color_pair)

    picked = option_a if round_data["my_pick"] == "a" else option_b
    reveal_text = f"I'm going with {picked['text']}. {round_data['pick_reason']}"
    reveal_audio, reveal_timings = voiceover.generate_voiceover(reveal_text, f"{base}_reveal.mp3")
    timeline.append({
        "image": reveal_frame, "audio": reveal_audio,
        "caption": {"word_timings": reveal_timings, "anchor": "center", "color_map": {}},
    })

    return timeline


def run_one(index: int):
    print(f"\n=== Video {index + 1} ===")
    out_dir = os.path.join(config.OUTPUT_DIR, f"video_{index}")
    os.makedirs(out_dir, exist_ok=True)

    print("Checking past video performance for learnings...")
    performance_notes = analytics.get_performance_notes()

    print("Generating full video script (ONE Gemini call)...")
    used_questions = question_tracker.load_used_questions()
    script_data = script_gen.generate_video_script(avoid_questions=used_questions)

    # Drop any round that slipped through as an exact repeat, rather than
    # calling Gemini again (keeps this to one call per video as intended)
    fresh_rounds = [
        r for r in script_data["rounds"]
        if not question_tracker.is_duplicate(r["option_a"]["text"], r["option_b"]["text"], used_questions)
    ]
    if len(fresh_rounds) < len(script_data["rounds"]):
        print(f"Dropped {len(script_data['rounds']) - len(fresh_rounds)} duplicate round(s).")
    if not fresh_rounds:
        print("All generated rounds were duplicates - aborting this run.")
        sys.exit(1)

    full_timeline = []
    for i, round_data in enumerate(fresh_rounds):
        print(f"Building round {i + 1}/{len(fresh_rounds)}...")
        full_timeline.extend(build_round_timeline(round_data, i + 1, out_dir))

    # Closing loop bumper - plain background
    print("Building closing bumper...")
    bumper_img = visual_gen.build_plain_frame(os.path.join(out_dir, "bumper_plain.png"))
    bumper_audio, bumper_timings = voiceover.generate_voiceover(
        script_data["closing_bumper"], os.path.join(out_dir, "bumper.mp3")
    )
    full_timeline.append({
        "image": bumper_img, "audio": bumper_audio,
        "caption": {"word_timings": bumper_timings, "anchor": "center", "color_map": {}},
    })

    print("Composing final video...")
    final_video = os.path.join(out_dir, "final_video.mp4")
    video_composer.compose_video(full_timeline, final_video)

    if config.MANUAL_REVIEW_GATE:
        print(f"\nReview before upload: {final_video}")
        print(f"Title: {script_data['title']}")
        input("Press Enter to continue with upload, or Ctrl+C to stop...")

    print("Scheduling and uploading...")
    publish_slot = scheduler.get_next_publish_slot()
    publish_iso = publish_slot.strftime("%Y-%m-%dT%H:%M:%SZ")

    video_id = youtube_upload.upload_video(
        final_video, script_data["title"], script_data["description"], script_data["tags"], publish_iso
    )

    for r in fresh_rounds:
        question_tracker.save_used_question(r["option_a"]["text"], r["option_b"]["text"])
    history.save_entry(video_id, "Would You Rather", fresh_rounds[0]["option_a"]["text"], script_data["title"], publish_iso)
    print("Done!")


def main():
    for i in range(config.VIDEOS_PER_RUN):
        run_one(i)
    print("\nAll videos processed for this run.")


if __name__ == "__main__":
    main()
