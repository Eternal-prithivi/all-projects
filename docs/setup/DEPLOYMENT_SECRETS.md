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
- Optional: `SENTRY_DSN`, `GOOGLE_OAUTH_*`

## Production (Vercel frontend)

Set in **Vercel → Project → Environment Variables**:

- `VITE_API_URL` — backend base URL **without** `/api` (e.g. `https://zenith-backend-707i.onrender.com`)
- Optional: `VITE_SENTRY_DSN`

## CORS

The API uses `DynamicCORSMiddleware` in `app/main.py`:

- **Production** (`ENVIRONMENT=production`): localhost is **not** allowed; use `FRONTEND_URL`, `CORS_ALLOWED_ORIGINS`, static domains, and `zenith-frontend-*.vercel.app` patterns.
- **Development**: localhost + broader Vercel preview patterns.

After changing domains, update `FRONTEND_URL` and redeploy the backend.

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
