# api.rajverse.me — first-party API subdomain

Zenith uses **api.rajverse.me** for httpOnly cookie auth so the browser treats API cookies as first-party (shared with rajverse.me via `Domain=.rajverse.me`).

## DNS (manual)

1. In your DNS provider (where rajverse.me is hosted), add:
   - **Type:** CNAME
   - **Name:** `api`
   - **Target:** your Render service hostname (e.g. `zenith-backend-xxxx.onrender.com`)
2. In **Render → zenith-backend → Settings → Custom Domains**, add `api.rajverse.me` and wait for TLS.

## Environment

| Service | Variable | Value |
|---------|----------|--------|
| Render backend | `BACKEND_URL` | `https://api.rajverse.me` |
| Render backend | `PUBLIC_API_URL` | `https://api.rajverse.me` |
| Vercel frontend | `VITE_API_URL` | `https://api.rajverse.me` |
| Render backend | `FRONTEND_URL` | `https://rajverse.me` |
| Optional | `AUTH_COOKIE_DOMAIN` | `.rajverse.me` (auto when BACKEND_URL contains rajverse.me) |

## Rollout

1. Deploy backend with hybrid auth (cookies + Bearer fallback).
2. Point DNS and update env vars.
3. Deploy frontend with `withCredentials` and no localStorage tokens.
4. Set `AUTH_LEGACY_TOKEN_BODY=false` in production when migration is complete.
