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
