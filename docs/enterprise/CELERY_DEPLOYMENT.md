# Celery worker + Beat (staging / production)

Zenith background jobs (storage lifecycle, cost anomalies, ML retrain, VM adaptive agent) require **Celery worker** and **Beat** in addition to the FastAPI web service.

**Current choice (2026):** Run Celery on **your Mac** for now; defer Render `zenith-celery` (~$7/month). See [Later Developments.md](../../Later%20Developments.md).

## Local

```bash
cd backend
source ../venv/bin/activate
# Terminal 1 — API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Terminal 2 — worker + beat
celery -A app.celery_worker worker --beat --loglevel=info
```

Or use `scripts/start-celery.sh`.

## Environment

Set in `backend/.env` (and Render dashboard for both web + worker):

- `CELERY_BROKER_URL` — Redis or CloudAMQP URL (required)
- `MONGO_CONNECTION_STRING` — same as API

## Render

[`render.yaml`](../../render.yaml) defines three services:

1. **zenith-api** — slim web image (`Dockerfile.api`), no Terraform CLI; `ZENITH_SERVICE_ROLE=api`
2. **zenith-celery** — general background jobs + Beat (`Dockerfile.api`)
3. **zenith-provision** — Terraform worker on `provision` queue (`Dockerfile.provision`)

**Enable on Render (manual):**

- [ ] Create all three services from `render.yaml` (or add `zenith-provision` if upgrading)
- [ ] Copy **all** env vars from `zenith-api` to `zenith-celery` and `zenith-provision` (Mongo, `CELERY_BROKER_URL`, cloud keys, Razorpay, etc.)
- [ ] Set `BACKEND_URL` / `PUBLIC_API_URL` to `https://api.rajverse.me` on API service
- [ ] Add custom domain `api.rajverse.me` — see [API_SUBDOMAIN.md](../setup/API_SUBDOMAIN.md)
- [ ] Confirm worker logs show Beat schedule and `provision.terraform_apply` registered on `zenith-provision`

## Verify

- `GET /health/ready` — `celery.broker.reachable`
- Admin → **System** — Celery card (broker, workers, beat task list)

## Scheduled tasks (UTC)

| Task | Schedule |
|------|----------|
| Storage lifecycle | 02:00 daily |
| Cost anomalies | 01:00 daily |
| ML feedback eval | 03:00 daily |
| ML retrain | Sun 03:30 |
| RL policy update | 03:15 daily |
| Federated stats | Sun 04:00 |
| VM metrics | Every 5 min |
| VM adaptive agent | Every 15 min |
| Provision drift | 06:00 daily |
