# PROGRESS.md — Task Tracker

> **Last Updated:** 2026-05-30  
> **Roadmap:** Phases **19–27** — summary table below. **Full checklists** for completed Phase 19 and future Phases 21–27 → `PROGRESS_HISTORY.md` (do not read at startup).  
> **Order rule:** Phases **19–21** isolated first; **22+** need org foundation.


---

## 🔴 Active Task

**None** — Phase **20** complete (Slices 0–16 + coverage gap follow-up).

| Next up | Phase **21** — Observability & runbooks |
|---------|----------------------------------------|

---

## Phase summary (19 → 27)

| Phase | Theme | Depends on | Status |
|-------|--------|------------|--------|
| **19** | Isolated ops & hygiene | — | ✅ Complete |
| **20** | Quality, CI depth & CD | 19 (secrets/CORS doc) | ✅ Complete (20.0–20.16 + gap tests) |
| **21** | Observability & runbooks | 19 | ⬜ Not started |
| **22** | Org foundation (data model) | 19–21 recommended | ⬜ Not started |
| **23** | Org-scoped product | **22** | ⬜ Not started |
| **24** | Enterprise IdP & API governance | **22**, partial 23 | ⬜ Not started |
| **25** | Scale-out & performance | 20 CI, 21 metrics | ⬜ Not started |
| **26** | Compliance & commercial | **22–23** for org billing | ⬜ Not started |
| **27** | Cloud parity & deferred UI | BYOC/GCP billing active | ⬜ Not started |

---

## Phase 20 — Quality, CI depth & CD

*Depends on: 19.2 secrets doc helpful. CI already exists (`.github/workflows/ci.yml`).*

- [x] **20.0** — Test foundation (`conftest.py`, markers, `docs/testing/TESTING.md`, CI Mongo)
- [x] **20.1** — Pytest: admin user CRUD + audit export (`tests/integration/test_admin_api.py`)
- [x] **20.2** — Pytest: BYOC connect / test / disconnect (mocks)
- [x] **20.3** — Pytest: storage list / upload / sync smoke
- [x] **20.4** — Pytest: password reset + email verify flows
- [x] **20.5** — Pytest: organizations (create org, invite, accept)
- [x] **20.6** — Pytest: notifications API
- [x] **20.7** — CI: MongoDB service container
- [x] **20.8** — CI: `--cov` report artifact
- [x] **20.9** — CD: `deploy-stage.yml`
- [x] **20.10** — CD: production deploy (`deploy-production.yml`, tag / manual)
- [x] **20.11** — Branch protection doc (`docs/testing/BRANCH_PROTECTION.md`)
- [x] **20.12** — Playwright: login page smoke
- [x] **20.13** — Playwright: settings auth redirect smoke
- [x] **20.14** — Staging environment doc (`docs/testing/STAGING.md`)
- [x] **20.15** — MongoDB Atlas migration guide (`docs/testing/MONGODB_ATLAS.md`)
- [x] **20.16** — Terraform CI doc (`docs/testing/TERRAFORM_CI.md`; validate job in CI)
- [x] **20.x** — Gap follow-up: `TESTING_POLICY.md`, storage analyze + security upload integration, settings/profile API tests, AWS BYOC + E2E admin/BYOC validation, CI `seed_e2e_admin.py`

---

## Reference

| Topic | Doc |
|-------|-----|
| Agent protocol | `AI_MASTER.md` |
| Live snapshot | `STATUS.md` |
| Resume / next step | `SCRATCHPAD.md` |
| Completed narratives + Phases 19–27 checklists | `PROGRESS_HISTORY.md` |
| Session log (8 recent) | `AUDIT_LOG.md` |
| Session log archive | `AUDIT_LOG_ARCHIVE_2026.md` |

> **Token rule:** This file = active task + summary table + **current phase checklist only**. Do not duplicate completed phase item lists here.
