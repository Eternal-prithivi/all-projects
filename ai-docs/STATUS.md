# STATUS.md — Live Project Snapshot (read every session)

> Protocol: `AI_MASTER.md` · History: `PROGRESS_HISTORY.md` · Rules: `AI_RULES.md`

**Last Updated:** 2026-05-29

---

## Identity

| Field | Value |
|-------|--------|
| Project | CloudResourceOptimizationPlatform (**Zenith**) |
| Phase | **14b** complete — next **14c** (audit/RBAC UI) |
| Last major complete | Provision P0: tests, BYOC scheduled drift, TF validate CI |
| Spec | `AWS_TERRAFORM_INTEGRATION_PLAN.md` |

---

## 🔴 Active Task

**None** — Phase 14b complete (2026-05-29).

| | |
|--|--|
| Resume | `SCRATCHPAD.md` (IDLE) |
| Next | Phase 14c — provision audit/RBAC UI + drift panel |

---

## 🛑 Standing Anti-Tasks

- Do NOT refactor `SecurityPage.jsx` to use `api.js`
- Do NOT delete stubs in `backend/app/aws/`, `providers/`, `queue/`, `errors/`
- Do NOT run `npm audit fix --force`
- Do NOT change **Zenith** / **ZenithApp** branding
- Do NOT add Redux/Zustand or paid services
- Do NOT commit `backend/.env`

---

## Health (verify if stale)

| Check | Status |
|-------|--------|
| Backend pytest | ✅ 67 passed |
| Frontend lint | ✅ 0 errors |
| Frontend build | ✅ Passes |
| Terraform CI | ✅ `terraform validate` job on `backend/terraform/` |

---

## Next Backlog

1. Phase 14c — audit/RBAC UI + drift history panel
2. Phase 14d — cost/VM linkage after deploy

---

## Critical Warnings

1. `backend/.env` — never commit
2. Product name **Zenith** — do not rebrand without asking
