# API Contract Summary

Base path: `/api/v1`. API responses use `Cache-Control: no-store`. Browser auth uses the `moderation_session` HttpOnly cookie; bearer tokens are supported for API clients. User and admin authorization is enforced in FastAPI dependencies, not only in the frontend.

## Authentication — `/auth`

* `POST /register`: create a USER account; `terms_accepted` must be true. No client-supplied role is accepted.
* `POST /login`, `POST /logout`, `GET /me`.
* `PATCH /profile`: update profile fields and `is_private`; requires the current password and rejects duplicate usernames/emails.

## Posts, media, events, articles, comments, dashboards

* `POST /posts`: authenticated text post creation and moderation.
* `POST /posts/media`: multipart media post (`caption`, `files`); accepts up to five combined JPG/JPEG, PNG, WEBP, MP4, and WEBM files, including mixed image/video posts.
* `POST /posts/events`: multipart event creation (`title`, `description`, `event_date`, `event_time`, `location`, optional `cover_image`).
* `POST /posts/articles`: multipart article creation (`title`, `content`, optional `cover_image`); `PUT /posts/{post_id}/article` edits an article owned by the current user.
* `GET /posts/media/{filename}` serves media only when the related post is approved and visible to the viewer. `DELETE /posts/{post_id}` deletes the current user's post and associated media; `DELETE /posts/{post_id}/media/{filename}` deletes only the owner's media.
* `GET /posts`: approved posts from public accounts plus the current user's own posts and posts from private accounts they are approved to follow. Supplying `status_filter` other than `APPROVED` returns 400.
* `GET /posts/explore`: approved posts from public accounts only; private-account posts are excluded for every viewer.
* `GET /posts/user/me`, `GET /comments/user/me`, `GET /dashboard/me`: authenticated and scoped to the current account.
* `POST /posts/{post_id}/appeal`: authenticated owner only; request body `{ "reason": "..." }`, so the reason is not placed in the URL.
* `GET /users/{user_id}` returns restricted profile details for private accounts only to the owner and approved followers. `GET /users/{user_id}/posts` returns 403 to other viewers until approval.
* `POST /comments`: authenticated comment creation; optional `parent_comment_id` creates a reply to an approved comment on a viewable post. `GET /comments/post/{post_id}` returns approved comments only when the viewer can access the post.
* `PUT /follows/{user_id}` immediately follows public accounts and creates a pending request for private accounts. `GET /follows/requests` lists incoming/outgoing pending requests. `POST /follows/requests/{follower_id}/accept|reject` lets only the followed account respond.
* `POST /moderation/analyze`: rate-limited sandbox analysis; text is not persisted by the endpoint.

Moderation is text-only: captions, event titles/descriptions, and article titles/body text are moderated; long article text is processed in bounded text chunks through the existing classifier, with the highest-severity chunk driving the result. Uploaded image and video bytes are stored and served separately and are never passed to the AI model. Media-only posts have no AI prediction.

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
