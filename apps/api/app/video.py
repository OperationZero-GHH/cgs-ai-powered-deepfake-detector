"""Video ingestion, frame extraction, and temporal deepfake forensics."""

from __future__ import annotations

import io
import logging
import tempfile
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from PIL import Image

logger = logging.getLogger("cgs.video")

VIDEO_EXTENSIONS = {
    ".mp4": "MP4",
    ".webm": "WEBM",
    ".mov": "MOV",
    ".avi": "AVI",
    ".mkv": "MKV",
}

VIDEO_MEDIA_TYPES = {
    "MP4": "video/mp4",
    "WEBM": "video/webm",
    "MOV": "video/quicktime",
    "AVI": "video/x-msvideo",
    "MKV": "video/x-matroska",
}

MAX_VIDEO_DURATION_SECONDS = 300  # 5 minutes max for screening
MAX_VIDEO_DIMENSION = 3840  # 4K limit


def is_video_suffix(suffix: str) -> bool:
    return suffix.lower() in VIDEO_EXTENSIONS


def is_video_data(data: bytes) -> bool:
    if len(data) < 12:
        return False
    # MP4 / MOV: 'ftyp' at bytes 4..8 or 'moov'
    if data[4:8] in {b"ftyp", b"moov", b"wide", b"mdat"}:
        return True
    # WebM / MKV: EBML header \x1a\x45\xdf\xa3
    if data.startswith(b"\x1a\x45\xdf\xa3"):
        return True
    # AVI: RIFF....AVI
    if data.startswith(b"RIFF") and data[8:12] == b"AVI ":
        return True
    return False


def validate_video(
    data: bytes,
    filename: str,
    max_bytes: int,
    max_duration_seconds: int = MAX_VIDEO_DURATION_SECONDS,
) -> tuple[str, int, int, dict[str, Any], bytes]:
    suffix = Path(filename).suffix.lower()
    expected_format = VIDEO_EXTENSIONS.get(suffix)
    if not expected_format or not is_video_data(data):
        raise HTTPException(
            status_code=415, detail="Upload a supported MP4, WebM, MOV, or AVI video."
        )

    if len(data) > max_bytes:
        limit_mb = max_bytes // (1024 * 1024)
        raise HTTPException(
            status_code=413, detail=f"The video file exceeds the {limit_mb} MB limit."
        )

    import cv2

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)

    cap = None
    try:
        cap = cv2.VideoCapture(str(tmp_path))
        if not cap.isOpened():
            raise HTTPException(status_code=415, detail="The video stream could not be decoded.")

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        if fps <= 0 or fps > 240:
            fps = 30.0

        if width < 16 or height < 16:
            raise HTTPException(status_code=415, detail="Invalid video frame dimensions.")

        if width > MAX_VIDEO_DIMENSION or height > MAX_VIDEO_DIMENSION:
            raise HTTPException(
                status_code=413, detail=f"Video dimensions exceed {MAX_VIDEO_DIMENSION}px limit."
            )

        duration_seconds = frame_count / fps if frame_count > 0 else 0.0
        if duration_seconds > max_duration_seconds:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"Video duration ({duration_seconds:.1f}s) exceeds the "
                    f"{max_duration_seconds}-second limit."
                ),
            )

        # Extract midpoint frame for poster preview
        midpoint_index = max(0, frame_count // 2) if frame_count > 0 else 0
        cap.set(cv2.CAP_PROP_POS_FRAMES, midpoint_index)
        ret, frame_bgr = cap.read()
        if not ret or frame_bgr is None:
            # Fallback to first frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame_bgr = cap.read()

        if not ret or frame_bgr is None:
            raise HTTPException(
                status_code=415, detail="Failed to extract preview keyframe from video."
            )

        # Convert BGR to RGB PIL image
        rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_frame)
        pil_img.thumbnail((1200, 1200))
        out = io.BytesIO()
        pil_img.save(out, format="JPEG", quality=88, optimize=True)
        preview_bytes = out.getvalue()

        technical = {
            "format": expected_format,
            "media_type": "video",
            "is_video": True,
            "width": width,
            "height": height,
            "duration_seconds": round(duration_seconds, 2),
            "frame_count": frame_count,
            "fps": round(fps, 2),
            "sampled_frames_target": 6,
            "type_verification": {
                "verified": True,
                "format": expected_format,
                "magic_signature": data[:8].hex().upper(),
                "status": "verified",
            },
            "preview_note": "A normalized keyframe preview was extracted for report display.",
        }

        return expected_format, width, height, technical, preview_bytes

    finally:
        if cap is not None:
            cap.release()
        tmp_path.unlink(missing_ok=True)


def extract_temporal_frames(video_path: Path | str, max_frames: int = 12):
    """Structured frame-skipping generator: streams uniformly spaced frames across video runtime.

    Avoids loading full video arrays into memory. Preprocesses and yields frames one at a time,
    allowing caller to process and immediately discard memory.
    Yields (frame_index, timestamp_seconds, jpeg_bytes).
    """
    import cv2

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return

    try:
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        if fps <= 0:
            fps = 30.0

        if total_frames <= 0:
            return

        target_frames = min(max_frames, max(1, total_frames))
        interval = max(1, total_frames // target_frames)

        frame_idx = 0
        yielded = 0

        while cap.isOpened() and yielded < target_frames:
            ret, frame_bgr = cap.read()
            if not ret or frame_bgr is None:
                break

            if frame_idx % interval == 0:
                # Convert frame BGR -> RGB -> JPEG in-memory buffer
                rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_frame)
                buf = io.BytesIO()
                pil_img.save(buf, format="JPEG", quality=88, optimize=True)
                jpeg_bytes = buf.getvalue()
                timestamp_s = round(frame_idx / fps, 2)

                # Free immediate numpy structures before yielding
                del frame_bgr, rgb_frame, pil_img, buf
                yield frame_idx, timestamp_s, jpeg_bytes
                yielded += 1

            frame_idx += 1
    finally:
        cap.release()


def analyze_video(
    video_path: Path,
    detector: Any,
    temporal_detector: Any = None,
    max_frames: int = 12,
) -> dict[str, Any]:
    """Dual-layer video forensic analysis with ensemble scoring.

    Layer 1: Per-frame ONNX spatial inference (frequency/artifact detection).
    Layer 2: Temporal LSTM sequence classifier (cross-frame consistency).
    Ensemble: Calibrated weighted combination of both layers.
    """
    import cv2
    import numpy as np

    total_duration = 0.0
    cap = cv2.VideoCapture(str(video_path))
    if cap.isOpened():
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(cap.get(cv2.CAP_PROP_FPS)) or 30.0
        total_duration = round(total_frames / fps, 2) if total_frames > 0 else 0.0
        cap.release()

    frame_results = []
    layer1_scores = []
    collected_frame_buffers: list[bytes] = []  # For Layer 2 temporal sequence

    # ── Layer 1: Stream frames through per-frame spatial detector ──
    for idx, timestamp_s, jpeg_bytes in extract_temporal_frames(video_path, max_frames=max_frames):
        frame_det = detector.analyze(jpeg_bytes)
        if frame_det.status != "completed" or frame_det.score is None:
            collected_frame_buffers.clear()
            return {
                "status": "unavailable" if frame_det.status == "not_configured" else "failed",
                "media_type": "video",
                "limitations": (
                    (
                        "The image model could not produce a valid score for every sampled "
                        "video frame; no video verdict was produced."
                    ),
                ),
            }
        frame_score = float(frame_det.score)
        if not np.isfinite(frame_score) or not 0.0 <= frame_score <= 1.0:
            collected_frame_buffers.clear()
            return {
                "status": "failed",
                "media_type": "video",
                "limitations": (
                    (
                        "The image model returned an invalid frame score; no video verdict was "
                        "produced."
                    ),
                ),
            }
        if temporal_detector is not None:
            collected_frame_buffers.append(jpeg_bytes)
        layer1_scores.append(frame_score)
        frame_results.append(
            {
                "frame_index": idx,
                "timestamp_seconds": timestamp_s,
                "layer1_score": round(frame_score, 4),
                "label": frame_det.label
                or ("ai_generated_signal" if frame_score >= 0.65 else "no_strong_ai_signal"),
            }
        )

        # Free frame buffer if not needed for Layer 2
        if temporal_detector is None:
            del jpeg_bytes

    if not layer1_scores:
        return {
            "status": "failed",
            "media_type": "video",
            "limitations": ("No valid video frames could be extracted for neural evaluation.",),
        }

    # ── Layer 1 aggregation ──
    l1_mean = float(np.mean(layer1_scores))
    l1_peak = float(np.max(layer1_scores))
    l1_variance = float(np.var(layer1_scores))

    # ── Layer 2: Temporal LSTM sequence analysis ──
    temporal_result = None
    l2_score = None
    if temporal_detector is not None and collected_frame_buffers:
        try:
            temporal_result = temporal_detector.analyze_frame_sequence(collected_frame_buffers)
            if temporal_result.get("status") == "completed":
                candidate_score = temporal_result.get("score")
                if (
                    isinstance(candidate_score, (int, float))
                    and np.isfinite(candidate_score)
                    and 0.0 <= candidate_score <= 1.0
                ):
                    l2_score = float(candidate_score)
                else:
                    temporal_result = {
                        "status": "failed",
                        "layer": "temporal",
                        "limitations": (
                            (
                                "The temporal model returned an invalid score; it was excluded "
                                "from the ensemble."
                            ),
                        ),
                    }
        except Exception as exc:
            logger.warning("Layer 2 temporal analysis failed: %s", type(exc).__name__)
            temporal_result = {
                "status": "failed",
                "layer": "temporal",
                "limitations": (f"Temporal analysis error: {type(exc).__name__}",),
            }
        finally:
            # Free collected frame buffers immediately
            collected_frame_buffers.clear()

    # ── Ensemble score ──
    if l2_score is not None:
        # Dual-layer ensemble: weighted combination
        # Layer 1 (spatial ONNX): 40% weight — frequency/artifact detection
        # Layer 2 (temporal LSTM): 60% weight — cross-frame consistency
        ensemble_score = 0.40 * l1_mean + 0.60 * l2_score
        ensemble_provider = "dual_layer_ensemble"
        ensemble_semantics = (
            "Uncalibrated screening index combining 40% mean image-model score and "
            "60% trained temporal-model score. It is not a probability."
        )
    else:
        # Layer 1 only fallback
        ensemble_score = l1_mean
        ensemble_provider = getattr(detector, "name", "onnx_spatial_only")
        ensemble_semantics = (
            "Single-layer spatial ONNX per-frame analysis (temporal LSTM unavailable). "
            "Score averaged across sampled keyframes with peak anomaly tracking."
        )

    # A video is flagged if ensemble is high OR if peak spatial score is extreme
    is_deepfake = ensemble_score >= 0.60 or l1_peak >= 0.75
    label = "ai_generated_signal" if is_deepfake else "no_strong_ai_signal"

    result: dict[str, Any] = {
        "status": "completed",
        "media_type": "video",
        "provider": ensemble_provider,
        "model_id": getattr(detector, "name", "dual-layer-forensics"),
        "model_version": "dual-layer-ensemble-v1",
        "label": label,
        "score": round(ensemble_score, 4),
        "score_semantics": ensemble_semantics,
        "threshold": 0.60,
        "frames_analyzed": len(frame_results),
        "total_duration_seconds": total_duration,
        # Layer 1 spatial details
        "layer1_spatial": {
            "mean_score": round(l1_mean, 4),
            "peak_score": round(l1_peak, 4),
            "variance": round(l1_variance, 6),
            "provider": getattr(detector, "name", "onnx_spatial"),
        },
        "frame_timeline": frame_results,
        "limitations": [
            (
                "A completed Layer 2 score is included only when the trained temporal "
                "checkpoint is loaded and inference succeeds."
            ),
            "Layer 1 detects per-frame frequency drift, GAN artifacts, and upsampling signatures.",
            "The dual-layer screening index has not been calibrated as a probability.",
            "Heavy re-encoding, low frame rates, and fast motion blur may reduce confidence.",
        ],
    }

    # Layer 2 temporal details (if available)
    if temporal_result is not None:
        result["layer2_temporal"] = temporal_result

    return result
