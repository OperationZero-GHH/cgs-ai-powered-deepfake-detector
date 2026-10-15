# Security controls and remaining risks

## Implemented

- JPEG/PNG/WebP allowlist; extension, decoded bytes, and declared image content type must agree. The API enforces request and decoded-pixel limits, Pillow verification, safe decoding, still-image-only input, and normalized previews.
- Generated storage keys are allowlisted and resolved inside private local storage outside the web root. Files use owner-only permissions on POSIX hosts and are created exclusively; report images are served through owner-checked routes with private no-store caching and `nosniff`.
- Argon2id password hashing, a 15-character passphrase minimum, opaque random session cookies, SHA-256 session-token digests at rest, `HttpOnly`, `SameSite=Lax`, configurable `Secure`, session expiry, and server-side revocation.
- Private-by-default `/api/v1` routing requires the verified server session on every operation except public configuration, signup, and login. A startup route check fails closed if a new private API route is added without the auth dependency. Admin APIs also check the database role.
- PostgreSQL row-level security uses `ENABLE` and `FORCE ROW LEVEL SECURITY` for users, sessions, analyses, inference jobs, and admin audit events. The API binds the user or admin role only after verifying the server session; session lookup is limited to the supplied token digest. Signup/login and the trusted bootstrap command use a restricted auth context, and the worker uses its worker identity. The Compose runtime role is non-owner and has no `BYPASSRLS` privilege. SQLite development relies on the matching owner-scoped application queries because SQLite does not implement RLS.
- Exact-origin credentialed CORS, same-origin mutation checks, and browser Fetch Metadata checks. Production startup requires exact `APP_ORIGINS` and secure cookies. The app never trusts arbitrary forwarded-address headers.
- Persistent fixed-window rate limits for signup, login, upload, and admin operations. Signup/login limits apply by direct peer address and normalized email; SQLite/PostgreSQL atomic upserts share counters across API processes. Rate-limit keys are HMAC digests rather than raw addresses. New account signup IPs are stored on the account for administrator review as described in the privacy notice; session cookies are not stored.
- ORM-generated queries bind values as parameters. Request models reject unexpected fields and strip unsafe control characters from display names; user content is rendered as text, not executable HTML.
- Upload creation stores the analysis and queue job together in the database. Worker leases, conditional claims, bounded retries, and safe error codes support restart recovery.
- The detector artifact has a fixed size and SHA-256 check. The local ONNX model is inference-only; the app does not load remote Python code or pickle checkpoints.
- C2PA verification returns a limited summary rather than the complete raw manifest. User reports do not expose source file paths or EXIF values.
- Admin entry has no public navigation link, is marked `noindex` in metadata and response headers, and uses private no-store caching. The server-rendered page and every admin API request verify the account role. Public signup always creates a standard user; a local operator must use the password-prompting bootstrap command to create or promote an address in `ADMIN_EMAILS`. Admin account changes, account deletion, and analysis retries are written to `audit_events`; disabling a user revokes their sessions. Administrators cannot disable/demote their own account through the console.
- API and frontend responses use security headers; production disables FastAPI debug mode and API documentation routes. The Next.js CSP, clickjacking, referrer, permissions, cross-origin, and production HSTS headers are configured at the frontend.
- The frontend npm lockfile passes `npm audit` with zero reported advisories. TypeScript is locked to 6.0.3 because the installed typescript-eslint line does not support TypeScript 7 yet.
- Logs omit image bytes, passwords, session tokens, raw EXIF, and raw model tensors.

## Configure before public deployment

- Replace `APP_SECRET_KEY` with a generated secret and protect `.env`; set `SESSION_COOKIE_SECURE=true` behind HTTPS.
- Use managed PostgreSQL or the Compose PostgreSQL service with separate random `POSTGRES_PASSWORD`, `APP_DB_PASSWORD`, and `MIGRATOR_DB_PASSWORD` values. Set `SESSION_COOKIE_SECURE=true`, exact `APP_ORIGINS`, and TLS at the reverse proxy. The Compose `private_storage` volume is not an internet-facing bucket; use a private object-storage adapter before a multi-host deployment.
- If upgrading an existing Compose database volume, provision the non-superuser runtime and migration roles and grant existing tables before starting the new app. The Postgres init script runs only when the database volume is first created.
- The API relies on the direct peer address for rate limiting. If a reverse proxy is used, configure edge rate limits there because multiple users may share one API peer address.
- Review worker concurrency and lease duration for the actual model host. The local launcher starts one worker. Production requires resource limits, queue-depth/error alerts, failed-job review, and recovery tests.
- Restrict administrator addresses in `ADMIN_EMAILS`; do not assign a default public admin credential. Protect administrator sessions and review audit events.
- Add malware scanning only with an explicit privacy/retention policy. Pillow parsing and the AI-generation model are not malware detection.
- Decide email verification, password reset/recovery, account/session UI, automatic retention, deletion guarantees for backups, incident response, and dependency/update procedures before launch.
- Review the C2PA SDK trust configuration and supported formats for the intended deployment. Valid provenance is not proof that depicted events are true.
- Obtain legal/privacy review. This application is not represented as compliant or certified.

## Threat model and residual risk

Treat uploaded bytes, metadata, file names, requests, credentials, and browser inputs as untrusted. File decode is still an attack surface even with size limits. The model is a fallible screening signal, can be evaded, and may false-positive on natural images or miss generated content. Local development uses a single-machine SQLite database and local filesystem; it is not suitable for shared multi-host production storage. Third-party package/model supply chains, operating system hardening, and production monitoring remain deployment responsibilities.
