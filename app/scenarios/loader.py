"""Scenario catalog and image loading from /data/xView2.

Parses `app/scenarios/catalog.yaml` and exposes helpers to resolve a
scenario_id to its pre/post image paths and post-label JSON path.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


XVIEW2_ROOT = Path(os.environ.get("XVIEW2_ROOT", "/data/xView2"))
CATALOG_PATH = Path(__file__).parent / "catalog.yaml"


@dataclass(frozen=True)
class Scenario:
    id: str
    event: str
    tile: str
    disaster_type: str
    description: str


def load_catalog(path: Path = CATALOG_PATH) -> list[Scenario]:
    """Parse catalog.yaml into a list of Scenario objects."""
    raise NotImplementedError


def scenario_image_paths(scenario: Scenario, xview2_root: Path = XVIEW2_ROOT) -> tuple[Path, Path, Path]:
    """Return (pre_image_path, post_image_path, post_label_path) for the scenario."""
    raise NotImplementedError
