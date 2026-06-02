# Professional standard — deferred improvements

**Purpose:** Single checklist of **enterprise / professional** work that is **intentionally not required now**, but should be done in **later stages** of Zenith (Cloud Resource Optimization Platform).

**Current posture (2026):** Staging-ready SaaS on Render + Vercel with Phase **20.5** CI in code. Solo/small-team flow: push to `stage`, CI runs in parallel, hosts auto-deploy. That is sufficient until scale, team size, or compliance demands stricter gates.

**Related docs:**

| Topic | Doc |
|-------|-----|
| Phase 20.5 gap map (done vs open) | `PHASE_20_5_CI_GATES.md` |
| Branch protection how-to | `BRANCH_PROTECTION.md` |
| Staging deploy | `STAGING.md` |
| GitHub secrets | `../setup/DEPLOYMENT_SECRETS.md` |
| Full roadmap Phases 21–27 | `../../ai-docs/PROGRESS.md`, `../../ai-docs/PROGRESS_HISTORY.md` |
| Historical improvement log | `../../ai-docs/PROGRESS_HISTORY.md` |

---

## What is already “professional enough” for now

Do **not** block current work on the items below. They are **later**.

| Area | Status |
|------|--------|
| CI on push (`ci.yml`) | Backend pytest, frontend lint/test/build, Terraform validate, Playwright, audits, CodeQL, gitleaks, Trivy |
| Deploy workflow skeleton | `deploy-stage.yml` runs after CI via `workflow_run` |
| Testing policy | `TESTING_POLICY.md` |
| Security baselines | Rate limits, optional Sentry, dependency scans in CI |
| Staging docs | `STAGING.md`, Atlas/Terraform CI guides |
| Mobile UX verification | `mobile_responsive_checklist.md` (marketing drawer, dashboard/admin bottom nav, safe areas) |

---

## Tier A — CI/CD & GitHub (do when you want “enterprise deploy”)

These are the two items most often discussed in project reviews: **deploy only after green CI**, and **GitHub enforcement** so broken code cannot land on `stage`.

### A1. CI-gated deploy to Render and Vercel (enterprise deploy flow)

**Not required now** if Render and Vercel are already connected to `stage` and deploy on every push.

**Do later when:** A failed CI run shipped broken code to staging, or multiple people merge to `stage`.

| Step | Action |
|------|--------|
| 1 | In **Render** → disable **auto-deploy** on push for the staging backend service |
| 2 | In **Vercel** → disable automatic deployments for the `stage` branch (or use preview-only) |
| 3 | Add GitHub Actions secrets: `RENDER_DEPLOY_HOOK`, `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` |
| 4 | Rely on **`deploy-stage.yml`** as the **only** deploy trigger (runs after CI success) |
| 5 | Verify one push → one CI run → one backend + one frontend deploy (no double deploy) |

**Trade-off:** Live site updates ~5–10 minutes **later** than today (~12–22 min push-to-fully-live vs ~10–15 min), but **only green CI** reaches production/staging.

**Code reference:** `.github/workflows/deploy-stage.yml` (20.5.1 — workflow already waits for CI; secrets + host settings complete the gate).

---

### A2. Branch protection on `stage` (and `main` when used)

**Manual** in GitHub — not enforceable from the repo alone (20.5.10).

**Do later when:** You use pull requests, or want merges blocked until CI passes (even if deploy is still fast via auto-deploy).

| Setting | Value |
|---------|--------|
| Branch pattern | `stage` (repeat for `main` if used) |
| Require status checks | `backend`, `frontend`, `terraform-validate`, `playwright`, `security-audit`, `docker-scan` |
| Optional | Require pull request before merging |
| Optional | Require branch up to date before merge |

**How-to:** `BRANCH_PROTECTION.md`

**Note:** Branch protection gates **merge**; it does **not** by itself stop Render/Vercel from deploying on direct push unless you also restrict who can push to `stage`.

---

### A3. Other CI/CD items (optional / polish)

| Item | When | Notes |
|------|------|--------|
| `STAGE_API_URL` secret | Soon (low effort) | Post-deploy smoke in `deploy-stage.yml`; not full enterprise, but recommended |
| `CODECOV_TOKEN` | Later | Coverage trends in Codecov; CI already enforces `--cov-fail-under=40` |
| Default branch = `stage` | When using keep-alive cron | Scheduled `render-keep-alive.yml` runs only on repo **default** branch (20.5.11) |
| OpenAPI snapshot tests | Later | 20.5.14 optional |
| PR-only workflow | Later | Feature branch → PR → `stage` instead of direct push |
| Production approval gate | Later | Manual `workflow_dispatch` or environment protection for `main`/tags |
| Signed commits / SLSA | Much later | Phase 26 optional |

---

## Tier B — Phase 21: Observability & operations

**Start after:** 20.5 stable on `stage`; deploy safety understood.

| ID | Item |
|----|------|
| 21.1 | Structured JSON logging (request id, user, route, duration) |
| 21.2 | Request ID middleware + pass to logs and error responses |
| 21.3 | Admin diagnostics: build version, git sha, Mongo/Redis/Celery status |
| 21.4 | Optional Prometheus `/metrics` (request count, latency) |
| 21.5 | Incident runbook (`docs/operations/INCIDENT_RUNBOOK.md`) |
| 21.6 | Celery queue monitoring (Flower or worker logs) |
| 21.7 | Status page synthetic checks → `maintenance_mode` integration |
| 21.8 | Log retention policy (align with privacy policy) |

**Why later:** Sentry (Phase 19) covers basic errors; full ops stack is overhead until real users or on-call needs exist.

---

## Tier C — Phases 22–23: Organization & multi-tenant product

**Start when:** Real teams need shared BYOC, billing, and data isolation.

| Phase | Theme | Highlights |
|-------|--------|------------|
| **22** | Org foundation | `org_id` on documents, membership roles, BYOC per org, isolation tests |
| **23** | Org-scoped product | Storage, VM, cost, provision, admin filtered by org; optional org switcher |

**Blocks:** Enterprise SSO policy (24), org billing (26), org-scoped cloud wizards (27).

---

## Tier D — Phase 24: Enterprise identity & API governance

| ID | Item |
|----|------|
| 24.1 | OIDC authorization-code + PKCE (full SPA flow) |
| 24.2 | SAML 2.0 SP (Okta / Azure AD metadata) |
| 24.3 | SCIM 2.0 user provisioning |
| 24.4 | Org policy: SSO required (block password login) |
| 24.5–24.6 | API keys with scopes; org-level issuance |
| 24.7–24.8 | Global and per-org rate limits (Redis-backed with Phase 25) |

---

## Tier E — Phase 25: Scale, workers & performance

| ID | Item |
|----|------|
| 25.1 | Dedicated Celery worker + Redis on Render (or Upstash) |
| 25.2 | WebSocket fan-out via Redis pub/sub (multi-instance API) |
| 25.3 | Horizontal scale doc (2+ API instances, stateless JWT) |
| 25.4 | MongoDB pool + read preference for Atlas replica set |
| 25.5–25.6 | k6 load tests (login/dashboard; provision path on staging) |
| 25.7 | SLO doc (p95 latency, error budget) |
| 25.8 | Heavy ML paths on Celery only |
| — | **Celery + Redis in CI** (deferred from 20.5.13) |

**Why later:** Free-tier Render is single-instance; load tests and workers matter after paid tier or traffic.

---

## Tier F — Phase 26: Compliance & commercial enterprise

| ID | Item |
|----|------|
| 26.1 | Secrets manager (AWS SM / GCP SM) — not flat `.env` in prod |
| 26.2 | BYOC credentials: CMK / envelope encryption path |
| 26.3–26.4 | GDPR export + account deletion workflow |
| 26.5 | SOC2-lite control matrix |
| 26.6 | Penetration test checklist (OWASP API top 10) |
| 26.7 | WAF/CDN (e.g. Cloudflare) in front of custom domain |
| 26.8 | Audit log export to S3/GCS (SIEM optional) |
| 26.9–26.11 | Org-level Razorpay, usage metering, invoice PDF |

---

## Tier G — Phase 27: Cloud parity & deferred product UI

| ID | Item |
|----|------|
| 27.1 | CloudFormation one-click BYOC UI |
| 27.2 | AWS bucket migration wizard |
| 27.3 | GCP BigQuery billing export wizard + Cost Analysis wiring |
| 27.4 | Azure Cost Management BYOC (beyond storage-only) |
| 27.5 | AWS EC2 / Azure VM parity scope doc |
| 27.6 | Razorpay redirect to `/billing/success` and `/billing/cancel` |
| 27.7 | Secure vault multi-cloud roadmap |
| 27.8 | S3 replication / dual-bucket strategy |

**Note:** GCP setup for dev (billing, service account) is operational work, not this doc — see `../setup/CLOUD_CREDENTIAL_SETUP_GUIDE.md` and `../setup/CLOUD_COST_GUARDRAILS.md`.

---

## Tier H — Infrastructure & hosting upgrades

Defer until free-tier limits hurt reliability or Terraform-on-Render is required again at scale.

| Item | When |
|------|------|
| Render **paid** plan (more CPU/RAM) | Terraform plans reliable; less sleep/cold start |
| Separate **staging** MongoDB cluster/DB name | Never point staging at production data |
| Separate Render service `zenith-api-stage` | True staging vs production isolation |
| Remote Terraform state (S3/GCS per org) | Enterprise BYOC; not copy-paste from single-account templates |
| Web Terminal / CloudShell | High security surface; enterprise tier only |
| Disable GitHub double-deploy | Part of A1 |

---

## Tier I — Testing depth (beyond current CI)

| Item | Phase / when |
|------|----------------|
| Broader Playwright regression (provision, BYOC, billing) | After staging stable |
| API contract tests (OpenAPI snapshots) | 20.5.14 optional |
| Celery/Redis integration in CI | 25 + 20.5.13 |
| Load / perf gates in CI | 25 |
| Coverage ratchet (e.g. 50% → 60% quarterly) | Ongoing after 40% floor |

---

## Suggested order (when you “go professional”)

```text
Now (optional, low effort)
  └─ STAGE_API_URL secret, confirm CI green on stage

Next tier (CI/CD enterprise — Tier A)
  └─ A2 Branch protection
  └─ A1 CI-gated deploy (disable host auto-deploy + GitHub deploy secrets)

Then (ops — Tier B)
  └─ Phase 21 observability + runbooks

Then (product scale — Tiers C–G)
  └─ 22 → 23 → 24 → 25 → 26 → 27 as product/compliance needs arise

Infrastructure (Tier H)
  └─ Paid Render, staging isolation, when free tier blocks you
```

---

## Triggers — when to pull an item forward

| Signal | Likely next step |
|--------|------------------|
| CI failed but site updated anyway | **A1** CI-gated deploy |
| Someone merged broken code to `stage` | **A2** branch protection + PR workflow |
| On-call for outages | **Phase 21** runbooks + metrics |
| Customer asks for SSO / SAML | **Phase 24** |
| Compliance questionnaire (SOC2, GDPR) | **Phase 26** |
| Terraform OOM / 20+ min plans on Render | **Tier H** paid Render or boto3-only on free tier |
| Multiple engineers on same org data | **Phases 22–23** |

---

## Definition of “professional standard complete”

There is no single finish line. Use this rough bar:

| Level | Meaning |
|-------|---------|
| **Staging-ready** (today) | CI on push, tests + audits, docs, Render/Vercel deploy |
| **Team-ready** | A2 + PRs + `STAGE_API_URL`; optional A1 |
| **Enterprise deploy** | A1 fully active; one deploy path; smoke after deploy |
| **Enterprise product** | Phases 22–27 per customer/compliance needs |

---

*Last updated: 2026-05-31 — aligns with Phase 20.5 and chat decisions on deferred enterprise CI/CD.*
