# Database Collections

The production backend uses MongoDB. Development can use in-memory collections. Mongo indexes created by `DatabaseManager.connect()` are listed below. Collection fields may vary across older records; response models omit internal Mongo `_id` fields.

## `users`

Stores `id` (application UUID), `username`, `email`, salted PBKDF2 `password_hash`, backend-assigned `role`, `terms_accepted`, `is_active`, `is_private`, and `created_at`. `is_private` defaults to false for new accounts; missing values in legacy records are treated as public. User registration does not create admins or demo users. Unique indexes protect email and username.

## `posts` and `comments`

Each post stores an application UUID, author UUID and username, text content, language heuristic, moderation recommendation/status/explanation, optional embedded prediction (label, scores, confidence, model name/version, inference timestamp and keyword highlights), creation time, `content_type` (`POST`, `EVENT`, or `ARTICLE`), and optional event/article details and media metadata. Media files are stored under `MEDIA_ROOT` with generated names; only their filename, MIME type, media kind, size, and API URL are stored in the post record. Images are limited to 10 MB each and videos to 100 MB each. Media-only posts have no AI prediction. Comments also include `post_id` and optional `parent_comment_id` for threaded replies. Follows include `follower_id`, `following_id`, and `status` (`PENDING`, `ACCEPTED`, or `REJECTED`); records without a status are treated as accepted for compatibility. Indexes support account history queries by author and creation time. Feed/profile/media APIs enforce private-account visibility server-side.

## `moderation_logs`

Stores content UUID/type, AI label, confidence, moderation recommendation/action, timestamp, and optional minimal manual-review event (reviewer UUID/role/action/time). It does not store review notes. A sparse unique index protects `content_id` where present.

## `notifications`

Stores notification UUID, recipient and optional actor IDs, kind, section, optional resource type/ID, read status, and timestamp. Notifications are recipient-scoped; post previews are hydrated from currently authorized posts when read through the API rather than copied into the notification document. Message notifications reference a conversation and are synchronized with the corresponding message read state.

## `audit_logs`

Stores audit UUID, actor reference/role, event type, optional resource reference, a short generic detail, and timestamp. Application cleanup purges rows beyond configured retention. Account deletion anonymizes the actor reference and clears owned content references.

## `consent_records`

Stores one current preference per signed-in account and consent type (`analytics_cookies`): status, privacy policy version, and timestamp. User-generated text and IP addresses are not stored with consent.

## `privacy_requests`

Stores request UUID, account UUID, request type, optional user description, `OPEN`/resolved/declined status, optional response, and submission/resolution timestamps. Owners see their own requests; backend-authorized administrators access the queue. Resolved records are purged after configured retention.

## Indexes and retention

Connection setup creates unique `users.email`, `users.username`; author/date indexes for posts and comments; a sparse unique `moderation_logs.content_id`; recipient/date, recipient/read-state, and recipient/section/read-state indexes for notifications; deduplication indexes for network post/article/event notifications; and timestamp/user indexes for audit, consent, and privacy requests. The application retention loop purges old audit events and resolved privacy requests daily. See [Privacy Data Map](PRIVACY_DATA_MAP.md) for the active retention defaults and other storage details.
