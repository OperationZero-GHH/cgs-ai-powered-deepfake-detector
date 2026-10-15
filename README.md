# CGS DeepFake Shield

**Inspect the image. Examine the evidence.**

CGS DeepFake Shield is an image- and video-forensics workspace with guest and registered access, private reports, local AI screening, a durable analysis worker, metadata inspection, and optional C2PA Content Credentials verification. Its results are evidence signals, not proof of authorship or that depicted events are true.

## Start the complete app

From the project root in PowerShell, run one command:

```powershell
.\run.ps1
```

The launcher prepares Python and web dependencies when they change, applies database migrations, verifies or downloads the pinned 44 MB model, then starts the API, inference worker, and frontend together. Press **Ctrl+C** in that terminal to stop all three. Logs are written under `.run/logs/`.

On first run, `run.ps1` creates `.env` from `.env.example` and generates a 256-bit URL-safe `ADMIN_LOGIN_SLUG` if it is blank. Set `ADMIN_EMAILS` in `.env` to the administrator email address. After the app has started, open another PowerShell window and create the administrator through the local bootstrap command:

```powershell
Set-Location apps/api
.\.venv\Scripts\python.exe -m app.bootstrap_admin admin@example.com
```

The command prompts for the password and only grants administrator access to an allowlisted address. Public signup never grants the admin role. `run.ps1` prints the private administrator sign-in URL when it starts. The page returns not found unless its path matches the high-entropy slug in `.env`; the admin area is excluded from indexing and verifies administrator role on the server and every admin API request. The slug reduces discovery but is not a substitute for authentication or authorization.

For Docker Compose, set `ADMIN_LOGIN_SLUG` in `.env` to at least 32 URL-safe random characters before starting the services.

The first setup requires package/model downloads. If the model download is unavailable, the rest of the app still starts and reports AI screening as unavailable. It never substitutes a fake production score. C2PA validation uses the official Python SDK; if that SDK cannot load in a particular runtime, the report labels provenance verification unavailable.

## What works

- Guest and account analysis without point balances or per-guest analysis quotas. File safeguards and security rate limits remain active.
- Registration, login, email verification, password reset, and account deletion using Gmail-alias-normalized email uniqueness, Argon2id password hashing, opaque HTTP-only sessions, and server-side role checks. Verified email remains an account-security requirement for signed-in analysis.
- Guest report history carries over to a newly registered account. Upload controls reflect email-verification and network-security status; they do not depend on a point balance.
- Hashed-IP account links enforce the configurable account limit. Admins can inspect and unblock access, raise a network limit, whitelist a network, and review unblock requests.
- Secure JPEG, PNG, and WebP validation, decode/pixel limits, SHA-256, dimensions, EXIF field names, and ICC-profile presence.
- Local CPU inference using the checksum-pinned Community Forensics low-quality ONNX detector. Reports show its model ID/version, screening score semantics, threshold, runtime, and limitations.
- A database-backed queue with transactional job creation, worker leases, crash recovery, bounded exponential retries, failed-job state, and admin retry controls. It works with local SQLite and PostgreSQL without requiring Redis or Docker for development.
- C2PA Content Credentials reading and validation through the CAI Python SDK when available. The report distinguishes trusted, valid-but-untrusted, invalid, absent, and unavailable credentials. A valid credential does not establish that an image depicts real events.
- Persistent fixed-window rate limits for account creation, login, uploads, and unblock requests, shared across API processes through the database. The API ignores forwarded addresses unless the direct peer is in `TRUSTED_PROXY_CIDRS`.
- A restricted admin console for actual account counts, detector/worker health, queue inspection, user search, account suspension/reactivation, allowlist-limited role management, retrying jobs, and audit events.
- Playwright browser journeys run against an isolated E2E database and an explicitly test-only detector fixture. That fixture is rejected outside test environments and is never used for ordinary app runs.
- Dark-first and light themes, responsive app pages, print-to-PDF reports, account settings, and owner-scoped report history.

## Detector scope and limitations

The configured model is a whole-image AI-generation screening classifier. It is not a face-swap detector, localized manipulation detector, provenance verifier, or universal deepfake scanner. A lower screening score is not proof that an image is authentic. The report provides an inconclusive overall result when the screening threshold is not crossed.

The selected model is an independently fine-tuned, MIT-licensed ONNX release based on Community Forensics. Its author reports useful development-set results, but also documents weaknesses for severe re-encoding, tiny synthetic composites, screenshots, and untested real-world laundering conditions. Those figures have not been reproduced on this project’s hardware. Read [the model card](docs/MODEL_CARD.md) before relying on its output.

## Test and build

Backend tests:

```powershell
Set-Location apps/api
.\.venv\Scripts\python.exe -m pytest
```

Frontend checks:

```powershell
Set-Location apps/web
npm run lint
npm run typecheck
npm run build
```

Install the matching Chromium binary once, then run browser journeys:

```powershell
npx playwright install chromium
npm run test:e2e
```

Playwright starts the stack with an isolated database and test-only detector, then shuts the services down when the run completes.

## Configuration

Important `.env` settings:

| Variable | Default | Purpose |
|---|---|---|
| `APP_ENV` | `development` | Runtime mode. The test detector only works in `test` and `e2e`. |
| `APP_SECRET_KEY` | example placeholder | Secret HMAC pepper for persistent rate-limit keys. Set a random secret before deployment. |
| `DATABASE_URL` | SQLite in `apps/api/data/` | Use PostgreSQL for a multi-host deployment. |
| `STORAGE_DIR` | `./storage` | Private local originals and normalized previews. |
| `ADMIN_EMAILS` | empty | Comma-separated addresses eligible for the admin role. Do not set a public default. |
| `AI_DETECTOR_PROVIDER` | `local` | `local` runs the checksum-verified ONNX model; `disabled` explicitly disables it. |
| `AI_MODEL_PATH` | `./models/community_forensics_low_quality_fp16.onnx` | Local model path. The launcher downloads the artifact if it is missing. |
| `MAX_UPLOAD_BYTES` | 10 MiB | Request file limit. |
| `MAX_VIDEO_BYTES` | 50 MiB | Video upload cap. |
| `MAX_VIDEO_SECONDS` | `300` | Maximum accepted video duration. |
| `MAX_IMAGE_PIXELS` | 40 million | Decoded-pixel safety limit. |
| `RATE_LIMIT_AUTH_LIMIT` | 12 / 15 minutes | Per-client signup and login request limit. |
| `RATE_LIMIT_AUTH_IDENTITY_LIMIT` | 12 / 15 minutes | Per-email login and per-email/per-username signup limit. |
| `RATE_LIMIT_UPLOAD_LIMIT` | 30 / hour | Fallback for the per-IP analysis rate limit. |
| `RATE_LIMIT_ANALYSIS_OWNER_LIMIT` | 12 / hour | Security rate limit per authenticated user or guest owner. |
| `RATE_LIMIT_ANALYSIS_IP_LIMIT` | 30 / hour | Security rate limit per client IP. |
| `RATE_LIMIT_ANALYSIS_WINDOW_SECONDS` | `3600` | Shared analysis rate-limit window. |
| `RATE_LIMIT_SUPPORT_LIMIT` | 3 / day | Unblock requests per client IP. |
| `GUEST_COOKIE_NAME` | `cgs_guest` | Signed, HttpOnly guest identity cookie. |
| `GUEST_COOKIE_TTL_DAYS` | `365` | Guest identity lifetime. |
| `MAX_ACCOUNTS_PER_IP` | `3` | Distinct accounts allowed from a hashed client IP. |
| `IP_ACCOUNT_WINDOW_DAYS` | `0` | `0` keeps account links for lifetime counting; positive values use a rolling window. |
| `IP_BLOCK_MODE` | `soft` | `soft` preserves access for the first linked accounts; `hard` denies all access until admin resolution. |
| `SUPPORT_CONTACT_EMAIL` | empty | Required in production; displayed on IP restriction notices. |
| `TRUSTED_PROXY_CIDRS` | empty | Only these reverse proxies may supply a client IP through `X-Forwarded-For`. |
| `EMAIL_VERIFICATION_TTL_HOURS` | `24` | Email verification link lifetime. |
| `PASSWORD_RESET_TTL_HOURS` | `1` | Password reset link lifetime. |
| `UPLOAD_RETENTION_DAYS` | `0` | `0` retains reports/media until user deletion; a positive value deletes completed/failed reports and private files after that age. |
| `DISPOSABLE_EMAIL_DOMAINS` | built-in list | Comma-separated additions/replacements for disposable email rejection. |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM_EMAIL` | empty / `587` / empty | Email delivery; all three required for production account email. |
| `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_STARTTLS` | empty / empty / `true` | Optional SMTP authentication and transport setting. |
| `PUBLIC_APP_ORIGIN` | `http://localhost:3000` | Base URL used in one-time email links. |
| `SESSION_COOKIE_SECURE` | `false` | Set `true` when deployed behind HTTPS. |
| `APP_ORIGINS` | localhost origins | Allowed browser origins for state-changing API requests. |

## API and health

With the app running, the API is at `http://127.0.0.1:8000`; local development docs are at `/docs`. `/health/live` checks the process and `/health/ready` checks the database and storage. The authenticated API is under `/api/v1`.

## Privacy and deployment

Uploads remain in private local storage until the report/account is deleted or an enabled `UPLOAD_RETENTION_DAYS` policy removes a completed/failed report and its media. The default `0` disables scheduled cleanup. Keyed IP hashes support account security controls; guest identity uses a signed cookie and no browser fingerprint. Review [privacy](docs/PRIVACY.md), [security](docs/SECURITY.md), and [operations](docs/OPERATIONS.md) before deployment. Legal review is required for the starter policy text.

Docker Compose describes a PostgreSQL deployment path, but the one-command PowerShell launcher is the verified local development route. Production still requires HTTPS, a managed database, private object storage, secret management, backups, monitoring, a reviewed retention policy, and deployment-specific concurrency controls.

## Vercel frontend deployment

Create a Vercel project from this repository and set its **Root Directory** to `apps/web`. Configure `NEXT_API_ORIGIN` as the HTTPS origin of a separately deployed FastAPI API. The Next.js rewrite keeps browser API requests same-origin while forwarding them to that service. Leave Vercel's framework preset and Next.js build settings enabled.

Deploy the FastAPI API, persistent analysis worker, PostgreSQL database, model artifacts, and private media storage on services that support long-running processes and durable storage. Before deploying the updated admin frontend, run `python -m app.migrate` from `apps/api` as the production migration role so revision `0008_admin_console_management` creates the contact inbox and platform settings tables. Set the API's `APP_ORIGINS` to the exact Vercel site origin, `PUBLIC_APP_ORIGIN` to that same origin, and `SESSION_COOKIE_SECURE=true`; also configure independent secrets, SMTP, support contact, and trusted proxy CIDRs. Deploy the worker separately against the same database and storage. The Vercel project serves the web app and API proxy; it does not host the persistent inference worker.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Technology stack](docs/STACK.md)
- [Implementation plan](docs/IMPLEMENTATION_PLAN.md)
- [Model card](docs/MODEL_CARD.md)
- [Security](docs/SECURITY.md)
- [Privacy](docs/PRIVACY.md)
- [Operations](docs/OPERATIONS.md)
- [Testing](docs/TESTING.md)
- [Decisions](docs/DECISIONS.md)
- [Design system](docs/DESIGN_SYSTEM.md)
