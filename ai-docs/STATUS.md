# STATUS.md — Live Project Snapshot (read every session)

> **Always-read bootstrap (~3KB).** Update at **PRE** (claim task, `IN PROGRESS`) and **POST** (COMPLETE, health) with `PROGRESS.md` and `SCRATCHPAD.md` — not only after coding.
> Protocol (PRE → EXECUTE → POST → git push): `AI_MASTER.md` · History: `PROGRESS_HISTORY.md` · Rules: `AI_RULES.md`

**Last Updated:** 2026-05-29

---

## Identity

| Field | Value |
|-------|--------|
| Project | CloudResourceOptimizationPlatform (**Zenith**) |
| Phase | **13** — Enterprise dashboard UI/UX (pass 3 complete) |
| Last major complete | Dashboard enterprise polish — headers, contrast, cost layout |
| Budget | Zero-cost / student free-tier only |
| Spec | `ai-docs/UI_UX_AUDIT_2026.md` |

---

## 🔴 Active Task

**None** — last completed: Enterprise dashboard UI/UX audit + fixes (pass 3), 2026-05-29.

| | |
|--|--|
| Resume | `SCRATCHPAD.md` (IDLE) |
| Audit | `UI_UX_AUDIT_2026.md` → Pass 3 gap table |

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

1. New-device login email alerts
2. Production ML artifact hot-swap after real feedback volume
3. Full GCP live demo (see `docs/GCP_DEMO_SETUP.md`)
4. PageHeader on VM Cluster / Provision / Security (optional)
5. Onboarding tour (`PROFESSIONAL_IMPROVEMENTS.md`)

---

## Doc Routing (load on demand — not at startup)

| Need | Read |
|------|------|
| Frontend/UI | `AI_CONTEXT_FRONTEND.md`, `DESIGN_SYSTEM.md` |
| UI/UX audit + wave log | `UI_UX_AUDIT_2026.md` |
| Backend/API/ML | `AI_CONTEXT_BACKEND.md` |
| Architecture dispute | `DECISIONS.md` |
| Hard constraints | `AI_RULES.md` |
| Session starter | `AI_MASTER.md` |

---

## Critical Warnings

1. `backend/.env` has live credentials — never commit; rotate before public repo
2. `CORS` — restricted for prod patterns; verify before public deploy
3. Product name **Zenith** — do not rebrand without asking
4. Dev machine **18GB RAM** — max 2 heavy tasks at once (see `AI_RULES.md`)
