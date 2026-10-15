# Technology Stack

> Repository stack map reviewed on 2026-10-15.

## Runtime

| Technology | Version or range | Purpose |
|---|---|---|
| Python | 3.11+ | FastAPI API, SQLAlchemy models, Alembic migrations, and durable worker |
| FastAPI | `>=0.115,<1` | HTTP API and dependency-based authorization |
| SQLAlchemy | `>=2.0,<3` | ORM and transactional database access |
| SQLite | Python bundled driver | Single-host local development and tests |
| PostgreSQL | supported deployment service | Production database with forced row-level security |
| Next.js | `^16.4.0` | App Router web application and same-origin API proxy |
| React / React DOM | `^19.3.0` | Client and server UI rendering |
| TypeScript | `^6.0.3` | Frontend type checking |
| Node.js | 24 LTS recommended | Next.js development, production build, and browser tests |

## Selected production dependencies

| Package | Constraint | Purpose |
|---|---|---|
| `argon2-cffi` | `>=23,<26` | Argon2id password hashing |
| `pydantic` | `>=2.7,<3` | Request validation and response schemas |
| `email-validator` | `>=2,<3` | Validated email addresses |
| `Pillow` | `>=10,<13` | Bounded still-image decoding, validation, metadata, and preview generation |
| `onnxruntime` | `>=1.20,<2` | Local CPU screening inference |
| `c2pa-python` | `>=0.33,<1` | Content Credentials inspection |
| `torch`, `torchvision` | `>=2.0`, `>=0.15` | Optional temporal video detector runtime |
| `opencv-python-headless` | `>=4.8,<5` | Video decoding and keyframe extraction |
| `Alembic` | `>=1.13,<2` | Versioned schema changes |
| `psycopg[binary]` | `>=3.2,<4` | PostgreSQL driver |

## Development and verification dependencies

| Package | Purpose |
|---|---|
| `pytest` | Backend unit and API tests |
| `httpx` / `httpx2` | FastAPI test clients and HTTP support |
| `eslint` / `typescript-eslint` | Frontend linting |
| `@playwright/test` | Isolated Chromium browser journeys |

## Infrastructure and integrations

| Service or component | Purpose |
|---|---|
| SMTP relay | Deliver one-time email verification and password-reset links |
| Private local storage | Store generated-key originals and report previews; never served as a static directory |
| Database-backed worker | Claim, retry, and complete queued analysis jobs |
| Local model artifact | Checksum-verified ONNX CPU image screening |
| CAI C2PA SDK | Verify credentials and retain compact provenance summaries |
| PowerShell `run.ps1` | Prepare local dependencies, apply migrations, and start API, worker, and web app |

## Configuration

Copy `.env.example` to `.env` for local settings. Deployments must supply independent secrets, PostgreSQL credentials, exact browser origins, secure cookies, SMTP sender/host, and the support address. Account limits, proxy trust, email link lifetimes, upload retention, model configuration, and security rate limits are environment-driven. See the configuration tables in [README](../README.md) and the rollout notes in [Operations](OPERATIONS.md).

## Patterns

- API routes and SQLAlchemy models live in `apps/api/app/main.py`; analysis access has no point balance or usage allowance.
- Alembic revisions are in `apps/api/migrations/versions/`.
- The durable queue worker is `apps/api/app/worker.py`; image/video detector implementations remain separate.
- The web UI uses the Next.js App Router in `apps/web/src/app/`, shared API contracts in `apps/web/src/lib/api.ts`, and account-access state for email verification and IP restrictions.
- Backend HTTP and service tests are in `apps/api/tests/`; browser journeys are in `apps/web/e2e/`.
