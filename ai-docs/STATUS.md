# STATUS.md — Live Project Snapshot

**Last Updated:** 2026-05-29

---

## Identity

| Field | Value |
|-------|--------|
| Project | CloudResourceOptimizationPlatform (**Zenith**) |
| Phase | **18** complete → **19–27** roadmap defined (not started) |
| Last major | Enterprise gap matrix → `PROGRESS.md` Phases 19–27 |
| Last product | Phase 18d: notifications, team/org, SSO, email verify |

---

## 🔴 Active Task

**None** — execute **Phase 19** when ready (start with **19.1**).

| Pick up | `PROGRESS.md` → Phase **19** (isolated ops first) |
|---------|---------------------------------------------------|

---

## Roadmap pointer (Phases 19–27)

| Phase | Focus | Start when |
|-------|--------|------------|
| **19** | Isolated ops & hygiene (CORS, Sentry, audit export, docs) | **Now** |
| **20** | Tests, CI Mongo, CD, Playwright | After 19.1–19.2 |
| **21** | Logging, runbooks, diagnostics | After 19.4 |
| **22** | Org `org_id` foundation | After 19–21 baseline |
| **23** | Org-scoped storage, VM, cost | **Requires 22** |
| **24** | SAML, SCIM, API scopes | **Requires 22** |
| **25** | Redis, WS scale, load tests | **Requires 20–21** |
| **26** | GDPR, SOC2-lite, org billing | **Requires 22–23** |
| **27** | CloudFormation UI, GCP billing wizard, deferred | GCP/AWS live |

Full checklist: **`PROGRESS.md`** (77 numbered items).

---

## Phase 18 — COMPLETE

| Phase | Deliverables |
|-------|----------------|
| 18a–18c | Trust, status, pricing, billing returns |
| **18d** | `/dashboard/notifications`, `/dashboard/team`, `/invite/:token`, SSO, register email verify |

---

## Deferred (rolled into Phase 27 unless noted)

| Item | Phase |
|------|-------|
| CloudFormation one-click UI | 27.1 |
| Bucket migration UI | 27.2 |
| Org-scoped BYOC / shared resources | 22–23 |
| Razorpay → `/billing/success` | 27.6 |

---

## Health

| Check | Status |
|-------|--------|
| Frontend build | ✅ pass (2026-05-29) |
| Backend pytest | `cd backend && pytest -q` (needs Mongo) |
| CI | ✅ `.github/workflows/ci.yml` (pytest, lint, build, terraform validate) |
| CD | ⬜ Phase **20.9–20.10** |

---

## Critical Warnings

1. `backend/.env` — never commit
2. Google SSO: `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `PUBLIC_API_URL`
3. Enable Google SSO in Admin → Settings after OAuth env is set
4. GCP new account: billing must be **active** before real VMs/storage (see Phase **19.10**)

---

## Tier B routing (unchanged)

| Task type | Read |
|-----------|------|
| UI | `DESIGN_SYSTEM.md`, `AI_CONTEXT_FRONTEND.md` |
| API | `AI_CONTEXT_BACKEND.md` |
| Architecture | `DECISIONS.md` |
| Enterprise checklist | **`PROGRESS.md` Phases 19–27** |
