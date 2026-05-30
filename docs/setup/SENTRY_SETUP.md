# Sentry error tracking (dashboard + API)

## What Sentry does

- Captures **JavaScript errors** in the browser (dashboard crashes, failed API calls in UI code, unhandled promise rejections).
- Captures **Python/FastAPI errors** on the backend when `SENTRY_DSN` is set.
- Shows stack traces, browser, route, and (optional) session replay when an error occurs.

Sentry does **not** automatically fix code. It **reports** issues; you (or Cursor) fix them from the report.

## What you need (one-time)

1. Create a free project at [sentry.io](https://sentry.io) → **React** for frontend, **FastAPI** for backend (or one project with two DSNs).
2. Copy the **DSN** (looks like `https://xxx@o123.ingest.sentry.io/456`).

### Local / Vercel (frontend)

`frontend/.env.local`:

```bash
VITE_SENTRY_DSN=https://your-key@o123.ingest.sentry.io/456
```

Restart `npm run dev` after adding.

### Verify (frontend)

Trigger any real error (or temporarily `throw new Error('test')` in dev), then open [sentry.io](https://sentry.io) → **Issues**. Events usually appear within ~1 minute.

### Render (backend)

```bash
SENTRY_DSN=https://your-backend-dsn@o123.ingest.sentry.io/789
```

Redeploy the API.

## What is covered in Zenith

| Layer | Coverage |
|-------|----------|
| React render errors | `ErrorBoundary` → `captureException` |
| Uncaught JS / promises | Sentry `init` (automatic) |
| Page performance (light) | Browser tracing sample 10% |
| Errors with context | Session replay on errors only (masked text) |
| API 500s | Backend `SENTRY_DSN` in `app/main.py` |

## Using reports with Cursor

1. Open Sentry → **Issues** → click an issue.
2. Copy **stack trace** + **breadcrumbs** (or use “Copy as Markdown”).
3. Paste into Cursor with: route you were on, what you clicked, and the Sentry text.

Example prompt:

> Sentry issue: TypeError Cannot read properties of undefined (reading 'map')  
> Route: /dashboard/storage  
> Stack: [paste]  
> Fix the root cause in our codebase.

## Privacy

- `sendDefaultPii: false` on the frontend.
- Replay masks text and blocks media. Do not put secrets in UI fields you need unmasked.

## Disable

Remove `VITE_SENTRY_DSN` / `SENTRY_DSN` or leave empty — Sentry code paths no-op.
