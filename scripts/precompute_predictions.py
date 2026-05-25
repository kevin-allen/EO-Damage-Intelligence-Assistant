"""Run the trained ResNet50 on every catalog scenario and write JSON predictions.

Runs OFFLINE inside the app image. On this workstation (Docker 29, no AMD
GPU), invoke with a plain `docker run` rather than `docker compose run`:

    docker compose stop ollama  # free VRAM
    docker run --rm --device nvidia.com/gpu=all --shm-size=2g \\
      -v /data/xView2:/data/xView2:ro \\
      -v /data/eo-damage-models:/data/eo-damage-models \\
      -v "$PWD/predictions:/app/predictions" \\
      -v "$HOME/.cache/torch":/root/.cache/torch \\
      -e XVIEW2_ROOT=/data/xView2 \\
      -e CV_CHECKPOINT_PATH=/data/eo-damage-models/resnet50_damage.pt \\
      eo-damage-app:latest python -u scripts/precompute_predictions.py
    docker compose start ollama

For each scenario in app/scenarios/catalog.yaml, loads pre/post images and
GT polygons from /data/xView2/test, classifies each building with the
trained model, and writes predictions/<scenario_id>.json. Re-run whenever
the catalog or model changes.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

import torch
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.cv.dataset import IDX_TO_LABEL, iter_building_patches
from app.cv.model import load_checkpoint
from app.cv.predictions import BuildingPrediction, save_predictions
from app.scenarios.loader import Scenario, get_scenario, load_catalog, scenario_image_paths


DEFAULT_CHECKPOINT = Path(os.environ.get("CV_CHECKPOINT_PATH", "/data/eo-damage-models/resnet50_damage.pt"))
DEFAULT_PREDICTIONS_DIR = Path("predictions")
DEFAULT_BATCH_SIZE = 128


log = logging.getLogger("precompute_predictions")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    p.add_argument("--predictions-dir", type=Path, default=DEFAULT_PREDICTIONS_DIR)
    p.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    p.add_argument("--device", default="auto", help="auto, cuda, or cpu")
    p.add_argument("--scenario-id", default=None, help="Only process this scenario (default: all)")
    return p.parse_args(argv)


def resolve_device(spec: str) -> torch.device:
    if spec == "cpu":
        return torch.device("cpu")
    if spec in ("cuda", "auto") and torch.cuda.is_available():
        return torch.device("cuda")
    if spec == "cuda":
        raise RuntimeError("--device cuda requested but CUDA is unavailable")
    return torch.device("cpu")


@torch.no_grad()
def predict_scenario(
    scenario: Scenario,
    model: torch.nn.Module,
    device: torch.device,
    batch_size: int,
) -> list[BuildingPrediction]:
    """Classify every annotated building in the scenario's tile."""
    pre_path, post_path, post_label_path = scenario_image_paths(scenario)
    patches = iter_building_patches(pre_path, post_path, post_label_path)
    if not patches:
        log.warning(f"{scenario.id}: no annotated buildings found")
        return []

    predictions: list[BuildingPrediction] = []
    for start in range(0, len(patches), batch_size):
        batch = patches[start : start + batch_size]
        x = torch.stack([bp.patch_6ch for bp in batch]).to(device, non_blocking=True)
        logits = model(x)
        probs = torch.softmax(logits, dim=1)
        confs, idxs = probs.max(dim=1)
        for bp, ci, ix in zip(batch, confs.tolist(), idxs.tolist()):
            predictions.append(
                BuildingPrediction(
                    building_id=bp.building_id,
                    polygon=[(float(x), float(y)) for x, y in bp.polygon_xy],
                    damage_class=IDX_TO_LABEL[ix],
                    confidence=float(ci),
                )
            )
    return predictions


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    device = resolve_device(args.device)
    log.info(f"device={device}, checkpoint={args.checkpoint}, batch_size={args.batch_size}")

    if not args.checkpoint.exists():
        log.error(f"checkpoint not found: {args.checkpoint}")
        return 1

    if args.scenario_id is not None:
        scenarios = [get_scenario(args.scenario_id)]
    else:
        scenarios = load_catalog()
    log.info(f"processing {len(scenarios)} scenario(s)")

    t0 = time.time()
    model = load_checkpoint(args.checkpoint, device=device)
    log.info(f"model loaded in {time.time()-t0:.1f}s")

    total_buildings = 0
    for s in tqdm(scenarios, desc="scenarios"):
        t_s = time.time()
        preds = predict_scenario(s, model, device, args.batch_size)
        out_path = save_predictions(s.id, preds, args.predictions_dir)
        total_buildings += len(preds)
        log.info(
            f"{s.id}: {len(preds):4d} buildings -> {out_path} "
            f"({time.time()-t_s:.1f}s)"
        )

    log.info(f"done: {len(scenarios)} scenarios, {total_buildings} buildings total "
             f"in {time.time()-t0:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
