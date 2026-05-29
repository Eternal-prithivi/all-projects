# STATUS.md — Live Project Snapshot (read every session)

> **Always-read bootstrap (~3KB).** Update at **PRE** (claim task, `IN PROGRESS`) and **POST** (COMPLETE, health) with `PROGRESS.md` and `SCRATCHPAD.md` — not only after coding.
> Protocol (PRE → EXECUTE → POST → git push): `AI_MASTER.md` · History: `PROGRESS_HISTORY.md` · Rules: `AI_RULES.md`

**Last Updated:** 2026-05-29

---

## Identity

| Field | Value |
|-------|--------|
| Project | CloudResourceOptimizationPlatform (**Zenith**) |
| Phase | **14** — AWS Terraform integration plan (complete) |
| Last major complete | `AWS_TERRAFORM_INTEGRATION_PLAN.md` feasibility + adopt/skip matrix |
| Budget | Zero-cost / student free-tier only |
| Spec | `ai-docs/AWS_TERRAFORM_INTEGRATION_PLAN.md` |

---

## 🔴 Active Task

**None** — last completed: AWS Terraform integration feasibility plan, 2026-05-29.

| | |
|--|--|
| Resume | `SCRATCHPAD.md` (IDLE) |
| Next | Phase 14b — P0 tests + BYOC scheduled drift (see plan doc) |

---

## 🛑 Standing Anti-Tasks

- Do NOT refactor `SecurityPage.jsx` to use `api.js` (inline API is intentional)
- Do NOT delete stubs in `backend/app/aws/`, `providers/`, `queue/`, `errors/`
- Do NOT run `npm audit fix --force`
- Do NOT change **Zenith** / **ZenithApp** branding
- Do NOT add Redux/Zustand or paid services
- Do NOT commit `backend/.env`

---

## Health (verify if stale)

| Check | Status |
|-------|--------|
| Backend pytest | ✅ 46 passed (`cd backend && .venv/bin/python -m pytest -q`) |
| Frontend lint | ✅ 0 errors (`cd frontend && npm run lint`) |
| Frontend build | ✅ Passes (`npm run build`) |
| MongoDB | Connected (Atlas) |
| Venv | `backend/.venv/` — not project root |

---

## Next Backlog (optional)

1. **Phase 14b** — Provision pytest suite + BYOC drift in Celery (P0 in plan)
2. **Phase 14c** — Provision audit/RBAC UI + drift panel (P1)
3. New-device login email alerts
4. Full GCP live demo (`docs/GCP_DEMO_SETUP.md`)

---

## Doc Routing (load on demand — not at startup)

| Need | Read |
|------|------|
| Terraform integration | `AWS_TERRAFORM_INTEGRATION_PLAN.md` |
| Frontend/UI | `AI_CONTEXT_FRONTEND.md`, `DESIGN_SYSTEM.md` |
| Backend/API/ML | `AI_CONTEXT_BACKEND.md` |
| Architecture dispute | `DECISIONS.md` |
| Hard constraints | `AI_RULES.md` |

---

## Critical Warnings

1. `backend/.env` has live credentials — never commit; rotate before public repo
2. `CORS` — restricted for prod patterns; verify before public deploy
3. Product name **Zenith** — do not rebrand without asking
4. Dev machine **18GB RAM** — max 2 heavy tasks at once (see `AI_RULES.md`)
