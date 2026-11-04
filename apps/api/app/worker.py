"""Durable, database-backed multi-model analysis worker.

Includes leases, automatic refunds, and retries.
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import os
import socket
import time
import uuid
from datetime import timedelta

from PIL import Image
from sqlalchemy import and_, or_, select, update

from app import main
from app.ensemble import (
    evaluate_audio_ensemble,
    evaluate_image_ensemble,
    evaluate_video_ensemble,
)
from app.media_safety import (
    convert_audio_to_pcm_wav,
    extract_audio_from_video,
    extract_uniform_video_frames,
)
from app.model_loader import registry, verify_models_lockfile
from app.scanner import scan_content_credentials

logger = logging.getLogger("cgs.worker")
MAX_ATTEMPTS = max(1, int(os.getenv("INFERENCE_MAX_ATTEMPTS", "3")))
LEASE_SECONDS = max(60, int(os.getenv("INFERENCE_LEASE_SECONDS", "1800")))
WORKER_ID = f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:8]}"


def _claim(worker_id: str) -> tuple[str, str] | None:
    db = main.SessionLocal()
    try:
        main.set_worker_rls_principal(db)
        now = main.utcnow()
        expired_at_limit = db.scalars(
            select(main.InferenceJob).where(
                main.InferenceJob.status == "processing",
                main.InferenceJob.locked_until <= now,
                main.InferenceJob.attempts >= MAX_ATTEMPTS,
            )
        ).all()
        for job in expired_at_limit:
            job.status = "failed"
            job.last_error = "worker_lease_expired"
            job.locked_until = None
            job.worker_id = None
            job.updated_at = now
            analysis = db.get(main.Analysis, job.analysis_id)
            if analysis:
                analysis.status = "failed"
                analysis.completed_at = now
        if expired_at_limit:
            db.commit()

        candidate = db.scalar(
            select(main.InferenceJob)
            .where(
                main.InferenceJob.attempts < MAX_ATTEMPTS,
                or_(
                    and_(
                        main.InferenceJob.status == "queued", main.InferenceJob.available_at <= now
                    ),
                    and_(
                        main.InferenceJob.status == "processing",
                        main.InferenceJob.locked_until <= now,
                    ),
                ),
            )
            .order_by(main.InferenceJob.created_at.asc())
            .limit(1)
        )
        if not candidate:
            db.commit()
            return None

        changed = db.execute(
            update(main.InferenceJob)
            .where(
                main.InferenceJob.id == candidate.id,
                main.InferenceJob.attempts < MAX_ATTEMPTS,
                or_(
                    and_(
                        main.InferenceJob.status == "queued", main.InferenceJob.available_at <= now
                    ),
                    and_(
                        main.InferenceJob.status == "processing",
                        main.InferenceJob.locked_until <= now,
                    ),
                ),
            )
            .values(
                status="processing",
                attempts=main.InferenceJob.attempts + 1,
                worker_id=worker_id,
                locked_until=now + timedelta(seconds=LEASE_SECONDS),
                updated_at=now,
            )
            .execution_options(synchronize_session=False)
        )
        if changed.rowcount != 1:
            db.rollback()
            return None
        analysis = db.get(main.Analysis, candidate.analysis_id)
        if not analysis:
            db.execute(
                update(main.InferenceJob)
                .where(main.InferenceJob.id == candidate.id)
                .values(status="failed", last_error="analysis_missing", locked_until=None)
            )
            db.commit()
            return None
        analysis.status = "processing"
        db.commit()
        return candidate.id, candidate.analysis_id
    finally:
        db.close()


def _finish(
    job_id: str, analysis_id: str, worker_id: str, detector_result: dict, provenance: dict
) -> None:
    db = main.SessionLocal()
    try:
        main.set_worker_rls_principal(db)
        now = main.utcnow()
        job = db.get(main.InferenceJob, job_id)
        analysis = db.get(main.Analysis, analysis_id)
        if not job or not analysis or job.status != "processing" or job.worker_id != worker_id:
            db.rollback()
            return
        analysis.detector_result_json = json.dumps(detector_result)
        analysis.provenance_json = json.dumps(provenance)
        analysis.status = "completed"
        analysis.completed_at = now
        job.status = "completed"
        job.worker_id = None
        job.locked_until = None
        job.last_error = None
        job.updated_at = now
        db.commit()
    finally:
        db.close()


def _retry_or_fail(job_id: str, analysis_id: str, worker_id: str, error_kind: str) -> None:
    db = main.SessionLocal()
    try:
        main.set_worker_rls_principal(db)
        now = main.utcnow()
        job = db.get(main.InferenceJob, job_id)
        analysis = db.get(main.Analysis, analysis_id)
        if not job or job.status != "processing" or job.worker_id != worker_id:
            db.rollback()
            return
        job.worker_id = None
        job.locked_until = None
        job.last_error = error_kind[:80]
        job.updated_at = now
        if job.attempts < MAX_ATTEMPTS:
            delay_seconds = min(300, 5 * (2 ** (job.attempts - 1)))
            job.status = "queued"
            job.available_at = now + timedelta(seconds=delay_seconds)
            if analysis:
                analysis.status = "queued"
        else:
            job.status = "failed"
            if analysis:
                analysis.status = "failed"
                analysis.completed_at = now
        db.commit()
    finally:
        db.close()


def cleanup_expired_uploads(batch_size: int = 100) -> int:
    """Delete private upload media older than the configured retention window (default 1 hour)."""
    retention_hours = int(os.getenv("UPLOAD_RETENTION_HOURS", "1"))
    db = main.SessionLocal()
    removed_keys: list[str] = []
    try:
        main.set_worker_rls_principal(db)
        cutoff = main.utcnow() - timedelta(hours=retention_hours)
        rows = db.scalars(
            select(main.Analysis)
            .where(
                main.Analysis.created_at < cutoff,
                main.Analysis.status.in_(("completed", "failed")),
            )
            .order_by(main.Analysis.created_at.asc())
            .limit(min(1000, max(1, batch_size)))
        ).all()
        for row in rows:
            removed_keys.extend((row.object_key, row.preview_key))
            db.delete(row)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    for key in removed_keys:
        try:
            main.private_storage_path(key).unlink(missing_ok=True)
        except (OSError, ValueError):
            logger.warning("Unable to remove expired private media object (%s)", key)
    if rows:
        logger.info("Removed %d expired analysis records", len(rows))
    return len(rows)


def _heartbeat(worker_id: str) -> None:
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    values = {"worker_id": worker_id, "last_seen": main.utcnow(), "process_id": str(os.getpid())}
    if main.engine.dialect.name == "sqlite":
        statement = sqlite_insert(main.WorkerHeartbeat).values(**values)
    elif main.engine.dialect.name == "postgresql":
        statement = pg_insert(main.WorkerHeartbeat).values(**values)
    else:
        raise RuntimeError("The analysis worker supports SQLite or PostgreSQL.")
    statement = statement.on_conflict_do_update(
        index_elements=[main.WorkerHeartbeat.worker_id],
        set_={"last_seen": values["last_seen"], "process_id": values["process_id"]},
    )
    with main.engine.begin() as connection:
        connection.execute(statement)


def process_one(worker_id: str = WORKER_ID) -> bool:
    """Process one available durable job using multi-model ensemble pipelines."""
    if not registry._initialized:
        registry.initialize()
    claimed = _claim(worker_id)
    if not claimed:
        return False
    job_id, analysis_id = claimed
    try:
        db = main.SessionLocal()
        try:
            main.set_worker_rls_principal(db)
            analysis = db.get(main.Analysis, analysis_id)
            if not analysis:
                raise FileNotFoundError("Analysis record is missing.")
            original_path = main.private_storage_path(analysis.object_key)
            if not original_path.is_file():
                raise FileNotFoundError("Stored media file is missing.")
            mime_type = analysis.detected_mime_type
            sha256_digest = analysis.sha256

            # Triage: Cache lookup
            cached_match = db.scalar(
                select(main.Analysis)
                .where(
                    main.Analysis.sha256 == sha256_digest,
                    main.Analysis.status == "completed",
                    main.Analysis.id != analysis.id,
                )
                .order_by(main.Analysis.completed_at.desc())
                .limit(1)
            )
            if cached_match and cached_match.detector_result_json and cached_match.provenance_json:
                cached_detection = json.loads(cached_match.detector_result_json)
                cached_provenance = json.loads(cached_match.provenance_json)
                is_legacy_provenance_result = (
                    cached_detection.get("provider") == "c2pa_hardware_cryptographic_trust"
                    or cached_detection.get("label") == "authentic_hardware_provenance"
                )
                if not is_legacy_provenance_result:
                    logger.info("Triage hit: SHA-256 cache match found for %s", analysis_id)
                    cached_detection["cached_from_digest"] = True
                    cached_provenance["is_hardware_authenticated"] = False
                    cached_provenance["hardware_signer"] = None
                    _finish(job_id, analysis_id, worker_id, cached_detection, cached_provenance)
                    return True
                logger.info("Skipping deprecated C2PA-derived cache result for %s.", analysis_id)
        finally:
            db.close()

        # C2PA provenance check
        provenance = scan_content_credentials(original_path)

        # ── Pipeline Branching by Media Type ──
        if mime_type.startswith("audio/"):
            # 1. Standalone Audio Pipeline
            pcm_wav_bytes = convert_audio_to_pcm_wav(original_path)
            if registry.audio_detector:
                audio_out = registry.audio_detector.predict_audio(pcm_wav_bytes)
            else:
                from app.adapters.protocol import DetectorOutput

                audio_out = DetectorOutput(
                    name="Vansh180/deepfake-audio-wav2vec2",
                    version="unloaded",
                    p_fake=0.5,
                    ok=False,
                    error="Audio detector is not configured or offline weights not available.",
                    latency_ms=0.0,
                )
            ensemble_res = evaluate_audio_ensemble(analysis_id, audio_out)
            detection_dict = ensemble_res.to_dict()

        elif mime_type.startswith("video/"):
            # 2. Video Pipeline: Frame Sampling + Audio Track Extraction
            video_frames = extract_uniform_video_frames(
                original_path, max_frames=30, fps_target=1.0
            )
            frame_ensembles = []
            for _f_idx, _f_time, frame_img in video_frames:
                frame_outputs = [
                    detector.predict(frame_img) for detector in registry.image_detectors
                ]
                frame_res = evaluate_image_ensemble(analysis_id, frame_outputs)
                frame_ensembles.append(frame_res)

            # Extract video audio track
            audio_track_wav = extract_audio_from_video(original_path)
            audio_out = None
            if audio_track_wav and registry.audio_detector:
                audio_out = registry.audio_detector.predict_audio(audio_track_wav)

            ensemble_res = evaluate_video_ensemble(
                analysis_id,
                frame_ensembles,
                audio_output=audio_out,
            )
            detection_dict = ensemble_res.to_dict()

        else:
            # 3. Image Pipeline: Multi-Model Image Ensemble
            image_bytes = original_path.read_bytes()
            # Support test monkeypatches and disabled/mock providers on main.synthetic_detector
            if (
                hasattr(main, "synthetic_detector")
                and main.synthetic_detector is not None
                and type(main.synthetic_detector).__name__ != "OnnxSyntheticImageDetector"
            ):
                from app.detectors import detection_to_dict

                detection_dict = detection_to_dict(main.synthetic_detector.analyze(image_bytes))
            else:
                with Image.open(io.BytesIO(image_bytes)) as raw_img:
                    rgb_img = raw_img.convert("RGB")
                    detector_outputs = [
                        detector.predict(rgb_img) for detector in registry.image_detectors
                    ]

                # Also compute spectral forensics for forensics panel
                from app.detectors import compute_spectral_drift

                spectral_data = compute_spectral_drift(image_bytes)

                ensemble_res = evaluate_image_ensemble(analysis_id, detector_outputs)
                detection_dict = ensemble_res.to_dict()
                detection_dict["spectral_forensics"] = spectral_data

        _finish(job_id, analysis_id, worker_id, detection_dict, provenance)
        return True
    except Exception as exc:
        logger.warning(
            "Analysis job failed (analysis_id=%s, kind=%s): %s",
            analysis_id,
            type(exc).__name__,
            exc,
        )
        _retry_or_fail(job_id, analysis_id, worker_id, type(exc).__name__)
        return True


def run_forever(poll_seconds: float = 1.0, worker_id: str = WORKER_ID) -> None:
    logger.info("Initializing CGS DeepFake Shield worker (worker_id=%s)", worker_id)

    # 1. Verify models integrity against models.lock.json on startup (Section 2 Rule 6)
    try:
        verify_models_lockfile()
    except Exception as exc:
        logger.error("Startup integrity check failed: %s", exc)
        raise

    # 2. Initialize warm model registry (Section 3)
    registry.initialize()
    logger.info("Worker models ready: %s", registry.healthcheck()["status"])

    last_cleanup = 0.0
    while True:
        try:
            _heartbeat(worker_id)
            if time.monotonic() - last_cleanup >= 1800:  # Check cleanup every 30m
                cleanup_expired_uploads()
                last_cleanup = time.monotonic()
            processed = process_one(worker_id)
        except Exception as exc:
            logger.warning("Worker loop encountered an error: %s", type(exc).__name__)
            processed = False
        if not processed:
            time.sleep(max(0.2, poll_seconds))


def main_cli() -> None:
    parser = argparse.ArgumentParser(description="CGS DeepFake Shield durable inference worker")
    parser.add_argument(
        "--poll-seconds", type=float, default=float(os.getenv("WORKER_POLL_SECONDS", "1"))
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    run_forever(args.poll_seconds)


if __name__ == "__main__":
    main_cli()
