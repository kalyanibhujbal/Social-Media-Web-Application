# OpenVibe frontend

React 19 + Vite application for the OpenVibe professional social-network prototype. The interface uses the existing FastAPI API contract for authentication, text posts, comments, moderation, account data, privacy requests, and administrator review.

## Run locally

From this directory:

```sh
npm install
npm run dev
```

Set `VITE_API_BASE_URL` in `.env` only when the API is not available at `http://localhost:8000/api/v1`. The browser authenticates with the backend's HttpOnly session cookie. Do not put secrets in frontend variables.

## Available interactions

- Feed search filters approved posts already returned by the public feed endpoint.
- Text posts and comments are sent to the existing moderation pipeline.
- The moderation sandbox calls the non-persisting analysis endpoint.
- The profile, user dashboard, and privacy controls read the signed-in account's backend data.
- Administrator pages use backend-protected endpoints.
- Network, notifications, and messaging are preview surfaces because this backend does not provide those APIs. Their actions are not simulated.
- Image assets are bundled locally; sources are listed in [`ASSET_CREDITS.md`](../docs/ASSET_CREDITS.md).

Build with `npm run build`. The production frontend is served from `dist/`.
