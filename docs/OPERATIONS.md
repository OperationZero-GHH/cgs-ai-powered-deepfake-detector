# Operations guide

## Local Windows development

From the repository root, run:

```powershell
.\run.ps1
```

The launcher creates `.env` if missing, creates/updates `apps/api/.venv`, and copies the frontend into a lockfile-specific directory under `.run` before installing its dependencies. It uses `.run/npm-cache` and keeps `npm ci` away from `apps/web/node_modules`, where a running Windows Node process may have the native Next/SWC module open. Use Node.js 24 LTS; the launcher warns when it finds an end-of-life Node 20 runtime. It prefers API port 8000 and web port 3000, selecting the next available local port if either is occupied; the startup output shows the actual URLs. It then attempts the detector artifact download, applies database migrations, and starts the API, worker, and frontend. Service output is recorded in `.run/logs/`. Press Ctrl+C in the launcher terminal to stop the processes.

Set `ADMIN_EMAILS` in `.env`. After launching once, create the administrator from a second PowerShell window with `Set-Location apps/api; .\.venv\Scripts\python.exe -m app.bootstrap_admin admin@example.com`. The command prompts for a password and only creates or promotes the specified allowlisted account. Public registration cannot claim an administrator address. The admin login page is `/admin/login`.

The first normal launch downloads a 43,778,110-byte model artifact. The downloader verifies the published SHA-256 before installing. If the network is unavailable, API/web still start; AI screening is explicitly unavailable. Once a valid artifact is present, the worker loads it for CPU inference.

## Analysis access, email verification, and IP controls

Analysis does not use point balances, guest run allowances, or per-analysis charges. Registered users must verify their email before analysis. Local development writes one-time email links to the API log when SMTP is not configured; production startup requires `SMTP_HOST`, `SMTP_FROM_EMAIL`, and `SUPPORT_CONTACT_EMAIL`, so configure a real SMTP relay and verify `PUBLIC_APP_ORIGIN` first. Verification and password-reset link lifetimes are configurable. Image bytes, video bytes, and video duration are bounded by `MAX_UPLOAD_BYTES`, `MAX_VIDEO_BYTES`, and `MAX_VIDEO_SECONDS`.

Account registration/login uses the distinct-account limit (`MAX_ACCOUNTS_PER_IP=3` by default), with a lifetime count when `IP_ACCOUNT_WINDOW_DAYS=0`. Soft mode (`IP_BLOCK_MODE=soft`) blocks new accounts and guest analysis while preserving access for already-linked accounts; hard mode denies all sign-in and analysis from the blocked IP. Only keyed hashes are retained and displayed. Review shared-network complaints through the admin IP-block and unblock-request endpoints, or whitelist/raise a limit where appropriate. Upload validation and persistent security rate limits remain active for guests and accounts.

The launcher applies Alembic migrations at startup. For a direct deployment, first configure production database roles and environment, then run `python -m app.migrate` from `apps/api` as the migration role. On existing installs, verify a database backup and role grants before upgrading: migration `0006_retire_credits` removes the live balance/ledger schema and guest quota/fingerprint fields. The former wallet and ledger tables are renamed to `retired_usage_wallets` and `retired_usage_transactions`, outside the application ORM and routes. Migration `0008_admin_console_management` creates the contact inbox and server-enforced platform settings; migration `0009_admin_workforce_and_logs` adds administrator invitations, signup attribution, and user activity logs. Apply the latest revision before deploying the updated admin frontend. Forced row-level security with no runtime policy protects the archive on PostgreSQL; SQLite database files remain directly accessible to their operators. Preserve or securely dispose of that legacy archive according to your retention policy. New accounts still require email verification. Signup IP values are retained with each account and removed when an administrator deletes that account; disclose this collection in the deployed privacy notice.

To enable automatic report/media cleanup, set `UPLOAD_RETENTION_DAYS` to a positive number. The worker periodically deletes completed or failed reports and their private files after that many days. `0` (default) disables automatic cleanup. Test actual backup retention/deletion separately; local file cleanup does not erase external backups.

## E2E mode

From `apps/web`, run `npm run test:e2e` after installing the matching browser with `npx playwright install chromium`. The Playwright config starts the root launcher in isolated E2E mode. E2E uses a per-run SQLite file, per-run storage folder, an allowlisted test admin, and a deterministic test-only detector that cannot be selected outside `APP_ENV=test` or `e2e`.

## Database and queue

- Apply migrations from `apps/api`: `.\.venv\Scripts\python.exe -m app.migrate` (or run the root launcher).
- Local single-host development uses SQLite. PostgreSQL is supported for multi-process API/worker deployment.
- A job is created in the same transaction as its report row. The worker polls durable rows and claims them with a conditional update and expiring lease.
- A worker crash leaves the current job recoverable after its lease expires. Retries use bounded exponential backoff, then mark the job/report failed with a safe error code.
- Admins can inspect worker health, queue state, last safe error code, and retry completed/failed work from the restricted admin console.
- `/health/live` checks process liveness. `/health/ready` checks database connectivity and writable storage. The admin console reports actual recent worker heartbeats and detector health.

## Model and provenance scanner

- `AI_DETECTOR_PROVIDER=local` enables the ONNX CPU model. `disabled` keeps integrity/provenance scanning while marking AI screening unavailable.
- `AI_MODEL_PATH` changes the model location. Do not replace the model without updating its ID, revision, SHA-256, evaluation documentation, and policy version.
- Detector health is checked through `/api/v1/config` and admin overview. Model loading/inference failure produces no score.
- The C2PA scanner uses the CAI `c2pa-python` SDK and records a small validation summary. If the SDK is unavailable, status is `unavailable`; if no manifest exists, status is `not_present`.

## Production deployment

1. Set independent random hexadecimal values for `POSTGRES_PASSWORD`, `APP_DB_PASSWORD`, and `MIGRATOR_DB_PASSWORD`, set `SESSION_COOKIE_SECURE=true`, and provide comma-separated exact HTTPS browser origins in `APP_ORIGINS`. Do not deploy the example values.
2. The Compose PostgreSQL init script creates a migration role that owns the schema and a non-owner runtime role. The API migrates with `MIGRATION_DATABASE_URL`; API requests and workers connect with the restricted `DATABASE_URL`. The migration applies forced row-level policies for analyses, queue jobs, and audit events. SQLite is local development only and relies on owner-scoped application queries.
3. On an existing PostgreSQL volume, the init script will not rerun. Create the two restricted roles, transfer table ownership to the migration role, and grant only SELECT/INSERT/UPDATE/DELETE on existing tables to the runtime role before starting this version.
4. Use a supported PostgreSQL release and run Alembic migrations as a deployment step.
5. Run the API and inference worker as separate non-root processes. Provision enough CPU/RAM for ONNX Runtime; add a GPU only after selecting a runtime/model that uses it.
6. Put the API behind TLS and a reverse proxy with explicit origin, upload size, body timeout, worker timeout, and edge rate limits. By default the app uses the direct network peer. Set `TRUSTED_PROXY_CIDRS` only to proxy networks you control; only those peers may supply a forwarded client address.
7. Use private object storage, secure cookies, a secret manager, restricted DB credentials, and tested retention/deletion procedures. The Compose `private_storage` volume is private local storage, not an externally managed bucket.
8. Monitor request errors, rate-limit responses, queue depth/age, expired leases, retry/failure counts, detector availability/latency, storage failures, and database capacity. Avoid image contents, full EXIF, session IDs, and user-specific labels in logs/metrics.
9. Test database/file backups and restore, failed-job recovery, and account/report deletion against the production storage adapter.
10. Review legal terms, privacy/retention, model licenses, the C2PA trust configuration, and incident-response procedures.

Docker Compose remains a reference path and has not been verified in this environment. The root PowerShell launcher is the local development workflow. No deployment is performed by this project.

## Vercel frontend deployment

Deploy `apps/web` as the Vercel project root. The package pins Node.js 24.x, which Vercel should select for the build and functions. Vercel serves the Next.js frontend only; the FastAPI API and durable inference worker need a separate host with PostgreSQL and persistent private storage shared by the API and worker. The Next.js rewrite proxies `/api/*` to the API origin, so configure `NEXT_API_ORIGIN` as the API's HTTPS origin (scheme and host only). Configure `APP_ORIGINS` on the API with the exact Vercel preview/production origins that should be allowed, and set `PUBLIC_APP_ORIGIN` to the public frontend URL used in account emails. Set `SESSION_COOKIE_SECURE=true` and use production secrets and SMTP credentials. Do not expose `HF_TOKEN` as a frontend or `NEXT_PUBLIC_*` variable; configure it only for the inference worker.

The Vercel build validates `NEXT_API_ORIGIN` when running in Vercel. API file upload, inference, database migrations, model weights, and worker processes are not hosted by that frontend deployment. Run Alembic as a release step on the API host, and verify API/worker readiness and both model statuses after deployment.
