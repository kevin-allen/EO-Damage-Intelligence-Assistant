"""Runtime predictions loader + offline writer.

Reads/writes `predictions/<scenario_id>.json`, the canonical artifact produced
by scripts/precompute_predictions.py and consumed by the Streamlit app.

File format: a flat JSON list of per-building dicts:
    [
      {"building_id": str, "polygon": [[x, y], ...],
       "damage_class": str, "confidence": float},
      ...
    ]

`damage_class` is one of the underscore-form labels in app/cv/model.DAMAGE_CLASSES.
No PyTorch operations execute in this module.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class BuildingPrediction:
    building_id: str
    polygon: list[tuple[float, float]]
    damage_class: str
    confidence: float


PREDICTIONS_DIR = Path("predictions")


def _predictions_path(scenario_id: str, predictions_dir: Path) -> Path:
    return predictions_dir / f"{scenario_id}.json"


def load_predictions(
    scenario_id: str,
    predictions_dir: Path = PREDICTIONS_DIR,
) -> list[BuildingPrediction]:
    """Load the precomputed prediction list for one scenario."""
    path = _predictions_path(scenario_id, predictions_dir)
    with open(path) as f:
        raw = json.load(f)
    return [
        BuildingPrediction(
            building_id=item["building_id"],
            polygon=[(float(x), float(y)) for x, y in item["polygon"]],
            damage_class=item["damage_class"],
            confidence=float(item["confidence"]),
        )
        for item in raw
    ]


def save_predictions(
    scenario_id: str,
    preds: list[BuildingPrediction],
    predictions_dir: Path = PREDICTIONS_DIR,
) -> Path:
    """Persist a list of predictions as JSON. Returns the file path."""
    predictions_dir.mkdir(parents=True, exist_ok=True)
    path = _predictions_path(scenario_id, predictions_dir)
    payload = [
        {
            "building_id": p.building_id,
            "polygon": [[x, y] for x, y in p.polygon],
            "damage_class": p.damage_class,
            "confidence": round(p.confidence, 4),
        }
        for p in preds
    ]
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    return path
