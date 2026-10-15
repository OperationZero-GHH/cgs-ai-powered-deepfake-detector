# Privacy and data handling

This is starter product information, not legal advice. Review and adapt it before public launch.

## Data processed

- Accounts store normalized email and email-identity digests, username, display name, optional phone number, Argon2 password hash, role, verification state, and creation timestamp. Verification and reset tokens are stored only as digests with expiry times.
- Sessions use opaque random cookies. The database stores a digest, expiry, and revocation time.
- Guests receive a signed, HttpOnly cookie with a random ID. Guest sessions store the signed guest ID and timestamps; browser/device fingerprints and guest-use counts are not stored. New account registrations and administrator invitations store the signup IP address so authorized administrators can review signup attribution. This address is visible only through administrator account-management access and is removed when the account is deleted. Existing accounts created before this field was added have no recorded signup IP. Account/IP security controls separately retain keyed client-IP hashes, account links, access references, and audit events.
- Uploads store an original and normalized preview in private local storage until user deletion or enabled retention cleanup. Database report data includes generated object keys, safe filename, detected format, dimensions/duration, byte count, SHA-256, selected EXIF field names, detector output, C2PA summary, and timestamps.
- Migration `0006_retire_credits` removes point balances and the active transaction ledger from the application schema. Existing wallet and transaction history is preserved in renamed tables that have no application mappings or routes. PostgreSQL blocks the runtime role from the archive with forced row-level security; a SQLite database operator can still inspect the underlying file. IP account links, restriction references, audit events, and submitted unblock requests are retained for abuse review; unblock requests include the contact name, email, reason, and reference ID.
- Persistent rate limits store HMAC-digested client/session keys, counts, and reset times rather than raw client addresses or cookie values.
- Administrator audit events store actor/subject IDs, action name, limited account-change details, and timestamp. They do not store passwords, session tokens, image bytes, or raw manifests.
- User activity and administrator audit logs are available only to administrators. Clearing user activity is recorded in the administrator audit log; clearing the administrator log retains a new purge record.

## Image processing

The configured image/video analysis runs in the separately hosted inference worker; no hosted inference provider is configured and the app does not send the media to a model API. The video model's checkpoint is downloaded from Hugging Face only by the worker when authorized access and a token are configured. The optional C2PA scanner reads embedded Content Credentials using the CAI SDK. The report stores validation state and selected assertion/source-type summaries, not the complete raw manifest. File metadata inspection records field names and presence; it does not publish GPS coordinates or raw EXIF values.

## Retention and deletion

With the default `UPLOAD_RETENTION_DAYS=0`, reports and media remain until a user deletes an individual report or account. A positive setting lets the worker remove completed/failed reports and their files after the configured number of days; processing reports stay until they finish. Deleting a report/account removes associated local files and database rows, including queued jobs and sessions through foreign-key cascades. Deployment backups may retain prior copies according to the operator's backup lifecycle; this app makes no promise of immediate backup erasure.

## User choices and provider disclosures

There is no opt-in for model training and uploaded media is not used to train this detector. Email verification and password recovery links are sent through the configured SMTP relay. Local development without SMTP writes one-time links to the API log for QA; production requires SMTP configuration. A future operator must disclose hosting region, trusted reverse proxies, database, object storage, email, monitoring, backup retention, and any added providers. Legal/privacy review is required before launch.
