# PROGRESS.md — Task Tracker

> **Last Updated:** 2026-05-30  
> **Roadmap:** Phases **19–27** + **20.5**. Full checklists → `PROGRESS_HISTORY.md`.  
> **Order rule:** **19 → 20 → 20.5 → 21**; **22+** need org foundation.


---

## 🔴 Active Task

**Phase 20.5 — CI/CD enterprise gates** — implementation in progress on `stage`.

**Next after 20.5:** Phase 21 (observability & runbooks).

---

## Phase summary (19 → 27)

| Phase | Theme | Depends on | Status |
|-------|--------|------------|--------|
| **19** | Isolated ops & hygiene | — | ✅ Complete |
| **20** | Quality, CI depth & CD | 19 | ✅ Complete |
| **20.5** | **CI/CD enterprise gates** | 20 | 🟡 In progress |
| **21** | Observability & runbooks | 19, **20.5** | ⬜ Not started |
| **22** | Org foundation (data model) | 19–21 recommended | ⬜ Not started |
| **23** | Org-scoped product | **22** | ⬜ Not started |
| **24** | Enterprise IdP & API governance | **22**, partial 23 | ⬜ Not started |
| **25** | Scale-out & performance | 20, 21, 24.8 optional | ⬜ Not started |
| **26** | Compliance & commercial | **22–23** | ⬜ Not started |
| **27** | Cloud parity & deferred UI | BYOC/GCP billing active | ⬜ Not started |

---

## Phase 20.5 — CI/CD enterprise gates

*Detail: `docs/testing/PHASE_20_5_CI_GATES.md`*

- [x] **20.5.1** — CI-gated stage deploy (`workflow_run` after CI)
- [x] **20.5.2** — Playwright required (removed `continue-on-error`)
- [x] **20.5.3** — Backend `--cov-fail-under=40`
- [x] **20.5.4** — Post-deploy stage smoke (`STAGE_API_URL` secret)
- [x] **20.5.5** — ESLint `--max-warnings 0` + warning fixes
- [x] **20.5.6** — Dependabot (`.github/dependabot.yml`)
- [x] **20.5.7** — `pip-audit` + `npm audit --audit-level=high` in CI
- [x] **20.5.8** — CodeQL workflow
- [x] **20.5.9** — Gitleaks + `.gitleaks.toml`
- [ ] **20.5.10** — Apply GitHub branch protection on `stage` (manual in repo Settings)
- [x] **20.5.11** — `STAGING.md` default branch + keep-alive notes
- [x] **20.5.12** — `terraform-plan.yml` on PR
- [x] **20.5.13** — Celery/Redis CI deferral documented in `PHASE_20_5_CI_GATES.md`
- [ ] **20.5.14** — *(Optional)* OpenAPI snapshot tests
- [x] **20.5.15** — Trivy Dockerfile scan in CI

---

## Phase 20 — Quality, CI depth & CD ✅

*Complete — see `PROGRESS_HISTORY.md`.*

---

## Reference

| Topic | Doc |
|-------|-----|
| Phase 20.5 gap map | `docs/testing/PHASE_20_5_CI_GATES.md` |
| Agent protocol | `AI_MASTER.md` |
| Live snapshot | `STATUS.md` |
| Resume | `SCRATCHPAD.md` |
