import tempfile
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image

from app.temporal_detector import HF_CHECKPOINT, TEMPORAL_CACHE_DIR, create_temporal_detector
from app.video import analyze_video, extract_temporal_frames, is_video_suffix, validate_video
from app.detectors import TestOnlyDetector


def _create_synthetic_mp4_bytes(num_frames: int = 15, width: int = 64, height: int = 64, fps: float = 10.0) -> bytes:
    """Create a temporary valid MP4 video in memory."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(tmp_path), fourcc, fps, (width, height))
    for i in range(num_frames):
        # Create subtle synthetic frame variance
        frame = np.full((height, width, 3), (i * 15) % 255, dtype=np.uint8)
        cv2.circle(frame, (width // 2, height // 2), 10, (255, 255, 255), -1)
        out.write(frame)
    out.release()

    video_bytes = tmp_path.read_bytes()
    tmp_path.unlink(missing_ok=True)
    return video_bytes


def test_video_suffix_and_validation():
    assert is_video_suffix(".mp4") is True
    assert is_video_suffix(".webm") is True
    assert is_video_suffix(".mov") is True
    assert is_video_suffix(".png") is False

    video_bytes = _create_synthetic_mp4_bytes(num_frames=10, width=64, height=64)
    fmt, w, h, tech, preview = validate_video(video_bytes, "sample.mp4", max_bytes=50 * 1024 * 1024)
    assert fmt == "MP4"
    assert w == 64
    assert h == 64
    assert tech["is_video"] is True
    assert tech["frame_count"] == 10
    assert len(preview) > 0


def test_video_capture_is_released_when_validation_fails(monkeypatch):
    released = False
    temp_paths = []

    class InvalidCapture:
        def __init__(self, path):
            temp_paths.append(Path(path))

        def isOpened(self):
            return True

        def get(self, prop):
            if prop == cv2.CAP_PROP_FRAME_WIDTH:
                return 0
            if prop == cv2.CAP_PROP_FRAME_HEIGHT:
                return 0
            return 10

        def release(self):
            nonlocal released
            released = True

    monkeypatch.setattr(cv2, "VideoCapture", InvalidCapture)
    with pytest.raises(Exception, match="Invalid video frame dimensions"):
        validate_video(b"\x00\x00\x00\x18ftypisom", "invalid.mp4", max_bytes=1024)

    assert released is True
    assert temp_paths and not temp_paths[0].exists()


def test_streaming_temporal_frame_extraction():
    video_bytes = _create_synthetic_mp4_bytes(num_frames=20, width=64, height=64)
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(video_bytes)
        tmp_path = Path(tmp.name)

    try:
        frames = list(extract_temporal_frames(tmp_path, max_frames=5))
        assert len(frames) == 5
        for idx, ts, jpeg_bytes in frames:
            assert isinstance(idx, int)
            assert isinstance(ts, float)
            assert isinstance(jpeg_bytes, bytes)
            assert len(jpeg_bytes) > 0
    finally:
        tmp_path.unlink(missing_ok=True)


def test_dual_layer_video_analysis():
    video_bytes = _create_synthetic_mp4_bytes(num_frames=12, width=64, height=64)
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(video_bytes)
        tmp_path = Path(tmp.name)

    try:
        spatial_detector = TestOnlyDetector()

        class TrainedTemporalFixture:
            def analyze_frame_sequence(self, _frames):
                return {"status": "completed", "score": 0.72, "temporal_lstm_score": 0.72}

        temporal_detector = TrainedTemporalFixture()

        result = analyze_video(tmp_path, detector=spatial_detector, temporal_detector=temporal_detector, max_frames=6)
        assert result["status"] == "completed"
        assert result["media_type"] == "video"
        assert result["provider"] == "dual_layer_ensemble"
        assert "layer1_spatial" in result
        assert "frame_timeline" in result
        assert len(result["frame_timeline"]) == 6
        assert "layer2_temporal" in result
        assert result["layer2_temporal"]["status"] == "completed"
        assert "temporal_lstm_score" in result["layer2_temporal"]
        assert 0.0 <= result["score"] <= 1.0
        assert result["threshold"] == 0.60
    finally:
        tmp_path.unlink(missing_ok=True)


def test_missing_trained_temporal_checkpoint_does_not_fabricate_a_score(tmp_path, monkeypatch):
    detector = create_temporal_detector(cache_dir=tmp_path)
    monkeypatch.setattr(detector, "_download_weights", lambda: None)
    result = detector.analyze_frame_sequence([b"not decoded because weights are absent"])
    assert result["status"] == "unavailable"
    assert "score" not in result


def test_cached_trained_temporal_model_runs_real_sequence_inference():
    if not (TEMPORAL_CACHE_DIR / HF_CHECKPOINT).is_file():
        pytest.skip("The publisher-gated temporal checkpoint is not installed in this environment.")
    detector = create_temporal_detector(cache_dir=TEMPORAL_CACHE_DIR)
    buffer = BytesIO()
    Image.new("RGB", (256, 256), (120, 110, 100)).save(buffer, format="JPEG")

    result = detector.analyze_frame_sequence([buffer.getvalue()] * 20)

    assert result["status"] == "completed"
    assert result["model_id"] == "Naman712/Deep-fake-detection"
    assert result["frames_processed"] == 20
    assert 0.0 <= result["score"] <= 1.0
