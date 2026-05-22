"""Patch extraction utilities for xView2 building polygons.

Shared between training and precompute. Reads xView2 image+label pairs,
crops 128x128 patches centered on each ground-truth building polygon from
both pre and post images, and stacks them into 6-channel tensors.

xView2 label JSON schema (relevant fields):
  features.xy[*].properties.uid           -> building id (str)
  features.xy[*].properties.subtype       -> damage class for post-labels
  features.xy[*].wkt                      -> polygon in pixel coords (WKT)

Pre-labels do not carry a damage subtype; post-labels do.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch


@dataclass(frozen=True)
class BuildingPatch:
    """One building's pre+post crop and ground-truth label (post only)."""

    building_id: str
    polygon_xy: list[tuple[float, float]]
    patch_6ch: torch.Tensor      # shape (6, 128, 128), float32 in [0, 1]
    damage_class: str | None     # None when called from inference on pre-only data


def load_image(path: Path) -> np.ndarray:
    """Read an xView2 PNG/TIF as an HxWx3 uint8 array."""
    raise NotImplementedError


def parse_label_json(path: Path) -> list[dict]:
    """Return the list of building features from an xView2 label JSON."""
    raise NotImplementedError


def crop_patch(image: np.ndarray, polygon_xy: list[tuple[float, float]], size: int = 128) -> np.ndarray:
    """Crop a fixed-size square patch from `image` centered on the polygon bbox."""
    raise NotImplementedError


def build_6ch_input(pre_patch: np.ndarray, post_patch: np.ndarray) -> torch.Tensor:
    """Stack pre and post patches into a 6-channel float tensor in [0, 1]."""
    raise NotImplementedError


def iter_building_patches(
    pre_image_path: Path,
    post_image_path: Path,
    post_label_path: Path,
) -> list[BuildingPatch]:
    """Extract all building patches for one (pre, post) tile."""
    raise NotImplementedError
