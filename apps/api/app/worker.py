"""Durable, database-backed analysis worker with leases and bounded retries."""

from __future__ import annotations

import argparse
import json
import logging
import os
import socket
import time
import uuid
from datetime import timedelta
from pathlib import Path

from sqlalchemy import and_, or_, select, update

from app import main
from app.detectors import detection_to_dict
from app.scanner import scan_content_credentials
from app.temporal_detector import create_temporal_detector

logger = logging.getLogger("cgs.worker")
MAX_ATTEMPTS = max(1, int(os.getenv("INFERENCE_MAX_ATTEMPTS", "3")))
LEASE_SECONDS = max(60, int(os.getenv("INFERENCE_LEASE_SECONDS", "1800")))
WORKER_ID = f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:8]}"

# ── Layer 2 Temporal Detector Singleton ──
_temporal_detector = None

def _get_temporal_detector():
    """Lazy-load the Layer 2 temporal deepfake detector."""
    global _temporal_detector
    if _temporal_detector is None:
        hf_token = os.getenv("HF_TOKEN", "")
        _temporal_detector = create_temporal_detector(hf_token=hf_token)
    return _temporal_detector


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
                    and_(main.InferenceJob.status == "queued", main.InferenceJob.available_at <= now),
                    and_(main.InferenceJob.status == "processing", main.InferenceJob.locked_until <= now),
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
                    and_(main.InferenceJob.status == "queued", main.InferenceJob.available_at <= now),
                    and_(main.InferenceJob.status == "processing", main.InferenceJob.locked_until <= now),
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
            db.execute(update(main.InferenceJob).where(main.InferenceJob.id == candidate.id).values(status="failed", last_error="analysis_missing", locked_until=None))
            db.commit()
            return None
        analysis.status = "processing"
        db.commit()
        return candidate.id, candidate.analysis_id
    finally:
        db.close()


def _finish(job_id: str, analysis_id: str, worker_id: str, detector_result: dict, provenance: dict) -> None:
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
    """Delete terminal reports and their private files after the configured retention period."""
    if main.UPLOAD_RETENTION_DAYS <= 0:
        return 0
    db = main.SessionLocal()
    removed_keys: list[str] = []
    try:
        main.set_worker_rls_principal(db)
        cutoff = main.utcnow() - timedelta(days=main.UPLOAD_RETENTION_DAYS)
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
            logger.warning("Unable to remove expired private media object (%s)", type(key).__name__)
    if rows:
        logger.info("Removed %s expired analysis report(s)", len(rows))
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
    """Process one available durable job with prioritized triage funnel:
    1. Instant SHA-256 digest lookup for past completed analyses.
    2. C2PA / EXIF provenance verification: hardware-signed camera certificates bypass CPU neural layer.
    3. Heavy neural & spectral analysis: streaming temporal keyframe extraction for video, isolated image inference.
    """
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

            # ── TRIAGE FUNNEL TIER 1: Instant SHA-256 Digest Cache Lookup ──
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
                    logger.info("Triage hit: SHA-256 cache match found for %s (digest=%s…)", analysis_id, sha256_digest[:12])
                    cached_detection["cached_from_digest"] = True
                    # Older cached reports could contain brand-name guesses as
                    # hardware authentication. Preserve C2PA status, but never
                    # reuse that deprecated assertion as proof of capture.
                    cached_provenance["is_hardware_authenticated"] = False
                    cached_provenance["hardware_signer"] = None
                    _finish(job_id, analysis_id, worker_id, cached_detection, cached_provenance)
                    return True
                logger.info("Skipping deprecated C2PA-derived cache result for %s.", analysis_id)
        finally:
            db.close()

        # C2PA provenance is reported independently; it does not replace the
        # model's screening result or prove that an asset is authentic.
        provenance = scan_content_credentials(original_path)
        # ── Neural & Spectral Deepfake Screening ──
        if mime_type.startswith("video/"):
            from app.video import analyze_video
            # Dual-layer streaming analysis: Layer 1 ONNX spatial + Layer 2 temporal LSTM
            temporal = _get_temporal_detector()
            detection = analyze_video(original_path, main.synthetic_detector, temporal_detector=temporal)
        else:
            image_bytes = original_path.read_bytes()
            detection = detection_to_dict(main.synthetic_detector.analyze(image_bytes))

        _finish(job_id, analysis_id, worker_id, detection, provenance)
        return True
    except Exception as exc:
        logger.warning("Analysis job failed (analysis_id=%s, kind=%s)", analysis_id, type(exc).__name__)
        _retry_or_fail(job_id, analysis_id, worker_id, type(exc).__name__)
        return True


def run_forever(poll_seconds: float = 1.0, worker_id: str = WORKER_ID) -> None:
    logger.info("Analysis worker started (worker_id=%s)", worker_id)
    detector_health = main.synthetic_detector.healthcheck()
    logger.info("Detector status: %s", detector_health.get("status"))
    last_cleanup = 0.0
    while True:
        try:
            _heartbeat(worker_id)
            if time.monotonic() - last_cleanup >= 3600:
                cleanup_expired_uploads()
                last_cleanup = time.monotonic()
            processed = process_one(worker_id)
        except Exception as exc:
            logger.warning("Worker loop encountered a service error: %s", type(exc).__name__)
            processed = False
        if not processed:
            time.sleep(max(0.2, poll_seconds))


def main_cli() -> None:
    parser = argparse.ArgumentParser(description="CGS DeepFake Shield durable inference worker")
    parser.add_argument("--poll-seconds", type=float, default=float(os.getenv("WORKER_POLL_SECONDS", "1")))
    args = parser.parse_args()
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s %(message)s")
    run_forever(args.poll_seconds)


if __name__ == "__main__":
    main_cli()
