# Plan: Admin navigation and shared visual system

Status: COMPLETE

## Objective
Finish the open admin workforce and visual-consistency phase while preserving the existing server-backed account, log, security, and traffic workflows.

## Existing implementation
- The inspection ledger and user-management sections are already separate.
- User search, signup attribution, ban/unban, and confirmed deletion are backed by administrator-only API endpoints.
- User activity and admin audit logs have separate search and confirmed purge actions.
- Administrator invitations, security restrictions, traffic summaries, allowlists, and cleanup actions are implemented.
- The admin sidebar already links to every dashboard section, but still uses the prior shared sidebar layout.
- Public, authentication, and admin views share one `ThemeToggle`; theme changes still trigger transitions across many styled elements.

## Tasks
1. [x] Review the existing admin endpoint protections and confirm all dashboard section IDs have navigation entries.
2. [x] Rebuild the admin-only sidebar with grouped navigation, clearer identity/status, compact collapse behavior, and the same links for all dashboard sections.
3. [x] Keep one shared theme control and centralize the neumorphic surface, control, and input tokens used by public, auth, workspace, and admin surfaces.
4. [x] Suppress CSS transitions only while the root theme value changes so large pages do not animate every surface during a theme switch.
5. [x] Update the Phase 7 roadmap and state snapshot with changed files and concrete verification evidence.

## Verification
- TypeScript check passed.
- ESLint passed with zero errors and zero warnings.
- Next.js 16.4 production build passed with the bundled Node 24 runtime; all 25 app routes were generated or compiled.
- PostCSS parsed the shared stylesheet, and a source mapping check found all 11 sidebar destinations with no missing or unlinked dashboard sections.
- The shared theme control remains used by sign-in, registration, admin sign-in, invitation acceptance, and the authenticated workspace.
- Admin endpoint roles, account protections, log purges, traffic actions, and signup-IP retention were reviewed in source; this task made no API or migration changes.
- Do not run automated tests unless requested; the current work does not require new API behavior.

## Scope limits
- Do not add scanner-branded plugins or transmit platform data to external services. The requested scanner plugins are not available as connected tools in this session.
- Do not change the already implemented account/log/security APIs unless the review finds a concrete correctness or security defect.
