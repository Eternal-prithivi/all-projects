# STATUS.md — Live Project Snapshot

**Last Updated:** 2026-05-29

---

## Identity

| Field | Value |
|-------|--------|
| Project | CloudResourceOptimizationPlatform (**Zenith**) |
| Phase | **18** — Enterprise public pages & trust |
| Last major | Phase 18a–18c pages + platform status API |

---

## 🔴 Active Task

**None** — Phase 18a–18c **COMPLETE** (2026-05-29). Phase 18d partially done (`/docs` hub).

| Deferred (18d) | `/dashboard/notifications`, org/team, SSO |
| Other deferred | CloudFormation stack, bucket migration UI |

---

## Phase 18 roadmap

| Phase | Priority | Status |
|-------|----------|--------|
| **18a** | High — trust & cookies | ✅ |
| **18b** | High — status, verify-email, maintenance gate | ✅ |
| **18c** | Medium — public pricing, billing returns, session-expired | ✅ |
| **18d** | Low — docs hub ✅; notifications, org, SSO | Planned |

---

## Health

| Check | Status |
|-------|--------|
| Frontend build | ✅ pass (2026-05-29) |
| Backend pytest | Run with Mongo: `cd backend && pytest -q` |

---

## Critical Warnings

1. `backend/.env` — never commit
2. Product name **Zenith** — do not rebrand without asking
3. Email verify tokens: set `email_verify_token` on user at registration when enabling `require_email_verification`
