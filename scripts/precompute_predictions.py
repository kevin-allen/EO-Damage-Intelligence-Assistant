"""Run the trained ResNet50 on every catalog scenario and write JSON predictions.

Runs OFFLINE inside the app image. Invoke with:

    docker compose stop ollama
    docker compose run --rm --gpus all app python scripts/precompute_predictions.py
    docker compose start ollama

For each scenario in app/scenarios/catalog.yaml, loads pre/post images and
GT polygons from /data/xView2, classifies each building, and writes
predictions/<scenario_id>.json. Re-run whenever the catalog or model changes.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


DEFAULT_CHECKPOINT = Path(os.environ.get("CV_CHECKPOINT_PATH", "/data/eo-damage-models/resnet50_damage.pt"))
DEFAULT_PREDICTIONS_DIR = Path("predictions")
DEFAULT_BATCH_SIZE = 128


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    p.add_argument("--predictions-dir", type=Path, default=DEFAULT_PREDICTIONS_DIR)
    p.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    p.add_argument("--device", default="cuda")
    p.add_argument("--scenario-id", default=None, help="Only process this scenario (default: all)")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    raise NotImplementedError("precompute loop not implemented yet")


if __name__ == "__main__":
    sys.exit(main())
