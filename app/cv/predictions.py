"""Runtime predictions loader.

Reads `predictions/<scenario_id>.json` from disk and returns the list of
per-building predictions produced offline by scripts/precompute_predictions.py.
No PyTorch operations execute here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BuildingPrediction:
    building_id: str
    polygon: list[tuple[float, float]]
    damage_class: str
    confidence: float


PREDICTIONS_DIR = Path("predictions")


def load_predictions(scenario_id: str, predictions_dir: Path = PREDICTIONS_DIR) -> list[BuildingPrediction]:
    """Load the precomputed prediction list for one scenario."""
    raise NotImplementedError


def save_predictions(scenario_id: str, preds: list[BuildingPrediction], predictions_dir: Path = PREDICTIONS_DIR) -> Path:
    """Persist a list of predictions as JSON. Returns the file path."""
    raise NotImplementedError
