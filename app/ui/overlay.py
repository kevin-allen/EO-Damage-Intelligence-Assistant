"""Damage-class polygon overlay rendering for the Streamlit UI.

Draws semi-transparent colored polygons on top of the post-disaster image,
one per predicted building, color-coded by damage class. Building footprints
come from the xView2 GT polygons (carried through in the prediction JSON);
the damage class is the model's prediction. See F12.
"""

from __future__ import annotations

from PIL import Image, ImageDraw

from app.cv.predictions import BuildingPrediction


DAMAGE_COLOR_RGB: dict[str, tuple[int, int, int]] = {
    "no_damage":    ( 59, 129,  50),   # green
    "minor_damage": (212, 160,  23),   # yellow
    "major_damage": (217, 107,  31),   # orange
    "destroyed":    (184,  30,  30),   # red
}

DAMAGE_COLOR_HEX: dict[str, str] = {
    cls: "#{:02x}{:02x}{:02x}".format(*rgb) for cls, rgb in DAMAGE_COLOR_RGB.items()
}

_FILL_ALPHA: int = 110   # 0..255 — semi-transparent polygon fill
_OUTLINE_ALPHA: int = 230


def render_overlay(
    post_image: Image.Image,
    predictions: list[BuildingPrediction],
) -> Image.Image:
    """Return a copy of `post_image` with colored polygons composited on top."""
    base = post_image.convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for pred in predictions:
        rgb = DAMAGE_COLOR_RGB.get(pred.damage_class, (128, 128, 128))
        points = [(float(x), float(y)) for x, y in pred.polygon]
        if len(points) < 3:
            continue
        draw.polygon(points, fill=rgb + (_FILL_ALPHA,), outline=rgb + (_OUTLINE_ALPHA,))
    return Image.alpha_composite(base, overlay).convert("RGB")
