# STATUS.md — Live Project Snapshot

**Last Updated:** 2026-05-29

---

## Identity

| Field | Value |
|-------|--------|
| Project | CloudResourceOptimizationPlatform (**Zenith**) |
| Phase | **17** |
| Last major | AWS BYOC wizard, auto-create buckets, secure dual-write |

---

## 🔴 Active Task

**None** — push local Phase 17 bundle to `stage` when ready.

| Deferred | CloudFormation stack, bucket migration UI |

---

## Health

| Check | Status |
|-------|--------|
| Backend pytest | `cd backend && pytest -q` |
| Frontend build | `cd frontend && npm run build` |

---

## Critical Warnings

1. `backend/.env` — never commit
2. Product name **Zenith** — do not rebrand without asking
