# API Contract Summary

Base path: `/api/v1`. API responses use `Cache-Control: no-store`. Browser auth uses the `moderation_session` HttpOnly cookie; bearer tokens are supported for API clients. User and admin authorization is enforced in FastAPI dependencies, not only in the frontend.

## Authentication — `/auth`

* `POST /register`: create a USER account; `terms_accepted` must be true. No client-supplied role is accepted.
* `POST /login`, `POST /logout`, `GET /me`.
* `PATCH /profile`: username/email correction; requires the current password and rejects duplicate values.

## Posts, comments, dashboards

* `POST /posts`: authenticated post creation and moderation.
* `GET /posts`: public approved posts only. Supplying `status_filter` other than `APPROVED` returns 400; use the own-account dashboard for private content states.
* `GET /posts/user/me`, `GET /comments/user/me`, `GET /dashboard/me`: authenticated and scoped to the current account.
* `POST /posts/{post_id}/appeal`: authenticated owner only; request body `{ "reason": "..." }`, so the reason is not placed in the URL.
* `POST /comments`: authenticated comment creation. `GET /comments/post/{post_id}` returns approved comments only.
* `POST /moderation/analyze`: rate-limited sandbox analysis; text is not persisted by the endpoint.

## Privacy — `/privacy`

* `GET /contact`: only configured public contact fields; unfilled placeholders are omitted.
* `POST /consent`: authenticated optional analytics-preference record. No analytics run in this version; anonymous browser preferences remain in local storage.
* `GET /export-data`: authenticated, account-scoped export of profile, own posts/comments, moderation records, consent history and privacy request history.
* `POST /requests`, `GET /requests/me`: submit/read the current account's privacy request queue.
* `POST /delete-account`: requires `{ "confirm_deletion": true }`; deletes account and associated content/records and anonymizes retained audit references.

## Administration — `/admin`

Every route below requires the current database account to have role `ADMIN`.

* `GET /queue`, `GET /content/{id}?content_type=post|comment`, `POST /review/{id}?content_type=...`.
* Review actions: approve, reject/block, flag, mark reviewed. Non-marking moderation decisions require `confirm_action: true`.
* `GET /analytics`, `GET /moderation-history`, `GET /audit-logs`, `GET /users`, `GET /report`.
* `GET /privacy-requests`, `PATCH /privacy-requests/{id}`; status update requires `RESOLVED` or `DECLINED` and an outcome message for the requester.

Summaries and reports read persisted content/audit records. Evaluation values are returned only when the evaluation file includes dataset source/hash, metrics, and confusion-matrix provenance; otherwise the API returns `NOT_AVAILABLE`. Empty moderation collections produce zero database counts and the UI shows “No moderation data available yet.”
