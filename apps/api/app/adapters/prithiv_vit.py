"""Adapter for prithivMLmods/Deep-Fake-Detector-v2-Model Vision Transformer model."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from app.adapters.protocol import DetectorOutput

logger = logging.getLogger("cgs.adapters.prithiv_vit")

REPO_ID = "prithivMLmods/Deep-Fake-Detector-v2-Model"
REVISION = "3a99ae26f52c7ac7c3a53103b6cf3a8b617f7093"
EXPECTED_SHA256 = "88ac0939285009e3700cfc9b9a0912b14b092d200ef0df86efe4f2cf190ea4de"
INPUT_SIZE = (224, 224)
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


class PrithivViTDetector:
    """Vision Transformer deepfake detector (prithivMLmods/Deep-Fake-Detector-v2-Model)."""

    name = REPO_ID
    version = REVISION

    def __init__(self, model_dir: Path | str | None = None, device: str | None = None):
        self.model_dir = Path(model_dir) if model_dir else None
        self.device = torch.device(
            device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        )
        self._model = None
        self._id2label: dict[int, str] = {0: "Realism", 1: "Deepfake"}
        self._fake_index = 1
        self._available = False
        self._unavailable_reason = "Model not initialized"

    def _ensure_loaded(self) -> bool:
        if self._available and self._model is not None:
            return True
        try:
            from transformers import AutoConfig, AutoModelForImageClassification

            source = (
                str(self.model_dir) if (self.model_dir and self.model_dir.is_dir()) else REPO_ID
            )
            config = AutoConfig.from_pretrained(
                source,
                revision=REVISION,
                local_files_only=False if not self.model_dir else True,
                trust_remote_code=False,
            )
            # Parse label mapping dynamically from config
            if hasattr(config, "id2label") and config.id2label:
                self._id2label = {int(k): str(v) for k, v in config.id2label.items()}
                for idx, lbl in self._id2label.items():
                    if lbl.lower() in {"deepfake", "fake", "synthesized", "ai"}:
                        self._fake_index = idx
                        break

            self._model = AutoModelForImageClassification.from_pretrained(
                source,
                revision=REVISION,
                config=config,
                torch_dtype=torch.float32,
                trust_remote_code=False,
            )
            self._model.to(self.device)
            self._model.eval()
            self._available = True
            self._unavailable_reason = ""
            logger.info("Loaded %s (revision=%s) on %s", REPO_ID, REVISION[:8], self.device)
            return True
        except Exception as exc:
            self._available = False
            self._unavailable_reason = f"Failed to load {REPO_ID}: {type(exc).__name__}"
            logger.warning("Failed to load %s: %s", REPO_ID, exc)
            return False

    def _preprocess(self, img: Image.Image) -> torch.Tensor:
        """Deterministic ViT preprocessing."""
        rgb = img.convert("RGB")
        resized = rgb.resize(INPUT_SIZE, Image.Resampling.BILINEAR)
        arr = np.asarray(resized, dtype=np.float32) / 255.0
        normalized = (arr - IMAGENET_MEAN) / IMAGENET_STD
        tensor = torch.from_numpy(np.transpose(normalized, (2, 0, 1))).unsqueeze(0)
        return tensor.to(self.device, dtype=torch.float32)

    def predict(self, img: Image.Image, test_time_crops: bool = True) -> DetectorOutput:
        start_time = time.perf_counter()
        if not self._ensure_loaded() or self._model is None:
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
                primary_tensor = self._preprocess(img)
                outputs = self._model(primary_tensor)
                logits = outputs.logits[0].cpu()

                if torch.isnan(logits).any() or torch.isinf(logits).any():
                    raise ValueError("Model output contains NaN or Inf values")

                probs = torch.softmax(logits, dim=-1)
                primary_fake = float(probs[self._fake_index].item())

                # Test-time crop robustness
                if test_time_crops and min(img.size) > 64:
                    w, h = img.size
                    cw, ch = int(w * 0.85), int(h * 0.85)
                    left, top = (w - cw) // 2, (h - ch) // 2
                    center_crop = img.crop((left, top, left + cw, top + ch))
                    crop_tensor = self._preprocess(center_crop)
                    crop_outputs = self._model(crop_tensor)
                    crop_logits = crop_outputs.logits[0].cpu()
                    if not (torch.isnan(crop_logits).any() or torch.isinf(crop_logits).any()):
                        crop_probs = torch.softmax(crop_logits, dim=-1)
                        crop_fake = float(crop_probs[self._fake_index].item())
                        final_fake = 0.7 * primary_fake + 0.3 * crop_fake
                    else:
                        final_fake = primary_fake
                else:
                    final_fake = primary_fake

                final_fake = max(0.0, min(1.0, float(final_fake)))
                latency = round((time.perf_counter() - start_time) * 1000)

                return DetectorOutput(
                    name=self.name,
                    version=self.version,
                    p_fake=round(final_fake, 6),
                    raw_logits=[round(float(x), 4) for x in logits.tolist()],
                    label_map_used={str(k): v for k, v in self._id2label.items()},
                    latency_ms=latency,
                    ok=True,
                    error=None,
                    details={"primary_score": round(primary_fake, 6), "device": str(self.device)},
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
            "ready": self._available,
            "device": str(self.device),
            "details": "Ready for inference" if self._available else self._unavailable_reason,
        }
