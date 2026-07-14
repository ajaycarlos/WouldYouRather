"""
Stage 1 — Timeline Builder

Pure function. Builds the complete video scene list as a Python dict.
No TTS, no rendering, no network. Just data.

The returned dict (and its JSON form) is the single source of truth.
Every downstream stage reads from it exclusively.
"""
import os
import visual_gen
import image_fetch
import percentage_gen


def _cmap(colored_words: list) -> dict:
    return {cw["word"].strip().lower(): cw["color"] for cw in colored_words}


def build_timeline(script_data: dict, out_dir: str) -> dict:
    """
    Fetches images, renders all frames, picks color pairs and splits.
    Returns a dict with 'scenes' (flat ordered list) ready for audio_builder.
    Does NOT write the JSON — caller does that after validation.
    """
    scenes = []
    used_splits = []

    for i, round_data in enumerate(script_data["rounds"]):
        r = i + 1
        opt_a = round_data["option_a"]
        opt_b = round_data["option_b"]
        base  = os.path.join(out_dir, f"round_{r}")

        print(f"  [timeline] Round {r}: fetching images...")
        img_a = image_fetch.fetch_image(opt_a["image_query"], f"{base}_img_a.jpg")
        img_b = image_fetch.fetch_image(opt_b["image_query"], f"{base}_img_b.jpg")

        print(f"  [timeline] Round {r}: building frames...")
        plain_frame               = visual_gen.build_plain_frame(f"{base}_plain.png")
        split_frame, color_pair   = visual_gen.build_split_frame(img_a, img_b, f"{base}_split.png")
        split_                    = percentage_gen.generate_split(used_splits=used_splits)
        used_splits.append(split_)
        reveal_frame              = visual_gen.build_reveal_frame(
            img_a, img_b, split_, f"{base}_reveal.png", color_pair=color_pair
        )

        picked      = opt_a if round_data["my_pick"] == "a" else opt_b
        reveal_text = f"I'm going with {picked['text']}. {round_data['pick_reason']}"

        scenes += [
            {
                "id":              f"r{r}_wyr",
                "round":           r,
                "frame":           plain_frame,
                "narration":       "Would you rather...",
                "sfx":             None,
                "subtitle_anchor": "center",
                "color_map":       {},
            },
            {
                "id":              f"r{r}_option_a",
                "round":           r,
                "frame":           split_frame,
                "narration":       opt_a["text"],
                "sfx":             None,
                "subtitle_anchor": "top_half",
                "color_map":       _cmap(opt_a["colored_words"]),
            },
            {
                "id":              f"r{r}_or",
                "round":           r,
                "frame":           split_frame,
                "narration":       "or",
                "sfx":             None,
                "subtitle_anchor": None,
                "color_map":       {},
            },
            {
                "id":              f"r{r}_option_b",
                "round":           r,
                "frame":           split_frame,
                "narration":       opt_b["text"],
                "sfx":             None,
                "subtitle_anchor": "bottom_half",
                "color_map":       _cmap(opt_b["colored_words"]),
            },
            {
                "id":              f"r{r}_tick",
                "round":           r,
                "frame":           split_frame,
                "narration":       None,
                "sfx":             "tick",
                "sfx_duration":    3.0,
                "subtitle_anchor": None,
                "color_map":       {},
            },
            {
                "id":              f"r{r}_reveal",
                "round":           r,
                "frame":           reveal_frame,
                "narration":       reveal_text,
                "sfx":             None,
                "subtitle_anchor": "center",
                "color_map":       {},
            },
        ]

    # Outro
    bumper_frame = visual_gen.build_plain_frame(os.path.join(out_dir, "bumper_plain.png"))
    scenes.append({
        "id":              "outro",
        "round":           None,
        "frame":           bumper_frame,
        "narration":       script_data["closing_bumper"],
        "sfx":             None,
        "subtitle_anchor": "center",
        "color_map":       {},
    })

    return {"scenes": scenes}
