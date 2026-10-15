# Testing

## Local checks

From the repository root:

```powershell
Push-Location apps\api
.\.venv\Scripts\python.exe -m pytest
Pop-Location

Push-Location apps\web
npm run lint
npm run typecheck
npm run build
npx playwright install chromium
npm run test:e2e
Pop-Location
```

The Playwright web server starts the root launcher with an isolated per-run SQLite database and storage directory. Its deterministic detector is explicitly marked as test-only and cannot be enabled in development or production. Browser tests cover signup, upload, durable processing, report evidence, delete, admin login, and non-admin access rejection.

## What tests establish

Backend tests cover authentication and sessions, image validation, ownership, persistent request limits, queue recovery/retries, admin actions/audit events, and detector configuration guards. Playwright tests exercise the main user and administrator paths through Chromium. Lint, TypeScript checks, and the production build cover the web app.

These tests do not measure detector accuracy. Model-specific smoke inference only confirms that the pinned graph loads and returns a result for a sample; it is not an evaluation dataset. The model card separates author-reported evaluation from CGS verification. Docker Compose is not verified when Docker is unavailable.

## Verified on 2026-10-14

- Backend: `python -m pytest -q` — 16 passed, including the real C2PA SDK returning `not_present` for a plain PNG.
- Frontend: ESLint 10, TypeScript, and the Next.js production build passed. The build includes the protected `/admin` route.
- Browser: Playwright Chromium — 3 passed for signup/upload/queue/report/delete, allowlisted admin login and console, and rejection of a normal user.
- Detector: the pinned ONNX file matched its published size and SHA-256; ONNX Runtime 1.31.0 loaded it on CPU and returned a completed screening result for a generated smoke-test image.
- Root launcher: `run.ps1` started the API, worker, and frontend; readiness returned `ready`, detector health returned `ready`, and the frontend returned HTTP 200. Services were stopped after the check.
- Docker Compose/PostgreSQL startup and independent model accuracy evaluation remain unverified.
