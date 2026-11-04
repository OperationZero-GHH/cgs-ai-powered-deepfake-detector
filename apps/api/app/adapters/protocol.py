"""Shared protocols and data structures for deepfake detection models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from PIL import Image


@dataclass(frozen=True)
class DetectorOutput:
    name: str
    version: str
    p_fake: float
    raw_logits: list[float] | None = None
    label_map_used: dict[str, str] | None = None
    latency_ms: int = 0
    ok: bool = True
    error: str | None = None
    details: dict[str, object] = field(default_factory=dict)


@runtime_checkable
class ImageDetector(Protocol):
    name: str
    version: str

    def predict(self, img: Image.Image) -> DetectorOutput:
        """Run deepfake prediction on a sanitized, RGB PIL Image."""
        ...

    def healthcheck(self) -> dict[str, object]:
        """Verify model weights and operational readiness."""
        ...


@runtime_checkable
class AudioDetector(Protocol):
    name: str
    version: str

    def predict_audio(self, wav_bytes: bytes, sample_rate: int = 16000) -> DetectorOutput:
        """Run audio deepfake prediction on mono 16 kHz PCM WAV bytes."""
        ...

    def healthcheck(self) -> dict[str, object]:
        """Verify model weights and operational readiness."""
        ...
