# Phase 20.5 — CI/CD enterprise gates

**Runs after:** Phase 20 (baseline CI/CD)  
**Runs before:** Phase 21 (observability & runbooks)

Goal: close gaps between “startup CI” and “enterprise pipeline” without waiting for org/compliance phases (22–26).

## Gap → owner map

| Enterprise gap | Owner phase | Item |
|----------------|-------------|------|
| Deploy without green CI | **20.5** | 20.5.1 |
| Playwright optional (`continue-on-error`) | **20.5** | 20.5.2 |
| No coverage threshold | **20.5** | 20.5.3 |
| No post-deploy smoke | **20.5** | 20.5.4 |
| ESLint warnings only | **20.5** | 20.5.5 |
| Dependabot / dependency PRs | **20.5** | 20.5.6 |
| `pip-audit` / `npm audit` | **20.5** | 20.5.7 |
| CodeQL / SAST | **20.5** | 20.5.8 |
| Secrets in git (scan) | **20.5** | 20.5.9 |
| Branch protection (doc only) | **20.5** | 20.5.10 |
| Default branch / keep-alive branch | **20.5** | 20.5.11 |
| `terraform plan` on PR (20.16 gap) | **20.5** | 20.5.12 |
| Celery + Redis in CI | **25** (+ 20.5.13 doc/smoke stub) | 20.5.13, 25.1 |
| API contract tests | **24+** or 20.5.14 optional | 20.5.14 |
| Centralized logs / metrics | **21** | 21.1–21.4 |
| Incident runbooks | **21** | 21.5 |
| Load / k6 / SLO | **25** | 25.5–25.7 |
| SOC2 / GDPR / pen test | **26** | 26.x |
| Enterprise SSO / SAML / SCIM | **24** | 24.x |
| Org tenancy | **22–23** | 22.x–23.x |
| Production secrets manager | **26** | 26.1 |
| Container image scan (prod registry) | **20.5** optional | 20.5.15 |
| Signed commits / SLSA | **26** optional | defer |

## Checklist (implementation order)

1. **20.5.1** — `deploy-stage.yml` triggers on `workflow_run` after **CI** succeeds for `stage` (same commit SHA).
2. **20.5.2** — Remove `continue-on-error` from Playwright job; add `playwright` to required checks in `BRANCH_PROTECTION.md`.
3. **20.5.3** — Backend `--cov-fail-under=40` (ratchet quarterly); upload to Codecov optional via `CODECOV_TOKEN`.
4. **20.5.4** — Post-deploy job: `STAGE_API_URL` secret → `/health` + `/api/platform/status` after stage deploy.
5. **20.5.5** — Frontend CI: `eslint . --max-warnings 0` (fix existing warn-only findings).
6. **20.5.6** — `.github/dependabot.yml` (npm + pip weekly).
7. **20.5.7** — CI jobs: `pip-audit` + `npm audit --audit-level=high` (fail on high/critical).
8. **20.5.8** — `.github/workflows/codeql.yml` (Python + JavaScript).
9. **20.5.9** — Gitleaks (or trufflehog) on pull_request.
10. **20.5.10** — Apply branch protection on GitHub for `stage` (and `main` if used).
11. **20.5.11** — Document/set default branch; ensure `render-keep-alive.yml` on that branch.
12. **20.5.12** — CI: `terraform plan` on PR (`terraform init -backend=false` + plan, no apply).
13. **20.5.13** — Doc: Celery/Redis not in CI until Phase 25 worker; optional smoke with `fakeredis` later.
14. **20.5.14** — *(Optional)* OpenAPI snapshot test for `/api/platform/status` + auth routes.
15. **20.5.15** — *(Optional)* Trivy scan `backend/Dockerfile` in CI.

## Secrets (GitHub)

| Secret | Used by |
|--------|---------|
| `RENDER_DEPLOY_HOOK` | Stage deploy (existing) |
| `VERCEL_*` | Stage/prod frontend (existing) |
| `STAGE_API_URL` | 20.5.4 post-deploy smoke |
| `CODECOV_TOKEN` | 20.5.3 optional |

## Definition of done

Phase 20.5 is complete when 20.5.1–20.5.12 are done, Playwright is green on `stage`, and branch protection enforces CI + Playwright before merge.
