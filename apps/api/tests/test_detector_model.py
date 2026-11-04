from io import BytesIO
from pathlib import Path

from PIL import Image

from app.detectors import MODEL_FILE, OnnxSyntheticImageDetector


def test_checked_in_image_model_loads_and_runs_real_onnx_inference():
    repo_root = Path(__file__).resolve().parents[3]
    model_path = repo_root / "models" / MODEL_FILE
    if not model_path.exists():
        model_path = Path(__file__).resolve().parents[1] / "models" / MODEL_FILE
    detector = OnnxSyntheticImageDetector(model_path)
    image = Image.new("RGB", (640, 480), color=(92, 135, 184))
    buffer = BytesIO()
    image.save(buffer, format="PNG")

    result = detector.analyze(buffer.getvalue())

    assert detector.healthcheck()["status"] == "ready"
    assert result.status == "completed"
    assert result.provider == "local_onnx"
    assert result.model_id is not None
    assert isinstance(result.score, float)
    assert 0.0 <= result.score <= 1.0
    assert result.latency_ms is not None and result.latency_ms >= 0
