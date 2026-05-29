# STATUS.md — Live Project Snapshot (read every session)

> **Always-read bootstrap (~3KB).** Update at **PRE** (claim task, `IN PROGRESS`) and **POST** (COMPLETE, health) with `PROGRESS.md` and `SCRATCHPAD.md` — not only after coding.
> Protocol (PRE → EXECUTE → POST → git push): `AI_MASTER.md` · History: `PROGRESS_HISTORY.md` · Rules: `AI_RULES.md`

**Last Updated:** 2026-05-29

---

## Identity

| Field | Value |
|-------|--------|
| Project | CloudResourceOptimizationPlatform (**Zenith**) |
| Phase | **12 COMPLETE** — Security research paper parity (SSE-S3 + browser CSE + auto SSE + sessions) |
| Last major complete | Phase 11 — Terraform provisioning + Phase 11b (OPA, drift, RBAC) |
| Budget | Zero-cost / student free-tier only |
| Spec | `ai-docs/PHASE_12_SECURITY_RESEARCH_PARITY.md` |

---

## 🔴 Active Task

**Post–Phase 12: Professional ops (CI, tests, handoff docs)**

| | |
|--|--|
| Status | **COMPLETE** (2026-05-29 gap execution) |
| Done | Auto SSE-S3, session geo + fingerprint, detector benchmark, CI workflow, expanded pytest (46), demo runbook |
| Resume | See `SCRATCHPAD.md` → Current Resume State |

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
| Backend pytest | 46 passed (re-run: `cd backend && .venv/bin/python -m pytest -q`) |
| Frontend lint | 0 errors (`cd frontend && npm run lint`) |
| Frontend build | Passes (`npm run build`) |
| MongoDB | Connected (Atlas) |
| Venv | `backend/.venv/` — not project root |

---

## Next Backlog (optional)

1. New-device login email alerts
2. Production ML artifact hot-swap after real feedback volume
3. Full GCP live demo (see `docs/GCP_DEMO_SETUP.md`)
4. Onboarding tour (`PROFESSIONAL_IMPROVEMENTS.md`)

---

## Doc Routing (load on demand — not at startup)

| Need | Read |
|------|------|
| Frontend/UI | `AI_CONTEXT_FRONTEND.md`, `DESIGN_SYSTEM.md` |
| UI/UX audit + wave log | `UI_UX_AUDIT_2026.md` (on demand — **platform polish complete 2026-05-29**) |
| Backend/API/ML | `AI_CONTEXT_BACKEND.md` |
| Architecture dispute | `DECISIONS.md` (Before You Code checklist) |
| Hard constraints | `AI_RULES.md` |
| Phase 12 detail | `PHASE_12_SECURITY_RESEARCH_PARITY.md` |
| Session starter (optional) | `AI_MASTER.md` → Session starter; optional PDF `ZENITH_AI_SESSION_PROMPTS.pdf` |
| Human runbooks | `docs/` (use `@` one file at a time) |
| Completed session write-ups | `PROGRESS_HISTORY.md` — **append only, never read at startup** |
| Past sessions | `AUDIT_LOG.md` — **append only at POST-PHASE** · never read at startup · archive → `AUDIT_LOG_ARCHIVE_2026.md` |

---

## Critical Warnings

1. `backend/.env` has live credentials — never commit; rotate before public repo
2. `CORS` — restricted for prod patterns; verify before public deploy
3. Product name **Zenith** — do not rebrand without asking
4. Dev machine **18GB RAM** — max 2 heavy tasks at once (see `AI_RULES.md`)
