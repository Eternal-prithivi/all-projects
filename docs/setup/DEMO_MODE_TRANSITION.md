# Demo mode vs live mode — quick operator guide

## One switch (billing charts)

| Variable | Demo (default for students) | Live billing APIs |
|----------|----------------------------|-------------------|
| `DEMO_MODE` | `true` | `false` |

**Does not block:** file uploads, provision apply, VM flows.

**Does mock:** cost pages, budgets, billing totals, forecast history, export, dashboard refresh-costs.

**Does skip (Celery):** budget alerts, anomaly scan, nightly storage tiering, scheduled provision drift.

## Where to change

| Environment | Where |
|-------------|--------|
| **Local** | `backend/.env` → restart `uvicorn` |
| **Render** | Dashboard → zenith-backend → **Environment** → redeploy/restart |
| **Vercel** | No `DEMO_MODE` — only `VITE_API_URL` pointing at Render |

## Optional (not `DEMO_MODE`)

| Variable | Demo-friendly | Live GCP VM metrics |
|----------|---------------|---------------------|
| `USE_REAL_METRICS` | `false` | `true` + GCP key path |
| `GCP_SERVICE_ACCOUNT_JSON_PATH` | empty | path to JSON |
| `REAL_TIME_MODE` | `false` | `true` (more API calls) |

## Verify

`GET /api/platform/status` → `"demo_mode": true`, `"billing_data": "demo_mock"`.

Cost API responses include `"demo_mode": true`.
