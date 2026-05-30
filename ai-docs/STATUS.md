# STATUS.md — Live Project Snapshot

**Last Updated:** 2026-05-30 (Phase 20.5 roadmap added)

---

## Identity

| Field | Value |
|-------|--------|
| Project | CloudResourceOptimizationPlatform (**Zenith**) |
| Phase | **20.5** — CI/CD enterprise gates — **in progress** (code landed; apply branch protection) |
| Last major | Playwright CI fixes, Render keep-alive, Boto3/Terraform parity |
| Prior push | `stage` (see git log) |

---

## 🔴 Active Task

**Phase 20.5** — CI/CD enterprise gates (before Phase 21). Checklist: `PROGRESS.md`, map: `docs/testing/PHASE_20_5_CI_GATES.md`.

---

## Phase 19 — COMPLETE (2026-05-29)

CORS hardening, deployment/rotation/cost docs, optional Sentry, uptime workflow, admin audit export UI, platform status GCP flag, Vitest in CI. **No cloud API keys required** for this phase.

---

## Roadmap pointer (Phases 20–27)

| Phase | Focus |
|-------|--------|
| **20** | Tests, CI Mongo, CD, Playwright ✅ |
| **20.5** | CI gates, security scans, gated deploy 🔴 |
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
