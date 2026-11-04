# Architecture decisions

## 2026-10-14 — Next.js + FastAPI monorepo

Keep the existing App Router/TypeScript frontend and FastAPI/Pydantic/SQLAlchemy API. The stack is already implemented and supports local Python inference without replacing the working UI or authentication flow.

## 2026-10-14 — SQLite locally, PostgreSQL in deployment

Use SQLite for a no-Docker local setup and support PostgreSQL through SQLAlchemy/Alembic. Multi-host deployment uses PostgreSQL. The one-command local launcher must not require Docker.

## 2026-10-14 — Select an inference-only model with public caveats

Use `Thermostatic/community-forensics-low-quality-detector-2026-08` for a real local screening path. Its ONNX export avoids loading model-repository Python or pickle checkpoints, and the app pins the artifact by fixed size and SHA-256. The model card is unusually explicit about its development evaluation, calibration data, and failed robustness gates. The app displays those caveats and labels output a calibrated screening score rather than a general-population probability. The model remains independently released, not an official upstream checkpoint, and its evaluation is not reproduced by this project. See `MODEL_CARD.md`.

## 2026-10-14 — Keep the model and provenance tasks separate

The ONNX classifier screens whole images for an AI-generation signal. It does not localize editing or identify face swaps. C2PA validation and metadata are separate report sections. Missing metadata/C2PA data is not interpreted as proof of fakery; lower AI scores are not proof of authenticity.

## 2026-10-14 — Database-backed durable work queue

Store inference jobs in SQL alongside each analysis so both are created in one transaction and recover across process restarts. Use conditional row claims and expiring leases with bounded retries. This supports SQLite and PostgreSQL without a required local Redis/Docker service. Redis/Celery can be considered if workload needs a separate broker, but is not required for this application scale.

## 2026-10-14 — Persistent database rate limits

Use atomic fixed-window upserts in SQLite/PostgreSQL for signup, login, and upload endpoints. HMAC-digest keys before storage. Use direct peer address because forwarding headers are untrusted by default; deployments behind proxies also require edge rate limits.

## 2026-10-14 — Private local storage and browser print reports

Store originals/previews under generated private keys, outside the web root, and authorize each preview request. Use the browser's print-to-PDF flow; a server-generated PDF/export queue is not required for the current request.

## 2026-10-14 — Hidden route with explicit admin authorization

Keep `/admin/login` and `/admin` out of public navigation and mark them noindex. These are discoverability controls only: SSR and every API handler still check the session role. `ADMIN_EMAILS` is required to grant administrator access. No default admin identity/password is shipped.

## 2026-10-14 — E2E-only deterministic detector fixture

Use a deterministic test provider for browser tests so user journeys remain repeatable without relying on model accuracy or network downloads. Reject the provider outside test modes and visibly mark its output test-only. Normal app runs always select the local model or explicit disabled/unavailable status.


## 2026-11-01 — Model Supply-Chain Hardening & Pinning (ADR-001)

Every model is locked to an exact 40-character Git commit hash (`revision="<sha>"`). All model weights, configs, and preprocessors are cryptographically verified using SHA-256 against `models.lock.json` before loading. `trust_remote_code=True` is strictly disallowed across all loaders and workers. Offline execution (`HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`) is enforced in running services.

## 2026-11-01 — Vendored Hybrid Model & Disable-by-Default Policy (ADR-002)

The model `Harshasnade/Deepfake_Detection_System_V1` uses a hybrid architecture (EfficientNetV2-S + Swin-V2-T + FFT magnitude + patch analysis). Because upstream license is unspecified, the architecture is fully vendored and reviewed locally in `app/adapters/harshasnade.py`, and the model is disabled by default behind `ENABLE_HARSHASNADE_MODEL=false`. Only SafeTensors weights are loaded.

## 2026-11-01 — Selection of Audio Deepfake Model (ADR-003)

Evaluated three candidate audio deepfake models. Selected `Vansh180/deepfake-audio-wav2vec2` for its Apache 2.0 license, native SafeTensors format, compatibility with standard Transformers (no remote code), and demonstrated ~92.8% benchmark accuracy on ASVspoof 2021 PA. Input audio is strictly normalized to mono 16 kHz PCM WAV.

## 2026-11-01 — Safe Media Decoding & Process Execution (ADR-004)

All FFmpeg subprocess calls use explicit argument lists with `shell=False`, `-nostdin`, `-protocol_whitelist file,pipe`, and 30-second hard timeouts. Never interpolate user input into CLI strings. Static FFmpeg fallback is provided via `imageio-ffmpeg`. Image decoding enforces `Image.MAX_IMAGE_PIXELS = 40_000_000`, `LOAD_TRUNCATED_IMAGES = False`, and treats decompression warnings as fatal errors.

## 2026-11-01 — Race-Safe Credit Reservation & Auto-Refunds (ADR-005) — SUPERSEDED

~~Re-implemented an atomic database credit reservation pattern. Uploads require an `Idempotency-Key` header to protect against double charges.~~ Credit system removed (see ADR-008). Idempotency-Key header and signed session cookies remain active for deduplication and guest ownership.

## 2026-11-01 — Conservative Multi-Model Ensemble Verdict (ADR-006)

Integrated image models into `app/ensemble.py`. Combines calibrated probabilities with weighted averaging and an agreement standard deviation. Produces three verdict bands: `likely_authentic`, `inconclusive`, and `likely_manipulated`. If models disagree or fewer than two image models are healthy, verdict conservatively defaults to `inconclusive`. UI and API never use absolute terms like "definitely fake" or "100% genuine".

## 2026-11-01 — Ephemeral Private Storage & 1-Hour Auto-Purge (ADR-007)

Stored media is isolated in private directories with UUID names and 0600 permissions. Files are deleted on completion or failure, with an automatic cleanup job purging files exceeding 1 hour.

## 2026-11-01 — Credit System Removal (ADR-008)

Removed the entire credit/wallet system. All users — guests and registered — can now perform unlimited analyses without balance restrictions. The `credits.py` module was deleted, credit ORM models removed from `main.py`, and credit refund logic removed from `worker.py`. Database migration files (e.g. `0010_race_safe_credits.py`) are preserved as historical records but the tables are no longer used. Idempotency keys and signed guest sessions remain for deduplication and ownership tracking.
