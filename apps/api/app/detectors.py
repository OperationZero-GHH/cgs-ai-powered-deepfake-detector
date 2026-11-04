"""Local, hash-verified ONNX and API providers for deepfake and synthetic media screening."""

from __future__ import annotations

import hashlib
import io
import logging
import math
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, Protocol

logger = logging.getLogger(__name__)

MODEL_ID = "Thermostatic/community-forensics-low-quality-detector-2026-08"
MODEL_VERSION = "sha256:88ca8e90e5ab33e6e13887124614e14ba96d7c8cc9ecb21505b63cdc6549ff17"
MODEL_FILE = "community_forensics_low_quality_fp16.onnx"
MODEL_SHA256 = "88ca8e90e5ab33e6e13887124614e14ba96d7c8cc9ecb21505b63cdc6549ff17"
MODEL_BYTES = 43_778_110
MODEL_THRESHOLD = 0.65
CALIBRATION_A = 0.6352260751077209
CALIBRATION_B = -0.2643220522904507

DetectorStatus = Literal["completed", "not_configured", "failed"]


def compute_spectral_drift(image_bytes: bytes) -> dict[str, float]:
    """Compute 2D FFT magnitude spectrum to identify high-frequency upsampling artifacts."""
    try:
        import numpy as np
        from PIL import Image, ImageOps

        with Image.open(io.BytesIO(image_bytes)) as raw:
            gray = ImageOps.exif_transpose(raw).convert("L")
        gray = gray.resize((256, 256), Image.Resampling.BILINEAR)
        arr = np.asarray(gray, dtype=np.float32)

        # 2D Fast Fourier Transform
        f = np.fft.fft2(arr)
        fshift = np.fft.fftshift(f)
        magnitude = 20 * np.log(np.abs(fshift) + 1e-6)

        # High frequency radial mask
        y, x = np.ogrid[:256, :256]
        r = np.sqrt((x - 128) ** 2 + (y - 128) ** 2)
        high_freq_mask = (r > 64) & (r <= 128)
        low_freq_mask = r <= 64

        high_power = float(np.mean(magnitude[high_freq_mask]))
        low_power = float(np.mean(magnitude[low_freq_mask]))
        ratio = high_power / (low_power + 1e-6)

        return {
            "high_freq_power_db": round(high_power, 2),
            "low_freq_power_db": round(low_power, 2),
            "spectral_drift_ratio": round(ratio, 4),
            "frequency_dispersion": round(float(np.std(magnitude)), 2),
        }
    except Exception as exc:
        logger.debug("Spectral frequency drift computation skipped: %s", exc)
        return {
            "high_freq_power_db": 0.0,
            "low_freq_power_db": 0.0,
            "spectral_drift_ratio": 1.0,
            "frequency_dispersion": 0.0,
        }


@dataclass(frozen=True)
class SyntheticDetection:
    status: DetectorStatus
    provider: str | None = None
    model_id: str | None = None
    model_version: str | None = None
    label: str | None = None
    score: float | None = None
    score_semantics: str | None = None
    calibrated_probability: float | None = None
    threshold: float | None = None
    threshold_policy_version: str | None = None
    latency_ms: int | None = None
    limitations: tuple[str, ...] = ()
    spectral_forensics: dict[str, float] | None = None


class SyntheticImageDetector(Protocol):
    name: str
    model_version: str

    def analyze(self, image_bytes: bytes) -> SyntheticDetection: ...
    def healthcheck(self) -> dict[str, object]: ...


class UnconfiguredSyntheticDetector:
    name = "unconfigured"
    model_version = "none"

    def __init__(self, reason: str = "No local synthetic-image detector is configured."):
        self.reason = reason

    def analyze(self, image_bytes: bytes) -> SyntheticDetection:
        del image_bytes
        return SyntheticDetection(status="not_configured", limitations=(self.reason,))

    def healthcheck(self) -> dict[str, object]:
        return {
            "status": "not_configured",
            "model_id": None,
            "model_version": None,
            "details": self.reason,
        }


class OnnxSyntheticImageDetector:
    """Inference-only ONNX adapter. Runs on verified FP16 ONNX weights with spectral analytics."""

    name = MODEL_ID
    model_version = MODEL_VERSION
    limitations = (
        (
            "Whole-image AI-generation screening only; inspects frequency-domain drift and "
            "neural artifact residuals."
        ),
        (
            "The score is calibrated on a class-balanced development set, not a population "
            "prevalence guarantee."
        ),
        (
            "Performance falls on extreme multi-hop compression, tiny synthetic composites, "
            "screenshots, and unseen generators."
        ),
        (
            "The published evaluation reports development/calibration results; its locked "
            "competition test was not opened."
        ),
    )

    def __init__(self, model_path: Path):
        self.model_path = model_path
        self._session = None
        self._input_name: str | None = None

    def _load(self):
        if self._session is not None:
            return self._session
        if not self.model_path.is_file():
            raise FileNotFoundError("The verified ONNX model file is not present.")
        digest = hashlib.sha256()
        with self.model_path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != MODEL_SHA256 or self.model_path.stat().st_size != MODEL_BYTES:
            raise ValueError("The local ONNX model did not match its published SHA-256 and size.")
        try:
            import onnxruntime as ort
        except ImportError as exc:
            raise RuntimeError("Install the API requirements to enable ONNX Runtime.") from exc
        options = ort.SessionOptions()
        options.intra_op_num_threads = max(1, int(os.getenv("INFERENCE_CPU_THREADS", "2")))
        options.inter_op_num_threads = 1
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        options.enable_cpu_mem_arena = True
        self._session = ort.InferenceSession(
            str(self.model_path), sess_options=options, providers=["CPUExecutionProvider"]
        )
        inputs = self._session.get_inputs()
        if len(inputs) != 1:
            self._session = None
            raise ValueError("The model has an unexpected input signature.")
        self._input_name = inputs[0].name
        return self._session

    def healthcheck(self) -> dict[str, object]:
        if not self.model_path.is_file():
            return {
                "status": "not_configured",
                "model_id": self.name,
                "model_version": self.model_version,
                "details": (
                    "Model weights are missing; start the launcher while connected "
                    "to download them."
                ),
            }
        try:
            self._load()
        except Exception as exc:
            logger.warning("Detector health check failed: %s", type(exc).__name__)
            return {
                "status": "unavailable",
                "model_id": self.name,
                "model_version": self.model_version,
                "details": "The local model could not be loaded or verified.",
            }
        return {
            "status": "ready",
            "model_id": self.name,
            "model_version": self.model_version,
            "details": "Verified local ONNX model; CPU inference enabled.",
        }

    @staticmethod
    def _input_tensor(image_bytes: bytes):
        import numpy as np
        from PIL import Image, ImageOps

        with Image.open(io.BytesIO(image_bytes)) as raw:
            image = ImageOps.exif_transpose(raw).convert("RGB")
        width, height = image.size
        short_edge = 440
        scale = short_edge / min(width, height)
        resized = (round(width * scale), round(height * scale))
        image = image.resize(resized, Image.Resampling.BILINEAR)
        left = (image.width - 384) // 2
        top = (image.height - 384) // 2
        image = image.crop((left, top, left + 384, top + 384))
        pixels = np.asarray(image, dtype=np.float32) / 255.0
        mean = np.asarray((0.485, 0.456, 0.406), dtype=np.float32)
        std = np.asarray((0.229, 0.224, 0.225), dtype=np.float32)
        return np.transpose((pixels - mean) / std, (2, 0, 1))[None, ...].astype(
            np.float32, copy=False
        )

    def analyze(self, image_bytes: bytes) -> SyntheticDetection:
        started = time.perf_counter()
        try:
            session = self._load()
            tensor = self._input_tensor(image_bytes)
            output = session.run(None, {self._input_name: tensor})
            if not output or getattr(output[0], "size", 0) != 1:
                raise ValueError("The model returned an unexpected output signature.")
            raw_logit = float(output[0].reshape(-1)[0])
            calibrated_score = 1.0 / (
                1.0 + math.exp(-max(-80.0, min(80.0, CALIBRATION_A * raw_logit + CALIBRATION_B)))
            )
            label = (
                "ai_generated_signal"
                if calibrated_score >= MODEL_THRESHOLD
                else "no_strong_ai_signal"
            )
            spectral = compute_spectral_drift(image_bytes)
            return SyntheticDetection(
                status="completed",
                provider="local_onnx",
                model_id=self.name,
                model_version=self.model_version,
                label=label,
                score=round(calibrated_score, 6),
                score_semantics=(
                    "Calibrated screening score on a 0–1 scale; not a population probability."
                ),
                threshold=MODEL_THRESHOLD,
                threshold_policy_version="community-forensics-low-quality-2026-08-threshold-0.65",
                latency_ms=round((time.perf_counter() - started) * 1000),
                limitations=self.limitations,
                spectral_forensics=spectral,
            )
        except Exception as exc:
            logger.warning("Synthetic detector inference failed: %s", type(exc).__name__)
            return SyntheticDetection(
                status="not_configured" if isinstance(exc, FileNotFoundError) else "failed",
                provider="local_onnx",
                model_id=self.name,
                model_version=self.model_version,
                latency_ms=round((time.perf_counter() - started) * 1000),
                limitations=(
                    "The local model could not complete inference; no prediction was produced.",
                ),
            )


class ApiSyntheticImageDetector:
    "REST API deepfake detector adapter. Calls external model API endpoints with graceful fallback."

    name = "external_deepfake_api"
    model_version = "api-v1"

    def __init__(
        self,
        api_url: str,
        api_key: str | None = None,
        fallback_detector: SyntheticImageDetector | None = None,
    ):
        self.api_url = api_url
        self.api_key = api_key
        self.fallback = fallback_detector

    def healthcheck(self) -> dict[str, object]:
        return {
            "status": "ready",
            "model_id": self.name,
            "model_version": self.model_version,
            "details": f"External API deepfake provider configured ({self.api_url}) with fallback.",
        }

    def analyze(self, image_bytes: bytes) -> SyntheticDetection:
        import httpx

        started = time.perf_counter()
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            with httpx.Client(timeout=8.0) as client:
                files = {"file": ("image.jpg", image_bytes, "image/jpeg")}
                response = client.post(self.api_url, headers=headers, files=files)
                if response.status_code == 200:
                    data = response.json()
                    score = float(data.get("score", data.get("deepfake_probability", 0.5)))
                    label = "ai_generated_signal" if score >= 0.65 else "no_strong_ai_signal"
                    return SyntheticDetection(
                        status="completed",
                        provider="external_api",
                        model_id=self.name,
                        model_version=self.model_version,
                        label=label,
                        score=round(score, 6),
                        score_semantics="External deepfake detection API response.",
                        threshold=0.65,
                        latency_ms=round((time.perf_counter() - started) * 1000),
                        spectral_forensics=compute_spectral_drift(image_bytes),
                    )
        except Exception as exc:
            logger.warning(
                "External deepfake API call failed (%s); falling back to local detector", exc
            )

        if self.fallback:
            return self.fallback.analyze(image_bytes)

        return SyntheticDetection(
            status="failed",
            provider="external_api",
            limitations=("The external API endpoint did not respond.",),
        )


class TestOnlyDetector:
    """Deterministic E2E provider. Configuration rejects it outside test modes."""

    name = "test_only"
    model_version = "e2e-fixture-v1"

    def analyze(self, image_bytes: bytes) -> SyntheticDetection:
        del image_bytes
        return SyntheticDetection(
            status="completed",
            provider="test_only",
            model_id="test-only-fixture",
            model_version=self.model_version,
            label="no_strong_ai_signal",
            score=0.31,
            score_semantics=(
                "Deterministic automated-test fixture; never a production detector result."
            ),
            limitations=("Automated-test fixture only; not valid for real image analysis.",),
            spectral_forensics={
                "high_freq_power_db": 12.4,
                "low_freq_power_db": 34.2,
                "spectral_drift_ratio": 0.362,
                "frequency_dispersion": 8.1,
            },
        )

    def healthcheck(self) -> dict[str, object]:
        return {
            "status": "test_only",
            "model_id": "test-only-fixture",
            "model_version": self.model_version,
            "details": "E2E-only deterministic fixture.",
        }


def create_detector(provider: str, model_path: Path, app_env: str) -> SyntheticImageDetector:
    local_onnx = OnnxSyntheticImageDetector(model_path)
    if provider == "disabled":
        return UnconfiguredSyntheticDetector(
            "Synthetic-image screening is disabled by configuration."
        )
    if provider == "local":
        return local_onnx
    if provider in {"api", "external"}:
        api_url = os.getenv(
            "AI_DETECTOR_API_URL", "https://api.deepfake-detector.internal/v1/detect"
        )
        api_key = os.getenv("AI_DETECTOR_API_KEY", "")
        return ApiSyntheticImageDetector(api_url, api_key, fallback_detector=local_onnx)
    if provider == "test" and app_env in {"test", "e2e"}:
        return TestOnlyDetector()
    if provider == "test":
        raise ValueError("The test-only detector is restricted to APP_ENV=test or e2e.")
    return local_onnx


def detection_to_dict(result: SyntheticDetection) -> dict[str, object]:
    return asdict(result)
