"""Comprehensive Load Testing, Crash/Overload Testing, and Dual AI Forensics Models Verification.

Executes:
1. Creation and verified login of multiple user accounts.
2. Thorough verification of Model 1 (Image ONNX detector + FFT spectral drift).
3. Thorough verification of Model 2 (Video temporal continuity detector).
4. High-concurrency Load Testing across verified user sessions.
5. Crash, Overload, Boundary, and Rate-Limit Stress Testing.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import io
import json
import logging
import os
import re
import sys
import tempfile
import time
from pathlib import Path

# Setup paths and environment
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))

os.environ["DATABASE_URL"] = "sqlite:///./data/cgs_shield.db"
os.environ["STORAGE_DIR"] = "./data/storage"
os.environ["COOKIE_SECURE"] = "false"
os.environ["APP_SECRET_KEY"] = "test-secret-key-32-bytes-minimum-length-cgs-2026"
os.environ["RATE_LIMIT_SECRET"] = "test-rate-limit-secret-key-cgs-2026"

import cv2
import numpy as np
from PIL import Image
from starlette.testclient import TestClient

from app import main, worker
from app.detectors import OnnxSyntheticImageDetector, compute_spectral_drift
from app.temporal_detector import TemporalDeepfakeDetector, create_temporal_detector
from app.video import analyze_video, extract_temporal_frames, validate_video

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("load_crash_tester")


def _generate_test_image_bytes(width: int = 512, height: int = 512, pattern: str = "gradient") -> bytes:
    """Generate high-contrast test image bytes."""
    img = Image.new("RGB", (width, height), (30, 40, 50))
    pixels = img.load()
    for x in range(width):
        for y in range(height):
            if pattern == "gradient":
                pixels[x, y] = (x % 256, y % 256, (x + y) % 256)
            elif pattern == "circles":
                dist = int(((x - width // 2) ** 2 + (y - height // 2) ** 2) ** 0.5)
                val = 255 if (dist // 16) % 2 == 0 else 0
                pixels[x, y] = (val, 128, 255 - val)
            else:
                pixels[x, y] = (120, 140, 160)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def _generate_test_video_bytes(num_frames: int = 24, width: int = 128, height: int = 128, fps: float = 12.0) -> bytes:
    """Create a temporary valid MP4 video in memory."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(tmp_path), fourcc, fps, (width, height))
    for i in range(num_frames):
        frame = np.full((height, width, 3), (i * 10) % 255, dtype=np.uint8)
        cv2.circle(frame, (width // 2, height // 2), 20 + (i % 10), (0, 255, 200), -1)
        out.write(frame)
    out.release()

    data = tmp_path.read_bytes()
    tmp_path.unlink(missing_ok=True)
    return data


def setup_users(client: TestClient, count: int = 5) -> list[dict]:
    """Create and verify multiple test users."""
    users = []
    logger.info("--- PHASE 1: CREATING & VERIFYING %d USER ACCOUNTS ---", count)
    for i in range(1, count + 1):
        email = f"forensic_user_{i}_{int(time.time())}@shield-test.internal"
        password = f"StrongP@ssw0rd!{i}X"
        name = f"Forensic Analyst {i}"

        username = f"user_{i}_{int(time.time())}"[:30]
        # 1. Signup
        signup_res = client.post(
            "/api/v1/auth/signup",
            json={
                "email": email,
                "password": password,
                "display_name": name,
                "username": username,
                "phone_number": f"+1202555010{i}",
            },
        )
        assert signup_res.status_code == 201, f"Signup failed for {email}: {signup_res.text}"

        # 2. Extract verification token from DB
        with main.SessionLocal() as db:
            db_user = db.scalar(main.select(main.User).where(main.User.email == email))
            assert db_user is not None
            # Extract token from verification record or verify directly
            db_user.email_verified_at = main.utcnow()
            db_user.email_verification_token_hash = None
            db.commit()

        # 3. Login
        login_res = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert login_res.status_code == 200, f"Login failed for {email}: {login_res.text}"

        cookie = login_res.cookies.get(main.COOKIE_NAME)
        assert cookie, f"No session cookie returned for {email}"

        # 4. Verify account status
        auth_client = TestClient(main.app)
        auth_client.cookies.set(main.COOKIE_NAME, cookie)
        status = auth_client.get("/api/v1/account/status").json()
        assert status["is_authenticated"] is True, f"User {email} not authenticated in status"
        assert status["can_analyze"] is True, f"User {email} cannot analyze"
        assert status["email_verified"] is True, f"User {email} not email verified"

        users.append({
            "email": email,
            "password": password,
            "name": name,
            "cookie": cookie,
            "client": auth_client,
        })
        logger.info("✓ User %d (%s) created, verified, and logged in.", i, email)

    return users


def test_ai_forensics_models(users: list[dict]):
    """Verify both AI forensics models (Spatial ONNX + FFT Spectral, and Temporal Video)."""
    logger.info("--- PHASE 2: VERIFYING BOTH AI FORENSICS MODELS ---")
    active_user = users[0]["client"]

    # --- MODEL 1: IMAGE ONNX FORENSICS + SPECTRAL DRIFT ---
    logger.info("[Model 1] Testing Spatial ONNX detector and FFT Spectral Analysis...")
    model_path = REPO_ROOT / "models" / "community_forensics_low_quality_fp16.onnx"
    assert model_path.is_file(), f"ONNX model file not found at {model_path}"

    detector = OnnxSyntheticImageDetector(model_path)
    health = detector.healthcheck()
    logger.info("[Model 1] Health check result: %s", health)
    assert health["status"] == "ready", f"Model 1 not ready: {health}"

    test_img_bytes = _generate_test_image_bytes(512, 512, "gradient")
    detection = detector.analyze(test_img_bytes)
    logger.info(
        "[Model 1] Output -> Status: %s, Score: %s, Label: %s, Latency: %d ms",
        detection.status,
        detection.score,
        detection.label,
        detection.latency_ms or 0,
    )
    assert detection.status == "completed"
    assert detection.score is not None and 0.0 <= detection.score <= 1.0
    assert detection.spectral_forensics is not None
    assert "spectral_drift_ratio" in detection.spectral_forensics
    assert "high_freq_power_db" in detection.spectral_forensics
    logger.info("✓ Model 1 (Spatial ONNX + FFT) successfully executed with verified output!")

    # Verify end-to-end through API + worker for Model 1
    logger.info("[Model 1] Testing end-to-end API ingestion and worker inference execution...")
    upload_res = active_user.post(
        "/api/v1/analyses",
        files={"file": ("evidence_sample.png", test_img_bytes, "image/png")},
    )
    assert upload_res.status_code == 201, f"Upload failed: {upload_res.text}"
    analysis_id = upload_res.json()["analysis_id"]

    processed = worker.process_one("worker-test-instance")
    assert processed is True, "Worker did not process inference job"

    report_res = active_user.get(f"/api/v1/analyses/{analysis_id}")
    assert report_res.status_code == 200
    report = report_res.json()
    assert report["status"] == "completed"
    assert report["summary"]["classification"] in {"likely_ai_generated", "inconclusive", "authentic_hardware_provenance"}
    logger.info("✓ Model 1 end-to-end API report verified (Classification: %s)", report["summary"]["classification"])

    # --- MODEL 2: VIDEO TEMPORAL DEEPFAKE DETECTOR ---
    logger.info("[Model 2] Testing Video Temporal Deepfake Forensics Pipeline...")
    video_bytes = _generate_test_video_bytes(num_frames=20, width=128, height=128)

    # 1. Validation & Technical Specs
    fmt, w, h, technical, preview = validate_video(video_bytes, "deepfake_probe.mp4", max_bytes=50 * 1024 * 1024)
    assert fmt == "MP4"
    assert technical["is_video"] is True
    assert technical["frame_count"] == 20
    assert len(preview) > 0
    logger.info("[Model 2] Video validated: %s, %dx%d, %d frames, preview generated.", fmt, w, h, technical["frame_count"])

    # 2. Temporal Frame Sequence Extraction
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(video_bytes)
        tmp_video_path = Path(tmp.name)

    try:
        frames = list(extract_temporal_frames(tmp_video_path, max_frames=10))
        assert len(frames) == 10
        logger.info("[Model 2] Extracted %d temporal keyframes.", len(frames))

        # 3. Dual-layer video ensemble execution
        temporal_det = create_temporal_detector()
        result = analyze_video(
            tmp_video_path,
            detector=detector,
            temporal_detector=temporal_det,
            max_frames=10,
        )
        assert result["status"] == "completed"
        assert result["media_type"] == "video"
        assert "frame_timeline" in result
        assert len(result["frame_timeline"]) == 10
        assert "layer1_spatial" in result
        assert "layer2_temporal" in result
        logger.info(
            "[Model 2] Video Analysis Result: status=%s, spatial_status=%s, temporal_status=%s, score=%s",
            result["status"],
            result["layer1_spatial"]["status"],
            result["layer2_temporal"]["status"],
            result.get("score"),
        )
        logger.info("✓ Model 2 (Video Temporal Continuity) successfully verified!")
    finally:
        tmp_video_path.unlink(missing_ok=True)


def test_load_and_concurrency(users: list[dict], concurrent_requests: int = 30):
    """Run concurrent load testing across multiple authenticated user sessions."""
    logger.info("--- PHASE 3: CONCURRENT LOAD TESTING (%d requests) ---", concurrent_requests)
    test_img = _generate_test_image_bytes(256, 256, "circles")

    def run_user_task(idx: int) -> dict:
        user = users[idx % len(users)]
        client = user["client"]
        started = time.perf_counter()
        
        # 1. Fetch status
        s_res = client.get("/api/v1/account/status")
        # 2. Post analysis
        u_res = client.post(
            "/api/v1/analyses",
            files={"file": (f"load_test_{idx}.png", test_img, "image/png")},
            headers={"Idempotency-Key": f"load-test-key-{idx}-{int(time.time())}"},
        )
        # 3. List analyses
        l_res = client.get("/api/v1/analyses?page=1&page_size=5")

        latency = (time.perf_counter() - started) * 1000
        return {
            "idx": idx,
            "status_code_status": s_res.status_code,
            "status_code_upload": u_res.status_code,
            "status_code_list": l_res.status_code,
            "latency_ms": latency,
        }

    start_time = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(run_user_task, i) for i in range(concurrent_requests)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    total_time = time.perf_counter() - start_time

    latencies = [r["latency_ms"] for r in results]
    success_uploads = sum(1 for r in results if r["status_code_upload"] == 201)
    success_status = sum(1 for r in results if r["status_code_status"] == 200)
    success_list = sum(1 for r in results if r["status_code_list"] == 200)

    logger.info("--- LOAD TEST METRICS ---")
    logger.info("Total Requests Executed: %d in %.2f seconds (%.1f req/s)", concurrent_requests, total_time, concurrent_requests / total_time)
    logger.info("Upload Success Rate: %d/%d (%.1f%%)", success_uploads, concurrent_requests, 100 * success_uploads / concurrent_requests)
    logger.info("Status Success Rate: %d/%d (%.1f%%)", success_status, concurrent_requests, 100 * success_status / concurrent_requests)
    logger.info("List Success Rate: %d/%d (%.1f%%)", success_list, concurrent_requests, 100 * success_list / concurrent_requests)
    logger.info("Latency p50: %.1f ms | p95: %.1f ms | max: %.1f ms", float(np.percentile(latencies, 50)), float(np.percentile(latencies, 95)), max(latencies))

    assert success_uploads == concurrent_requests, f"Some uploads failed during load test: {results}"
    assert success_status == concurrent_requests
    assert success_list == concurrent_requests
    logger.info("✓ Concurrency load test passed with 100% success rate!")


def test_crash_overload_and_slowdown(users: list[dict]):
    """Subject system to edge-case corrupt inputs, overload flooding, and rate limits."""
    logger.info("--- PHASE 4: CRASH, OVERLOAD & SLOWDOWN RESISTANCE TESTING ---")
    client = users[0]["client"]

    # 1. Unauthenticated user strict rejection (Req 4)
    logger.info("[Crash Test 1] Testing unauthenticated / unregistered user rejection...")
    raw_guest = TestClient(main.app)
    unauth_upload = raw_guest.post(
        "/api/v1/analyses",
        files={"file": ("unauth.png", b"fake-png-bytes", "image/png")},
    )
    assert unauth_upload.status_code == 401, f"Expected 401 for unauth upload, got {unauth_upload.status_code}"
    assert unauth_upload.json()["code"] == "UNAUTHORIZED"
    logger.info("✓ Unauthenticated user strictly blocked from scanning (401 UNAUTHORIZED).")

    # 2. Corrupt / Truncated image binary
    logger.info("[Crash Test 2] Testing malformed/corrupted file resilience...")
    corrupt_res = client.post(
        "/api/v1/analyses",
        files={"file": ("corrupt.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRtruncated", "image/png")},
    )
    assert corrupt_res.status_code == 400
    assert corrupt_res.json()["code"] == "INVALID_FILE"
    logger.info("✓ Corrupt binary rejected safely without crashing (400 INVALID_FILE).")

    # 3. Path Traversal & Unicode Injection
    logger.info("[Crash Test 3] Testing path traversal and malicious filenames...")
    traversal_res = client.post(
        "/api/v1/analyses",
        files={"file": ("../../../../etc/passwd\x00.png", _generate_test_image_bytes(64, 64), "image/png")},
    )
    assert traversal_res.status_code in {201, 400}
    if traversal_res.status_code == 201:
        sanitized = traversal_res.json()["file"]["original_filename"]
        assert ".." not in sanitized and "/" not in sanitized and "\\" not in sanitized
    logger.info("✓ Path traversal filename safely normalized: '%s'", sanitized if traversal_res.status_code == 201 else "Rejected")

    # 4. Decompression Bomb Protection
    logger.info("[Crash Test 4] Testing decompression bomb prevention...")
    huge_pixels_img = Image.new("RGB", (10000, 10000), (255, 255, 255))
    bomb_buf = io.BytesIO()
    huge_pixels_img.save(bomb_buf, format="JPEG", quality=20)
    bomb_bytes = bomb_buf.getvalue()
    bomb_res = client.post(
        "/api/v1/analyses",
        files={"file": ("pixel_bomb.jpg", bomb_bytes, "image/jpeg")},
    )
    assert bomb_res.status_code == 400 or bomb_res.status_code == 413
    logger.info("✓ Extreme pixel dimension attack stopped safely.")

    # 5. Contact Us Form Overload & Rate Limit Protection
    logger.info("[Crash Test 5] Testing Contact Us form and spam flood rate limiter...")
    contact_flood_results = []
    for flood_idx in range(10):
        c_res = raw_guest.post(
            "/api/v1/support/contact",
            json={
                "name": f"Stress Tester {flood_idx}",
                "email": f"stresstester{flood_idx}@test.org",
                "topic": "technical",
                "message": "Testing automated rapid submission overload resistance.",
            },
        )
        contact_flood_results.append(c_res.status_code)

    assert 201 in contact_flood_results, "Valid contact submission should succeed"
    assert 429 in contact_flood_results, "Flood submissions should trigger 429 Rate Limiting"
    logger.info(
        "✓ Contact Us form properly rate-limited under rapid overload (Responses: %s)",
        contact_flood_results,
    )

    # 6. Database Connection Pool and Worker Stress
    logger.info("[Crash Test 6] Testing worker drain and queue recovery...")
    processed_count = 0
    while worker.process_one("stress-worker-instance"):
        processed_count += 1
    logger.info("✓ Worker cleanly processed and drained %d background inference jobs.", processed_count)

    # 7. Final Health check verification
    health = client.get("/health/live").json()
    assert health["status"] == "ok"
    logger.info("✓ Platform healthcheck is OK. System is completely resilient and stable!")


def main_suite():
    logger.info("================================================================================")
    logger.info("  CGS DEEPFAKE SHIELD — COMPLETE LOAD, CRASH & DUAL AI FORENSICS TEST SUITE     ")
    logger.info("================================================================================")

    # Clean test storage directory
    os.makedirs("./data/storage", exist_ok=True)
    os.makedirs("./data", exist_ok=True)
    main.Base.metadata.create_all(main.engine)
    main._send_account_email = lambda address, subject, body: logger.debug("Email dispatched to %s: %s", address, subject)
    main.MAX_ACCOUNTS_PER_IP = 1000
    client = TestClient(main.app)

    # Step 1: Users creation & verified login
    users = setup_users(client, count=4)

    # Step 2: Test both AI forensics models
    test_ai_forensics_models(users)

    # Step 3: Load Testing
    test_load_and_concurrency(users, concurrent_requests=24)

    # Step 4: Crash Testing, Slowdown and Overload Testing
    test_crash_overload_and_slowdown(users)

    logger.info("================================================================================")
    logger.info("  ALL TESTS PASSED WITH 100% SUCCESS — ZERO ISSUES, ZERO ERRORS, ZERO CRASHES!  ")
    logger.info("================================================================================")


if __name__ == "__main__":
    main_suite()
