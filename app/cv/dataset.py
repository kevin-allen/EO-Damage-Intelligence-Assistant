"""Patch extraction utilities for xView2 building polygons.

Shared between training and precompute. Reads xView2 image+label pairs,
crops 128x128 patches centered on each ground-truth building polygon from
both pre and post images, and stacks them into 6-channel tensors.

xView2 label JSON schema (post_disaster, relevant fields):
  metadata.width, metadata.height                          -> image dims (1024 x 1024)
  features.xy[*].properties.feature_type                   -> "building"
  features.xy[*].properties.uid                            -> stable building id
  features.xy[*].properties.subtype                        -> damage label (dash form)
  features.xy[*].wkt                                       -> "POLYGON ((x y, ...))" in pixel coords

Subtype values use dashes: "no-damage", "minor-damage", "major-damage",
"destroyed", "un-classified". We normalize to underscores and skip
"un-classified". Pre-disaster labels only carry "no-damage" and are
ignored at the label level — we use post-disaster labels for both the
polygon list and the damage class.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch.utils.data import Dataset


PATCH_SIZE: int = 128
IMAGE_SIZE: int = 1024

LABEL_NAMES: tuple[str, ...] = ("no_damage", "minor_damage", "major_damage", "destroyed")
LABEL_TO_IDX: dict[str, int] = {name: i for i, name in enumerate(LABEL_NAMES)}
IDX_TO_LABEL: dict[int, str] = {i: name for i, name in enumerate(LABEL_NAMES)}

_WKT_POLYGON_RE = re.compile(r"POLYGON\s*\(\(([^)]+)\)\)")


@dataclass(frozen=True)
class BuildingPatch:
    """One building's pre+post crop and ground-truth label (post only)."""

    building_id: str
    polygon_xy: list[tuple[float, float]]
    patch_6ch: torch.Tensor      # shape (6, PATCH_SIZE, PATCH_SIZE), float32 in [0, 1]
    damage_class: str | None     # underscore form; None for un-classified or pre-only


def load_image(path: Path) -> np.ndarray:
    """Read an xView2 PNG as an HxWx3 uint8 array."""
    with Image.open(path) as im:
        return np.asarray(im.convert("RGB"))


def parse_label_json(path: Path) -> list[dict]:
    """Return the `features.xy` list from an xView2 label JSON."""
    with open(path) as f:
        data = json.load(f)
    return data.get("features", {}).get("xy", [])


def parse_wkt_polygon(wkt: str) -> list[tuple[float, float]]:
    """Parse 'POLYGON ((x y, x y, ...))' into a list of (x, y) tuples.

    Only the outer ring is returned. xView2 buildings have no holes.
    """
    m = _WKT_POLYGON_RE.search(wkt)
    if not m:
        raise ValueError(f"unparseable WKT polygon: {wkt[:80]!r}")
    points: list[tuple[float, float]] = []
    for pair in m.group(1).split(","):
        x_str, y_str = pair.strip().split()
        points.append((float(x_str), float(y_str)))
    return points


def normalize_subtype(subtype: str) -> str | None:
    """Map xView2 raw subtype to our underscore form. Returns None for 'un-classified'."""
    if subtype == "un-classified":
        return None
    return subtype.replace("-", "_")


def crop_patch(
    image: np.ndarray,
    polygon_xy: list[tuple[float, float]],
    size: int = PATCH_SIZE,
) -> np.ndarray:
    """Crop a fixed-size square patch from `image` centered on the polygon's bbox.

    Pads with zeros for buildings near image borders so the output is always
    exactly `size x size`.
    """
    h, w = image.shape[:2]
    xs = [p[0] for p in polygon_xy]
    ys = [p[1] for p in polygon_xy]
    cx = (min(xs) + max(xs)) / 2.0
    cy = (min(ys) + max(ys)) / 2.0
    half = size // 2
    x0 = int(round(cx - half))
    y0 = int(round(cy - half))
    x1 = x0 + size
    y1 = y0 + size

    out_shape: tuple[int, ...]
    if image.ndim == 3:
        out_shape = (size, size, image.shape[2])
    else:
        out_shape = (size, size)
    out = np.zeros(out_shape, dtype=image.dtype)

    sx0, sy0 = max(0, x0), max(0, y0)
    sx1, sy1 = min(w, x1), min(h, y1)
    if sx0 >= sx1 or sy0 >= sy1:
        return out

    dx0 = sx0 - x0
    dy0 = sy0 - y0
    dx1 = dx0 + (sx1 - sx0)
    dy1 = dy0 + (sy1 - sy0)
    out[dy0:dy1, dx0:dx1] = image[sy0:sy1, sx0:sx1]
    return out


def build_6ch_input(pre_patch: np.ndarray, post_patch: np.ndarray) -> torch.Tensor:
    """Stack pre and post HxWx3 uint8 patches into a (6, H, W) float tensor in [0, 1]."""
    if pre_patch.shape != post_patch.shape:
        raise ValueError(f"pre/post shapes differ: {pre_patch.shape} vs {post_patch.shape}")
    stacked = np.concatenate([pre_patch, post_patch], axis=-1).astype(np.float32) / 255.0
    return torch.from_numpy(stacked).permute(2, 0, 1).contiguous()


def iter_building_patches(
    pre_image_path: Path,
    post_image_path: Path,
    post_label_path: Path,
) -> list[BuildingPatch]:
    """Extract all annotated building patches for one (pre, post) tile.

    Used by precompute (and useful for ad-hoc inspection). Skips features whose
    subtype is 'un-classified' or whose feature_type is not 'building'.
    """
    pre = load_image(pre_image_path)
    post = load_image(post_image_path)
    out: list[BuildingPatch] = []
    for feat in parse_label_json(post_label_path):
        props = feat.get("properties", {})
        if props.get("feature_type") != "building":
            continue
        damage = normalize_subtype(props.get("subtype", ""))
        if damage is None:
            continue
        polygon = parse_wkt_polygon(feat["wkt"])
        pre_p = crop_patch(pre, polygon)
        post_p = crop_patch(post, polygon)
        out.append(BuildingPatch(
            building_id=props.get("uid", ""),
            polygon_xy=polygon,
            patch_6ch=build_6ch_input(pre_p, post_p),
            damage_class=damage,
        ))
    return out


@dataclass(frozen=True)
class _BuildingRecord:
    """Compact per-building record used by the training Dataset.

    Storing the parsed polygon avoids reparsing the label JSON on every
    __getitem__ call.
    """

    tile_key: str
    polygon_xy: tuple[tuple[float, float], ...]
    label_idx: int


def _augment_6ch(patch: torch.Tensor) -> torch.Tensor:
    """Random hflip + vflip + 90-degree rotation. Channel-symmetric so it
    applies identically to the pre and post halves of the 6-channel input."""
    if torch.rand(1).item() < 0.5:
        patch = torch.flip(patch, dims=[-1])
    if torch.rand(1).item() < 0.5:
        patch = torch.flip(patch, dims=[-2])
    k = int(torch.randint(0, 4, (1,)).item())
    if k:
        patch = torch.rot90(patch, k, dims=[-2, -1])
    return patch


class XView2BuildingDataset(Dataset):
    """PyTorch Dataset over annotated xView2 buildings (one item = one building).

    On __init__, walks `<root>/<split>/labels/*_post_disaster.json` and indexes
    every annotated building (skipping un-classified and non-building features).
    On __getitem__, loads the relevant pre and post images and crops one patch.

    Image I/O is per-building, which is wasteful when the DataLoader returns
    buildings from the same tile in different batches. For a few-day prototype
    this is acceptable — use num_workers>=4 in the DataLoader to overlap I/O.
    """

    def __init__(
        self,
        xview2_root: Path,
        split: str = "train",
        augment: bool = False,
    ) -> None:
        self.split_dir = Path(xview2_root) / split
        self.augment = augment
        self.records: list[_BuildingRecord] = []
        self._index_split()

    def _index_split(self) -> None:
        labels_dir = self.split_dir / "labels"
        for json_path in sorted(labels_dir.glob("*_post_disaster.json")):
            tile_key = json_path.name.removesuffix("_post_disaster.json")
            for feat in parse_label_json(json_path):
                props = feat.get("properties", {})
                if props.get("feature_type") != "building":
                    continue
                damage = normalize_subtype(props.get("subtype", ""))
                if damage is None or damage not in LABEL_TO_IDX:
                    continue
                polygon = parse_wkt_polygon(feat["wkt"])
                self.records.append(_BuildingRecord(
                    tile_key=tile_key,
                    polygon_xy=tuple(polygon),
                    label_idx=LABEL_TO_IDX[damage],
                ))

    def class_counts(self) -> dict[str, int]:
        """Per-class record counts. Useful for sanity checks and class weighting."""
        counts = {name: 0 for name in LABEL_NAMES}
        for rec in self.records:
            counts[IDX_TO_LABEL[rec.label_idx]] += 1
        return counts

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, int]:
        rec = self.records[idx]
        pre_path = self.split_dir / "images" / f"{rec.tile_key}_pre_disaster.png"
        post_path = self.split_dir / "images" / f"{rec.tile_key}_post_disaster.png"
        pre = load_image(pre_path)
        post = load_image(post_path)
        polygon = list(rec.polygon_xy)
        pre_p = crop_patch(pre, polygon)
        post_p = crop_patch(post, polygon)
        patch = build_6ch_input(pre_p, post_p)
        if self.augment:
            patch = _augment_6ch(patch)
        return patch, rec.label_idx
