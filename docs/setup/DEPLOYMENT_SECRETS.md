# Deployment secrets & environment variables

Zenith reads configuration from **`backend/.env`** locally and from the host dashboard in production (Render, Vercel). **Never commit** real secrets to Git.

## Required for local API boot

| Variable | Purpose |
|----------|---------|
| `MONGO_CONNECTION_STRING` | MongoDB URI |
| `MONGO_DB_NAME` | Database name |
| `SECRET_KEY` | JWT signing (long random string) |
| `AWS_*` / `GCP_*` / `Azure_*` | Platform cloud defaults (see `backend/.env.example`) |
| `CELERY_BROKER_URL` | Redis URL for background tasks |

Copy `backend/.env.example` → `backend/.env` and fill placeholders.

## Production (Render backend)

Set in **Render → Service → Environment**:

- All variables from `.env.example` that the API uses
- `ENVIRONMENT=production`
- `FRONTEND_URL=https://your-frontend-domain` (exact origin, no trailing slash)
- `CORS_ALLOWED_ORIGINS` — comma-separated extra origins if needed (preview URLs, custom domains)
- `PUBLIC_API_URL=https://your-api.onrender.com`
- Optional single-tenant owner plan (keeps Settings/Billing/BYOC in sync on production):
  - `PLATFORM_OWNER_USERNAMES` — exact Zenith username(s), comma-separated (e.g. `Tanjore developer`)
  - `PLATFORM_OWNER_PLAN` — `enterprise` (default), `pro`, `basic`, or `free`
- Optional: `SENTRY_DSN`, `GOOGLE_OAUTH_*`

## Production (Vercel frontend)

Set in **Vercel → Project → Environment Variables**:

- `VITE_API_URL` — backend base URL **without** `/api` (e.g. `https://zenith-backend-707i.onrender.com`)
- `VITE_SITE_URL` — public frontend URL for canonical/OG tags (production: `https://rajverse.me`). Defaults in `index.html`, `robots.txt`, and `sitemap.xml` match this domain.
- Optional: `VITE_SENTRY_DSN`

## CORS

The API uses `DynamicCORSMiddleware` in `app/main.py`:

- **Production** (`ENVIRONMENT=production`): localhost is **not** allowed; use `FRONTEND_URL`, `CORS_ALLOWED_ORIGINS`, static domains, and `zenith-frontend-*.vercel.app` patterns.
- **Development**: localhost + broader Vercel preview patterns.

After changing domains, update `FRONTEND_URL` and redeploy the backend.

## Phase 20.5 CI secrets

| Secret | Purpose |
|--------|---------|
| `STAGE_API_URL` | Post-deploy smoke in `deploy-stage.yml` (e.g. `https://zenith-backend-707i.onrender.com`) |
| `CODECOV_TOKEN` | Optional coverage upload |

## Render free tier — keep backend awake

Render spins down free web services after about **15 minutes** with no HTTP traffic. Zenith uses two layers:

| Layer | What | When it runs |
|-------|------|----------------|
| **GitHub Actions** | `.github/workflows/render-keep-alive.yml` pings `/health` every 5 minutes | Only on the repo **default branch** (check GitHub → Settings → General) |
| **Frontend** | `renderKeepAlive.js` pings `/health` every 10 minutes while a production tab is open | After Vercel deploy |

Optional GitHub secret: `RENDER_API_URL` (backend origin, no `/api`). If unset, the workflow uses `https://zenith-backend-707i.onrender.com`.

**Actions:** merge `render-keep-alive.yml` into your default branch, enable Actions, run **Render keep-alive** once via *workflow_dispatch* to verify. Paid Render plans do not sleep — no heartbeat needed.

## Optional observability (Phase 19)

| Variable | Required? | Notes |
|----------|-----------|--------|
| `SENTRY_DSN` | No | Backend error tracking; leave empty to disable |
| `SENTRY_TRACES_SAMPLE_RATE` | No | Default `0.1` |
| `VITE_SENTRY_DSN` | No | Frontend errors; leave empty to disable |

Create a free project at [sentry.io](https://sentry.io) — you get a DSN string, not a cloud API key.

## GCP / AWS / Azure keys

- **Not required for Phase 19** (ops/docs/Sentry/CORS).
- Required when you use **real** storage, VMs, or cost APIs — see `CLOUD_CREDENTIAL_SETUP_GUIDE.md`.
- Users can connect **BYOC** in Settings without editing server `.env`.

## Rotation

See `CREDENTIAL_ROTATION.md`.
