"""ResNet50 damage classifier.

Architecture: torchvision ResNet50 with ImageNet-pretrained backbone and a
4-class classification head. Input is a 6-channel tensor (pre RGB stacked
with post RGB) on a 128x128 patch. The conv1 layer is expanded from 3 to 6
input channels by duplicating the pretrained 3-channel weights.

Used offline by scripts/train_classifier.py and scripts/precompute_predictions.py.
Not used at runtime by the Streamlit app.
"""

from __future__ import annotations

import torch
from torch import nn


DAMAGE_CLASSES: tuple[str, ...] = (
    "no_damage",
    "minor_damage",
    "major_damage",
    "destroyed",
)
NUM_CLASSES: int = len(DAMAGE_CLASSES)
INPUT_CHANNELS: int = 6
PATCH_SIZE: int = 128


def build_model(pretrained: bool = True) -> nn.Module:
    """Construct the ResNet50 with 6-channel conv1 and a 4-class head."""
    raise NotImplementedError


def load_checkpoint(path: str, device: str | torch.device = "cpu") -> nn.Module:
    """Load a trained checkpoint from disk into a fresh model instance."""
    raise NotImplementedError


def save_checkpoint(model: nn.Module, path: str) -> None:
    """Persist model weights to disk."""
    raise NotImplementedError
