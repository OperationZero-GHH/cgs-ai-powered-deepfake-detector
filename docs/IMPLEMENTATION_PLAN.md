# Implementation record

Updated 2026-10-14. CGS DeepFake Shield is a local-first image-forensics application built from a Next.js App Router frontend and FastAPI service.

## Current capabilities

- One root PowerShell launcher (`run.ps1`) prepares dependencies, downloads/verifies the pinned ONNX artifact when enabled, applies Alembic migrations, and starts the frontend, API, and worker.
- Account registration/login, Argon2id password hashing, server-side sessions, owner-scoped report history, and account deletion.
- Image validation and private storage, metadata/integrity reporting, a durable database-backed inference queue, and CPU model execution.
- Separate C2PA Content Credentials verification with trust state, plus rate limiting and audited server-authorized administration.
- Hidden admin login/console and Playwright browser journeys for user and administrator workflows.

## Detector scope

The configured local model performs whole-image AI-generation screening only. Its output is a calibrated screening score and threshold signal, not proof or a real-population probability. Face-swap detection, video analysis, and localized manipulation detection are not configured. C2PA and file metadata are separate evidence sources and do not determine whether depicted events are true.

The model artifact is downloaded as ONNX, pinned by revision and SHA-256, and loaded with ONNX Runtime CPU. The app does not execute repository Python code or unpickle checkpoints. Evaluation findings and limits are documented in [MODEL_CARD.md](MODEL_CARD.md).

## Operational boundaries

Local development uses SQLite and local private storage. PostgreSQL and a shared filesystem are supported by the API/worker configuration; the Compose file is a deployment starting point, not a verified production recipe. Production still needs HTTPS, managed secrets, private object storage, backups, alerting, retention/deletion procedures, and review of legal and privacy terms.

The project does not claim a universal deepfake detector, a perfect detector, or model validation by CGS. A missing or failed model produces no score. Every report preserves the model identity and score semantics used for its result.
