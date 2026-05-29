# STATUS.md — Live Project Snapshot

**Last Updated:** 2026-05-29

---

## Identity

| Field | Value |
|-------|--------|
| Project | CloudResourceOptimizationPlatform (**Zenith**) |
| Phase | **18** — Enterprise pages **COMPLETE** |
| Last major | 18d: notifications, team/org, SSO, email verify on register |

---

## 🔴 Active Task

**None**

| Deferred | CloudFormation stack, bucket migration UI |

---

## Phase 18 — COMPLETE

| Phase | Deliverables |
|-------|----------------|
| 18a–18c | Trust, status, pricing, billing returns |
| **18d** | `/dashboard/notifications`, `/dashboard/team`, `/invite/:token`, SSO, register email verify |

---

## Health

| Check | Status |
|-------|--------|
| Frontend build | ✅ pass (2026-05-29) |
| Backend pytest | `cd backend && pytest -q` (needs Mongo) |

---

## Critical Warnings

1. `backend/.env` — never commit
2. Google SSO: `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `PUBLIC_API_URL`
3. Enable Google SSO in Admin → Settings after OAuth env is set
