"""Generate visual assets for the project README.

Reads precomputed predictions for a hero scenario and produces a composite
PNG: pre-disaster / post-disaster / damage-overlay, side-by-side, with
labels and a damage-class legend. Output goes to `docs/hero_composite.png`.

Also produces a small catalog grid (`docs/catalog_grid.png`) showing
post-disaster thumbnails of all 12 catalog scenarios with their severity
labels.

Run inside the app container or anywhere PIL is available:

    python scripts/build_readme_assets.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.cv.aggregator import aggregate
from app.cv.predictions import load_predictions
from app.scenarios.loader import load_catalog, scenario_image_paths
from app.ui.overlay import DAMAGE_COLOR_RGB, render_overlay


REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"

HERO_SCENARIO_ID = "palu-tsunami-0181"

PANEL_SIZE = 280
TITLE_HEIGHT = 28
LEGEND_HEIGHT = 42
GAP = 8
BG_COLOR = (245, 245, 247)
TEXT_COLOR = (29, 29, 31)


def _load_font(size: int) -> ImageFont.ImageFont:
    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ):
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def _resize_square(im: Image.Image, size: int) -> Image.Image:
    return im.resize((size, size), Image.LANCZOS)


def _draw_centered_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int],
                        text: str, font: ImageFont.ImageFont, fill=TEXT_COLOR) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    cx = (xy[0] + xy[2]) // 2 - tw // 2
    cy = (xy[1] + xy[3]) // 2 - th // 2
    draw.text((cx, cy), text, font=font, fill=fill)


def build_hero(scenario_id: str = HERO_SCENARIO_ID) -> Path:
    """Build the 3-panel hero composite for the README."""
    cat = {s.id: s for s in load_catalog()}
    if scenario_id not in cat:
        raise KeyError(f"scenario {scenario_id} not in catalog")
    scenario = cat[scenario_id]
    pre_p, post_p, _ = scenario_image_paths(scenario)
    pre = Image.open(pre_p).convert("RGB")
    post = Image.open(post_p).convert("RGB")
    preds = load_predictions(scenario_id)
    overlay = render_overlay(post, preds)
    metrics = aggregate(scenario_id, preds, (1024, 1024))

    panels = [(_resize_square(pre, PANEL_SIZE),     "Pre-disaster"),
              (_resize_square(post, PANEL_SIZE),    "Post-disaster"),
              (_resize_square(overlay, PANEL_SIZE), "Damage overlay")]

    total_w = PANEL_SIZE * 3 + GAP * 2
    total_h = TITLE_HEIGHT + PANEL_SIZE + LEGEND_HEIGHT + GAP * 2

    canvas = Image.new("RGB", (total_w, total_h), BG_COLOR)
    draw = ImageDraw.Draw(canvas)
    title_font = _load_font(15)
    legend_font = _load_font(11)
    caption_font = _load_font(10)

    # Titles
    for i, (_, label) in enumerate(panels):
        x = i * (PANEL_SIZE + GAP)
        _draw_centered_text(draw, (x, 0, x + PANEL_SIZE, TITLE_HEIGHT),
                            label, title_font)

    # Panels
    for i, (img, _) in enumerate(panels):
        x = i * (PANEL_SIZE + GAP)
        canvas.paste(img, (x, TITLE_HEIGHT))

    # Legend strip
    legend_y = TITLE_HEIGHT + PANEL_SIZE + GAP
    legend_caption = (f"Scenario: {scenario_id}  ·  "
                      f"{metrics['total_buildings']} buildings  ·  "
                      f"severity_index = {metrics['severity_index']:.2f}")
    _draw_centered_text(draw, (0, legend_y - GAP, total_w, legend_y + 4),
                        legend_caption, caption_font)

    # Legend chips
    legend_y += 14
    chip_w, chip_h = 12, 12
    labels = [
        ("no_damage",    "No damage"),
        ("minor_damage", "Minor"),
        ("major_damage", "Major"),
        ("destroyed",    "Destroyed"),
    ]
    chip_text_pad = 4
    chip_gap = 16
    items = []
    for key, label in labels:
        bbox = draw.textbbox((0, 0), label, font=legend_font)
        items.append((key, label, bbox[2] - bbox[0]))
    total_chip_w = sum(chip_w + chip_text_pad + tw for _, _, tw in items) + chip_gap * (len(items) - 1)
    x_cursor = (total_w - total_chip_w) // 2
    for key, label, tw in items:
        rgb = DAMAGE_COLOR_RGB[key]
        draw.rectangle((x_cursor, legend_y, x_cursor + chip_w, legend_y + chip_h),
                       fill=rgb, outline=TEXT_COLOR)
        draw.text((x_cursor + chip_w + chip_text_pad,
                   legend_y + (chip_h - legend_font.size) // 2),
                  label, font=legend_font, fill=TEXT_COLOR)
        x_cursor += chip_w + chip_text_pad + tw + chip_gap

    DOCS.mkdir(parents=True, exist_ok=True)
    out = DOCS / "hero_composite.png"
    canvas.save(out, "PNG", optimize=True)
    print(f"wrote {out}")
    return out


def build_catalog_grid() -> Path:
    """Build a 4x3 grid (post + overlay) of all 12 catalog scenarios."""
    cat = load_catalog()
    cell_w = 160
    cell_h = 160
    label_h = 26
    cols = 4
    rows = 3
    total_w = cols * cell_w + (cols + 1) * GAP
    total_h = rows * (cell_h + label_h) + (rows + 1) * GAP

    canvas = Image.new("RGB", (total_w, total_h), BG_COLOR)
    draw = ImageDraw.Draw(canvas)
    label_font = _load_font(9)
    sev_font = _load_font(11)

    for i, scenario in enumerate(cat):
        r, c = divmod(i, cols)
        pre_p, post_p, _ = scenario_image_paths(scenario)
        post = Image.open(post_p).convert("RGB")
        preds = load_predictions(scenario.id)
        overlay = render_overlay(post, preds)
        overlay_small = overlay.resize((cell_w, cell_h), Image.LANCZOS)

        x = GAP + c * (cell_w + GAP)
        y = GAP + r * (cell_h + label_h + GAP)
        canvas.paste(overlay_small, (x, y))

        metrics = aggregate(scenario.id, preds, (1024, 1024))
        sev = metrics["severity_index"]
        sev_label = (
            "minor" if sev < 0.25
            else "moderate" if sev < 0.5
            else "severe" if sev < 0.75
            else "catastrophic"
        )
        draw.text((x + 3, y + cell_h + 2),
                  scenario.id, font=label_font, fill=TEXT_COLOR)
        draw.text((x + 3, y + cell_h + 13),
                  f"{sev_label} · sev {sev:.2f}", font=sev_font, fill=TEXT_COLOR)

    DOCS.mkdir(parents=True, exist_ok=True)
    out = DOCS / "catalog_grid.png"
    canvas.save(out, "PNG", optimize=True)
    print(f"wrote {out}")
    return out


def main() -> None:
    build_hero()
    build_catalog_grid()


if __name__ == "__main__":
    main()
