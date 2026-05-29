# PROGRESS.md — Task Tracker

> **Last Updated:** 2026-05-29  
> **Roadmap:** Phases **19–27** = enterprise platform maturity (ops → quality → org → scale → compliance → cloud parity).  
> **Order rule:** Phases **19–21** are **isolated** (little or no cross-feature dependency). Phases **22–27** build on org/tenancy and prior ops work — do **not** start 22+ until 19–21 foundations are far enough along.

---

## 🔴 Active Task

**None** — Phase **19** complete. Next: **20.1**.

| Next up | Phase **20.1** — pytest admin CRUD |
|---------|-------------------------------------|

---

## Phase summary (19 → 27)

| Phase | Theme | Depends on | Status |
|-------|--------|------------|--------|
| **19** | Isolated ops & hygiene | — | ✅ Complete |
| **20** | Quality, CI depth & CD | 19 (secrets/CORS doc) | ⬜ Not started |
| **21** | Observability & runbooks | 19 | ⬜ Not started |
| **22** | Org foundation (data model) | 19–21 recommended | ⬜ Not started |
| **23** | Org-scoped product | **22** | ⬜ Not started |
| **24** | Enterprise IdP & API governance | **22**, partial 23 | ⬜ Not started |
| **25** | Scale-out & performance | 20 CI, 21 metrics | ⬜ Not started |
| **26** | Compliance & commercial | **22–23** for org billing | ⬜ Not started |
| **27** | Cloud parity & deferred UI | BYOC/GCP billing active | ⬜ Not started |

---

## Phase 19 — Isolated ops & hygiene (do first)

*No org model changes. No multi-service deploy required. Can be done one item at a time.*

- [x] **19.1** — CORS: production tightening + `CORS_ALLOWED_ORIGINS` in `main.py`; `docs/setup/DEPLOYMENT_SECRETS.md`
- [x] **19.2** — Secrets hygiene: `.env.example` + `DEPLOYMENT_SECRETS.md`
- [x] **19.3** — Credential rotation runbook — `docs/setup/CREDENTIAL_ROTATION.md`
- [x] **19.4** — Sentry backend (`sentry-sdk`, optional `SENTRY_DSN`)
- [x] **19.5** — Sentry frontend (`@sentry/react`, optional `VITE_SENTRY_DSN`)
- [x] **19.6** — Uptime workflow `.github/workflows/uptime.yml` (needs `UPTIME_API_URL` secret)
- [x] **19.7** — Admin audit CSV export button (`/audit-logs/export`; user activity export already on Security Settings)
- [x] **19.8** — Platform status: `gcp_credentials_present` + `gcp_integration` service row
- [x] **19.9** — `PROFESSIONAL_IMPROVEMENTS.md` synced to Phase 19–27
- [x] **19.10** — `docs/setup/CLOUD_COST_GUARDRAILS.md`
- [x] **19.11** — Vitest scaffold + CI `npm run test`
- [x] **19.12** — Security 2FA overlay dialog (shipped prior — verified)

---

## Phase 20 — Quality, CI depth & CD

*Depends on: 19.2 secrets doc helpful. CI already exists (`.github/workflows/ci.yml`).*

- [ ] **20.1** — Pytest: admin user CRUD (`routes_admin.py`)
- [ ] **20.2** — Pytest: BYOC connect / test / disconnect (AWS + GCP mocks)
- [ ] **20.3** — Pytest: storage upload → analyze → tier assignment (smoke)
- [ ] **20.4** — Pytest: password reset + email verify flows
- [ ] **20.5** — Pytest: organizations (create org, invite, accept, leave)
- [ ] **20.6** — Pytest: notifications API
- [ ] **20.7** — CI: MongoDB service container (or `mongodb` action) so pytest runs green in GitHub without local Mongo
- [ ] **20.8** — CI: fail job if pytest count drops / add coverage threshold (optional, start with `--cov` report artifact)
- [ ] **20.9** — CD: GitHub Actions workflow `deploy-stage.yml` — on push to `stage`, deploy backend (Render hook) + frontend (Vercel)
- [ ] **20.10** — CD: production deploy on version tag or manual `workflow_dispatch` only
- [ ] **20.11** — Branch protection doc: require `ci.yml` pass before merge to `stage` / `main`
- [ ] **20.12** — Playwright: install + smoke — login → dashboard loads
- [ ] **20.13** — Playwright: smoke — Settings BYOC form validation (no real cloud)
- [ ] **20.14** — Staging environment: second Render service or preview env doc; staging `.env` template
- [ ] **20.15** — MongoDB Atlas: migration guide from local Mongo + enable automated backups
- [ ] **20.16** — Terraform CI: `terraform plan` on PR (read-only; `backend/terraform`)

---

## Phase 21 — Observability & runbooks

*Depends on: 19.4–19.5 Sentry recommended first.*

- [ ] **21.1** — Structured JSON logging (request id, user, route, duration)
- [ ] **21.2** — Request ID middleware + pass to logs and error responses
- [ ] **21.3** — Admin diagnostics page: show build version, git sha (env), Mongo/Redis/Celery status
- [ ] **21.4** — Optional Prometheus `/metrics` endpoint (request count, latency histogram)
- [ ] **21.5** — Alerting runbook: `docs/operations/INCIDENT_RUNBOOK.md` (who, what, rollback, Render/Vercel)
- [ ] **21.6** — Celery queue monitoring doc (flower or Render worker logs)
- [ ] **21.7** — Status page: synthetic checks documented; wire failures to `maintenance_mode` admin toggle
- [ ] **21.8** — Log retention policy doc (what we store, 90-day activity log alignment with privacy policy)

---

## Phase 22 — Org foundation (tenancy data model)

*Depends on: Phase 19–21 ops baseline. **Blocks Phase 23–26.***

- [ ] **22.1** — `DECISIONS.md`: tenancy model (single org per user vs multi-org later; org_id on documents)
- [ ] **22.2** — Add `org_id` to `cloud_credentials` / BYOC records + migration script for existing users
- [ ] **22.3** — Add `org_id` to: `file_metadata`, VM assignment records, cost cache keys (schema + indexes)
- [ ] **22.4** — `require_org_membership` dependency (role: owner | admin | member)
- [ ] **22.5** — Org BYOC: only owner/admin can connect/disconnect; members read-only on connection status
- [ ] **22.6** — Team page: show org-linked BYOC status (connected CSP, bucket name — no secrets)
- [ ] **22.7** — Leave/remove member: revoke sessions for removed user
- [ ] **22.8** — Pytest: org isolation (user A cannot read user B org data)

---

## Phase 23 — Org-scoped product

*Depends on: **Phase 22** complete.*

- [ ] **23.1** — Storage: list/upload/download scoped to org BYOC / org bucket prefix
- [ ] **23.2** — Security vault: org-shared AWS prefix policy (owner configures; members inherit access rules)
- [ ] **23.3** — VM cluster: pools and assignments per `org_id` (real GCP uses org BYOC SA)
- [ ] **23.4** — Cost dashboard: per-org cache and refresh (AWS BYOC CE; GCP when export exists)
- [ ] **23.5** — Notifications: org-wide alerts (billing, security) to all members
- [ ] **23.6** — Provision / Terraform: deployments tagged with `org_id`; RBAC uses org role
- [ ] **23.7** — Admin: filter users/deployments by organization
- [ ] **23.8** — Multi-org per user (org switcher) — **optional**; only if 22.1 chooses multi-org

---

## Phase 24 — Enterprise IdP & API governance

*Depends on: **Phase 22** (org exists); **23** for org-enforced SSO policy.*

- [ ] **24.1** — OIDC: full authorization-code flow (not issuer redirect only); PKCE for SPA
- [ ] **24.2** — SAML 2.0 service provider (Okta / Azure AD metadata upload)
- [ ] **24.3** — SCIM 2.0 provisioning (create/update/deactivate users)
- [ ] **24.4** — Org policy: “SSO required” — block password login for org members
- [ ] **24.5** — API keys: scopes (`read`, `write`, `admin`)
- [ ] **24.6** — API keys: org-level issuance + revoke (not only per-user)
- [ ] **24.7** — Rate limits: global slowapi on `/api/storage`, `/api/vm`, `/api/cost`
- [ ] **24.8** — Rate limits: per-org buckets (Redis-backed when Phase 25 Redis lands)

---

## Phase 25 — Scale-out & performance

*Depends on: **20** CD/stable deploy; **21** observability; **24.8** optional Redis.*

- [ ] **25.1** — `render.yaml`: dedicated Celery worker service + Redis instance (or Upstash Redis URL)
- [ ] **25.2** — WebSocket: Redis pub/sub fan-out so multiple API instances receive notify events
- [ ] **25.3** — Document horizontal scale: 2+ Render instances, sticky sessions or stateless JWT only
- [ ] **25.4** — MongoDB: connection pool settings + read preference doc for Atlas replica set
- [ ] **25.5** — Load test: k6 script — login + dashboard + list storage (baseline RPS/latency)
- [ ] **25.6** — Load test: k6 script — VM provision path (staging only, with GCP creds)
- [ ] **25.7** — SLO doc: p95 latency targets, error budget, when to scale workers
- [ ] **25.8** — Move spaCy/ML heavy paths to Celery task only (optional API offload)

---

## Phase 26 — Compliance & commercial enterprise

*Depends on: **22–23** for org billing; legal pages exist (Phase 18).*

- [ ] **26.1** — Secrets manager: platform secrets from AWS SM / GCP SM (not flat `.env` in prod)
- [ ] **26.2** — BYOC credential storage: document upgrade path to CMK / envelope encryption
- [ ] **26.3** — GDPR: `GET /api/users/me/export` (profile, files metadata, activity)
- [ ] **26.4** — GDPR: account deletion workflow (anonymize + revoke sessions + BYOC disconnect)
- [ ] **26.5** — SOC2-lite: control matrix doc mapping features → controls (`docs/compliance/`)
- [ ] **26.6** — Penetration test checklist (OWASP API top 10 for Zenith routes)
- [ ] **26.7** — WAF/CDN: Cloudflare in front of custom domain doc
- [ ] **26.8** — Audit log: append-only export to S3/GCS bucket (optional SIEM)
- [ ] **26.9** — Org-level billing: Razorpay subscription per org (seats)
- [ ] **26.10** — Usage metering hooks (storage GB, API calls) for future plans
- [ ] **26.11** — Invoice PDF / receipt email for org owner

---

## Phase 27 — Cloud parity & deferred product

*Depends on: user GCP/AWS accounts active; **23** for org-scoped cloud.*

- [ ] **27.1** — CloudFormation one-click stack UI (AWS BYOC)
- [ ] **27.2** — Bucket migration wizard UI (AWS multi-bucket)
- [ ] **27.3** — GCP: BigQuery billing export setup wizard + Cost Analysis tab wired
- [ ] **27.4** — Azure: Cost Management BYOC credentials (not storage-only)
- [ ] **27.5** — VM: document AWS EC2 / Azure VM parity scope (or explicit WONTFIX)
- [ ] **27.6** — Razorpay: redirect success/cancel to `/billing/success` and `/billing/cancel`
- [ ] **27.7** — Secure vault: multi-cloud roadmap doc (currently AWS-only)
- [ ] **27.8** — Replication strategy doc (dual-bucket / replica S3) — implement or defer with DEC

---

## Phase 18 — Enterprise pages — ✅ COMPLETE

| Sub | Deliverables |
|-----|----------------|
| 18a–18c | Trust, cookies, DPA, status, pricing, billing returns, maintenance gate |
| 18d | Notifications, team/org invites, SSO (Google + OIDC redirect), email verify |

---

## Earlier phases (complete)

| Phase | Status |
|-------|--------|
| 17 | ✅ Multi-bucket BYOC (local) |
| 15 | ✅ Theme sync |
| 9–16 | ✅ ML, security, UI waves — see `PROGRESS_HISTORY.md` |

---

## Reference

| Topic | Doc |
|-------|-----|
| Agent protocol | `AI_MASTER.md` |
| Live snapshot | `STATUS.md` |
| Resume / next step | `SCRATCHPAD.md` |
| Narrative archive | `PROGRESS_HISTORY.md` |
| Maturity assessment (2026-05-29) | Chat + Phase 19–27 above |
| Outdated “no CI” note | `PROFESSIONAL_IMPROVEMENTS.md` — update in **19.9** |
