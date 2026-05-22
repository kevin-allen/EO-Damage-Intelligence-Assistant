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
    destroyed_pct: float


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


def aggregate(scenario_id: str, preds: list[BuildingPrediction], image_size_xy: tuple[int, int]) -> DamageMetrics:
    """Compute counts, percentages, quadrant stats, and severity_index."""
    raise NotImplementedError


def render_damage_tables(metrics: DamageMetrics) -> dict[str, str]:
    """Render deterministic markdown tables (per F10).

    Returns a dict with keys:
      - "damage_breakdown": markdown table of per-class counts and pct.
      - "priority_zones":    markdown table of per-quadrant total + destroyed_pct.

    These strings are inserted verbatim into the final report; the LLM never
    emits the numbers itself.
    """
    raise NotImplementedError
