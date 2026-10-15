# Roadmap: Remove credit gating and prepare model-backed Vercel deployment

## Phase 1 — Remove runtime credit enforcement
- [x] Remove balance, grant, charge, refund, guest quota, and admin adjustment code paths.
- [x] Keep guest identities, reports, authentication, email verification, file checks, and abuse rate limits.
- [x] Add migration `0006` to retire live credit tables and guest quota state; verify from a database at revision `0005`.

## Phase 2 — Remove credit UI and documentation
- [x] Remove global credits state/widget and upload gating/cost copy.
- [x] Update signup/verification/report states, pricing/usage page, privacy notice, environment examples, and operating docs.
- [x] Replace credit-specific browser and API coverage with repeated-analysis and no-credit-route checks.

## Phase 3 — Validate both forensic model paths
- [x] Run the image detector against an input and confirm artifact identity, output range, and health state.
- [x] Validate the trained temporal checkpoint and architecture; remove random/untrained fallback predictions.
- [x] Keep video reports truthful when trained temporal weights are unavailable; expose readiness only after trained weights load.

## Phase 4 — Responsive and Vercel readiness
- [x] Fix fluid layout issues found across public, workspace, report, auth, and pricing/usage pages.
- [x] Validate representative viewport widths and report results.
- [x] Add Vercel build configuration for the Next.js frontend, explicit API-origin validation, and deployment documentation for the external API, database, worker, secrets, and storage.

## Phase 5 — Verification
- [x] Run backend tests, frontend lint/typecheck/build, model checks, and browser journeys.
- [x] Resolve regressions found and record concrete evidence in `.gsd/JOURNAL.md` and `.gsd/STATE.md`.

## Phase 6 — Professional reports and admin operations
- [x] Replace the generic print page with a branded, readable A4 report that prints cleanly to PDF.
- [x] Add the admin ledger, persistent contact inbox, typed platform settings, and confirmed session revocation.
- [x] Redesign the admin console cards and add a centered animated sidebar collapse control.
- [x] Add migration `0008` with admin-only record access and safe runtime-setting read policy.
- [x] Validate API schema/migrations, frontend types/build, admin responsive views, and PDF output while leaving app services stopped.

## Phase 7 — Admin workforce, logging, and visual consistency
- [x] Keep user management separate from the inspection ledger and expose signup attribution plus protected account actions.
- [x] Complete invitation acceptance, administrator management, and searchable/purgeable activity logs.
- [x] Complete security monitoring and traffic controls; document signup IP handling in privacy and operations guidance.
- [x] Group every dashboard section in the rebuilt admin sidebar; keep collapse and mobile drawer behavior responsive.
- [x] Unify theme controls and neumorphic surface tokens; suppress page-wide transitions during theme changes.
- [x] Review existing migration/API protections, pass frontend TypeScript, ESLint, and production build checks, and confirm all 11 sidebar links target dashboard sections.
