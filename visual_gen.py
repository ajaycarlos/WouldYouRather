"""
Builds the three frame types this format needs:
- plain background (for "would you rather" line and the pick/reason beat)
- split screen (top half = option A image, bottom half = option B image, OR badge)
- reveal frame (same split screen + big green/red percentage over each half)
Matches the template in the reference screenshot: full-bleed images, bold
centered "OR" divider badge, percentages positioned over each half.
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageOps
import config

W, H = 1080, 1920
HALF_H = H // 2
BG_COLOR = (20, 20, 28)
GREEN = (70, 220, 90)
RED = (230, 60, 60)
WHITE = (255, 255, 255)


def _font(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(config.FONT_PATH, size)
    except OSError:
        return ImageFont.load_default()


def _draw_centered(draw, text, cx, cy, font, fill, stroke_width=0, stroke_fill=None):
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        (cx - w / 2 - bbox[0], cy - h / 2 - bbox[1]), text, font=font, fill=fill,
        stroke_width=stroke_width, stroke_fill=stroke_fill,
    )


def build_plain_frame(out_path: str) -> str:
    img = Image.new("RGB", (W, H), BG_COLOR)
    img.save(out_path)
    return out_path


def _fit_image(path: str, size: tuple) -> Image.Image:
    img = Image.open(path).convert("RGB")
    return ImageOps.fit(img, size, Image.LANCZOS)


def build_split_frame(image_a_path: str, image_b_path: str, out_path: str) -> str:
    img = Image.new("RGB", (W, H), BG_COLOR)

    top = _fit_image(image_a_path, (W, HALF_H))
    bottom = _fit_image(image_b_path, (W, HALF_H))
    img.paste(top, (0, 0))
    img.paste(bottom, (0, HALF_H))

    draw = ImageDraw.Draw(img)
    # OR badge - dark circle at the exact center divider
    badge_r = 60
    draw.ellipse([W // 2 - badge_r, HALF_H - badge_r, W // 2 + badge_r, HALF_H + badge_r], fill=(15, 15, 15))
    _draw_centered(draw, "OR", W // 2, HALF_H, _font(50), WHITE)

    img.save(out_path)
    return out_path


def build_reveal_frame(image_a_path: str, image_b_path: str, split: dict, out_path: str) -> str:
    """split: {"a": int, "b": int} percentages."""
    img_path = build_split_frame(image_a_path, image_b_path, out_path)
    img = Image.open(img_path).convert("RGB")
    draw = ImageDraw.Draw(img)

    pct_font = _font(110)
    for pct, cy in [(split["a"], HALF_H // 2), (split["b"], HALF_H + HALF_H // 2)]:
        color = GREEN if pct >= 50 else RED
        text = f"{pct}%"
        _draw_centered(draw, text, W // 2, cy, pct_font, color, stroke_width=6, stroke_fill=(0, 0, 0))

    img.save(out_path)
    return out_path


if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    build_plain_frame("output/test_plain.png")
    print("Saved test frames (run image_fetch.py first for split/reveal tests)")
