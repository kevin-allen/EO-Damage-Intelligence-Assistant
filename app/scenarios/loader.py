"""Scenario catalog and image loading from /data/xView2.

Parses `app/scenarios/catalog.yaml` and exposes helpers to resolve a
scenario_id to its pre/post image paths and post-label JSON path.

Scenarios are drawn from the xView2 **test** split (held out from training).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml


XVIEW2_ROOT = Path(os.environ.get("XVIEW2_ROOT", "/data/xView2"))
CATALOG_PATH = Path(__file__).parent / "catalog.yaml"
SCENARIO_SPLIT = "test"


@dataclass(frozen=True)
class Scenario:
    id: str
    event: str
    tile: str
    disaster_type: str
    description: str


def load_catalog(path: Path = CATALOG_PATH) -> list[Scenario]:
    """Parse catalog.yaml into a list of Scenario objects."""
    with open(path) as f:
        raw = yaml.safe_load(f) or []
    scenarios = [
        Scenario(
            id=entry["id"],
            event=entry["event"],
            tile=entry["tile"],
            disaster_type=entry["disaster_type"],
            description=entry.get("description", ""),
        )
        for entry in raw
    ]
    ids = [s.id for s in scenarios]
    if len(set(ids)) != len(ids):
        raise ValueError(f"duplicate scenario ids in {path}: {ids}")
    return scenarios


def get_scenario(scenario_id: str, path: Path = CATALOG_PATH) -> Scenario:
    """Lookup a single scenario by id; raises KeyError if absent."""
    for s in load_catalog(path):
        if s.id == scenario_id:
            return s
    raise KeyError(f"scenario_id={scenario_id!r} not found in {path}")


def scenario_image_paths(
    scenario: Scenario,
    xview2_root: Path = XVIEW2_ROOT,
) -> tuple[Path, Path, Path]:
    """Return (pre_image_path, post_image_path, post_label_path) for the scenario.

    Paths are resolved against the xView2 test split (see SCENARIO_SPLIT).
    """
    split_dir = Path(xview2_root) / SCENARIO_SPLIT
    pre = split_dir / "images" / f"{scenario.tile}_pre_disaster.png"
    post = split_dir / "images" / f"{scenario.tile}_post_disaster.png"
    post_label = split_dir / "labels" / f"{scenario.tile}_post_disaster.json"
    return pre, post, post_label
