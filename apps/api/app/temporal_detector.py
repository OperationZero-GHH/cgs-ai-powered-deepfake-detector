"""ResNeXt50 + LSTM temporal detector for video media.

The model uses the publisher's checkpoint and architecture. It never substitutes
randomly initialized weights: a video score is emitted only after checkpoint
validation and a successful forward pass.
"""

from __future__ import annotations

import io
import logging
import os
import time
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger("cgs.temporal_detector")

HF_MODEL_ID = "Naman712/Deep-fake-detection"
HF_CHECKPOINT = "model_87_acc_20_frames_final_data.pt"
HF_TOKEN = os.getenv("HF_TOKEN", "")
TEMPORAL_THRESHOLD = 0.60
_FILE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _FILE_DIR.parent.parent
DEFAULT_TEMPORAL_CACHE = _REPO_ROOT / "models" / "temporal_cache"
TEMPORAL_CACHE_DIR = Path(os.getenv("TEMPORAL_MODEL_CACHE", str(DEFAULT_TEMPORAL_CACHE))).resolve()
INPUT_SIZE = (112, 112)
SEQUENCE_LENGTH = 20
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def _preprocess_frame_tensor(jpeg_bytes: bytes) -> np.ndarray:
    """Convert a JPEG frame to the publisher's normalized (3, 112, 112) input."""
    from PIL import Image, ImageOps

    with Image.open(io.BytesIO(jpeg_bytes)) as image:
        image = ImageOps.exif_transpose(image).convert("RGB")
        image = image.resize(INPUT_SIZE, Image.Resampling.BILINEAR)
        pixels = np.asarray(image, dtype=np.float32) / 255.0
    normalized = (pixels - IMAGENET_MEAN) / IMAGENET_STD
    return np.transpose(normalized, (2, 0, 1)).copy()


class TemporalDeepfakeDetector:
    """Load and run the trained, gated ResNeXt50 + LSTM video checkpoint."""

    name = "temporal_resnext50_lstm"
    model_version = "naman712-resnext50-lstm-20f-v1"

    def __init__(self, hf_token: str = "", cache_dir: Path | None = None):
        self._hf_token = hf_token or HF_TOKEN
        self._cache_dir = cache_dir or TEMPORAL_CACHE_DIR
        self._model = None
        self._device = None
        self._available: bool | None = None
        self._unavailable_reason = "The trained temporal checkpoint has not been loaded."

    def _ensure_loaded(self) -> bool:
        if self._available is not None:
            return self._available

        try:
            import torch
            import torch.nn as nn
            import torchvision.models as models

            try:
                torch.set_num_threads(max(1, int(os.getenv("INFERENCE_CPU_THREADS", "2"))))
                torch.set_num_interop_threads(1)
            except RuntimeError:
                # The runtime may already have initialized its inter-op pool.
                pass

            checkpoint_path = self._checkpoint_path()
            if checkpoint_path is None:
                checkpoint_path = self._download_weights()
            if checkpoint_path is None:
                self._unavailable_reason = (
                    "The trained video checkpoint is unavailable. Grant access to the model "
                    "on Hugging Face and configure HF_TOKEN, or install the checkpoint locally."
                )
                self._available = False
                return False

            self._device = torch.device("cpu")
            model = self._build_model(nn, models)
            checkpoint = torch.load(checkpoint_path, map_location=self._device, weights_only=True)
            if isinstance(checkpoint, dict):
                state_dict = checkpoint.get("state_dict", checkpoint.get("model_state_dict", checkpoint))
            else:
                raise TypeError("Checkpoint must contain a state dictionary.")
            cleaned = {key.removeprefix("module."): value for key, value in state_dict.items()}
            model.load_state_dict(cleaned, strict=True)
            model.eval()

            # Verify the architecture/checkpoint pair before reporting readiness.
            with torch.inference_mode():
                _, logits = model(torch.zeros((1, SEQUENCE_LENGTH, 3, *INPUT_SIZE), dtype=torch.float32))
            if tuple(logits.shape) != (1, 2) or not torch.isfinite(logits).all():
                raise ValueError("Checkpoint smoke inference returned an invalid result.")

            self._model = model
            self._available = True
            self._unavailable_reason = ""
            logger.info("Loaded trained temporal checkpoint %s", checkpoint_path.name)
            return True
        except ImportError:
            self._unavailable_reason = "PyTorch and torchvision are required for video analysis."
        except Exception as exc:
            # Do not print exception strings from model access; they may include credentials or URLs.
            self._unavailable_reason = f"The trained temporal checkpoint could not be loaded ({type(exc).__name__})."
            logger.warning("Temporal checkpoint load failed (%s).", type(exc).__name__)
        self._available = False
        return False

    def _checkpoint_path(self) -> Path | None:
        if not self._cache_dir.is_dir():
            return None
        path = self._cache_dir / HF_CHECKPOINT
        if path.is_file() and path.stat().st_size > 1_000_000:
            return path
        return None

    def _download_weights(self) -> Path | None:
        try:
            from huggingface_hub import hf_hub_download

            self._cache_dir.mkdir(parents=True, exist_ok=True)
            path = Path(hf_hub_download(
                repo_id=HF_MODEL_ID,
                filename=HF_CHECKPOINT,
                token=self._hf_token or None,
                cache_dir=str(self._cache_dir),
                local_dir=str(self._cache_dir),
            ))
            return path if path.is_file() and path.stat().st_size > 1_000_000 else None
        except ImportError:
            self._unavailable_reason = "huggingface_hub is required to download the video checkpoint."
        except Exception as exc:
            logger.warning("Temporal checkpoint download failed (%s).", type(exc).__name__)
        return None

    @staticmethod
    def _build_model(nn: Any, models: Any):
        """Architecture and parameter names matching the publisher's checkpoint."""

        class DeepFakeDetector(nn.Module):
            def __init__(self):
                super().__init__()
                backbone = models.resnext50_32x4d(weights=None)
                self.model = nn.Sequential(*list(backbone.children())[:-2])
                # The publisher's checkpoint has no LSTM biases; match it exactly.
                self.lstm = nn.LSTM(2048, 2048, num_layers=1, bias=False)
                self.relu = nn.LeakyReLU()
                self.dp = nn.Dropout(0.4)
                self.linear1 = nn.Linear(2048, 2)
                self.avgpool = nn.AdaptiveAvgPool2d(1)

            def forward(self, x):
                batch_size, sequence_length, channels, height, width = x.shape
                x = x.reshape(batch_size * sequence_length, channels, height, width)
                feature_map = self.model(x)
                features = self.avgpool(feature_map)
                features = features.reshape(batch_size, sequence_length, 2048)
                sequence_output, _ = self.lstm(features, None)
                logits = self.dp(self.linear1(sequence_output[:, -1, :]))
                return feature_map, logits

        return DeepFakeDetector()

    def healthcheck(self) -> dict[str, object]:
        if self._available is True:
            status = "ready"
            details = "Validated trained ResNeXt50 + LSTM checkpoint; CPU inference enabled."
        elif self._available is False:
            status = "unavailable"
            details = self._unavailable_reason
        else:
            status = "ready_to_load" if self._checkpoint_path() else "unavailable"
            details = (
                "Trained checkpoint is present and will be validated on first video analysis."
                if status == "ready_to_load"
                else "Trained checkpoint is missing or requires Hugging Face access."
            )
        return {
            "status": status,
            "model_id": HF_MODEL_ID,
            "model_version": self.model_version,
            "layer": "temporal_sequence",
            "details": details,
        }

    def analyze_frame_sequence(
        self, frame_jpeg_list: list[bytes], *, max_sequence: int = SEQUENCE_LENGTH
    ) -> dict[str, Any]:
        started = time.perf_counter()
        if not self._ensure_loaded():
            return {
                "status": "unavailable",
                "provider": self.name,
                "layer": "temporal",
                "model_id": HF_MODEL_ID,
                "limitations": (self._unavailable_reason,),
            }
        if not frame_jpeg_list:
            return {
                "status": "failed",
                "provider": self.name,
                "layer": "temporal",
                "limitations": ("No frames were supplied for temporal analysis.",),
            }

        try:
            import torch
            import torch.nn.functional as F

            frames = [
                _preprocess_frame_tensor(jpeg_bytes)
                for jpeg_bytes in frame_jpeg_list[: min(max_sequence, SEQUENCE_LENGTH)]
            ]
            if not frames:
                raise ValueError("No video frames could be decoded.")
            while len(frames) < SEQUENCE_LENGTH:
                frames.append(frames[-1].copy())
            sequence = torch.from_numpy(np.stack(frames[:SEQUENCE_LENGTH])).unsqueeze(0)
            with torch.inference_mode():
                _, logits = self._model(sequence)
                probabilities = F.softmax(logits, dim=1)[0]
            # The publisher defines output index 1 as fake; keep this mapping aligned.
            fake_score = float(probabilities[1].item())
            if not np.isfinite(fake_score):
                raise ValueError("Model returned a non-finite probability.")
            return {
                "status": "completed",
                "provider": self.name,
                "model_id": HF_MODEL_ID,
                "model_version": self.model_version,
                "layer": "temporal",
                "label": "ai_generated_signal" if fake_score >= TEMPORAL_THRESHOLD else "no_strong_ai_signal",
                "score": round(fake_score, 6),
                "temporal_lstm_score": round(fake_score, 6),
                "frames_processed": min(len(frame_jpeg_list), SEQUENCE_LENGTH),
                "sequence_length": SEQUENCE_LENGTH,
                "threshold": TEMPORAL_THRESHOLD,
                "score_semantics": "Softmax score for the model's fake class; not a calibrated probability.",
                "latency_ms": round((time.perf_counter() - started) * 1000),
                "limitations": (
                    "The publisher trained this detector primarily for human-face videos; it may be less reliable without clear faces or with low resolution, heavy compression, or motion blur.",
                    "This detector may not generalize to every manipulation type.",
                    "The score is a model output, not proof of authenticity or population-calibrated probability.",
                ),
            }
        except Exception as exc:
            logger.warning("Temporal detector inference failed (%s).", type(exc).__name__)
            return {
                "status": "failed",
                "provider": self.name,
                "layer": "temporal",
                "latency_ms": round((time.perf_counter() - started) * 1000),
                "limitations": (f"Temporal inference failed ({type(exc).__name__}); no temporal score was produced.",),
            }


def create_temporal_detector(hf_token: str = "", cache_dir: Path | None = None) -> TemporalDeepfakeDetector:
    return TemporalDeepfakeDetector(hf_token=hf_token, cache_dir=cache_dir)
