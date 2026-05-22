"""ResNet50 damage classifier.

Architecture: torchvision ResNet50 with ImageNet-pretrained backbone and a
4-class classification head. Input is a 6-channel tensor (pre RGB stacked
with post RGB) on a 128x128 patch. The conv1 layer is expanded from 3 to 6
input channels by duplicating the pretrained 3-channel weights to both
halves (and scaling by 0.5 to preserve activation magnitude on unchanged
regions where pre ~= post).

Used offline by scripts/train_classifier.py and scripts/precompute_predictions.py.
Not used at runtime by the Streamlit app (predictions are precomputed).
"""

from __future__ import annotations

from pathlib import Path

import torch
from torch import nn
from torchvision import models
from torchvision.models import ResNet50_Weights


DAMAGE_CLASSES: tuple[str, ...] = (
    "no_damage",
    "minor_damage",
    "major_damage",
    "destroyed",
)
NUM_CLASSES: int = len(DAMAGE_CLASSES)
INPUT_CHANNELS: int = 6
PATCH_SIZE: int = 128


def _expand_conv1_to_6ch(model: nn.Module) -> None:
    """Replace the 3-channel conv1 with a 6-channel one in-place.

    The 3-channel ImageNet conv1 weights are duplicated to channels 0..2
    AND 3..5 and scaled by 0.5. With pre ~= post (most pixels in a tile),
    the conv output magnitude is preserved. Both halves start with the
    same ImageNet prior; the network learns to weight them differently
    during fine-tuning.
    """
    orig: nn.Conv2d = model.conv1
    new = nn.Conv2d(
        in_channels=INPUT_CHANNELS,
        out_channels=orig.out_channels,
        kernel_size=orig.kernel_size,
        stride=orig.stride,
        padding=orig.padding,
        bias=orig.bias is not None,
    )
    with torch.no_grad():
        w = orig.weight.data
        new.weight.data[:, 0:3] = w * 0.5
        new.weight.data[:, 3:6] = w * 0.5
        if orig.bias is not None:
            new.bias.data.copy_(orig.bias.data)
    model.conv1 = new


def build_model(pretrained: bool = True) -> nn.Module:
    """Construct the ResNet50 with 6-channel conv1 and a 4-class head."""
    weights = ResNet50_Weights.IMAGENET1K_V2 if pretrained else None
    model = models.resnet50(weights=weights)
    _expand_conv1_to_6ch(model)
    model.fc = nn.Linear(model.fc.in_features, NUM_CLASSES)
    return model


def load_checkpoint(path: str | Path, device: str | torch.device = "cpu") -> nn.Module:
    """Load a trained checkpoint into a fresh model instance.

    Returns the model on `device` in eval mode. For resuming training,
    call `.train()` on the returned model.
    """
    model = build_model(pretrained=False)
    state = torch.load(str(path), map_location=device, weights_only=True)
    model.load_state_dict(state)
    model.to(device)
    model.eval()
    return model


def save_checkpoint(model: nn.Module, path: str | Path) -> None:
    """Persist model weights (state_dict only) to disk."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), str(path))
