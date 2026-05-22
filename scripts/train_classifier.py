"""One-time fine-tune of the ResNet50 damage classifier.

Runs OFFLINE inside the app image. Invoke with:

    docker compose stop ollama
    docker compose run --rm --gpus all app python scripts/train_classifier.py
    docker compose start ollama

Reads xView2 train split from /data/xView2, crops building patches via
ground-truth polygons, trains the 4-class head (and optionally the last
backbone block), and writes /data/eo-damage-models/resnet50_damage.pt.

Expected runtime on RTX 2080 Ti: ~2-3 h.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


DEFAULT_XVIEW2_ROOT = Path(os.environ.get("XVIEW2_ROOT", "/data/xView2"))
DEFAULT_CHECKPOINT = Path(os.environ.get("CV_CHECKPOINT_PATH", "/data/eo-damage-models/resnet50_damage.pt"))
DEFAULT_EPOCHS = 5
DEFAULT_BATCH_SIZE = 64
DEFAULT_LR = 1e-4


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--xview2-root", type=Path, default=DEFAULT_XVIEW2_ROOT)
    p.add_argument("--checkpoint-out", type=Path, default=DEFAULT_CHECKPOINT)
    p.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS)
    p.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    p.add_argument("--lr", type=float, default=DEFAULT_LR)
    p.add_argument("--device", default="cuda")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    raise NotImplementedError("training loop not implemented yet")


if __name__ == "__main__":
    sys.exit(main())
