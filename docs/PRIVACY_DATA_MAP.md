# Privacy and Data Map

Reviewed 27 September 2026. This records the code paths in this repository. It does not identify or contractually verify a deployment operator, cloud host, database provider, or legal entity.

## Data inventory

| Data | Purpose | Storage and access |
| --- | --- | --- |
| Username, email, password hash, role, active flag, terms acceptance flag, creation time | Account registration, sign-in, profile display, backend authorization | `users` collection; the authenticated user can view/correct their own username and email; administrator user list omits email and password hash |
| Post/comment text, author reference, parent post reference, language heuristic | Feed, moderation, dashboards, appeals | `posts` and `comments`; approved posts/comments appear in public feed; owners see their own records; admins see moderation review content |
| Prediction label, scores/confidence, rule highlights, recommendation, status, model name/version, timestamps, manual review action | Moderation and review history | Embedded in content and summarized in `moderation_logs`; owners see their own history; admins see required review/history fields |
| Event ID, actor ID/role, event type, optional resource ID, timestamp | Audit of data exports, privacy requests, profile changes, account deletion, reports, and admin review actions | `audit_logs`; admin-only view omits details. Logs do not contain IP, passwords, tokens, or submitted content. Account deletion anonymizes actor IDs and clears owned content references. |
| Privacy request category, optional description, user ID, state and timestamps | Handle private account requests and grievances | `privacy_requests`; owner can see own requests; admin can see the queue. Descriptions are limited to 2,000 characters. |
| Analytics preference category/status, policy version, timestamp, user ID when signed in | Remember optional browser preference | Browser `localStorage` key `cookie_consent`; signed-in choices also appear in `consent_records`. No analytics currently execute. |
| Client IP and request time | In-process rate limiting at selected endpoints | Volatile rate-limit map only; not written to MongoDB or audit records. Deployment proxies may independently keep access logs. |
| Client IP, HTTP method, request path, protocol, response status, and timestamp | HTTP access diagnostics | The standard Uvicorn access logger records these fields to process output when enabled (the development command enables it). Request bodies, passwords, cookies, and authorization headers are not included in that access line. Production server/proxy logging and retention must be configured by the operator. |

MongoDB is used when configured and available. Development can use process memory, which is lost when the process exits; production startup refuses that fallback. MongoDB vendor/location depend on operator configuration. The application has no connected analytics, advertising, email, payment, or support provider.

## Model and outbound requests

The frontend requests the configured API. No analytics SDK, advertising pixel, external embed, remote image, remote script, or remote font is used by the frontend. Unsplash demonstration photos are bundled as local frontend assets; their source URLs and license reference are listed in `docs/ASSET_CREDITS.md`. Transformer files are loaded locally by default (`MODEL_LOCAL_FILES_ONLY=true`). A deployment must provision weights into the local cache; inference text is not sent to Hugging Face or another model API. Package installation/build tooling contacts package registries, but runtime moderation content is not sent to those registries.

## Browser storage

* `moderation_session`: signed authentication cookie, HttpOnly, SameSite Strict, path `/api/v1`, 120 minutes by default, Secure in production.
* `cookie_consent`: local storage preference only; it has no identifier and enables no analytics in this version.
* Legacy `token` local storage keys are removed on app initialization; current auth tokens are not available to JavaScript.

## Retention and deletion implemented

* Active account and owned posts/comments are retained while the account is active so account/feed/moderation features work. Users can immediately delete the account.
* Account deletion removes the user, their posts and comments, moderation logs tied to those items, consent records, and privacy requests. Audit rows are retained in anonymized form and content references are cleared.
* Audit rows older than `AUDIT_RETENTION_DAYS` (365 days by default) are purged at startup and daily.
* Resolved/declined privacy requests older than `RESOLVED_PRIVACY_REQUEST_RETENTION_DAYS` (365 days by default) are purged at startup and daily. Open requests are retained until resolved.
* Browser preference storage remains on that browser until cleared there; account consent rows are removed during account deletion.
* Rate-limit state is in process memory and is not written to persistent storage.

If operators override the retention settings, they must update the in-app notice and assess the changed purpose/period. The application does not currently implement automatic expiry of active accounts or active user content.

## Access controls and security boundary

The standard Uvicorn access logger records client IP, method, path, protocol, and response status to process output when enabled. Production server/proxy logging and retention are controlled by deployment operators and cannot be verified from this source; operators should restrict and set retention for those logs.

Admin endpoints use a backend dependency that loads the account from the database and checks its current `ADMIN` role. Client-side route hiding is supplementary. Browser sessions use an HttpOnly signed token cookie, SameSite Strict, an origin check for cookie-authenticated mutation requests, a configured CORS allow-list, and PBKDF2 password hashes. Production requires MongoDB and a unique JWT secret. Rate limiting is in-process and per worker, not a distributed gateway control. HTTPS, encrypted database disks/backups, access to database backups, and hosting logs are controlled by deployment operators and cannot be verified from this source.

## Consent and data requests

Necessary session processing supports account access. Optional analytics/tracking is absent. User text is not used for model training, so there is no model-training opt-in. Signed-in users can download an account-scoped export, correct username/email after password confirmation, change the browser preference, submit a private request or grievance, and delete their account. Request history is visible to that account and authorized administrators only.

## India DPDP implementation status

The app includes a data notice, account-scoped access/correction/erasure controls, privacy request handling, optional browser preference controls, minimization, security controls, and retention/deletion logic. It is designed with privacy and applicable data-protection requirements in mind; it is not legally certified and does not claim that the operator satisfies all statutory duties.

As of 27 September 2026, the published commencement notification phases the DPDP Act: certain provisions commenced on publication; provisions under section 6(9) and section 27(1)(d) are scheduled one year after publication (November 2026); many substantive duties, including sections 3–17, are scheduled eighteen months after publication (May 2027). These are commencement dates in the notification, not a legal applicability conclusion for this project. Verify later amendments, applicability, notice/contact requirements, and obligations with the deployment operator/counsel before launch. See the [official commencement notification](https://www.meity.gov.in/static/uploads/2025/11/c56ceae6c383460ca69577428d36828b.pdf), the [Digital Personal Data Protection Act](https://www.indiacode.nic.in/bitstream/123456789/22037/2/a2023-22.pdf), and MeitY's [DPDP Rules page](https://www.meity.gov.in/documents/act-and-policies/digital-personal-data-protection-rules-2025-gDOxUjMtQWa?pageTitle=Digital-Personal-Data-Protection-Rules-2025%3B).
