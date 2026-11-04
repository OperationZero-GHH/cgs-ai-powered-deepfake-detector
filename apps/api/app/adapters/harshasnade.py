"""Vendored & reviewed implementation of Harshasnade/Deepfake_Detection_System_V1.

Combines EfficientNetV2-S (spatial), 2D FFT magnitude CNN (frequency), 4x4 patch
unfold CNN (local anomalies), and Swin Transformer V2-T (global context).
Weights are loaded strictly via SafeTensors. No remote code is executed.
Disabled by default behind ENABLE_HARSHASNADE_MODEL due to unspecified upstream license.
"""

from __future__ import annotations

import logging
import math
import os
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from PIL import Image

from app.adapters.protocol import DetectorOutput

logger = logging.getLogger("cgs.adapters.harshasnade")

REPO_ID = "Harshasnade/Deepfake_Detection_System_V1"
REVISION = "14d286569e5fd1deab4def3a2d8af97aff442007"
EXPECTED_SHA256 = "a58fd840e8ebab964a3021acb9e365fe445a86dbcb8af93d808f68eb3a254ad4"
INPUT_SIZE = (256, 256)


def _get_fft_feature(x: torch.Tensor) -> torch.Tensor:
    """Compute Log-Magnitude Spectrum of input images (B, C, H, W)."""
    if x.dim() == 3:
        x = x.unsqueeze(0)
    fft = torch.fft.fft2(x, norm="ortho")
    mag = torch.abs(fft)
    mag = torch.log(mag + 1e-6)
    return torch.fft.fftshift(mag, dim=(-2, -1))


class _RGBBranch(nn.Module):
    def __init__(self):
        super().__init__()
        from torchvision import models

        self.net = models.efficientnet_v2_s(weights=None)
        self.features = self.net.features
        self.avgpool = self.net.avgpool
        self.out_dim = 1280

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = self.avgpool(x)
        return torch.flatten(x, 1)


class _FreqBranch(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((1, 1)),
        )
        self.out_dim = 128

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return torch.flatten(self.net(x), 1)


class _PatchBranch(nn.Module):
    def __init__(self):
        super().__init__()
        self.patch_encoder = nn.Sequential(
            nn.Conv2d(3, 16, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(16, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((1, 1)),
        )
        self.out_dim = 64

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # Create 4x4=16 patches of size 64x64 from 256x256 image
        patches = x.unfold(2, 64, 64).unfold(3, 64, 64)
        b, c, h_grid, w_grid, h_patch, w_patch = patches.shape
        patches = patches.permute(0, 2, 3, 1, 4, 5).contiguous()
        patches = patches.view(b * h_grid * w_grid, c, h_patch, w_patch)
        feats = self.patch_encoder(patches)
        feats = torch.flatten(feats, 1)
        feats = feats.view(b, h_grid * w_grid, -1)
        feats_max, _ = torch.max(feats, dim=1)
        return feats_max


class _ViTBranch(nn.Module):
    def __init__(self):
        super().__init__()
        from torchvision import models

        self.net = models.swin_v2_t(weights=None)
        self.out_dim = self.net.head.in_features
        self.net.head = nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class _DeepfakeHybridNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.rgb_branch = _RGBBranch()
        self.freq_branch = _FreqBranch()
        self.patch_branch = _PatchBranch()
        self.vit_branch = _ViTBranch()

        input_dim = (
            self.rgb_branch.out_dim
            + self.freq_branch.out_dim
            + self.patch_branch.out_dim
            + self.vit_branch.out_dim
        )
        self.classifier = nn.Sequential(
            nn.Linear(input_dim, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(512, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        rgb_feat = self.rgb_branch(x)
        freq_img = _get_fft_feature(x)
        freq_feat = self.freq_branch(freq_img)
        patch_feat = self.patch_branch(x)
        vit_feat = self.vit_branch(x)
        combined = torch.cat([rgb_feat, freq_feat, patch_feat, vit_feat], dim=1)
        return self.classifier(combined)


class HarshasnadeDetector:
    """Vendored hybrid detector (Harshasnade/Deepfake_Detection_System_V1)."""

    name = REPO_ID
    version = REVISION

    def __init__(self, weights_path: Path | str | None = None, device: str | None = None):
        self.weights_path = Path(weights_path) if weights_path else None
        self.device = torch.device(
            device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        )
        self._model = None
        self._enabled = os.getenv("ENABLE_HARSHASNADE_MODEL", "false").strip().lower() in {
            "1",
            "true",
            "yes",
        }
        self._available = False
        self._unavailable_reason = (
            "Disabled by default due to unspecified upstream license. "
            "Set ENABLE_HARSHASNADE_MODEL=true to enable."
            if not self._enabled
            else "Weights not loaded"
        )

    def _ensure_loaded(self) -> bool:
        if not self._enabled:
            return False
        if self._available and self._model is not None:
            return True

        if not self.weights_path or not self.weights_path.is_file():
            self._available = False
            self._unavailable_reason = "SafeTensors weights file not found"
            return False

        try:
            from safetensors.torch import load_file

            model = _DeepfakeHybridNet()
            state_dict = load_file(str(self.weights_path), device="cpu")
            model.load_state_dict(state_dict, strict=True)
            model.to(self.device)
            model.eval()
            self._model = model
            self._available = True
            self._unavailable_reason = ""
            logger.info("Loaded vendored %s (revision=%s)", REPO_ID, REVISION[:8])
            return True
        except Exception as exc:
            self._available = False
            self._unavailable_reason = f"Failed to load weights: {type(exc).__name__}"
            logger.warning("Failed to load %s: %s", REPO_ID, exc)
            return False

    def _preprocess(self, img: Image.Image) -> torch.Tensor:
        rgb = img.convert("RGB")
        resized = rgb.resize(INPUT_SIZE, Image.Resampling.BILINEAR)
        arr = np.asarray(resized, dtype=np.float32) / 255.0
        # Normalize to [-1, 1] as typical for hybrid architectures
        normalized = (arr - 0.5) / 0.5
        tensor = torch.from_numpy(np.transpose(normalized, (2, 0, 1))).unsqueeze(0)
        return tensor.to(self.device, dtype=torch.float32)

    def predict(self, img: Image.Image) -> DetectorOutput:
        start_time = time.perf_counter()
        if not self._enabled or not self._ensure_loaded() or self._model is None:
            return DetectorOutput(
                name=self.name,
                version=self.version,
                p_fake=0.5,
                ok=False,
                error=self._unavailable_reason,
                latency_ms=round((time.perf_counter() - start_time) * 1000),
            )

        try:
            with torch.inference_mode():
                tensor = self._preprocess(img)
                logit = self._model(tensor)
                val = float(logit[0, 0].item())

                if math.isnan(val) or math.isinf(val):
                    raise ValueError("Model output contains NaN or Inf values")

                p_fake = float(torch.sigmoid(torch.tensor(val)).item())
                p_fake = max(0.0, min(1.0, p_fake))
                latency = round((time.perf_counter() - start_time) * 1000)

                return DetectorOutput(
                    name=self.name,
                    version=self.version,
                    p_fake=round(p_fake, 6),
                    raw_logits=[round(val, 4)],
                    label_map_used={"0": "single_logit_sigmoid"},
                    latency_ms=latency,
                    ok=True,
                    error=None,
                    details={"architecture": "EfficientNetV2-S + Swin-V2-T + FFT + Patch"},
                )
        except Exception as exc:
            latency = round((time.perf_counter() - start_time) * 1000)
            logger.warning("Prediction error in %s: %s", self.name, exc)
            return DetectorOutput(
                name=self.name,
                version=self.version,
                p_fake=0.5,
                ok=False,
                error=f"Inference error: {type(exc).__name__}",
                latency_ms=latency,
            )

    def healthcheck(self) -> dict[str, object]:
        return {
            "name": self.name,
            "version": self.version,
            "enabled": self._enabled,
            "ready": self._available,
            "device": str(self.device),
            "details": "Ready for inference" if self._available else self._unavailable_reason,
        }
