"""One-time fine-tune of the ResNet50 damage classifier.

Runs OFFLINE inside the app image. Invoke with:

    docker compose stop ollama
    docker compose run --rm --gpus all app python scripts/train_classifier.py
    docker compose start ollama

Reads xView2 train split from /data/xView2, crops building patches via
ground-truth polygons, fine-tunes the model, and writes
/data/eo-damage-models/resnet50_damage.pt.

Validation is done against the xView2 test split (we never benchmark
against it as a real held-out test set — this is a prototype, the test
split just gives us a quick val signal during training).

Expected runtime on RTX 2080 Ti: ~2-3 h for 5 epochs at batch 64.
"""

from __future__ import annotations

import argparse
import logging
import math
import os
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader
from tqdm import tqdm

# Make the repo root importable when running this as `python scripts/...`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.cv.dataset import IDX_TO_LABEL, LABEL_NAMES, XView2BuildingDataset
from app.cv.model import build_model, save_checkpoint


DEFAULT_XVIEW2_ROOT = Path(os.environ.get("XVIEW2_ROOT", "/data/xView2"))
DEFAULT_CHECKPOINT = Path(os.environ.get("CV_CHECKPOINT_PATH", "/data/eo-damage-models/resnet50_damage.pt"))
DEFAULT_EPOCHS = 5
DEFAULT_BATCH_SIZE = 64
DEFAULT_LR = 1e-4
DEFAULT_NUM_WORKERS = 6
DEFAULT_SEED = 0


log = logging.getLogger("train_classifier")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--xview2-root", type=Path, default=DEFAULT_XVIEW2_ROOT)
    p.add_argument("--checkpoint-out", type=Path, default=DEFAULT_CHECKPOINT)
    p.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS)
    p.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    p.add_argument("--lr", type=float, default=DEFAULT_LR)
    p.add_argument("--num-workers", type=int, default=DEFAULT_NUM_WORKERS)
    p.add_argument("--device", default="auto", help="auto, cuda, or cpu")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--limit-train", type=int, default=None, help="Subsample N train buildings (smoke test)")
    p.add_argument("--limit-val", type=int, default=None, help="Subsample N val buildings (smoke test)")
    return p.parse_args(argv)


def resolve_device(spec: str) -> torch.device:
    if spec == "cpu":
        return torch.device("cpu")
    if spec in ("cuda", "auto") and torch.cuda.is_available():
        return torch.device("cuda")
    if spec == "cuda":
        raise RuntimeError("--device cuda requested but CUDA is unavailable")
    return torch.device("cpu")


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def compute_class_weights(counts: dict[str, int]) -> torch.Tensor:
    """1 / sqrt(freq) class weights, normalized to mean 1.

    sqrt softens the over-correction from pure inverse frequency; with raw
    inverse-freq the rare classes dominate the loss and the network just
    learns to predict them everywhere.
    """
    n = sum(counts[name] for name in LABEL_NAMES)
    weights = torch.tensor(
        [math.sqrt(n / max(1, counts[name])) for name in LABEL_NAMES],
        dtype=torch.float32,
    )
    return weights / weights.mean()


@torch.no_grad()
def validate(
    model: nn.Module,
    loader: DataLoader,
    loss_fn: nn.Module,
    device: torch.device,
) -> tuple[float, float, dict[str, float]]:
    """Return (balanced_accuracy, mean_loss, per_class_recall)."""
    model.eval()
    n_classes = len(LABEL_NAMES)
    per_class_correct = torch.zeros(n_classes, dtype=torch.long)
    per_class_total = torch.zeros(n_classes, dtype=torch.long)
    total_loss = 0.0
    total_seen = 0
    for x, y in tqdm(loader, desc="val", leave=False):
        x = x.to(device, non_blocking=True)
        y = y.to(device, non_blocking=True)
        logits = model(x)
        loss = loss_fn(logits, y)
        total_loss += loss.item() * x.size(0)
        total_seen += x.size(0)
        preds = logits.argmax(dim=1)
        for c in range(n_classes):
            mask = (y == c)
            per_class_total[c] += int(mask.sum().item())
            per_class_correct[c] += int(((preds == c) & mask).sum().item())
    per_class_recall = {
        IDX_TO_LABEL[c]: (per_class_correct[c].item() / per_class_total[c].item())
        if per_class_total[c].item() > 0 else float("nan")
        for c in range(n_classes)
    }
    valid = [v for v in per_class_recall.values() if not math.isnan(v)]
    balanced_acc = sum(valid) / len(valid) if valid else 0.0
    mean_loss = total_loss / max(1, total_seen)
    return balanced_acc, mean_loss, per_class_recall


def train_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    loss_fn: nn.Module,
    opt: torch.optim.Optimizer,
    device: torch.device,
    epoch: int,
) -> float:
    """Single training pass. Returns mean loss over the epoch."""
    model.train()
    total_loss = 0.0
    total_seen = 0
    pbar = tqdm(loader, desc=f"epoch {epoch} train", leave=False)
    for x, y in pbar:
        x = x.to(device, non_blocking=True)
        y = y.to(device, non_blocking=True)
        opt.zero_grad(set_to_none=True)
        logits = model(x)
        loss = loss_fn(logits, y)
        loss.backward()
        opt.step()
        bsz = x.size(0)
        total_loss += loss.item() * bsz
        total_seen += bsz
        pbar.set_postfix(loss=f"{loss.item():.4f}")
    return total_loss / max(1, total_seen)


def _maybe_subsample(ds: XView2BuildingDataset, limit: int | None, label: str) -> None:
    """In-place truncate the dataset's record list. For smoke tests only."""
    if limit is not None and limit < len(ds.records):
        rng = random.Random(0)
        sampled = rng.sample(ds.records, limit)
        ds.records = sampled
        log.info(f"{label}: subsampled to {limit} records")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    device = resolve_device(args.device)
    set_seed(args.seed)
    log.info(f"device={device}, seed={args.seed}, epochs={args.epochs}, "
             f"batch_size={args.batch_size}, lr={args.lr}")

    log.info(f"indexing train split at {args.xview2_root}/train ...")
    t0 = time.time()
    train_ds = XView2BuildingDataset(args.xview2_root, split="train", augment=True)
    log.info(f"train: {len(train_ds):,} buildings in {time.time()-t0:.1f}s")
    log.info(f"train class counts: {train_ds.class_counts()}")
    _maybe_subsample(train_ds, args.limit_train, "train")

    log.info(f"indexing val split at {args.xview2_root}/test ...")
    t0 = time.time()
    val_ds = XView2BuildingDataset(args.xview2_root, split="test", augment=False)
    log.info(f"val: {len(val_ds):,} buildings in {time.time()-t0:.1f}s")
    _maybe_subsample(val_ds, args.limit_val, "val")

    if len(train_ds) == 0:
        log.error("no training records found; aborting")
        return 1

    pin = device.type == "cuda"
    train_loader = DataLoader(
        train_ds, batch_size=args.batch_size, shuffle=True,
        num_workers=args.num_workers, pin_memory=pin, drop_last=True,
        persistent_workers=args.num_workers > 0,
    )
    val_loader = DataLoader(
        val_ds, batch_size=args.batch_size, shuffle=False,
        num_workers=args.num_workers, pin_memory=pin,
        persistent_workers=args.num_workers > 0,
    )

    model = build_model(pretrained=True).to(device)
    n_params = sum(p.numel() for p in model.parameters())
    log.info(f"model: ResNet50 6ch + 4-class head, {n_params:,} params")

    class_weights = compute_class_weights(train_ds.class_counts()).to(device)
    log.info(f"class weights (1/sqrt(freq), normalized): "
             f"{dict(zip(LABEL_NAMES, [round(w, 3) for w in class_weights.tolist()]))}")
    loss_fn = nn.CrossEntropyLoss(weight=class_weights)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)

    best_balanced_acc = -1.0
    args.checkpoint_out.parent.mkdir(parents=True, exist_ok=True)

    for epoch in range(args.epochs):
        t_epoch = time.time()
        train_loss = train_one_epoch(model, train_loader, loss_fn, opt, device, epoch)
        val_bacc, val_loss, per_class = validate(model, val_loader, loss_fn, device)
        log.info(
            f"epoch {epoch}: train_loss={train_loss:.4f} val_loss={val_loss:.4f} "
            f"val_balanced_acc={val_bacc:.4f} "
            f"per_class={ {k: round(v, 3) for k, v in per_class.items()} } "
            f"({time.time()-t_epoch:.1f}s)"
        )
        if val_bacc > best_balanced_acc:
            best_balanced_acc = val_bacc
            save_checkpoint(model, args.checkpoint_out)
            log.info(f"  new best val_balanced_acc={val_bacc:.4f}; saved to {args.checkpoint_out}")

    log.info(f"training complete; best val_balanced_acc={best_balanced_acc:.4f}; "
             f"checkpoint at {args.checkpoint_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
