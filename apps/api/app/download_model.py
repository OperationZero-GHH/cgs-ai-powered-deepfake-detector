"""Download pinned Hugging Face models and verify exact cryptographic hashes.

Verifies model files against models.lock.json.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv
from huggingface_hub import hf_hub_download

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("cgs.download_model")

REPO_ROOT = Path(__file__).resolve().parents[3]
LOCKFILE_PATH = REPO_ROOT / "models.lock.json"
MODELS_DIR = REPO_ROOT / "models"


def compute_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def download_and_verify_model(model_id: str, spec: dict) -> bool:
    revision = spec.get("revision")
    files = spec.get("files", {})
    sub_folder_name = model_id.split("/")[-1]
    dest_dir = MODELS_DIR / sub_folder_name
    dest_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=== Processing model %s (commit: %s) ===", model_id, revision[:8])

    for filename, meta in files.items():
        expected_sha = meta.get("sha256")
        expected_size = meta.get("size_bytes")
        target_path = dest_dir / filename

        # Check existing file
        if target_path.is_file():
            actual_size = target_path.stat().st_size
            if actual_size == expected_size:
                actual_sha = compute_sha256(target_path)
                if actual_sha == expected_sha:
                    logger.info("✓ Verified existing file: %s/%s", sub_folder_name, filename)
                    continue
                else:
                    logger.warning("Hash mismatch for %s. Re-downloading...", filename)
            else:
                logger.warning("Size mismatch for %s. Re-downloading...", filename)

        # Download from Hugging Face Hub using pinned revision
        logger.info("Downloading %s/%s at revision %s...", sub_folder_name, filename, revision[:8])
        try:
            downloaded_path = hf_hub_download(
                repo_id=model_id,
                filename=filename,
                revision=revision,
                local_dir=str(dest_dir),
            )
            downloaded = Path(downloaded_path)
            # Verify downloaded file
            actual_size = downloaded.stat().st_size
            if expected_size and actual_size != expected_size:
                downloaded.unlink(missing_ok=True)
                raise ValueError(f"Size mismatch: got {actual_size}, expected {expected_size}")

            actual_sha = compute_sha256(downloaded)
            if expected_sha and actual_sha != expected_sha:
                downloaded.unlink(missing_ok=True)
                raise ValueError(f"SHA-256 mismatch: got {actual_sha}, expected {expected_sha}")

            logger.info("✓ Successfully downloaded and verified %s/%s", sub_folder_name, filename)
        except Exception as exc:
            logger.error("Failed to download or verify %s/%s: %s", sub_folder_name, filename, exc)
            return False

    return True


def download_onnx_model():
    """Download and verify the ONNX legacy model."""
    onnx_path = MODELS_DIR / "community_forensics_low_quality_fp16.onnx"
    expected_sha = "88ca8e90e5ab33e6e13887124614e14ba96d7c8cc9ecb21505b63cdc6549ff17"
    expected_size = 43778110

    if onnx_path.is_file() and onnx_path.stat().st_size == expected_size:
        if compute_sha256(onnx_path) == expected_sha:
            logger.info("✓ Verified ONNX model: %s", onnx_path.name)
            return True

    logger.info("Downloading ONNX model...")
    import urllib.request

    url = (
        "https://huggingface.co/Thermostatic/community-forensics-low-quality-detector-2026-08/"
        "resolve/6fca3e7f4365363ee5c0fdb1a17d73917d54413d/community_forensics_low_quality_fp16.onnx"
    )
    if not url.startswith("https://"):
        raise ValueError("Untrusted URL scheme for model download.")
    temp_path = onnx_path.with_suffix(".download")
    try:
        urllib.request.urlretrieve(url, temp_path)  # nosec B310
        if temp_path.stat().st_size == expected_size and compute_sha256(temp_path) == expected_sha:
            temp_path.replace(onnx_path)
            logger.info("✓ Successfully downloaded and verified ONNX model")
            return True
        temp_path.unlink(missing_ok=True)
        return False
    except Exception as exc:
        temp_path.unlink(missing_ok=True)
        logger.error("Failed to download ONNX model: %s", exc)
        return False


def main() -> int:
    if not LOCKFILE_PATH.is_file():
        logger.error("Lockfile missing at %s", LOCKFILE_PATH)
        return 1

    lock_data = json.loads(LOCKFILE_PATH.read_text(encoding="utf-8"))
    models = lock_data.get("models", {})

    all_ok = True
    for model_id, spec in models.items():
        if spec.get("format") == "onnx":
            continue
        ok = download_and_verify_model(model_id, spec)
        if not ok:
            all_ok = False

    download_onnx_model()

    if all_ok:
        logger.info("All pinned detection models downloaded and verified.")
        return 0
    else:
        logger.warning("One or more models could not be downloaded/verified.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
