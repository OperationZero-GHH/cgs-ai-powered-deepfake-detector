# Remove credit gating, validate forensic models, and prepare Vercel deployment

Status: FINALIZED

## Objective
Remove the limited credit and per-analysis point system throughout CGS DeepFake Shield. Keep valid authentication, guest report ownership, abuse protections, and analysis integrity controls. Ensure image and video forensic outputs come from configured, loaded models and never from random fallback weights. Make the web experience fluid across small and large viewports, and prepare the Next.js frontend for a Vercel deployment backed by a separately hosted API and worker.

## Requirements
- Remove balances, grants, charges, refunds, per-guest verification quotas, credit-related admin operations, and credit status endpoints from runtime behavior and user-facing pages.
- Keep analysis available to guests and accounts without balance checks; retain upload validation, report ownership, authentication, email verification, and non-credit security rate limits.
- Add a database migration that removes credit services from the live schema, quarantines the old ledger from application access, and removes guest quota/device/IP fingerprint fields while preserving account, report, and historical ledger records. Keep historical migrations immutable.
- Update sign-up, verification, upload, report, history, pricing, privacy, configuration, and operations language so no credit or point system remains described or enforced.
- Verify the image ONNX artifact and video temporal model’s loaded weights, preprocessing, inference, health status, and failure behavior. Do not label an untrained fallback as a completed model prediction.
- Use fluid layouts and validate representative narrow, tablet, desktop, ultrawide, and high-density viewport sizes for horizontal overflow and usable controls.
- Prepare the Next.js app in `apps/web` for Vercel. Require an HTTPS `NEXT_API_ORIGIN` for Vercel builds, document backend origin/cookie/worker/storage configuration, and do not claim that the Python API or persistent inference worker runs on Vercel.
- Keep account governance out of the inspection ledger. Provide standalone user management with signup method, signup IP for new registrations, name, phone, email, ban/unban, and confirmed deletion; restrict this sensitive data and actions to administrators and disclose IP retention.
- Provide standalone administrator management using one-time expiring invitations, plus searchable and separately purgeable user-activity and administrator-audit logs. Administrator role changes must revoke sessions where applicable and preserve a protected bootstrap administrator.
- Provide security-monitoring and traffic-management sections with working restriction, allowlist, unblock-request, and expired-counter actions. Clearly label tracked security events instead of implying every HTTP request is counted.
- Use one shared theme control and a consistent embossed/neumorphic token system across public, authentication, and admin surfaces. Remove the expensive theme ripple, honor reduced-motion preferences, and keep admin layouts usable without horizontal scrolling on narrow screens.

## Constraints and decisions
- Preserve migration history and historical ledger data; use a new Alembic revision rather than rewriting revision `0005_guest_credits_auth`.
- Preserve the existing API, database-backed analysis queue, account/report ownership, detector architecture, and file-size/media-duration safeguards.
- The frontend uses same-origin `/api/*` rewrites. Production requires the rewrite destination to be a separately deployed HTTPS API origin allowed by the API's exact-origin and email-link settings.
- A video model that cannot obtain its gated trained weights must report unavailable for temporal inference; spatial ONNX frame screening and provenance checks may still complete and must state the limitation.

## Acceptance evidence
- Backend API tests prove there is no credit status or adjustment API, guest and signed-in analysis are not balance- or quota-gated, reports remain owner-scoped, and the schema upgrade removes credit tables/quota fields on SQLite.
- Model checks show valid ONNX inference and truthful temporal-model readiness; if gated weights cannot be accessed, the temporal layer reports unavailable and does not emit a fabricated score.
- Frontend lint, typecheck, production build, backend test suite, and browser journeys pass.
- Browser evidence at representative viewport widths shows no horizontal overflow on landing, analysis, report/history, auth, and pricing/usage pages.
- Vercel configuration fails early when the required production API origin is absent, while the local build remains usable; deployment instructions identify required settings and external services.

## Known limits
- No software can guarantee zero defects on every device, browser, resolution, dataset, or production environment. Validation covers the declared test suite and a representative viewport matrix.
- The video checkpoint is gated by its upstream host. Its weights can only be validated if the configured account already has access to the model files.

## Additional scope — admin operations and result reports (2026-10-15)

### Requirements
- Replace the generic print output with an A4-friendly result report layout that clearly presents the case identity, result, evidence metadata, integrity digest, model findings, provenance, and limitations. Media controls and app navigation must not appear in the PDF.
- Redesign the admin navigation and console with a smooth, accessible collapse control centered at the top of the sidebar. Keep navigation and cards usable at narrow and wide viewports, without horizontal scrolling inside record lists.
- Add a searchable admin inspection ledger backed by an authenticated endpoint. Return only report summary and account details required for administration; keep media bytes private and owner-scoped.
- Persist contact form submissions, including name, email, topic, message, and submission time. Only administrators may view, search, assign a status, and add private notes to submissions.
- Add actual platform settings for new registration and new inspections. Apply changes on the server immediately, accept JSON booleans only, and require the exact confirmation phrase before writes.
- Add a security review area for pending access requests and active network restrictions. The danger-zone action may revoke other administrator sessions only after exact typed confirmation and must retain the current session.
- Record administrator actions in the existing audit log. Do not expose contact submissions or settings mutations to unauthenticated callers.

### Acceptance evidence
- Backend compilation and focused API checks cover contact persistence/admin access, admin ledger search, settings type/confirmation validation and enforcement, and session revocation scoping.
- Frontend typecheck/build and browser screenshots confirm the PDF print layout, admin menu collapse behavior, and responsive admin cards without inner horizontal overflow.
- The database migration applies cleanly on SQLite and PostgreSQL-compatible RLS policies limit reads and writes as specified.
