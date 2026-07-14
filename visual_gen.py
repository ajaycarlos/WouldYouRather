"""
Builds the three frame types this format needs:
- plain background (for "would you rather" line and the pick/reason beat)
- split screen:  top half = colored bg + framed image A, bottom half = colored bg + framed image B,
                 large "OR" badge at the exact centre divider
- reveal frame:  same split screen + large white percentage in the colored strip at
                 the very top (A%) and very bottom (B%) of the frame

Template (from reference sketch):
  ┌───────────────────────────────────────┐
  │  [  TOP COLOUR FILL  ]                │  ← top strip (% lives here)
  │  ┌───────────────────────────────┐    │
  │  │        IMAGE  1               │    │  ← image with white border
  │  └───────────────────────────────┘    │
  │─────────────────── (OR) ─────────────│  ← divider with badge
  │  ┌───────────────────────────────┐    │
  │  │        IMAGE  2               │    │  ← image with white border
  │  └───────────────────────────────┘    │
  │  [  BOT  COLOUR FILL  ]               │  ← bottom strip (% lives here)
  └───────────────────────────────────────┘

Random harmonious colour pairs are chosen once per round and reused
across the split → reveal frames so the colours stay consistent.
"""
import os
import random
from PIL import Image, ImageDraw, ImageFont, ImageOps
import config

# ── Canvas ────────────────────────────────────────────────────────────────
W, H     = 1080, 1920
HALF_H   = H // 2          # 960  (top / bottom divider)
BG_COLOR = (20, 20, 28)
WHITE    = (255, 255, 255)

# ── Image box inside each 1080×960 half ───────────────────────────────────
IMG_W        = 860
IMG_H        = 500                           # shorter → bigger strips for % text
IMG_X        = (W - IMG_W) // 2              # 110 px side margins
IMG_PAD_V    = (HALF_H - IMG_H) // 2        # 230 px strips top & bottom in each half
BORDER_W     = 8                             # white border thickness around image

# ── OR badge ──────────────────────────────────────────────────────────────
OR_RADIUS    = 100   # prominent, unmissable badge
OR_RING_W    = 6     # white ring around the dark circle
OR_FONT_SIZE = 88

# ── Percentage strip geometry ──────────────────────────────────────────────
# Top strip centre:   y ∈ [0, IMG_PAD_V]          →  cy = IMG_PAD_V // 2 = 115
# Bottom strip centre: y ∈ [HALF_H+IMG_PAD_V+IMG_H, H]  →  cy = H - IMG_PAD_V//2 = 1805
PCT_TOP_CY   = IMG_PAD_V // 2                               # 115
PCT_BOT_CY   = H - IMG_PAD_V // 2                          # 1805
PCT_FONT_SIZE = 130

# ── Harmonious colour pairs (top, bottom) ─────────────────────────────────
COLOR_PAIRS = [
    ((220, 53,  69),  (13,  110, 253)),   # Crimson     + Royal Blue
    ((25,  135, 84),  (255, 193,   7)),   # Emerald     + Amber
    ((111, 66,  193), (253, 126,  20)),   # Violet      + Burnt Orange
    ((13,  202, 240), (220,  53,  69)),   # Sky Cyan    + Crimson
    ((214, 51,  132), (32,  201, 151)),   # Hot Pink    + Teal
    ((253, 126,  20), (13,  110, 253)),   # Amber       + Royal Blue
    ((102, 16,  242), (255, 193,   7)),   # Deep Purple + Gold
    ((23,  162, 184), (255,  87,  34)),   # Teal        + Deep Orange
    ((233, 30,   99), (33,  150, 243)),   # Rose        + Dodger Blue
    ((40,  167,  69), (220,  53,  69)),   # Forest Green+ Crimson
]


# ── Helpers ───────────────────────────────────────────────────────────────
def _font(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(config.FONT_PATH, size)
    except OSError:
        return ImageFont.load_default()


def _draw_centered(draw, text, cx, cy, font, fill, stroke_width=0, stroke_fill=None):
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(
        (cx - w / 2 - bbox[0], cy - h / 2 - bbox[1]),
        text, font=font, fill=fill,
        stroke_width=stroke_width, stroke_fill=stroke_fill,
    )


def get_random_color_pair() -> tuple:
    """Returns a (top_color_rgb, bottom_color_rgb) tuple."""
    return random.choice(COLOR_PAIRS)


def build_plain_frame(out_path: str) -> str:
    img = Image.new("RGB", (W, H), BG_COLOR)
    img.save(out_path)
    return out_path


def _fit_image(path: str, size: tuple) -> Image.Image:
    img = Image.open(path).convert("RGB")
    return ImageOps.fit(img, size, Image.LANCZOS)


def _draw_half(draw: ImageDraw.Draw, canvas: Image.Image,
               image_path: str, top_y: int, bg_color: tuple):
    """
    Draw one half (top_y … top_y+HALF_H) of the canvas:
    • flood-fill the half with bg_color
    • paste the image centred inside it
    • draw a white border around the image box
    """
    # Coloured background for this half
    draw.rectangle([0, top_y, W - 1, top_y + HALF_H - 1], fill=bg_color)

    # Image position within this half
    ix = IMG_X
    iy = top_y + IMG_PAD_V

    # Paste photo
    photo = _fit_image(image_path, (IMG_W, IMG_H))
    canvas.paste(photo, (ix, iy))

    # White border (drawn OVER the image edges so it sits on top)
    draw.rectangle(
        [ix - BORDER_W,          iy - BORDER_W,
         ix + IMG_W + BORDER_W - 1, iy + IMG_H + BORDER_W - 1],
        outline=WHITE, width=BORDER_W,
    )


# ── Public builders ───────────────────────────────────────────────────────
def build_split_frame(image_a_path: str, image_b_path: str, out_path: str,
                      color_pair: tuple = None) -> tuple:
    """
    Returns (out_path, color_pair) — the colour pair is returned so
    build_reveal_frame can reuse the exact same colours.
    """
    if color_pair is None:
        color_pair = get_random_color_pair()
    top_color, bot_color = color_pair

    canvas = Image.new("RGB", (W, H), BG_COLOR)
    draw   = ImageDraw.Draw(canvas)

    _draw_half(draw, canvas, image_a_path, 0,      top_color)
    _draw_half(draw, canvas, image_b_path, HALF_H, bot_color)

    # OR badge — white ring + dark fill + bold text
    cx, cy = W // 2, HALF_H
    r = OR_RADIUS
    draw.ellipse([cx - r - OR_RING_W, cy - r - OR_RING_W,
                  cx + r + OR_RING_W, cy + r + OR_RING_W], fill=WHITE)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(20, 20, 28))
    _draw_centered(draw, "OR", cx, cy, _font(OR_FONT_SIZE), WHITE)

    canvas.save(out_path)
    return out_path, color_pair


def build_reveal_frame(image_a_path: str, image_b_path: str, split: dict,
                       out_path: str, color_pair: tuple = None) -> str:
    """
    split: {"a": int, "b": int} percentages (must sum to 100).
    Percentages are drawn in large white text with heavy black stroke —
    A% at the very top strip, B% at the very bottom strip.
    """
    # Build the base split frame (reuses the same colour pair)
    frame_path, used_pair = build_split_frame(
        image_a_path, image_b_path, out_path, color_pair
    )
    canvas = Image.open(frame_path).convert("RGB")
    draw   = ImageDraw.Draw(canvas)

    pct_font = _font(PCT_FONT_SIZE)

    for pct, cy in [(split["a"], PCT_TOP_CY), (split["b"], PCT_BOT_CY)]:
        _draw_centered(
            draw, f"{pct}%", W // 2, cy,
            pct_font, WHITE,
            stroke_width=10, stroke_fill=(0, 0, 0),
        )

    canvas.save(out_path)
    return out_path


if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    build_plain_frame("output/test_plain.png")
    print("Saved test frames (run image_fetch.py first for split/reveal tests)")
