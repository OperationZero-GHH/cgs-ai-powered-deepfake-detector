# Plan: Admin operations and professional result PDFs

Status: COMPLETE

## Objective
Deliver a professional print-to-PDF inspection report and a responsive admin console with a redesigned collapsible sidebar, complete inspection ledger, contact inbox, platform settings, security review, and typed danger-zone action.

## Phase 1 — Persistent services
- Add contact and platform-setting models plus migration `0008`.
- Persist contact submissions and provide administrator-only list, search, and update endpoints.
- Add administrator search for inspection records with minimal report/account fields.
- Apply strict boolean settings to registration and inspection entry points; add typed confirmation and scoped session revocation.

## Phase 2 — Admin experience
- Replace the existing admin page with overview, ledger, control, contact, and settings sections.
- Use responsive cards for records instead of inner-scroll tables.
- Add exact-text confirmation prompts for settings writes and session revocation.
- Replace the workspace sidebar on admin pages with administrator navigation and smooth collapse/expand animation.

## Phase 3 — Report output and proof
- Add branded report header/footer, PDF-friendly page sizing, readable metadata, and media handling for print.
- Run static/type/build checks and focused API/migration checks without starting long-running services.
- Capture browser/PDF evidence at representative viewport sizes where the local browser can be used without logging in with user credentials.

## Completion evidence
- Backend suite: 36 passed.
- Frontend TypeScript, ESLint, and optimized production build passed with the bundled Node runtime.
- New migration `0008` upgraded a scratch SQLite database through revision head and exposed the expected inquiry/settings schema.
- Local app ports 3000, 8000, and 8001 remained closed. Browser screenshot/PDF preview was not captured because the user had requested local services stay stopped.
