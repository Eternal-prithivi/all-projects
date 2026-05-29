# PROGRESS.md — Task Tracker

> **Startup:** read `STATUS.md` only (not this file unless updating active task).
> Last Updated: 2026-05-29

---

## 🛑 STANDING ANTI-TASKS

- Do NOT refactor `SecurityPage.jsx` to use `api.js`
- Do NOT delete stubs in `backend/app/aws/`, `providers/`, `queue/`, `errors/`
- Do NOT run `npm audit fix --force`
- Do NOT change **Zenith** / **ZenithApp** branding
- Do NOT use Redux/Zustand or paid services
- Do NOT commit `backend/.env`

---

## 🔴 Active Task

**None** — AWS Terraform integration feasibility plan **COMPLETE** (2026-05-29). See `AWS_TERRAFORM_INTEGRATION_PLAN.md` and `PROGRESS_HISTORY.md`.

---

## 🗺️ Phase Summary

| Phase | Status | Notes |
|-------|--------|-------|
| 1–3 | ✅ | UI polish, BYOC, Mission Control dashboard, settings |
| 4 | 🔲 partial | Storage sync ✅; cost/VM/admin items remain |
| 5–10 | ✅ | ML foundation → hardening, demo runbook |
| 11–11b | ✅ | Terraform provision, OPA, drift, RBAC, audit |
| **12** | **✅** | SSE-S3 + browser CSE + auto SSE + sessions + benchmarks |
| **13** | **✅** | Enterprise dashboard UI/UX passes 0–5 |
| **14** | **✅ plan** | AWS Terraform adopt/skip matrix + roadmap |
| **14b+** | 🔲 | Implementation waves per plan (user approval) |

### Phase 14 checklist

- [x] Inventory both repos
- [x] Gap analysis + adopt/skip matrix
- [x] Recommendation + phased roadmap (`AWS_TERRAFORM_INTEGRATION_PLAN.md`)
- [ ] P0 implementation (tests, BYOC drift) — **next session**

---

## 🔍 Open Issues

| Issue | Status |
|-------|--------|
| Provision path has no dedicated pytest suite | Open — P0 in plan |
| Scheduled drift without BYOC creds | Open — P0 in plan |
| Sidebar dead links (`/dashboard/costs`, `/dashboard/compute`) | Open |

---

## Report parity

High-level report vs code matrix lives in `PROGRESS_HISTORY.md`. Phase 5 contracts: `DECISIONS.md` + `backend/app/ml/acceptance.py`.
