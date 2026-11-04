"""Model supply-chain loader, integrity verification, and warm singleton registry."""

from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any

from app.adapters.audio_wav2vec2 import AudioWav2Vec2Detector
from app.adapters.dima_vit import DimaViTDetector
from app.adapters.harshasnade import HarshasnadeDetector
from app.adapters.prithiv_vit import PrithivViTDetector
from app.adapters.protocol import AudioDetector, ImageDetector

logger = logging.getLogger("cgs.model_loader")

REPO_ROOT = Path(__file__).resolve().parents[3]
LOCKFILE_PATH = REPO_ROOT / "models.lock.json"
MODELS_CACHE_DIR = REPO_ROOT / "models"


class ModelIntegrityError(Exception):
    """Raised when local model files do not match cryptographic lockfile digests."""

    pass


def compute_sha256(file_path: Path) -> str:
    """Compute streaming SHA-256 digest of a file."""
    hasher = hashlib.sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_models_lockfile(
    lockfile_path: Path = LOCKFILE_PATH, models_dir: Path = MODELS_CACHE_DIR
) -> dict[str, bool]:
    """Verify local files against models.lock.json. Returns map of model_id -> verified."""
    if not lockfile_path.is_file():
        logger.warning("models.lock.json not found at %s", lockfile_path)
        return {}

    try:
        lock_data = json.loads(lockfile_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ModelIntegrityError(f"Failed to parse models.lock.json: {exc}") from exc

    results: dict[str, bool] = {}
    models_spec = lock_data.get("models", {})

    for model_id, spec in models_spec.items():
        files_spec = spec.get("files", {})
        all_ok = True
        for filename, file_meta in files_spec.items():
            expected_hash = file_meta.get("sha256")
            expected_size = file_meta.get("size_bytes")

            # Candidate locations
            target_file = models_dir / filename
            if not target_file.is_file():
                # Check nested under model_id folder
                nested_target = models_dir / model_id.split("/")[-1] / filename
                if nested_target.is_file():
                    target_file = nested_target
                else:
                    logger.debug("Model file not found locally: %s for %s", filename, model_id)
                    all_ok = False
                    continue

            # Verify size
            if expected_size and target_file.stat().st_size != expected_size:
                raise ModelIntegrityError(
                    f"Size mismatch for {filename} "
                    f"({target_file.stat().st_size} != {expected_size})"
                )

            # Verify SHA-256
            if expected_hash:
                actual_hash = compute_sha256(target_file)
                if actual_hash != expected_hash:
                    raise ModelIntegrityError(
                        f"SHA-256 mismatch for {filename} ({actual_hash} != {expected_hash})"
                    )

        results[model_id] = all_ok

    logger.info("Cryptographic model integrity verification completed: %s", results)
    return results


class ModelRegistry:
    """Warm model registry holding singletons initialized once on worker/API startup."""

    def __init__(self, models_dir: Path = MODELS_CACHE_DIR):
        self.models_dir = models_dir
        self.image_detectors: list[ImageDetector] = []
        self.audio_detector: AudioDetector | None = None
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return

        # Enforce offline execution at runtime (Section 2 Rule 5)
        if os.getenv("OFFLINE_INFERENCE", "true").strip().lower() in {"1", "true"}:
            os.environ["HF_HUB_OFFLINE"] = "1"
            os.environ["TRANSFORMERS_OFFLINE"] = "1"

        logger.info("Initializing warm model registry...")

        # 1. Initialize dima806 ViT
        dima_enabled = os.getenv("ENABLE_DIMA_MODEL", "true").strip().lower() in {"1", "true"}
        if dima_enabled:
            dima = DimaViTDetector(model_dir=self.models_dir / "deepfake_vs_real_image_detection")
            self.image_detectors.append(dima)

        # 2. Initialize prithivMLmods ViT
        prithiv_enabled = os.getenv("ENABLE_PRITHIV_MODEL", "true").strip().lower() in {"1", "true"}
        if prithiv_enabled:
            prithiv = PrithivViTDetector(model_dir=self.models_dir / "Deep-Fake-Detector-v2-Model")
            self.image_detectors.append(prithiv)

        # 3. Initialize Harshasnade hybrid (disabled by default)
        harshas_enabled = os.getenv("ENABLE_HARSHASNADE_MODEL", "false").strip().lower() in {
            "1",
            "true",
        }
        if harshas_enabled:
            weights_path = (
                self.models_dir / "Deepfake_Detection_System_V1" / "best_model.safetensors"
            )
            harshas = HarshasnadeDetector(weights_path=weights_path)
            self.image_detectors.append(harshas)

        # 4. Initialize Audio Wav2Vec2 detector
        audio_enabled = os.getenv("ENABLE_AUDIO_DETECTION", "true").strip().lower() in {"1", "true"}
        if audio_enabled:
            self.audio_detector = AudioWav2Vec2Detector(
                model_dir=self.models_dir / "deepfake-audio-wav2vec2"
            )

        self._initialized = True
        logger.info(
            "Model registry ready: %d image detector(s), audio detector: %s",
            len(self.image_detectors),
            "ready" if self.audio_detector else "disabled",
        )

    def healthcheck(self) -> dict[str, Any]:
        return {
            "status": "ready"
            if (len(self.image_detectors) >= 2 and self.audio_detector is not None)
            else "degraded",
            "image_models": [d.healthcheck() for d in self.image_detectors],
            "audio_model": self.audio_detector.healthcheck()
            if self.audio_detector
            else {"ready": False, "details": "Disabled"},
        }


# Singleton registry instance
registry = ModelRegistry()
