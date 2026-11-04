"""Secure media validation, decoding, and conversion pipelines for image, video, and audio."""

from __future__ import annotations

import io
import logging
import os
import shutil
import subprocess  # nosec B404
import warnings
from pathlib import Path

from fastapi import HTTPException
from PIL import Image, ImageOps

logger = logging.getLogger("cgs.media_safety")

# Pillow safety configuration
MAX_IMAGE_PIXELS = max(1, int(os.getenv("MAX_IMAGE_PIXELS", "40000000")))
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
warnings.filterwarnings("error", category=Image.DecompressionBombWarning)

# Allowed formats and magic bytes
IMAGE_MAGIC_MAP = {
    "JPEG": b"\xff\xd8\xff",
    "PNG": b"\x89PNG\r\n\x1a\n",
    "WEBP": b"RIFF",  # with WEBP at byte 8..12
}

AUDIO_MAGIC_EXTS = {
    ".wav": "WAV",
    ".mp3": "MP3",
    ".flac": "FLAC",
    ".ogg": "OGG",
    ".m4a": "M4A",
    ".aac": "AAC",
}

VIDEO_MAGIC_EXTS = {
    ".mp4": "MP4",
    ".webm": "WEBM",
    ".mov": "MOV",
    ".avi": "AVI",
    ".mkv": "MKV",
}


# Resolve safe ffmpeg path
def get_ffmpeg_binary() -> str:
    path = shutil.which("ffmpeg")
    if path:
        return path
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


FFMPEG_EXE = get_ffmpeg_binary()


def check_image_magic_bytes(data: bytes) -> str | None:
    """Validate image magic bytes. Returns 'JPEG', 'PNG', 'WEBP' or None."""
    if len(data) < 16:
        return None
    if data.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "WEBP"
    return None


def check_audio_magic_bytes(data: bytes, suffix: str) -> str | None:
    """Validate audio container magic bytes."""
    if len(data) < 12:
        return None
    # WAV: RIFF....WAVE
    if data.startswith(b"RIFF") and data[8:12] == b"WAVE":
        return "WAV"
    # FLAC: fLaC
    if data.startswith(b"fLaC"):
        return "FLAC"
    # OGG: OggS
    if data.startswith(b"OggS"):
        return "OGG"
    # MP3: ID3 or MPEG sync frames
    if data.startswith(b"ID3") or (len(data) >= 2 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0):
        return "MP3"
    # M4A: ....ftypM4A / ....ftypmp42
    if len(data) >= 8 and data[4:8] == b"ftyp":
        return "M4A"
    return None


def check_video_magic_bytes(data: bytes) -> str | None:
    """Validate video container magic bytes."""
    if len(data) < 12:
        return None
    if data[4:8] in {b"ftyp", b"moov", b"wide", b"mdat"}:
        return "MP4"
    if data.startswith(b"\x1a\x45\xdf\xa3"):
        return "WEBM"
    if data.startswith(b"RIFF") and data[8:12] == b"AVI ":
        return "AVI"
    return None


def validate_and_sanitize_image(data: bytes, max_bytes: int) -> tuple[str, int, int, bytes]:
    """Strictly validate and sanitize an uploaded image.

    Decodes the raw bytes in memory, validates magic bytes, verifies no decompression
    bomb, checks dimensions, applies EXIF orientation, and re-encodes to clean RGB PNG.
    """
    if len(data) > max_bytes:
        limit_mb = max_bytes // (1024 * 1024)
        raise HTTPException(status_code=413, detail=f"The image exceeds the {limit_mb} MB limit.")

    format_detected = check_image_magic_bytes(data)
    if not format_detected:
        raise HTTPException(
            status_code=415,
            detail=(
                "Upload a supported JPEG, PNG, or WebP image. "
                "The file signature was unrecognized."
            ),
        )

    try:
        bio = io.BytesIO(data)
        with Image.open(bio) as raw_img:
            # Reject animated / multi-frame images
            if getattr(raw_img, "is_animated", False) or getattr(raw_img, "n_frames", 1) > 1:
                raise HTTPException(
                    status_code=415, detail="Animated or multi-frame images are not supported."
                )

            raw_img.load()
            w, h = raw_img.size
            if w < 16 or h < 16:
                raise HTTPException(
                    status_code=415, detail="Image dimensions are too small (minimum 16x16 pixels)."
                )
            if w * h > MAX_IMAGE_PIXELS:
                raise HTTPException(
                    status_code=413, detail="Image pixel count exceeds the configured system limit."
                )

            # Apply orientation and normalize to standard RGB
            sanitized = ImageOps.exif_transpose(raw_img).convert("RGB")

            # Re-encode to clean internal format (PNG)
            out_buf = io.BytesIO()
            sanitized.save(out_buf, format="PNG", optimize=True)
            clean_bytes = out_buf.getvalue()
            return format_detected, sanitized.width, sanitized.height, clean_bytes
    except HTTPException:
        raise
    except Image.DecompressionBombError as exc:
        raise HTTPException(
            status_code=413, detail="Image exceeds decompression bomb thresholds."
        ) from exc
    except Exception as exc:
        logger.warning("Image sanitization failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=415, detail="The image could not be safely decoded or verified."
        ) from exc


def convert_audio_to_pcm_wav(input_path: Path, max_duration_seconds: int = 120) -> bytes:
    """Safely decode an audio file into mono 16 kHz 16-bit PCM WAV using sandboxed FFmpeg."""
    cmd = [
        FFMPEG_EXE,
        "-nostdin",
        "-y",
        "-protocol_whitelist",
        "file,pipe",
        "-t",
        str(max_duration_seconds),
        "-i",
        str(input_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "wav",
        "pipe:1",
    ]

    try:
        proc = subprocess.run(  # nosec B603
            cmd,
            shell=False,
            timeout=30,
            capture_output=True,
            check=True,
        )
        return proc.stdout
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="Audio decoding timed out.") from exc
    except subprocess.CalledProcessError as exc:
        err_msg = exc.stderr.decode("utf-8", errors="ignore")[:200]
        logger.warning("FFmpeg audio decode failed: %s", err_msg)
        raise HTTPException(
            status_code=415, detail="The audio stream could not be decoded."
        ) from exc


def extract_audio_from_video(video_path: Path, max_duration_seconds: int = 120) -> bytes | None:
    """Extract audio track from video file. Returns PCM WAV bytes or None if no audio track."""
    cmd = [
        FFMPEG_EXE,
        "-nostdin",
        "-y",
        "-protocol_whitelist",
        "file,pipe",
        "-t",
        str(max_duration_seconds),
        "-i",
        str(video_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "wav",
        "pipe:1",
    ]

    try:
        proc = subprocess.run(  # nosec B603
            cmd,
            shell=False,
            timeout=30,
            capture_output=True,
        )
        if proc.returncode == 0 and len(proc.stdout) > 44:  # WAV header is 44 bytes
            return proc.stdout
        return None
    except Exception as exc:
        logger.debug("No audio track extracted from video (%s)", type(exc).__name__)
        return None


def extract_uniform_video_frames(
    video_path: Path, max_frames: int = 30, fps_target: float = 1.0
) -> list[tuple[int, float, Image.Image]]:
    """Sample uniform frames from video using OpenCV in a sandboxed, memory-bounded loop."""
    import cv2

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return []

    try:
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        if fps <= 0 or fps > 240:
            fps = 30.0

        if total_frames <= 0:
            return []

        # Determine frame interval for target sampling
        interval = max(1, int(round(fps / fps_target)))
        frames: list[tuple[int, float, Image.Image]] = []

        frame_idx = 0
        while cap.isOpened() and len(frames) < max_frames:
            ret, bgr = cap.read()
            if not ret or bgr is None:
                break

            if frame_idx % interval == 0:
                timestamp = round(frame_idx / fps, 2)
                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(rgb)
                frames.append((frame_idx, timestamp, img))

            frame_idx += 1

        return frames
    finally:
        cap.release()
