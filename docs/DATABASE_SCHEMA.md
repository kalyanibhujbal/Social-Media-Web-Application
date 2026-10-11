# Database Collections

The production backend uses MongoDB. Development can use in-memory collections. Mongo indexes created by `DatabaseManager.connect()` are listed below. Collection fields may vary across older records; response models omit internal Mongo `_id` fields.

## `users`

Stores `id` (application UUID), `username`, `email`, salted PBKDF2 `password_hash`, backend-assigned `role`, `terms_accepted`, `is_active`, and `created_at`. User registration does not create admins or demo users. Unique indexes protect email and username.

## `posts` and `comments`

Each record stores an application UUID, author UUID and username, text content, language heuristic, moderation recommendation/status/explanation, embedded prediction (label, scores, confidence, model name/version, inference timestamp and keyword highlights), and creation time. Comments also include `post_id`. Indexes support account history queries by author and creation time. Only approved items are returned by public feed endpoints.

## `moderation_logs`

Stores content UUID/type, AI label, confidence, moderation recommendation/action, timestamp, and optional minimal manual-review event (reviewer UUID/role/action/time). It does not store review notes. A sparse unique index protects `content_id` where present.

## `audit_logs`

Stores audit UUID, actor reference/role, event type, optional resource reference, a short generic detail, and timestamp. Application cleanup purges rows beyond configured retention. Account deletion anonymizes the actor reference and clears owned content references.

## `consent_records`

Stores one current preference per signed-in account and consent type (`analytics_cookies`): status, privacy policy version, and timestamp. User-generated text and IP addresses are not stored with consent.

## `privacy_requests`

Stores request UUID, account UUID, request type, optional user description, `OPEN`/resolved/declined status, optional response, and submission/resolution timestamps. Owners see their own requests; backend-authorized administrators access the queue. Resolved records are purged after configured retention.

## Indexes and retention

Connection setup creates unique `users.email`, `users.username`; author/date indexes for posts and comments; a sparse unique `moderation_logs.content_id`; and timestamp/user indexes for audit, consent, and privacy requests. The application retention loop purges old audit events and resolved privacy requests daily. See [Privacy Data Map](PRIVACY_DATA_MAP.md) for the active retention defaults and other storage details.
