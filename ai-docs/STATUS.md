# STATUS.md — Live Project Snapshot

**Last Updated:** 2026-05-29

---

## Identity

| Field | Value |
|-------|--------|
| Project | CloudResourceOptimizationPlatform (**Zenith**) |
| Phase | **16** complete |
| Last major complete | BYOC credential routing across storage, security, cost, VM GCP |

---

## 🔴 Active Task

**None** — Phase 16 complete (2026-05-29).

| Next | Optional: Azure BYOC cost SP fields; per-user Celery anomaly |

---

## Health

| Check | Status |
|-------|--------|
| Backend pytest | Run after pull (`cd backend && pytest -q`) |
| Frontend lint | ✅ 0 errors (prior) |
| Frontend build | ✅ Passes (prior) |

---

## Critical Warnings

1. `backend/.env` — never commit
2. Product name **Zenith** — do not rebrand without asking
3. GCP BYOC for VMs requires Compute API roles on the service account
