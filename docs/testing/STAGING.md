# Staging environment (Phase 20.14)

Use a **non-production** environment to validate merges before `main`.

## Recommended layout

| Component | Suggestion |
|-----------|------------|
| Backend | Second Render service (e.g. `zenith-api-stage`) or preview with `stage` branch deploy |
| Frontend | Vercel preview for `stage` branch or dedicated staging project |
| Database | Separate MongoDB Atlas cluster or database name (not `CloudResourceOptimizationDB` prod) |
| Secrets | Staging-only keys in GitHub Environment `staging` |

## Environment variables

Copy `backend/.env.example` and `frontend/.env.example` to staging-specific values:

- `MONGO_CONNECTION_STRING` → staging cluster
- `MONGO_DB_NAME` → e.g. `zenith_stage`
- `FRONTEND_URL` / `BACKEND_URL` → staging URLs
- `ENVIRONMENT=staging`
- Use test/sandbox payment keys (Razorpay test mode)

## Deploy

- **Automatic:** push to `stage` triggers `.github/workflows/deploy-stage.yml` when `RENDER_DEPLOY_HOOK` and Vercel secrets are configured.
- **Manual:** Render dashboard deploy + Vercel promote preview.

## Smoke checklist after deploy

1. `GET /api/platform/status` returns 200.
2. Register/login on staging frontend.
3. Run Playwright against staging URL (set `PLAYWRIGHT_BASE_URL` and `PLAYWRIGHT_API_URL`).

## Do not

- Point staging at production MongoDB or production S3 buckets.
- Reuse production admin passwords in shared docs.
