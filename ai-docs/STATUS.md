# STATUS.md — Live Project Snapshot

**Last Updated:** 2026-05-30

---

## Identity

| Field | Value |
|-------|--------|
| Project | CloudResourceOptimizationPlatform (**Zenith**) |
| Phase | **19** — Isolated ops & hygiene — **COMPLETE** (code + docs) |
| Last major | Phase 19: CORS, secrets docs, Sentry optional, vitest, platform status |
| Prior push | `stage` @ `153a519` |

---

## 🔴 Active Task

**None** — Provision engine toggle (DEC-022) complete 2026-05-30. Next: Phase 20.1 pytest expansion when ready.

---

## Phase 19 — COMPLETE (2026-05-29)

CORS hardening, deployment/rotation/cost docs, optional Sentry, uptime workflow, admin audit export UI, platform status GCP flag, Vitest in CI. **No cloud API keys required** for this phase.

---

## Roadmap pointer (Phases 20–27)

| Phase | Focus |
|-------|--------|
| **20** | Tests, CI Mongo, CD, Playwright |
| **21** | Logging, runbooks |
| **22–27** | Org tenancy → scale → compliance → cloud parity |

Checklist: **`PROGRESS.md`**

---

## Phase 18 — COMPLETE

Trust, pricing, team/org, SSO, notifications, email verify.

---

## Health

| Check | Status |
|-------|--------|
| Frontend build | Run after `npm ci` |
| Frontend test | `npm run test` (vitest) |
| Backend pytest | `cd backend && pytest -q` |
| CI | pytest, lint, **test**, build, terraform validate, uptime (optional secret) |

---

## Critical Warnings

1. `backend/.env` — never commit
2. **Phase 19 optional only:** `SENTRY_DSN`, `VITE_SENTRY_DSN`, `UPTIME_API_URL` (GitHub secret)
3. **GCP/AWS not required** for Phase 19 — connect cloud when resuming VM/storage (see `CLOUD_COST_GUARDRAILS.md`)
