"""Fetch the published ONNX model and verify its exact size and SHA-256."""

from __future__ import annotations

import hashlib
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv
from app.detectors import MODEL_BYTES, MODEL_FILE, MODEL_SHA256

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

MODEL_URL = (
    "https://huggingface.co/Thermostatic/community-forensics-low-quality-detector-2026-08/"
    f"resolve/main/{MODEL_FILE}"
)
DESTINATION = Path(os.getenv("AI_MODEL_PATH", "./models/community_forensics_low_quality_fp16.onnx")).resolve()


def main() -> int:
    if DESTINATION.is_file():
        digest = hashlib.sha256(DESTINATION.read_bytes()).hexdigest()
        if DESTINATION.stat().st_size == MODEL_BYTES and digest == MODEL_SHA256:
            print(f"Verified detector model: {DESTINATION}")
            return 0
        print(
            f"A file already exists at {DESTINATION}, but it does not match the pinned detector model. "
            "Move it aside before downloading the expected artifact.",
            file=sys.stderr,
        )
        return 2

    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    temporary = DESTINATION.with_suffix(DESTINATION.suffix + ".download")
    digest = hashlib.sha256()
    byte_count = 0
    request = urllib.request.Request(MODEL_URL, headers={"User-Agent": "CGS-DeepFake-Shield/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response, temporary.open("wb") as output:
            while block := response.read(1024 * 1024):
                byte_count += len(block)
                if byte_count > MODEL_BYTES:
                    raise ValueError("Downloaded model was larger than its published size.")
                digest.update(block)
                output.write(block)
        if byte_count != MODEL_BYTES or digest.hexdigest() != MODEL_SHA256:
            raise ValueError("Downloaded model did not match its published size and SHA-256.")
        temporary.replace(DESTINATION)
        print(f"Downloaded and verified detector model: {DESTINATION}")
        return 0
    except (OSError, urllib.error.URLError, TimeoutError, ValueError) as exc:
        temporary.unlink(missing_ok=True)
        print(f"Detector model download failed ({type(exc).__name__}). The app can start, but AI screening will show unavailable until the model is downloaded.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
