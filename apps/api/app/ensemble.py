"""Multi-model ensemble aggregator, calibration, and verdict determination."""

from __future__ import annotations

import logging
import math
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np

from app.adapters.protocol import DetectorOutput

logger = logging.getLogger("cgs.ensemble")

DISCLAIMER_TEXT = "Automated probabilistic analysis. Not proof. Results can be wrong."

# Calibration parameters (Platt scaling: calibrated = 1 / (1 + exp(-(A * p_fake + B))))
# Versioned calibration config: 2026.1
CALIBRATION_PARAMS = {
    "dima806/deepfake_vs_real_image_detection": {"a": 1.15, "b": -0.08, "weight": 0.40},
    "prithivMLmods/Deep-Fake-Detector-v2-Model": {"a": 1.10, "b": -0.05, "weight": 0.40},
    "Harshasnade/Deepfake_Detection_System_V1": {"a": 1.00, "b": 0.00, "weight": 0.20},
    "Thermostatic/community-forensics-low-quality-detector-2026-08": {
        "a": 0.90,
        "b": 0.05,
        "weight": 0.20,
    },
    "Vansh180/deepfake-audio-wav2vec2": {"a": 1.05, "b": -0.02, "weight": 1.00},
}

# Agreement threshold: if standard deviation across healthy image models
# exceeds this, force inconclusive
DISAGREEMENT_STD_THRESHOLD = 0.35


@dataclass
class EnsembleResult:
    job_id: str
    media_type: str  # "image" | "video" | "audio"
    verdict: str  # "likely_authentic" | "inconclusive" | "likely_manipulated"
    confidence_band: str  # "low" | "medium" | "high"
    score: float
    models: list[dict[str, Any]]
    status: str = "completed"
    audio: dict[str, Any] | None = None
    frames_analyzed: int = 0
    warnings: list[str] = field(default_factory=list)
    disclaimer: str = DISCLAIMER_TEXT
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def calibrate_probability(raw_p: float, model_name: str) -> float:
    """Calibrate a raw detector probability using versioned scaling params."""
    params = CALIBRATION_PARAMS.get(model_name, {"a": 1.0, "b": 0.0})
    a, b = params["a"], params["b"]
    # Logit transform then scaled sigmoid
    clamped = max(1e-6, min(1.0 - 1e-6, raw_p))
    logit = math.log(clamped / (1.0 - clamped))
    calibrated_logit = a * logit + b
    # Guard against overflow
    clamped_logit = max(-30.0, min(30.0, calibrated_logit))
    calibrated = 1.0 / (1.0 + math.exp(-clamped_logit))
    return max(0.0, min(1.0, float(calibrated)))


def evaluate_image_ensemble(
    job_id: str,
    detector_outputs: list[DetectorOutput],
    warnings_list: list[str] | None = None,
) -> EnsembleResult:
    """Compute ensemble score, agreement metrics, and verdict for an image."""
    warnings: list[str] = list(warnings_list or [])
    healthy_models = [m for m in detector_outputs if m.ok]
    failed_models = [m for m in detector_outputs if not m.ok]

    model_entries: list[dict[str, Any]] = []
    for m in detector_outputs:
        entry = {
            "name": m.name,
            "version": m.version,
            "p_fake": round(m.p_fake, 4) if m.ok else None,
            "ok": m.ok,
        }
        if not m.ok:
            entry["error"] = m.error
        model_entries.append(entry)

    if failed_models:
        failed_names = ", ".join(m.name.split("/")[-1] for m in failed_models)
        warnings.append(f"Some models were unavailable or failed during screening: {failed_names}.")

    # Graceful degradation rule (Section 6 & Section 13)
    if len(healthy_models) < 2:
        warnings.append(
            "Fewer than two image models were healthy; forcing verdict to inconclusive."
        )
        fallback_score = healthy_models[0].p_fake if healthy_models else 0.5
        return EnsembleResult(
            job_id=job_id,
            media_type="image",
            verdict="inconclusive",
            confidence_band="low",
            score=round(fallback_score, 4),
            models=model_entries,
            audio=None,
            frames_analyzed=0,
            warnings=warnings,
            metadata={"agreement_std": 0.0, "healthy_models_count": len(healthy_models)},
        )

    # 1. Calibrate each healthy model
    calibrated_scores: list[float] = []
    weights: list[float] = []

    for m in healthy_models:
        calibrated = calibrate_probability(m.p_fake, m.name)
        weight = CALIBRATION_PARAMS.get(m.name, {}).get("weight", 0.33)
        calibrated_scores.append(calibrated)
        weights.append(weight)

    # 2. Compute agreement measure (standard deviation)
    std_dev = float(np.std(calibrated_scores)) if len(calibrated_scores) > 1 else 0.0

    # 3. Weighted average
    total_weight = sum(weights) or 1.0
    weighted_score = sum(s * w for s, w in zip(calibrated_scores, weights)) / total_weight
    weighted_score = max(0.0, min(1.0, float(weighted_score)))

    # 4. Agreement check: if models strongly disagree, force inconclusive
    if std_dev > DISAGREEMENT_STD_THRESHOLD:
        warnings.append(
            f"Detectors showed substantial disagreement (variance={std_dev:.2f}); "
            "verdict is marked inconclusive."
        )
        verdict = "inconclusive"
        confidence = "low"
    else:
        # Map to verdict bands
        if weighted_score >= 0.65:
            verdict = "likely_manipulated"
            confidence = "high" if (weighted_score >= 0.80 and std_dev < 0.15) else "medium"
        elif weighted_score <= 0.35:
            verdict = "likely_authentic"
            confidence = "high" if (weighted_score <= 0.20 and std_dev < 0.15) else "medium"
        else:
            verdict = "inconclusive"
            confidence = "medium"

    return EnsembleResult(
        job_id=job_id,
        media_type="image",
        verdict=verdict,
        confidence_band=confidence,
        score=round(weighted_score, 4),
        models=model_entries,
        audio=None,
        frames_analyzed=0,
        warnings=warnings,
        metadata={
            "agreement_std": round(std_dev, 4),
            "calibrated_scores": [round(s, 4) for s in calibrated_scores],
            "healthy_models_count": len(healthy_models),
        },
    )


def evaluate_audio_ensemble(
    job_id: str,
    audio_output: DetectorOutput,
    warnings_list: list[str] | None = None,
) -> EnsembleResult:
    """Compute ensemble score and verdict for a standalone audio file."""
    warnings: list[str] = list(warnings_list or [])
    model_entry = {
        "name": audio_output.name,
        "version": audio_output.version,
        "p_fake": round(audio_output.p_fake, 4) if audio_output.ok else None,
        "ok": audio_output.ok,
    }
    if not audio_output.ok:
        model_entry["error"] = audio_output.error

    audio_details = {
        "analyzed_seconds": audio_output.details.get("duration_seconds", 0),
        "p_fake": round(audio_output.p_fake, 4) if audio_output.ok else None,
        "ok": audio_output.ok,
        "windows_analyzed": audio_output.details.get("windows_analyzed", 0),
    }

    if not audio_output.ok:
        warnings.append(
            f"Audio detector encountered an error: {audio_output.error or 'unavailable'}."
        )
        return EnsembleResult(
            job_id=job_id,
            media_type="audio",
            verdict="inconclusive",
            confidence_band="low",
            score=0.5,
            models=[model_entry],
            audio=audio_details,
            frames_analyzed=0,
            warnings=warnings,
        )

    score = audio_output.p_fake
    if score >= 0.65:
        verdict = "likely_manipulated"
        confidence = "high" if score >= 0.82 else "medium"
    elif score <= 0.35:
        verdict = "likely_authentic"
        confidence = "high" if score <= 0.18 else "medium"
    else:
        verdict = "inconclusive"
        confidence = "medium"

    return EnsembleResult(
        job_id=job_id,
        media_type="audio",
        verdict=verdict,
        confidence_band=confidence,
        score=round(score, 4),
        models=[model_entry],
        audio=audio_details,
        frames_analyzed=0,
        warnings=warnings,
        metadata=audio_output.details,
    )


def evaluate_video_ensemble(
    job_id: str,
    per_frame_ensembles: list[EnsembleResult],
    audio_output: DetectorOutput | None = None,
    temporal_output: dict[str, Any] | None = None,
    warnings_list: list[str] | None = None,
) -> EnsembleResult:
    """Compute aggregate video verdict across sampled keyframes and optional audio track."""
    warnings: list[str] = list(warnings_list or [])

    if not per_frame_ensembles:
        return EnsembleResult(
            job_id=job_id,
            media_type="video",
            verdict="inconclusive",
            confidence_band="low",
            score=0.5,
            models=[],
            audio=None,
            frames_analyzed=0,
            warnings=["No video frames could be extracted for analysis."],
        )

    # Frame-level metrics
    frame_scores = [f.score for f in per_frame_ensembles]
    mean_frame_score = float(np.mean(frame_scores))
    peak_frame_score = float(np.max(frame_scores))
    frame_std = float(np.std(frame_scores))

    # Representative model list from first frame
    rep_models = per_frame_ensembles[0].models

    # Aggregate audio
    audio_info: dict[str, Any] | None = None
    has_audio = audio_output is not None and audio_output.ok
    if has_audio and audio_output is not None:
        audio_info = {
            "analyzed_seconds": audio_output.details.get("duration_seconds", 0),
            "p_fake": round(audio_output.p_fake, 4),
            "ok": True,
        }
    elif audio_output is not None and not audio_output.ok:
        audio_info = {
            "analyzed_seconds": 0,
            "p_fake": None,
            "ok": False,
            "error": audio_output.error,
        }
        warnings.append("Video audio track analysis was skipped or encountered an error.")
    else:
        warnings.append("No audio track detected in video file.")

    # Composite video score:
    # 50% mean frame + 25% peak frame anomaly + 25% audio (if present, else split 65% + 35%)
    if has_audio and audio_output is not None:
        composite_score = (
            0.50 * mean_frame_score + 0.25 * peak_frame_score + 0.25 * audio_output.p_fake
        )
    else:
        composite_score = 0.65 * mean_frame_score + 0.35 * peak_frame_score

    composite_score = max(0.0, min(1.0, float(composite_score)))

    # Frame disagreement / anomaly handling
    if frame_std > 0.35:
        warnings.append(
            "Significant score variance observed across video frames; review frame timeline."
        )

    # Map to verdict
    if composite_score >= 0.60 or peak_frame_score >= 0.80:
        verdict = "likely_manipulated"
        confidence = "high" if composite_score >= 0.75 else "medium"
    elif composite_score <= 0.38 and peak_frame_score <= 0.50:
        verdict = "likely_authentic"
        confidence = "high" if composite_score <= 0.20 else "medium"
    else:
        verdict = "inconclusive"
        confidence = "medium"

    return EnsembleResult(
        job_id=job_id,
        media_type="video",
        verdict=verdict,
        confidence_band=confidence,
        score=round(composite_score, 4),
        models=rep_models,
        audio=audio_info,
        frames_analyzed=len(per_frame_ensembles),
        warnings=warnings,
        metadata={
            "mean_frame_score": round(mean_frame_score, 4),
            "peak_frame_score": round(peak_frame_score, 4),
            "frame_std": round(frame_std, 4),
            "temporal_layer": temporal_output,
        },
    )
