"""Audio deepfake detector based on Vansh180/deepfake-audio-wav2vec2."""

from __future__ import annotations

import io
import logging
import time
import wave
from pathlib import Path

import numpy as np
import torch

from app.adapters.protocol import DetectorOutput

logger = logging.getLogger("cgs.adapters.audio_wav2vec2")

REPO_ID = "Vansh180/deepfake-audio-wav2vec2"
REVISION = "e1197e2063deb056b0a6a348f3913d27de7f3d83"
EXPECTED_SHA256 = "e6bc501e391e78a52f5ce76f34c726c6b30fe225c0d24a37a55daf284b5b70ec"
TARGET_SAMPLE_RATE = 16000
WINDOW_SECONDS = 4.0
STRIDE_SECONDS = 2.0
MIN_AUDIO_SECONDS = 1.0
SILENCE_RMS_THRESHOLD = 0.005  # Normalized amplitude threshold for silence


class AudioWav2Vec2Detector:
    """Audio deepfake detector based on fine-tuned Wav2Vec2."""

    name = REPO_ID
    version = REVISION

    def __init__(self, model_dir: Path | str | None = None, device: str | None = None):
        self.model_dir = Path(model_dir) if model_dir else None
        self.device = torch.device(
            device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        )
        self._model = None
        self._feature_extractor = None
        self._id2label: dict[int, str] = {0: "real", 1: "fake"}
        self._fake_index = 1
        self._available = False
        self._unavailable_reason = "Audio model not initialized"

    def _ensure_loaded(self) -> bool:
        if self._available and self._model is not None:
            return True
        try:
            from transformers import (
                AutoConfig,
                AutoFeatureExtractor,
                AutoModelForAudioClassification,
            )

            source = (
                str(self.model_dir) if (self.model_dir and self.model_dir.is_dir()) else REPO_ID
            )
            config = AutoConfig.from_pretrained(
                source,
                revision=REVISION,
                local_files_only=False if not self.model_dir else True,
                trust_remote_code=False,
            )
            if hasattr(config, "id2label") and config.id2label:
                self._id2label = {int(k): str(v) for k, v in config.id2label.items()}
                for idx, lbl in self._id2label.items():
                    if lbl.lower() in {"fake", "spoof", "synthetic", "ai"}:
                        self._fake_index = idx
                        break

            self._feature_extractor = AutoFeatureExtractor.from_pretrained(
                source,
                revision=REVISION,
                trust_remote_code=False,
            )
            self._model = AutoModelForAudioClassification.from_pretrained(
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
            logger.warning("Failed to load audio model %s: %s", REPO_ID, exc)
            return False

    @staticmethod
    def _read_wav_samples(wav_bytes: bytes) -> tuple[np.ndarray, float]:
        """Read 16-bit mono PCM WAV bytes into a float32 numpy array in [-1.0, 1.0]."""
        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            frames = wf.readframes(n_frames)

        if channels != 1 or sample_width != 2:
            raise ValueError(
                f"Expected mono 16-bit PCM WAV (got channels={channels}, width={sample_width})"
            )

        duration = n_frames / float(framerate)
        samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        return samples, duration

    def predict_audio(
        self, wav_bytes: bytes, sample_rate: int = TARGET_SAMPLE_RATE
    ) -> DetectorOutput:
        start_time = time.perf_counter()
        if not self._ensure_loaded() or self._model is None or self._feature_extractor is None:
            return DetectorOutput(
                name=self.name,
                version=self.version,
                p_fake=0.5,
                ok=False,
                error=self._unavailable_reason,
                latency_ms=round((time.perf_counter() - start_time) * 1000),
            )

        try:
            samples, duration = self._read_wav_samples(wav_bytes)

            # Silence / too short check (Section 5 Rule 4)
            if duration < MIN_AUDIO_SECONDS:
                return DetectorOutput(
                    name=self.name,
                    version=self.version,
                    p_fake=0.5,
                    ok=False,
                    error="insufficient_audio: duration is under 1 second",
                    latency_ms=round((time.perf_counter() - start_time) * 1000),
                    details={
                        "duration_seconds": round(duration, 2),
                        "insufficient_reason": "too_short",
                    },
                )

            # Check RMS energy for near-silence
            rms = float(np.sqrt(np.mean(samples**2)))
            if rms < SILENCE_RMS_THRESHOLD:
                return DetectorOutput(
                    name=self.name,
                    version=self.version,
                    p_fake=0.5,
                    ok=False,
                    error="insufficient_audio: audio is silent or near-silent",
                    latency_ms=round((time.perf_counter() - start_time) * 1000),
                    details={
                        "duration_seconds": round(duration, 2),
                        "rms": round(rms, 6),
                        "insufficient_reason": "silence",
                    },
                )

            # Window the audio (4s windows with 2s stride)
            window_size = int(WINDOW_SECONDS * sample_rate)
            stride = int(STRIDE_SECONDS * sample_rate)
            total_samples = len(samples)

            windows: list[np.ndarray] = []
            if total_samples <= window_size:
                # Pad with zeros to window_size
                padded = np.zeros(window_size, dtype=np.float32)
                padded[:total_samples] = samples
                windows.append(padded)
            else:
                for start_idx in range(0, total_samples - window_size + 1, stride):
                    windows.append(samples[start_idx : start_idx + window_size])
                # Ensure last segment is analyzed
                if (total_samples - window_size) % stride != 0:
                    windows.append(samples[-window_size:])

            # Cap maximum windows analyzed for performance (e.g. 15 windows = ~30s of audio)
            max_windows = 15
            analyzed_windows = windows[:max_windows]

            window_scores: list[float] = []
            with torch.inference_mode():
                for win in analyzed_windows:
                    inputs = self._feature_extractor(
                        win,
                        sampling_rate=sample_rate,
                        return_tensors="pt",
                        padding=True,
                    )
                    input_values = inputs.input_values.to(self.device, dtype=torch.float32)
                    outputs = self._model(input_values)
                    logits = outputs.logits[0].cpu()

                    if torch.isnan(logits).any() or torch.isinf(logits).any():
                        continue

                    probs = torch.softmax(logits, dim=-1)
                    score = float(probs[self._fake_index].item())
                    window_scores.append(score)

            if not window_scores:
                raise ValueError("All audio windows produced invalid model outputs")

            # Aggregate window scores: weighted mean + peak anomaly
            mean_score = float(np.mean(window_scores))
            max_score = float(np.max(window_scores))
            fraction_flagged = float(
                sum(1 for s in window_scores if s >= 0.65) / len(window_scores)
            )

            # Composite p_fake: 60% mean + 30% max + 10% fraction flagged
            composite_p_fake = 0.60 * mean_score + 0.30 * max_score + 0.10 * fraction_flagged
            composite_p_fake = max(0.0, min(1.0, composite_p_fake))

            latency = round((time.perf_counter() - start_time) * 1000)
            return DetectorOutput(
                name=self.name,
                version=self.version,
                p_fake=round(composite_p_fake, 6),
                raw_logits=[round(mean_score, 4), round(max_score, 4)],
                label_map_used={str(k): v for k, v in self._id2label.items()},
                latency_ms=latency,
                ok=True,
                error=None,
                details={
                    "duration_seconds": round(duration, 2),
                    "windows_analyzed": len(window_scores),
                    "mean_window_score": round(mean_score, 6),
                    "peak_window_score": round(max_score, 6),
                    "fraction_flagged": round(fraction_flagged, 4),
                    "per_window_scores": [round(s, 4) for s in window_scores],
                },
            )
        except Exception as exc:
            latency = round((time.perf_counter() - start_time) * 1000)
            logger.warning("Audio prediction error in %s: %s", self.name, exc)
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
