"""Aggregate per-building predictions into structured damage metrics.

The structured JSON returned here is the single source of truth for damage
figures in the report. Per F10, numeric content in the final report comes
from `render_damage_tables` (below), not from the LLM.
"""

from __future__ import annotations

from typing import TypedDict

from app.cv.predictions import BuildingPrediction


class ClassCount(TypedDict):
    count: int
    pct: float


class QuadrantStats(TypedDict):
    total: int
    mean_severity: float


class DamageMetrics(TypedDict):
    scenario_id: str
    total_buildings: int
    by_class: dict[str, ClassCount]
    spatial: dict[str, dict[str, QuadrantStats]]
    severity_index: float


CLASS_WEIGHTS: dict[str, float] = {
    "no_damage": 0.0,
    "minor_damage": 0.33,
    "major_damage": 0.66,
    "destroyed": 1.0,
}
DAMAGE_CLASSES: tuple[str, ...] = tuple(CLASS_WEIGHTS)
QUADRANTS: tuple[str, ...] = ("NW", "NE", "SW", "SE")

_CLASS_DISPLAY: dict[str, str] = {
    "no_damage": "No damage",
    "minor_damage": "Minor damage",
    "major_damage": "Major damage",
    "destroyed": "Destroyed",
}


def _polygon_centroid(polygon: list[tuple[float, float]]) -> tuple[float, float]:
    """Bbox center of the polygon — matches dataset.crop_patch's centering."""
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    return (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0


def _quadrant_for(cx: float, cy: float, width: int, height: int) -> str:
    """Assign an (x, y) point to NW/NE/SW/SE relative to image center.

    Image coords: y=0 at top. East = x >= width/2, South = y >= height/2.
    """
    mid_x, mid_y = width / 2.0, height / 2.0
    ns = "S" if cy >= mid_y else "N"
    ew = "E" if cx >= mid_x else "W"
    return ns + ew


def aggregate(
    scenario_id: str,
    preds: list[BuildingPrediction],
    image_size_xy: tuple[int, int],
) -> DamageMetrics:
    """Compute counts, percentages, quadrant stats, and severity_index."""
    width, height = image_size_xy
    total = len(preds)

    class_counts: dict[str, int] = {c: 0 for c in DAMAGE_CLASSES}
    quad_total: dict[str, int] = {q: 0 for q in QUADRANTS}
    quad_severity_sum: dict[str, float] = {q: 0.0 for q in QUADRANTS}

    for p in preds:
        if p.damage_class in class_counts:
            class_counts[p.damage_class] += 1
        cx, cy = _polygon_centroid(p.polygon)
        q = _quadrant_for(cx, cy, width, height)
        quad_total[q] += 1
        quad_severity_sum[q] += CLASS_WEIGHTS.get(p.damage_class, 0.0)

    by_class: dict[str, ClassCount] = {
        c: {
            "count": class_counts[c],
            "pct": round(100.0 * class_counts[c] / total, 1) if total else 0.0,
        }
        for c in DAMAGE_CLASSES
    }

    quadrants: dict[str, QuadrantStats] = {
        q: {
            "total": quad_total[q],
            "mean_severity": round(
                quad_severity_sum[q] / quad_total[q], 2
            ) if quad_total[q] else 0.0,
        }
        for q in QUADRANTS
    }

    severity = (
        sum(CLASS_WEIGHTS[c] * class_counts[c] for c in DAMAGE_CLASSES) / total
        if total else 0.0
    )

    return {
        "scenario_id": scenario_id,
        "total_buildings": total,
        "by_class": by_class,
        "spatial": {"quadrants": quadrants},
        "severity_index": round(severity, 2),
    }


def render_damage_tables(metrics: DamageMetrics) -> dict[str, str]:
    """Render deterministic markdown tables (per F10).

    Returns a dict with keys:
      - "damage_breakdown": markdown table of per-class counts and pct.
      - "priority_zones":    markdown table of per-quadrant total + mean_severity,
                             sorted by mean_severity descending (priority order).

    These strings are inserted verbatim into the final report; the LLM never
    emits the numbers itself.
    """
    total = metrics["total_buildings"]
    by_class = metrics["by_class"]

    breakdown_rows = [
        "| Damage class | Buildings | Share |",
        "|---|---:|---:|",
    ]
    for c in DAMAGE_CLASSES:
        row = by_class[c]
        breakdown_rows.append(
            f"| {_CLASS_DISPLAY[c]} | {row['count']} | {row['pct']:.1f}% |"
        )
    breakdown_rows.append(f"| **Total** | **{total}** | 100.0% |")
    damage_breakdown = "\n".join(breakdown_rows)

    quadrants = metrics["spatial"]["quadrants"]
    ranked = sorted(
        QUADRANTS,
        key=lambda q: (-quadrants[q]["mean_severity"], -quadrants[q]["total"]),
    )
    priority_rows = [
        "| Quadrant | Buildings | Mean severity |",
        "|---|---:|---:|",
    ]
    for q in ranked:
        st = quadrants[q]
        priority_rows.append(
            f"| {q} | {st['total']} | {st['mean_severity']:.2f} |"
        )
    priority_zones = "\n".join(priority_rows)

    return {"damage_breakdown": damage_breakdown, "priority_zones": priority_zones}
