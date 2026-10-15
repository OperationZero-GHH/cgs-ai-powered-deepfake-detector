# JOURNAL.md — Session Log

## Session: 2026-10-15 11:58 UTC

### Objective
Remove the platform's point-credit system, validate both forensic model paths, improve responsive behavior, and prepare the Next.js frontend for Vercel.

### Accomplished
- Removed balance, charge, grant, refund, guest-quota, and admin-adjustment behavior from the running application. Added migration `0006_retire_credits`; prior ledger data is archived outside application mappings/routes.
- Removed credit UI and replaced account access checks with email-verification and network-security status. Guests can submit repeated analyses without a credit balance or usage allowance.
- Removed leftover compiled and cached copies of the retired credit service and frontend credit widget; the launcher now retires those files from its runtime copy cache.
- Reworked temporal video inference to strictly load the publisher's trained ResNeXt50 + LSTM checkpoint, with no random-weight fallback. Confirmed the publisher's class mapping (`index 1 = fake`), added face/quality limitations to reports, and made missing or invalid weights return an unavailable temporal result without a score.
- Fixed the verified-account Continue flow to use the Next.js router when cleaning the verification URL. Updated the local cached frontend launcher to remove the renamed middleware file.
- Added responsive coverage across public and guest analysis pages, mobile navigation, auth panels, and multiple viewport widths.
- Prepared Vercel configuration and operations guidance. `apps/web` pins Node.js 24.x and requires a valid HTTPS `NEXT_API_ORIGIN` in Vercel builds; the API and durable inference worker remain separate services.

### Verification
- [x] Backend suite: 33 test functions passed (`apps/api/.venv/Scripts/python.exe -m pytest -q`); includes migration upgrade/downgrade, ONNX detector inference, and cached trained temporal checkpoint sequence inference. Pytest emitted a non-blocking Windows cache-directory warning.
- [x] Real temporal checkpoint: loaded strictly and completed inference on 20 frames. The result verifies model execution only, not predictive accuracy or a real/fake ground-truth verdict.
- [x] Re-ran the cached 20-frame temporal inference test after recording class mapping and known input limitations.
- [x] Frontend lint and TypeScript checks passed.
- [x] Full Playwright suite: 11 passed. Responsive page sweep covered 320–3840 CSS-pixel widths across seven public/guest routes; auth and workspace flows also passed.
- [x] Production Next.js build passed with Node.js 24.19.0, `VERCEL=1`, and an HTTPS API origin; 25 pages generated successfully.
- [x] Source scan found no active credit models, routes, UI, or service. Remaining mentions explain that balances are absent, check for their absence, or document migration history.

### Blockers Encountered
- The local E2E cache retained `src/middleware.ts` after the source moved to `src/proxy.ts`; the launcher now removes that specific stale file.
- E2E assertions had old labels and one auth-navigation issue. Updated assertions to the current interface and changed verification URL cleanup from direct History API mutation to `router.replace`; all browser tests pass.

### Handoff Notes
- No live Vercel deployment was performed. Configure `NEXT_API_ORIGIN`, API `APP_ORIGINS`/`PUBLIC_APP_ORIGIN`, production cookie/security settings, SMTP, PostgreSQL, shared persistent private storage, and the Hugging Face access token for the inference worker before deployment.
- The gated temporal model requires upstream access approval and a token. The validated checkpoint is present in the local ignored model cache; deploy the weights or provide worker credentials/cache separately.
- Viewport testing is representative, not a guarantee for every device/browser/resolution. The application uses fluid layouts between tested widths.
- The active local shell uses Node.js 20 for Playwright and warns that it is end-of-life; Vercel build verification used Node.js 24.19.0, matching the package engine.

---

*Last updated: 2026-10-15*

## Session: 2026-10-15 18:02 UTC — Admin operations and report PDF design

### Accomplished
- Replaced the browser's generic result print layout with a branded A4 report header, clean verdict/evidence panels, video poster frame in print, digest wrapping, and clear interpretation limits. The report action is labeled Download PDF and uses the browser's Save as PDF flow.
- Rebuilt the admin experience as responsive Overview, Inspection Ledger, Control Panel, Contact Inbox, and Settings & Security sections. The ledger and inbox paginate; records use responsive cards with no horizontal table scrolling.
- Added the centered, animated administrator sidebar collapse control and anchors for each management section.
- Persisted contact form messages and added administrator search/status/private-note management. Added migration `0008_admin_console_management` with PostgreSQL row policies.
- Added typed platform switches for account registration and new inspections, enforced server-side and reflected on public registration/upload forms. Added exact-phrase confirmation for settings changes and revocation of other admin sessions.

### Verification
- [x] Focused API checks: contact persistence/admin access, search, status and private notes, setting type and confirmation validation, settings enforcement, session scope, inspection ledger, and public config.
- [x] Full backend suite: 36 passed.
- [x] Alembic applied through `0008_admin_console_management` on a scratch SQLite database; new tables/columns confirmed.
- [x] TypeScript check, ESLint, and Next.js production build passed with the bundled Node runtime.
- [x] Local listeners on ports 3000, 8000, and 8001 are absent; no app server was started.

### Limits
- Visual browser screenshots and a PDF preview were not captured because the platform's local services remained stopped, honoring the earlier stop-process request.
- PostgreSQL RLS statements were inspected but not exercised against a live PostgreSQL server.
- The PDF download uses the browser print dialog; choose its Save as PDF destination.

### Deployment note
- Apply Alembic migration `0008_admin_console_management` on the API database before deploying the new admin frontend.

## Session: 2026-10-16 01:35 PKT — Full project audit and verified fixes

### Confirmed findings and fixes
- Fixed the migrated guest-session schema mismatch: the runtime `GuestSession` model now supplies the required `last_seen_at` value, with a migration-based regression check that also confirms the row can be inserted after upgrade to head.
- Fixed administrator section navigation. Client-side sidebar navigation now notifies the content panel directly, so each selected management tab reveals only its own section; Overview shows its summary without rendering a management section.
- Restored the documented guest inspection flow end to end. Unrestricted guests can open `/app/analyze`, upload to the signed guest identity, view their own report, and retain ownership when registering. Email verification for accounts, upload validation, IP restrictions, and request limits remain enforced.
- Fixed the 320 px `/solutions` horizontal overflow caused by the centered right-edge testimonial tooltip; its bubble now aligns inward at the control edge.
- Updated browser/API assertions that still described retired guest denial and older contact/auth UI behavior. Added browser coverage for admin invitations, invite cancellation, both log searches and purge confirmations, and per-tab content isolation.
- Fixed E2E lifecycle cleanup. Playwright now signals the isolated launcher to stop its API, worker, and web services after test completion.

### Verification
- [x] Full backend suite: `apps/api/.venv/Scripts/python.exe -m pytest -q` passed after fixes.
- [x] Frontend ESLint and `tsc --noEmit` passed.
- [x] Production Next.js build passed with `VERCEL=1` and `NEXT_API_ORIGIN=https://api.example.test`; 25 routes generated.
- [x] Full Playwright suite: 11 passed, including guest upload/repeat analysis, blocked-network recovery, admin tab isolation, invitation create/cancel, user/admin log search and purge, and viewport checks from 320 px through 3840 px.
- [x] E2E cleanup reported “Stopping isolated E2E services”; ports 3100 and 8100 had no listeners afterward.
- [x] PowerShell parser accepted the launcher changes.

### Audit limits
- The named remote security plugins were not exposed as connected scanner tools in this session; no plugin scan is claimed. The review used repository source, tests, lint, type-check, production build, and browser/API verification.
- PostgreSQL row-level-security behavior was not exercised against a live PostgreSQL instance. No live deployment or production database was changed.
- The workspace has no Git repository metadata, so no commit or Git-based change summary was possible.

### Files touched
- `apps/api/app/main.py`, `apps/api/tests/test_api.py`, `apps/api/tests/test_credit_retirement_migration.py`
- `apps/web/src/app/admin/admin-content.tsx`, `apps/web/src/app/globals.css`, `apps/web/src/components/auth-guard.tsx`, `apps/web/src/components/upload-form.tsx`, `apps/web/e2e/user-journey.spec.ts`, `apps/web/e2e/global-teardown.ts`, `apps/web/playwright.config.ts`
- `run.ps1`
- `.gsd/JOURNAL.md`

## Session: 2026-10-16 02:17 PKT — Audit continuation and security regressions

### Confirmed findings and fixes
- Centralized local return-path validation and applied it to login, signup, and email-verification continuation links. Backslash-based paths such as `/%5Cattacker.example/landing` previously passed the prefix check and could navigate off-site.
- Fixed C2PA text cleaning, which inserted spaces between every character and made normal validation states and assertion labels unreadable. Removed camera-hardware claims based on signer-name substrings; trusted provenance no longer bypasses the AI screening model.
- Added safeguards for old cached and persisted C2PA-only reports: legacy hardware-authentic verdicts are not reused, and existing reports are presented as inconclusive pending a fresh model screening.
- Added streaming request-body enforcement for analysis uploads without `Content-Length`; chunked uploads are now stopped at the configured request cap before multipart parsing can spool an unbounded body.
- Released OpenCV video captures in the cleanup path when validation fails, including before temporary-file removal.
- Aligned upload MIME handling: image files cannot declare video types, and accepted MKV files now retain `video/x-matroska` in reports and supported-type configuration.
- Hardened the C2PA scanner against a malformed non-string active-manifest reference.
- Corrected a Playwright mobile-navigation selector to target the banner rather than matching both banner and drawer navigation.

### Verification
- [x] Baseline backend, frontend lint/type-check, production build, and browser suite passed before these fixes; the original backend test count was not preserved.
- [x] Final backend suite: 48 tests passed.
- [x] Final ESLint and TypeScript checks passed.
- [x] Final production Next.js build passed; 25 routes generated.
- [x] Final Playwright suite: 11 tests passed, including admin section isolation, admin invitation create/cancel, user/admin log search and purge, and both login and verification redirect regressions.
- [x] Ruff is configured but not installed in the local API environment; it was not installed as part of the audit.
- [x] E2E teardown completed; ports 3000, 3100, 8000, 8001, and 8100 have no listeners.

### Audit limits
- Requested remote security plugins were not exposed as connected scanner tools; no plugin scan is claimed. C2PA behavior was cross-checked against official SDK documentation.
- PostgreSQL RLS was not exercised on a live PostgreSQL instance. No deployment or production database was changed.
- No Git metadata is present, so a Git diff/status and commit were unavailable.

### Files touched in this continuation
- `apps/api/app/main.py`, `apps/api/app/scanner.py`, `apps/api/app/worker.py`, `apps/api/app/video.py`
- `apps/api/tests/test_api.py`, `apps/api/tests/test_scanner.py`, `apps/api/tests/test_video_temporal.py`
- `apps/web/src/components/auth-form.tsx`, `apps/web/src/components/account-recovery.tsx`, `apps/web/src/lib/navigation.ts`, `apps/web/e2e/user-journey.spec.ts`
- `.gsd/JOURNAL.md`

## Session: 2026-10-16 PKT — Remaining audit gaps

### Item 1: Safe version control
- Checked the project, Desktop, user-profile, and drive-root `.git` markers; none existed. Initialized this project on `main` and created baseline commit `3fe9157` (`chore(phase-1): capture audit baseline`).
- Expanded `.gitignore` before staging to exclude environment files (except `.env.example`), generated output, local databases/media, E2E storage, model weights, logs, and OS junk. Confirmed `.env` is ignored and `.env.example` is included.
- A high-confidence credential-pattern scan found no matches in readable source/config files or `.env.example`. The active `.env`, local data/media, generated directories, and binary/model files were excluded from scanning; `.env` was not read. No such files are in the baseline commit.
- The initial source tree has pre-existing whitespace warnings in `.git diff --cached --check`; these were preserved in the baseline rather than mass-editing unrelated project files.

### Verified Baseline
- Reference commit: `3fe9157` (`main`); `git status --short` was clean after the commit and E2E run.
- Backend: `apps/api/.venv/Scripts/python.exe -m pytest -q` exited 0; 48 tests collected and completed, with 48 passes, 0 failures, and 0 skips.
- Collection by file (`pytest --collect-only -q`): `test_admin_workforce_migration.py` 1; `test_api.py` 35; `test_credit_retirement_migration.py` 1; `test_detector_model.py` 1; `test_scanner.py` 4; `test_video_temporal.py` 6 (48 total).
- Frontend checks under bundled Node `v24.19.0`: ESLint passed; TypeScript `tsc --noEmit` passed.
- Production build under Next.js `16.4.0`, `VERCEL=1`, and `NEXT_API_ORIGIN=https://api.example.test` passed; 25 of 25 static pages generated.
- Playwright: 11 passed in 1.3 minutes. Ports 3000, 3100, 8000, 8001, and 8100 were free before the run and had no listeners after teardown.
- Ruff was not installed at this baseline; live PostgreSQL RLS tests and dependency/code security audits remain for their ordered items below.

### Pending items
- Item 3: add pinned project-local Ruff development tooling and fix genuine findings.
- Item 4: validate migrations and forced RLS against a disposable local PostgreSQL instance with a non-owner role.
- Item 5: benchmark maximum and representative video limits and add evidence-based guard/regression coverage.
- Item 6: run local dependency, code, and secret scanners; triage findings.
- Item 7: review product claims and add the owner decision note for hardware credentials.
