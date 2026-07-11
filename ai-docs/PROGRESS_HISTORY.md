# PROGRESS_HISTORY.md — Archived Session Narratives

> **Append-only archive.** Do not read at startup or mid-task.
> Put long “what we completed” narratives here — **not** in chat, **not** in `PROGRESS.md`.
> Lightweight/trivial fixes: skip this file unless the user wants a paper trail.
> Migrated from PROGRESS.md on 2026-05-29.

---

**Stage 1 — Production Beta closeout** — COMPLETE 2026-06-15

- **CI:** Playwright admin tests refactored (API layer + sidebar link); Redis in CI playwright services; desktop-release `releases.json` stash/rebase; CI green on `stage`.
- **Onboarding:** Username-scoped tour localStorage; Getting Started checklist on dashboard; Restart Tour navigates to dashboard; `docs/development/ONBOARDING_GUIDE.md`.
- **Cache:** Per-user `billing_cache`; auth on `DELETE /cost/cache/clear`; cloud availability 5m sessionStorage TTL + server cache; BYOC single-query + invalidation hooks; `CACHING_GUIDE.md` rewrite; `ADR_001_CACHING_STRATEGY.md`.
- **Performance:** Dashboard critical path 3 APIs + deferred secondary loads; no `refresh_user_costs` on GET `/stats`; Mongo aggregation + indexes; MaintenanceGate 60s cache; Vite `manualChunks`; lazy joyride + recharts sparkline.
- **Desktop:** `png2icons` generates `icon.icns` / `icon.ico` from brand master; electron-builder mac/win/linux icon paths; `prebuild` hooks; `docs/desktop/INSTALL.md` note.
- **Admin:** `AdminLayout.jsx` loading state while auth user resolves.

**How to test:** `npm run lint && npm run build && npm run test:e2e`; open `/dashboard` (fast load + Getting Started card); `npm run brand:assets && npm run build:mac` → DMG shows Zenith Z icon.

---

**Phase 22 — SaaS pages polish (zero/low-cost)** — COMPLETE 2026-06-11

- **Trust copy:** `productFacts.js` — Help FAQs, public pricing, support email; removed stale USD/personal-email content.
- **Overview:** Platform status banner; plan-based storage cap; budget/team cards; needs-attention strip; cost sparkline from Mongo after explicit Refresh (`dashboard_cost_snapshots`, `GET /api/dashboard/cost-trend`).
- **Billing:** `billing_constants` FX (83); plan names from `/api/payments/plans`.
- **Support:** `POST /api/support/tickets`; in-app New ticket on Support page.
- **Team:** `DELETE /api/organizations/invites/{email}`; invite link copy; per-account billing callout.
- **Admin:** Support inbox quick action; `/admin/test` dev-only.
- **Tests/docs:** `test_dashboard_cost_trend.py`; manual_testing rows 6.4–6.10.

**How to test:** `/help` INR pricing; `/dashboard` Refresh cost → sparkline; `/dashboard/support` New ticket.

---

**Phase 21 — Provision intent wizard + GCP/Azure SDK parity** — COMPLETE 2026-06-11

- Intent-first Build wizard (5 steps): NLP, tri-cloud compare, plain-English review, success handoffs, Terraform export.
- New APIs: `POST /analyze-intent`, `/compare-clouds`, `/review-summary`, `GET /deployments/{id}/handoff`, `/export/terraform`.
- GCP SDK modules: `gcp_network`, `gce`, `gcp_service_account`, `gcp_monitoring`, `firestore` (+ existing `gcs`).
- Azure SDK modules: `vnet`, `azure_vm`, `azure_monitor`, `cosmos` (+ refactored `azure_storage`).
- Wiring: intent auto-applies template flags, `disk_size_gb` end-to-end, Boto3 public IP handoff, multicloud policy rules, AWS billing module in catalog.
- Tests: `test_sdk_composer_parity.py`, `test_provision_sdk_gcp/azure.py`, `test_provision_disk.py`, intent/compare API tests.
- Docs: `manual_testing.md`, `MULTI_CLOUD_PARITY_MATRIX.md`, `AI_CONTEXT_BACKEND.md`, `AI_CONTEXT_FRONTEND.md`.

**Phase 20 — Trust narrative + BYOC credential encryption** — COMPLETE 2026-06-10

- **Docs:** Created `docs/security/TRUST_AND_ENCRYPTION.md` (user-facing custody: platform vs BYOC, SSE vs CSE, archive/replica, FAQ) and `docs/security/BYOC_CREDENTIAL_ENCRYPTION.md` (AES-GCM field format, merge, rotation). Updated `docs/README.md`, `BYOC_IMPLEMENTATION.md`, `CREDENTIAL_CONTRACT.md`, `MULTI_CLOUD_PARITY_MATRIX.md`, `manual_testing.md` (4.18–4.22), `CLIENT_SIDE_ENCRYPTION.md` cross-links.
- **Backend:** `encryption.py` — `zenith:enc:v1:` prefix, idempotent encrypt (no double encryption), `merge_and_encrypt_credentials` for incremental field updates; `_save_*_byoc_record` merges with existing Mongo credentials. Tests: `test_byoc_encryption.py`.
- **AI docs:** `STATUS.md`, `SCRATCHPAD.md`, `PROGRESS.md`, `AI_CONTEXT_BACKEND.md` updated per `AI_MASTER.md`.

**How to test:** Read `TRUST_AND_ENCRYPTION.md`; connect BYOC → inspect Mongo `credentials.*` values start with `zenith:enc:v1:`; `pytest tests/test_byoc_encryption.py -q`.

---

**Phase 19 — Platform multi-region storage + page refresh UX** — COMPLETE 2026-06-09

- **Backend:** `platform_storage_catalog.py` serves static bucket/container lists per region slug (`asia`, `us`, `europe`, `africa`). Upload and sync resolve destinations via `resolve_platform_storage_target` with `region_slug`. Sync stale-object removal and file list queries scoped by `cloud_bucket` + `cloud_account` (Azure). New tests: `test_platform_storage_catalog.py`, `test_storage_sync_filters.py`, `test_storage_metering.py`.
- **Frontend:** `CloudDestinationPanel` stacks AWS/GCP/Azure selectors; platform region pills filter catalog entries. Removed per-CSP refresh buttons; **page header Refresh** reloads that page only (`usePageRefresh` + loading toasts). `BucketSelectorLoading` + `minLoadingDelay` show gold bar on all three CSPs during reload. `StorageRegionScopeBar` places region context near upload/files.
- **Render:** Set `PLATFORM_STORAGE_CATALOG_JSON` + upload catalog secret; see `docs/cloud/PLATFORM_STORAGE_REGIONS.md`.
- pytest 320 passed; `npm run build` green.

**How to test:** `/dashboard/storage` → header Refresh → gold bars on AWS/GCP/Azure → buckets listed; upload with region pill → sync → correct file counts per bucket.

---

**Phase 18d — Support Chat UX** — COMPLETE 2026-06-05

- Shared chat-style `SupportThreadPanel` across dashboard, guest, and admin support pages.
- 10s polling (pauses when tab hidden); WebSocket `support_reply` / `support_customer_reply` via `SupportWsBridge` + event bus for instant refresh.
- Backend `ws_notify.py` notifies admins on customer reply; agent reply payload includes `ticket_id`.
- Optimistic send, auto-scroll, sticky composer. pytest 304 passed; build green.

**How to test:** Open `/dashboard/support` and `/admin/support` side by side — reply on each side; thread updates without manual refresh.

---

**Phase 18c — Async Support Tickets** — COMPLETE 2026-06-05

- Replaced one-shot contact flow with MongoDB ticket threads (`support_tickets`, `support_messages`, `support_ticket_otps`).
- APIs: `/api/support/*` (JWT user + guest OTP), `/api/admin/support/*` (admin inbox). `POST /api/contact/submit` creates tickets; legacy admin submissions endpoint secured.
- Emails: OTP, agent reply, resolved, updated auto-reply linking `/support/ticket`.
- Frontend: `SupportTicketPage` (guest OTP), `SupportPage` (dashboard), `AdminSupportPage` (admin). Contact page track link; `SupportReplyListener` for WS `support_reply` notifications.
- Migration script `migrate_contact_to_tickets.py`; integration tests `test_support_api.py` (5 cases). pytest 302 passed; frontend build green.

**How to test:** Contact submit → email with `ZN-…` → `/support/ticket` OTP flow → `/admin/support` reply → customer email + dashboard notification.

---

**Boto3 / Terraform full parity** — COMPLETE 2026-05-30

- Extracted `app/provision/boto3_modules/` (vpc, ec2, s3, iam, cloudwatch, dynamodb, billing) with Terraform-aligned behavior.
- Gaps closed: VPC MapPublicIpOnLaunch, IAM instance profile, DynamoDB SSE + PITR, CloudWatch resource names, AWS Budgets via boto3.
- `engine_resolver` allows billing on boto3; `boto3_drift` checks vpc/iam/billing/dynamodb detail.
- Terraform `main.tf` passes dynamodb capacity/hash_key_type/enable_pitr to module.
- Tests: `test_boto3_composer_parity.py` (17 cases) + updated `test_provision_engine.py`; 153 pytest total.

---

**Provision engine toggle (Boto3 / Terraform)** — COMPLETE 2026-05-30

- Settings `provision_engine` (`boto3` default, `terraform` optional); persisted via `PUT /api/settings/preferences`.
- `engine_resolver.py` picks engine per plan; deployments store `provision_engine`; apply/destroy/drift/remediate branch on engine.
- `boto3_composer.py` modular plan/apply/destroy (s3, dynamodb, vpc, ec2, iam, cloudwatch); `boto3_drift.py` for drift without Terraform workspace.
- Frontend: Settings “Infrastructure provisioning” card; Provision status bar shows engine + hosting hint; wizard labels engine-aware.
- Tests: `tests/test_provision_engine.py` (10 passed).

---

**Phase 19: Isolated ops & hygiene** — COMPLETE 2026-05-29

- CORS production tightening + `CORS_ALLOWED_ORIGINS`; `DEPLOYMENT_SECRETS.md`, `CREDENTIAL_ROTATION.md`, `CLOUD_COST_GUARDRAILS.md`
- Optional Sentry (backend `SENTRY_DSN`, frontend `VITE_SENTRY_DSN`); `.github/workflows/uptime.yml`
- Platform `/api/platform/status` exposes `gcp_credentials_present`; admin **Export audit CSV** on System Health
- Vitest smoke test + CI `npm run test`; `gcp_credentials.py` helper

---

**Enterprise roadmap Phases 19–27** — DOCUMENTED 2026-05-29 (docs only, no code)

- Captured enterprise gap assessment (tenancy, CI/CD, observability, IdP, scale, compliance, cloud parity).
- Wrote **77 numbered checklist items** into `PROGRESS.md`:
  - **19–21** isolated / low dependency (ops, quality+CD, observability) — **do first**
  - **22–27** dependent (org foundation → org-scoped product → SAML/SCIM → scale → commercial → CloudFormation/GCP billing UI)
- Updated `STATUS.md` (phase pointer, deferred → phase map), `SCRATCHPAD.md` (resume at 19.1).
- `PROFESSIONAL_IMPROVEMENTS.md` sync deferred to task **19.9**.

---

**Phase 18d: Notifications, team, SSO, email verify** — COMPLETE 2026-05-29

- `/dashboard/notifications` + persisted `/api/notifications`
- `/dashboard/team` + `/api/organizations` (create org, invites, accept)
- `/invite/:token` public accept flow
- Google SSO (`/api/auth/sso`) + OIDC issuer redirect; admin toggles
- Register sends verification email when `require_email_verification` enabled; login blocked until verified
- `NotificationContext` syncs with API; bell links to full page

---

**Phase 18: Enterprise public pages** — COMPLETE 2026-05-29 (18a–18c + docs hub)

- Tracking: phased plan in `STATUS.md` / `PROGRESS.md` per enterprise page audit
- **18a:** `TrustCenterPage`, `CookiePolicyPage`, `DpaPage`, `CookieConsent`, footer legal links
- **18b:** `StatusPage`, `VerifyEmailPage`, `MaintenanceGate`, `GET /api/platform/status`, `POST /api/auth/verify-email`
- **18c:** `PublicPricingPage` + `marketingPricing.js`, billing success/cancel, `SessionExpiredPage`
- **18d (partial):** `DocsHubPage` → Swagger + Help
- `App.jsx` wraps `MaintenanceGate` + `CookieConsent`; frontend build pass

---

**Phase 15: UI controls & theme wiring** — COMPLETE 2026-05-29

- Theme: `ThemeSync` on login, Settings auto-save, header toggle, `toggleTheme` in context
- CSS: sidebar/header use design tokens; expanded `theme-light.css` for dashboard shell
- BYOC: subscription lookup accepts `username` or `user_id` (fixes enterprise grants)
- Tests: `test_settings_preferences.py`; invalid theme returns 400; **73 pytest** pass

---

**Phase 14c: Provision governance UI (Zenith-scoped)** — COMPLETE 2026-05-29

- ✅ Provision page tabs: Deployments & drift, Activity (audit), Policies, New stack (optional wizard)
- ✅ BYOC gate: if AWS not connected in Settings, single CTA to Settings — no credential forms on Provision
- ✅ Drift history + detail panel; link to cost optimization
- ✅ Admin `provision-roles` page; `GET /provision/policy-rules`
- ✅ Sidebar renamed Infrastructure; deploy wizard notes optimization is on other pages
- ✅ pytest 69, lint 0 errors, build pass

---

**Phase 14b: Provision P0 (tests, BYOC drift, CI validate)** — COMPLETE 2026-05-29

- ✅ `app/provision/byoc_credentials.py` — BYOC-only Terraform env (no platform fallback for scheduled drift)
- ✅ `tasks.py` — scheduled drift resolves owner `user_id` BYOC; skips with audit record when missing
- ✅ `credential_resolver.resolve_credentials()` — fixed missing symbol for provision routes
- ✅ Tests: `test_provision_policy`, `_cost`, `_rbac`, `_tasks`, `_terraform`, `_byoc` (21 tests; 67 total)
- ✅ CI: `terraform-validate` job (`init -backend=false` + `validate`)
- ✅ `provision.css` — `--gold-primary`, `--bg-elevated`, `--border-subtle` tokens

---

**Phase 14: AWS Terraform integration feasibility plan** — COMPLETE 2026-05-29

- Audited Zenith (`backend/terraform/`, `app/provision/`, `ProvisionPage.jsx`) vs standalone `aws using terraform` (Phases 1–16, 308 tests, Next.js ops UI).
- Finding: DEC-019 merge already delivered modules, policy/OPA, wizard API, drift/RBAC/audit, BYOC — ~70% parity; gaps are tests, BYOC on scheduled drift, admin UI for audit/RBAC/policies, cost/VM linkage after deploy.
- Deliverable: `ai-docs/AWS_TERRAFORM_INTEGRATION_PLAN.md` — adopt/skip matrix, P0–P2 roadmap, explicit “do not port” list (Next.js, CLI wizard, CloudShell, GitHub teams.yaml, hardcoded remote state).
- Verdict: **Yes, continue integration** as upstream spec + sync; keep standalone repo for module/tests reference; do not duplicate UI stack.
- Quality: pytest 46, lint 0 errors, build pass; docs-only session (no product code).

---

**Enterprise dashboard UI/UX — pass 3** — COMPLETE 2026-05-29

- ✅ Pass 3 gap table in `UI_UX_AUDIT_2026.md` (layout, headers, contrast, IA, admin)
- ✅ `dashboard-polish.css` — cost nested viewport fix, kickers, back-button, gold CTA text, focus rings
- ✅ `PageHeader` on Storage, Settings, Profile; `CostHubNav` already on cost routes
- ✅ Cost analysis/simulator/optimization: transparent bg, no `100vh` inside dashboard
- ✅ Storage title gradient; Billing empty-state gold SVG
- ✅ Quality gates: pytest 46, lint 0 errors, build pass; pushed `stage`

---

**Secure vault AWS sync (Security page parity with Storage)** — COMPLETE 2026-05-29

- ✅ `POST /api/security/sync/aws`, `syncAwsSecureBucket()`, Security page sync button

---

**Phase 11b: Terraform Integration — Missing Components (OPA Engine, Drift Remediation, RBAC, Audit Logging)**

Status: **COMPLETE** | Started: 2026-05-25 21:25 IST | Finished: 2026-05-25 21:33 IST | Agent: Antigravity Opus

**What was completed (Antigravity Opus — 2026-05-25):**
- ✅ `opa_engine.py` — OPAEngine class + OPAResult dataclass, integrated into policy_checker.py
- ✅ Drift remediation — `remediate_drift()` + `/deployments/{id}/remediate` endpoint
- ✅ RBAC — 4 roles (admin/devops/developer/viewer), `/my-permissions`, `/roles/assign`, `/roles`
- ✅ Audit logging — `audit_logger.py` + `/audit-log` endpoint, all routes instrumented
- ✅ Frontend — role badge, Fix Drift button, RBAC-aware button states
- ✅ Provision endpoints: 10 → 16, Python files: 7 → 10
- ✅ Verified: zero syntax errors, all imports pass, frontend builds (2.13s)
- ✅ Commit `c8a53c4` pushed to `stage`

**What was completed (Antigravity Opus — 2026-05-25):**
- ✅ Copied 28 Terraform files from standalone `aws-provision-using-terraform` project into `backend/terraform/`
- ✅ 7 AWS modules: VPC, EC2, S3, IAM, CloudWatch, Billing, DynamoDB
- ✅ Dual policy engine: 12 YAML security rules + OPA Rego integration
- ✅ Created `backend/app/provision/` module (7 Python files, 10 API endpoints)
- ✅ Terraform CLI wrapper with BYOC credential injection + workspace isolation
- ✅ Cost estimator with Infracost integration + built-in free-tier lookup fallback
- ✅ Drift detector — daily Celery Beat at 06:00 UTC + on-demand button
- ✅ `ProvisionPage.jsx` — 4-step wizard (choose → configure → review → deploy)
- ✅ Glassmorphic CSS matching Zenith design system
- ✅ Sidebar nav item with cloud-deploy icon
- ✅ MongoDB `provision_deployments` collection with 3 indexes
- ✅ AI docs updated: AI_RULES (DEC-019 checklist + collections + beat schedule), DECISIONS (DEC-019), SCRATCHPAD
- ✅ Frontend build passes (2.2s), backend 18/18 tests pass

**What was completed this session (Antigravity — onboarding tour + docs cleanup):**
- ✅ Implemented guided onboarding tour using `react-joyride` with 7 steps
- ✅ Created `OnboardingTour.jsx` component with custom Zenith-styled tooltips
- ✅ Created `onboarding.css` with glassmorphism + gold accent design
- ✅ Welcome modal appears for first-time users with "Start Tour" / "I'll explore" options
- ✅ Tour targets: sidebar nav, global search, cost card, storage, VMs, quick actions, help center
- ✅ Completion tracked in localStorage — only shows once per user
- ✅ "Restart Tour" button added to Settings > Preferences
- ✅ Added `data-tour` attributes to Sidebar.jsx, Header.jsx, DashboardPage.jsx
- ✅ Integrated into DashboardLayout.jsx
- ✅ Deleted 2 redundant AI docs (AGENT_SESSION_TEMPLATE, AI_SYSTEM_PROMPT)
- ✅ Full staleness audit: rewrote AI_CONTEXT.md, updated AI_RULES.md, DECISIONS.md, AI_MASTER.md
- ✅ Updated PROFESSIONAL_IMPROVEMENTS.md: FAQ confirmed done (15/20 items implemented)
- ✅ Build passes, lint: 0 errors / 28 warnings (all pre-existing)

**Previous completed (form validation):**
- ✅ User requested a design-score audit and frontend beautification pass before edits.
- ✅ Initial design score: **78/100** overall. Dashboard concept was strong, but consistency was reduced by legacy hardcoded colors, emoji-like command controls, older purple/blue gradients, and partially upgraded pages.
- ✅ Scope completed: dashboard overview, shared dashboard surfaces, VM cluster page, global search/breadcrumb/loading details, empty states, and obvious token violations.
- ✅ Required order followed: plan documented first, MD files updated, then frontend implementation.
- ✅ Quality gates: `npm run lint` exited 0 with existing warning noise; `npm run build` passed.
- ✅ Validation this session: backend `pytest` passed (`34 passed`), frontend `npm run lint` exited 0, frontend `npm run build` passed, and `scripts/phase9_benchmarks.py` passed with overall status `passed`.

**What was just completed (Frontend UI polish + design audit):**
- ✅ Estimated dashboard/frontend design score improved from **78/100** to **86/100** for the first polished dashboard surfaces.
- ✅ Dashboard overview now uses a stronger glass command surface, tone kicker, SVG refresh/action/activity icons, and tokenized bento accents.
- ✅ VM cluster page now uses Zenith glass cards, tokenized status colors, professional SVG button/disk/empty-state icons, and polished topology/process/metrics cards.
- ✅ Shared UI polished: global search, breadcrumbs, loading, empty states, and base letter spacing now better match the design system.
- ✅ Fixed old global-search routes for Cost Simulator and Cost Optimization so search navigates to the actual dashboard paths.
- ✅ Follow-up production-standard pass raised dashboard-adjacent surfaces to an estimated **91/100** by polishing Cost Simulator, Cost Optimization, Cost Analysis controls, Storage process cards, Profile stats, accessibility focus states, and modal/search semantics.
- ✅ Follow-up cleanup pass reduced frontend lint warnings from **35** to **26**, polished Billing, Legal, and Admin surfaces, and added a final demo runbook in `docs/technical/DEMO_RUNBOOK.md`.
- ✅ Lint configuration now handles JSX component usage correctly; warning count reduced from **354** to **26**.
- ✅ Verification: `npm run lint` exits 0 with remaining pre-existing warnings; `npm run build` passes.

**What was just completed (documentation alignment session):**
- ✅ Clarified that form validation means in-app input validation, not integrating a third-party form product.
- ✅ Recorded the future work split: validation, testing, and CI/CD are separate product-readiness tracks.
- ✅ Updated the AI-facing docs so future agents do not treat planned work as already complete.
- ✅ Kept the startup focus explicit: production-grade UX and release readiness still need implementation, test coverage, and deployment automation.
- ✅ Remaining lint debt: 26 pre-existing warnings remain for a later cleanup pass, mostly around shared context files and a few settings/profile/security hooks.

**What was just completed (form validation implementation):**
- ✅ `frontend/src/utils/formValidation.js` now provides shared validators for login, registration, forgot password, reset password, and contact forms.
- ✅ `frontend/src/pages/LoginPage.jsx`, `RegisterPage.jsx`, `ForgotPasswordPage.jsx`, `ResetPasswordPage.jsx`, and `ContactPage.jsx` now surface field-level errors and disable submit when invalid.
- ✅ `frontend/src/pages/ProfilePage.jsx`, `SettingsPage.jsx`, and `SecuritySettingsPage.jsx` now surface field-level errors and block invalid submissions for profile, recovery, BYOC, and password flows.
- ✅ `frontend/src/styles/auth.css` and `frontend/src/styles/contact.css` now style invalid inputs and inline error text.
- ✅ `frontend/src/styles/profile.css`, `frontend/src/styles/settings.css`, and `frontend/src/styles/security-settings.css` now style invalid inputs and inline error text.
- ✅ Validation was verified with `eslint` on the edited frontend files; no new errors were introduced.

**What was just completed (automated feedback retraining session):**
- ✅ Added true guarded self-retraining from eligible user feedback in `backend/app/ml/retraining.py`.
- ✅ Feedback retraining now trains candidate artifacts from `ml_predictions` + `ml_workload_descriptions` plus synthetic seed data.
- ✅ Candidate artifacts are staged under `backend/app/ml/artifacts/candidates/` and only replace active artifacts if they beat the current feedback baseline by +1% absolute or +2% relative gain.
- ✅ Added manual endpoint: `POST /api/ml/feedback/retrain?minimum_samples=25&deploy=true`.
- ✅ Added Celery task `retrain_ml_models_from_feedback` and weekly schedule at Sunday 03:30 UTC.
- ✅ Upgraded VM workload ML from simple TF-IDF + Logistic Regression to heavier TF-IDF soft-voting ensemble: Logistic Regression + Naive Bayes + Random Forest.
- ✅ Regenerated `workload_classifier.joblib`; artifact model version now `workload_text_ensemble_v2.sample_trained`.
- ✅ Updated `docs/technical/ML_TRAINING_AND_DATASETS.md` with automation, guardrails, and retraining behavior.
- ✅ Verification: `backend/.venv/bin/python -m pytest` → **34 passed**; `scripts/phase9_benchmarks.py` → **overall_status passed**.

**What was just completed (ML/NLP dataset + training session):**
- ✅ Audited ML/NLP truth: storage ensemble was functioning but trained in-memory from synthetic code, not from a visible dataset; workload NLP was functioning but mostly deterministic TextBlob/spaCy/dictionary logic, not a trained project dataset.
- ✅ Added repeatable sample dataset generator in `backend/app/ml/sample_datasets.py`.
- ✅ Added local trainer `backend/scripts/train_sample_ml_models.py`.
- ✅ Generated `backend/app/ml/datasets/storage_tier_training.csv` with **13,824** storage samples.
- ✅ Generated `backend/app/ml/datasets/workload_classification_training.csv` with **600** workload text samples.
- ✅ Trained persisted artifacts: `backend/app/ml/artifacts/storage_ensemble.joblib` and `backend/app/ml/artifacts/workload_classifier.joblib`.
- ✅ `storage_ensemble.py` now prefers trained persisted artifacts when present and falls back safely when missing.
- ✅ `nlp_workload.py` now keeps the report NLP pipeline but adds a trained workload ML signal when artifact exists.
- ✅ Added documentation: `docs/technical/ML_TRAINING_AND_DATASETS.md`.
- ✅ Verification: trainer ran successfully; `backend/.venv/bin/python -m pytest` → **32 passed**; `scripts/phase9_benchmarks.py` → **overall_status passed**.

**What was just completed (PDF parity hardening session):**
- ✅ Re-read `Major Project latest22- Report-5.pdf` against current Phase 5-9 progress.
- ✅ Found one real missed report feature: storage lifecycle demotion still used basic threshold loops instead of report-style priority ranking.
- ✅ `backend/app/storage/tiering_tasks.py` now implements five-factor lifecycle priority scoring: file age, inactivity, access frequency, file type, and estimated cost savings.
- ✅ Lifecycle demotions are sorted by priority before execution; promotions remain conservative one-level moves after >2 accesses in 5 days.
- ✅ Tier transitions now store `last_tier_change`, `tier_transition_count`, `lifecycle_last_action`, and transparent `lifecycle_priority` details.
- ✅ Lifecycle optimizer writes activity-log audit entries and daily `storage_lifecycle_reports` summaries.
- ✅ Added lifecycle indexes in `mongo_client.ensure_indexes()`.
- ✅ Fixed stale NLP test expectation so TensorFlow/GPU workloads align with report Phase 9 AI/ML cluster taxonomy.
- ✅ Verification: `backend/.venv/bin/python -m pytest` → **30 passed**; `scripts/phase9_benchmarks.py` → **overall_status passed**.

**What was just completed (Phase 9 parity session):**
- ✅ Re-read `Major Project latest22- Report-5.pdf` Chapter 4 and Chapter 6 against current code.
- ✅ VM taxonomy now matches report §4.1: `general`, `storage`, `memory`, `performance`, and `ai_ml` are first-class `ClusterType` values.
- ✅ NLP workload analysis now returns deployable five-cluster assignments instead of collapsing memory/performance/AI-ML back to `general`.
- ✅ VM assignment/migration can run in local/demo mode without GCP credentials by using simulated VM assignment records.
- ✅ Cluster health includes report-style multi-factor `S_eff_v1` efficiency scoring.
- ✅ Cost forecasting now uses decay-weighted linear regression via `backend/app/cost/forecasting.py`.
- ✅ Added `backend/scripts/phase9_benchmarks.py` to validate storage ensemble accuracy, five-cluster NLP routing, and decay-weighted cost responsiveness.
- ✅ Installed local NLP runtime packages into `venv`: `textblob`, `spacy`, and `en_core_web_sm`.
- ✅ Verification: Phase 9 benchmark overall status `passed`; storage ensemble sample accuracy `1.0`; five workload cluster cases `5/5`; decay-weighted 7-day forecast responds above unweighted baseline.

**What was just completed (Phase 8 session):**
- ✅ `backend/app/ml/feedback.py` — outcome evaluation for `ml_predictions` + `ml_workload_descriptions` using the report's 7-30 day window.
- ✅ Data quality filtering — only evaluated samples with `feedback_score >= 0.5` become training-eligible.
- ✅ Retraining readiness — computes eligible sample counts, current feedback accuracy, and deployment guardrails (+1% absolute or +2% relative gain required).
- ✅ `backend/app/ml/routes_feedback.py` — `/api/ml/feedback/evaluate`, `/readiness`, `/training-dataset`, `/retraining-snapshot`.
- ✅ `backend/app/ml/tasks_feedback.py` + Celery Beat — daily low-cost feedback evaluation and retraining readiness snapshot.
- ✅ MongoDB indexes for feedback score and retraining snapshots.
- ✅ Tests: `backend/tests/test_ml_feedback.py`; **28 backend pytest pass**.

**What was just completed (Phase 7 session):**
- ✅ `backend/app/ml/storage_ensemble.py` — 10-feature storage vector, Random Forest expert, XGBoost expert with sklearn gradient-boosting fallback when `xgboost` is absent, weighted voting 30/35/35.
- ✅ `backend/requirements.txt` — pinned `xgboost==3.2.0`; local macOS runtime verified with Homebrew `libomp`.
- ✅ `backend/app/storage/optimizer.py` — storage analysis now returns ensemble tier, confidence, `expert_votes[]`, `tier_scores`, feature metadata, and still preserves `recommendation` + `options_by_csp`.
- ✅ `backend/app/ml/repository.py` — Phase 7 ensemble prediction logs stored through existing `ml_predictions` contract.
- ✅ `backend/app/storage/routes_storage.py` — `/api/storage/analyze` logs ensemble predictions instead of rule-only predictions.
- ✅ `frontend/src/pages/StoragePage.jsx` + `storage.css` — recommendation modal shows ensemble confidence and individual expert votes.
- ✅ Tests: `backend/tests/test_storage_ensemble.py` + expanded `test_ml_foundation.py`; **25 backend pytest pass**, frontend production build passes.

**What was just completed (Phase 6 session):**
- ✅ `backend/app/vm/nlp_workload.py` — TextBlob sentiment/urgency, spaCy NER (optional), tech dictionaries, negation, confidence boost
- ✅ `workload_analyzer.py` — uses NLP pipeline (`nlp_v1`) with keyword fallback
- ✅ `POST /api/vm/analyze-workload` — preview classification without provisioning VM
- ✅ Workload readiness bar + guided follow-up Q&A in VM request modal (`WorkloadGuidancePanel`, `workload_guidance.py`)
- ✅ Workload guidance + VM modals aligned with Zenith tokens, glassmorphism, light theme (`vmcluster.css`, `theme-light.css`)
- ✅ ML logs store `nlp_features` + `classifier_version` on VM assign
- ✅ `textblob` + `spacy` + `en_core_web_sm` wheel in `requirements.txt`; **17 pytest pass**
- ✅ Render `buildCommand`: `pip install -r requirements.txt` (installs NER model for all users — no client download)

**What was just completed (Phase 5 session):**
- ✅ Frozen report contracts for §4.1–§4.5 documented below + `backend/app/ml/acceptance.py`
- ✅ `backend/app/ml/` — models, acceptance constants, repository (`ml_predictions`, `ml_workload_descriptions`)
- ✅ MongoDB indexes for ML collections in `mongo_client.ensure_indexes()`
- ✅ Logging hooks: storage analyze → rule-only prediction log; VM assign → workload classification log
- ✅ Tests: `backend/tests/test_ml_foundation.py` (12 pytest total pass)

**What was just completed (report cross-check session):**
- ✅ Parsed `Major Project latest22- Report-5.pdf` and compared claimed NLP/ML vs code.
- ✅ Report-vs-code gap matrix lives in **this file** (section below).
- ✅ Reframed implementation into **Phase 5 → Phase 10** roadmap.
- ✅ Corrected backlog: VM/cost/session modules are partially implemented, not fully missing.

**What was just completed (recovery contacts session):**
- ✅ **Profile → Password recovery:** `recovery_email`, `phone`, `recovery_phone` (alternate mobile)
- ✅ **Forgot password enforcement:** Identifier must match username, login email, or recovery email; reset link sent only to recovery email when set
- ✅ **SMS path fixes:** E.164 normalization (+91 for 10-digit IN), Twilio `is_sms_configured()` check, actionable `hint` in API/UI when SMS cannot send
- ✅ **Tests:** `backend/tests/test_password_recovery.py` (7 pytest total pass)

**What was just completed (prior session):**
- ✅ **Security Settings UI:** Restyled password, 2FA, and sign-in sections to match dashboard/settings (glass cards, gold tokens).
- ✅ **Change password fix:** Backend now verifies/updates `hashed_password` (same field as login) via `auth_utils`.
- ✅ **Sessions UX:** “This device” card + collapsible other sign-ins (no endless unknown-device list).
- ✅ **Audit log (professional pattern):** Settings shows 30-day **summary stats** + **3 recent events** only; full history in modal with filters (auth/security/account) + pagination; backend dedupes repeat events within 30 min.
- ✅ **Login metadata:** User-Agent + client IP on new sign-ins.
- ✅ **Session revoke fix:** Works with UUID session IDs.

**What was just completed (Phase 4 earlier):**
- ✅ **AWS Storage Sync:** Added `POST /api/storage/sync/aws` to reconcile S3 objects → MongoDB metadata (free-tier friendly, on-demand).
- ✅ **Storage UI Sync Button:** Added “Sync with Bucket (AWS)” button on Storage page.
- ✅ **BYOC AWS IAM Role support for sync:** Credential resolver now returns temporary STS credentials when BYOC is configured with IAM role.
- ✅ **Security Alerts (Email + SMS):** Daily Celery task `check_security_alerts` sends Gmail SMTP email + Twilio SMS (if configured) when sensitive files are not encrypted.
- ✅ **Database Indexes:** Implemented `ensure_indexes()` in `mongo_client.py` for core collections.
- ✅ **Render deployment config:** Added `render.yaml` for backend service.
- ✅ **Quality gates:** Backend `pytest` passed (via `backend/.venv`), frontend `npm run lint` passed.

**Next immediate step:** Remaining professional improvements (see `PROFESSIONAL_IMPROVEMENTS.md`): backend test expansion, CI/CD pipeline, FAQ page, and security hardening.

**What was completed (form validation by Copilot, audited + fixed by Antigravity):**
- ✅ `frontend/src/utils/formValidation.js` — shared validators. **Antigravity fix:** removed registration-strength rules from login form.
- ✅ All auth, profile, recovery, BYOC, and security forms now have inline validation.
- ✅ `backend/app/admin/routes_admin.py` — admin CRUD. **Antigravity fixes:** self-protection guards, DeleteResult bug, audit-log paging, .dict() deprecation.
- ✅ `backend/app/vm/routes_vm.py` — /transfer alias. **Antigravity fix:** delegates to migrate_vm() instead of copy-paste.

## 🙂 Recent AI Work — Quick Faces

- 😀 : Fixed login button critical bug (Copilot over-validated login form) — Antigravity
- 😀 : Completed 7-session Copilot code audit, fixed 3 moderate + 2 minor issues — Antigravity
- 🙂 : Rewrote PROFESSIONAL_IMPROVEMENTS.md (945 lines → focused 6-item list) — Antigravity
- 😀 : Completed adding `/api/vm/transfer` alias endpoint so legacy frontend calls succeed
- 🙂 : Added admin CRUD endpoints: create user, delete (soft/hard), change role, bulk actions

## ✅ Validation

- ✅ : Backend unit tests: `34 passed` (validated 2026-05-25, Antigravity)
- ✅ : Frontend lint: `0 errors, 11 warnings` (validated 2026-05-25, Antigravity)
- ✅ : Frontend build: passes in ~2s (validated 2026-05-25, Antigravity)
- ✅ : Python syntax check: both `routes_admin.py` and `routes_vm.py` compile cleanly


**Also completed:** Forgot password flow (email reset link + SMS OTP) with recovery-contact validation.

---

## 🗺️ ROADMAP & TRACKER

### Product Readiness Backlog
- [x] Form validation framework across auth, settings, profile, billing, and admin forms.
- [ ] Backend re-validation and shared request schemas for every user-facing form.
- [ ] Test suite foundation: unit, integration, and API tests for the highest-risk flows.
- [ ] CI/CD pipeline with build, lint, test, and deployment stages.
- [ ] Release hygiene: staged preview checks, rollback plan, and operational monitoring notes.

### Phase 1: UI/UX Polish ✅ COMPLETE
- [x] Global Design Tokens & Micro-Animations (`index.css`)
- [x] Dashboard Stat Cards (`dashboard-enhanced.css`) — color-coded, staggered animations
- [x] Sidebar Polish (`sidebar.css`)
- [x] Dashboard Header (`dashboard.css`)
- [x] Footer Overhaul (`footer.css`)
- [x] Build verification — `vite build` passes

### Phase 2: Backend + BYOC + Infrastructure ✅ COMPLETE
- [x] BYOC Encryption Service (`AES-256-GCM`)
- [x] BYOC Credential Resolver
- [x] BYOC API Routes (status, connect, test, disconnect)
- [x] True IAM Role support via STS AssumeRole (No access keys exchanged)
- [x] Frontend BYOC UI in SettingsPage (Quick Setup / Secure Setup)
- [x] CloudAMQP broker URL configured
- [x] Gmail SMTP configured
- [x] Fixed `list_vms()` 500 error with MongoDB fallback
- [x] Full API endpoint audit (25/25 endpoints passing)
- [x] Premium `NotFoundPage.jsx` (Animated 404 with particles, glitch text)

### Phase 2.5: "Mission Control" Dashboard Redesign ✅ COMPLETE
*Transformed the generic sidebar+content layout into a unique command center.*
- [x] Install Recharts charting library
- [x] Sidebar → 56px icon-only rail (hover-expand to 220px)
- [x] Bento grid layout (varying card sizes: 2-col cost card, 1-col others)
- [x] Sparkline area chart in Cost Overview card (gold gradient, 7-day trend)
- [x] Circular progress rings (Storage Used, VM Health)
- [x] Animated number counters (`useCountUp` hook)
- [x] Time-aware personalized greeting ("Good afternoon, Prithivi 🌤️")
- [x] Horizontal scrolling activity timeline
- [x] Header upgrade (search bar, Zenith brand badge, remove redundant greeting)
- [x] Mobile bottom tab bar (< 768px)

### Phase 3: Settings Page — Make Everything Functional ✅ COMPLETE
*Settings toggles now actually affect the app. Theme switching, preferences context, and billing cleanup done.*
- [x] Theme System (Dark ↔ Light ↔ Auto) with `ThemeContext.jsx`
- [x] Preferences Context (Currency, Date Format, Timezone) with `PreferencesContext.jsx`
- [x] Notification Preferences (Coming Soon badge on Weekly Reports; data model ready for email gating)
- [x] Billing & Payment Cleanup (Replaced fake billing with honest "Free Plan" display)
- [x] Mark unimplemented settings (Language, Weekly Reports) as "Coming Soon"
- [x] Settings page bug fix (state/hook name collision)
- [x] Settings CSS audit (design tokens, glassmorphism, hover states)
- [x] Dashboard integration (currency symbol, date format from preferences)
- [x] Backend endpoint (`GET /settings/preferences-summary`)

### Phase 12: Security Research Paper Parity 🔲 NEXT (see `PHASE_12_SECURITY_RESEARCH_PARITY.md`)

**Server-side (SSE-S3 — sufficient; KMS not required):**
- [ ] Document & complete **SSE-S3** pipeline (`ServerSideEncryption='AES256'`) — see spec §2
- [ ] **Auto SSE-S3** when sensitive data detected (no forced modal for default path)
- [ ] UI badges: **SSE** / **CSE** / **None** (not “KMS”)

**Client-side (browser architecture — currently missing):**
- [ ] Add `frontend/src/utils/clientEncryption.js` (Web Crypto: PBKDF2 + AES-256-CBC)
- [ ] Encrypt before upload; **password never sent to API**
- [ ] Browser decrypt on download; fix `docs/security/CLIENT_SIDE_ENCRYPTION.md`

**Other:**
- [ ] `sensitive_file_detector.py` — CC, PII, private IP + benchmark tests
- [ ] Session geolocation + device fingerprint
- [ ] Replication strategy documented (dual-bucket OK for Phase 12)
- [x] Secure vault AWS sync (2026-05-29)

### Phase 4: Remaining Platform Features 🔲 IN PROGRESS
- [x] **Storage Sync (AWS):** "Sync with Bucket" button — `s3.list_objects_v2()` → reconcile with MongoDB (free-tier friendly, no SNS/SQS).
- [ ] **Cost Module:** Cost anomaly detection, multi-cloud aggregation, forecasts.
- [ ] **VM Module:** GCP service account integration, VM metrics collection, workload analyzer.
- [x] **Security Alerts (email + SMS):** Daily Celery task for unencrypted sensitive files (Twilio optional).
- [x] **Security Module (partial):** Paginated audit log API + summary UX on Security Settings.
- [ ] **Security Module:** Audit log CSV export (optional).
- [ ] **Admin Panel:** User management actions, system health monitoring, email templates.
- [x] **Deployment (partial):** Render/Vercel config.

### Phase 5: Report Parity Foundation ✅ COMPLETE
- [x] Freeze report acceptance criteria per module (§4.1–§4.5) — see **Phase 5 contracts** below
- [x] Add model logging schemas/collections (`ml_predictions`, `ml_workload_descriptions`)
- [x] Define measurable validation metrics — `backend/app/ml/acceptance.py`
- [x] MongoDB indexes + rule-only / keyword logging hooks

#### Phase 5 contracts (frozen — report §4.1–§4.5)

| Section | Input → Output | Metrics / code |
|---------|----------------|----------------|
| **§4.1 NLP** (Phase 6) | `workload_description` → cluster + confidence 0–100 | Auto-assign if ≥85%; training samples word_count ≥10; code: `workload_analyzer.py`, logs `ml_workload_descriptions` |
| **§4.2 Ensemble** (Phase 7) | file metadata → tier + CSP + `expert_votes[]` | Weights 30/35/35; targets 89.3% ensemble; code: `optimizer.py` + `ml/repository.py`, logs `ml_predictions` |
| **§4.3 Lifecycle** | file inventory → tier transitions | 30d hot→warm, 90d warm→cold, promotion >2 accesses in 5d; code: `tiering_tasks.py` |
| **§4.4 Security** | — | SSE-S3 partial; **browser CSE architecture missing**; **Phase 12**: auto SSE, Web Crypto CSE, detector, geo — see `PHASE_12_SECURITY_RESEARCH_PARITY.md` §2–§3 |
| **§4.5 Feedback** (Phase 8) | predictions → outcome | Eval 7–30d; feedback_score ≥0.5; deploy if +1% abs or +2% rel gain |

**ML code paths:** `backend/app/ml/models.py`, `acceptance.py`, `repository.py` · **Collections:** `ml_predictions`, `ml_workload_descriptions`

### Phase 6: NLP Workload Intelligence ✅ COMPLETE
- [x] TextBlob sentiment + urgency scoring
- [x] spaCy NER + technology dictionaries + negation handling
- [x] Confidence boost + VM assignment integration (`nlp_v1`)
- [x] `POST /api/vm/analyze-workload` preview endpoint

### Phase 7: Ensemble Storage ML ✅ COMPLETE
- [x] Add Random Forest expert.
- [x] Add XGBoost expert.
- [x] Add weighted ensemble voting (rule 30% + RF 35% + XGB 35%).
- [x] Surface `expert_votes[]`, `tier_scores`, and `ensemble_confidence` in API response and UI.
- [x] Log ensemble predictions to `ml_predictions` for Phase 8 feedback evaluation.

### Phase 8: Feedback Retraining Loop ✅ COMPLETE
- [x] Outcome evaluation windows (7/30 days) for predictions.
- [x] Data quality filtering and dataset extraction.
- [x] Scheduled feedback evaluation + guarded retraining readiness criteria.
- [x] API endpoints for evaluation, readiness, training dataset inspection, and retraining snapshots.

### Phase 9: VM/Cost Deepening & Validation ✅ CORE COMPLETE
- [x] Align VM cluster taxonomy with report (General, Storage, Memory, Performance, AI/ML).
- [x] Upgrade cost model behavior toward report methodology (decay-weighted linear regression).
- [x] Add benchmark scripts to validate claimed accuracy/cost impact.
- [x] Add report-style multi-factor VM efficiency scoring (`S_eff_v1`).
- [x] Add report-style five-factor storage lifecycle priority scoring + audit/report metadata.
- [ ] Optional: replace synthetic benchmark baselines with larger real production feedback datasets.

### Phase 10: Hardening & Final Handoff ✅ COMPLETE
- [x] Full docs/API parity pass.
- [x] Security/observability hardening.
- [x] End-to-end final validation + demo runbook.

---

## ✅ Completed Features (What's Working — Code Exists)

| Area | Feature | Status | Files |
|------|---------|--------|-------|
| Auth | User registration (username + email + password) | ✅ Code exists | `auth/routes_auth.py`, `auth/auth_service.py` |
| Auth | JWT login (OAuth2 form → token) | ✅ Code exists | `auth/routes_auth.py`, `auth/auth_utils.py` |
| 2FA | Enable/Finalize/Verify/Disable 2FA | ✅ Code exists | `security/routes_2fa.py` |
| BYOC | Connect/Test/Disconnect with IAM/STS support | ✅ Code exists | `byoc/routes_byoc.py`, `byoc/encryption.py` |
| Storage | Rule-based file analysis (scoring → tier + CSP) | ✅ Code exists | `storage/optimizer.py` |
| Storage | Multi-cloud upload (AWS, GCP, Azure) | ✅ Code exists | `storage/uploader.py` |
| Storage | File listing, download, delete | ✅ Code exists | `storage/routes_storage.py`, `storage/manager.py` |
| Security | Vault UI + 2FA + **SSE-S3** (manual path) + server-labeled “CSE” + scan/sync | ⚠️ Partial — **Phase 12**: auto SSE, **browser CSE**, detector | `PHASE_12_SECURITY_RESEARCH_PARITY.md` §2–§3 |
| Celery | process_secure_file + nightly tiering | ✅ Code exists | `storage/tasks.py`, `storage/tiering_tasks.py` |
| WebSocket | Real-time notifications | ✅ Code exists | `websockets/routes_ws.py` |
| Config | pydantic_settings + MongoDB client | ✅ Code exists | `utils/config.py`, `database/mongo_client.py` |
| ML Foundation | Prediction/workload log schemas + indexes | ✅ Phase 5 | `ml/models.py`, `ml/repository.py`, `ml/acceptance.py` |
| ML Ensemble | Rule + Random Forest + XGBoost-style weighted storage prediction | ✅ Phase 7 | `ml/storage_ensemble.py`, `storage/optimizer.py` |
| ML Feedback | Outcome evaluation + retraining readiness | ✅ Phase 8 | `ml/feedback.py`, `ml/routes_feedback.py`, `ml/tasks_feedback.py` |
| VM Intelligence | Five-cluster NLP assignment + `S_eff_v1` health scoring | ✅ Phase 9 | `vm/models.py`, `vm/nlp_workload.py`, `vm/manager.py` |
| Cost Forecasting | Decay-weighted linear regression forecast model | ✅ Phase 9 | `cost/forecasting.py`, `cost/routes_forecast.py` |
| Benchmarks | Report-parity validation script | ✅ Phase 9 | `scripts/phase9_benchmarks.py` |

---

## Report vs Code (`Major Project latest22- Report-5.pdf`)

Reference: 97-page project report (Chapter 4–6). Last cross-check: 2026-05-24.

### Claims vs implementation

| Report capability | Expected (report) | Current code | Gap |
|-------------------|-------------------|--------------|-----|
| NLP workload classification (§4.1) | TextBlob + spaCy + tech dictionaries + negation + confidence boost | **Present** — `nlp_workload.py` + `nlp_v1`; local `venv` has TextBlob/spaCy model installed | Mostly aligned |
| VM cluster assignment (§4.1/§4.3) | General/Storage/Memory/Performance/AI-ML + scaling | **Present** — five `ClusterType` values, five VM pools, simulated local assignment when GCP is not configured | Real GCP pool provisioning remains environment-dependent |
| Ensemble storage (§4.2) | Rule 30% + RF 35% + XGB 35% (~89.3%) | **Present** — `storage_ensemble.py` + `optimizer.py`; benchmark script validates sample accuracy | Mostly aligned |
| Lifecycle tiering (§4.3) | Multi-factor demotion + conservative promotion | **Mostly present** — `tiering_tasks.py` | Explicit 5-factor priority queue → Phase 9 |
| Session management (§4.4) | Device/IP tracking + remote revoke | **Present** — `routes_profile.py` | Mostly aligned |
| Cost forecast + anomaly (§5/§6) | Decay-weighted forecasting + anomaly + aggregation | **Present** — `cost/forecasting.py` uses decay-weighted linear regression; anomaly remains Z-score | Optional advanced anomaly model later |
| Feedback retraining (§4.5) | Outcome eval + quality filter + retrain + gated deploy | **Present** — evaluation window, quality filter, readiness snapshot, guarded deploy criteria | Actual model artifact retraining can be expanded after real feedback volume |

### What is actually working (post-recovery)

1. VM API — assignment, migration, cluster metrics, load prediction endpoints.
2. Cost module — forecast + anomaly APIs + Celery anomaly task.
3. Storage lifecycle — Celery hot/warm/cold demotion and promotion.
4. Auth extras — password reset, recovery contacts, sessions, audit log UX.

### Still needed for full report parity

1. Optional real model artifact hot-swap after enough feedback volume exists.
2. Larger benchmark datasets derived from actual user/cloud telemetry.
3. Final demo runbook and screenshots for handoff.

---

## Archived phase checklists (2026-05-29)

> Moved from `PROGRESS.md` to reduce startup token load. Item numbers unchanged.

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

## Phase 20.5 — CI/CD enterprise gates

*Depends on: Phase 20 complete. **Blocks recommended start of Phase 21** (deploy safety before adding observability). Full gap map: `docs/testing/PHASE_20_5_CI_GATES.md`.*

- [ ] **20.5.1** — CI-gated stage deploy (`workflow_run` after CI success on `stage`)
- [ ] **20.5.2** — Playwright required in CI (remove `continue-on-error`); update `BRANCH_PROTECTION.md`
- [ ] **20.5.3** — Backend coverage gate (`--cov-fail-under=40`, ratchet quarterly)
- [ ] **20.5.4** — Post-deploy stage smoke (`STAGE_API_URL` → `/health` + `/api/platform/status`)
- [ ] **20.5.5** — ESLint `--max-warnings 0` in CI (fix current warnings)
- [ ] **20.5.6** — Dependabot (`.github/dependabot.yml` npm + pip)
- [ ] **20.5.7** — `pip-audit` + `npm audit` (fail high/critical) in CI
- [ ] **20.5.8** — CodeQL workflow (Python + JavaScript)
- [ ] **20.5.9** — Gitleaks (or equivalent) on pull_request
- [ ] **20.5.10** — Apply GitHub branch protection for `stage` per doc
- [ ] **20.5.11** — Default branch + `render-keep-alive` on deploy branch
- [ ] **20.5.12** — Terraform `plan` on PR (read-only; completes 20.16 plan gap)
- [ ] **20.5.13** — Doc: Celery/Redis CI deferred to Phase 25
- [ ] **20.5.14** — *(Optional)* OpenAPI snapshot tests
- [ ] **20.5.15** — *(Optional)* Trivy scan `backend/Dockerfile`

---

## Phase 21 — Observability & runbooks

*Depends on: 19.4–19.5 Sentry recommended first; **20.5** deploy gates recommended.*

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

*Depends on: Phase 19–**20.5**–21 ops baseline. **Blocks Phase 23–26.***

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

## Multi-cloud parity — Phase 3 (2026-06-03)

**Goal:** BYOC onboarding parity — verify, discovery, Terraform resolver.

**Completed:**
- `POST /verify-credentials` for GCP (SA JSON + bucket list) and Azure (storage + optional Cost Management check).
- `GET /gcp-buckets`, `POST /gcp-buckets/discover`, `GET /azure-containers`, `POST /azure-containers/discover`.
- `resolve_credentials(username, provider)` returns GCP/Azure BYOC shapes for Terraform (`GOOGLE_CREDENTIALS`, `ARM_*` env).
- Settings BYOC: verify-before-connect for GCP/Azure with bucket/container dropdowns.
- Tests: extended `test_byoc_api.py`, `test_byoc_terraform_resolver.py`; 251 pytest green.

**Next:** Phase 4 — secure vault multi-cloud.

---

## Multi-cloud parity — Phase 4 (2026-06-03)

**Goal:** Secure vault on AWS, GCP, and Azure with consistent `csp` metadata.

**Completed:**
- `app/storage/secure_vault.py` — `SecureGcpStorage`, `SecureAzureStorage`, vault CRUD helpers.
- `routes_security.py` — `POST /security/sync/{csp}`, tri-cloud upload/list/download/delete.
- Frontend `syncSecureVault`, upload `csp`; `SECURE_VAULT_REPLICATION.md`; DEC-025.
- OPA stubs `gcp_security.rego`, `azure_security.rego`; 253 pytest green.

**Next:** Phase 5 — VM AWS parity.

---

## Multi-cloud parity — Phase 5 (2026-06-03)

**Goal:** AWS EC2 VM lifecycle parity with existing GCP VM Cluster API.

**Completed:**
- `aws_manager.py`, `aws_runtime.py`, `vm_provider.py`, `aws_metrics.py`.
- `routes_vm.py` + `manager.py` dispatch by `csp`; Azure request returns 501.
- `VMClusterPage.jsx` cloud provider toolbar; `test_vm_api.py`.
- 257 pytest green.

**Next:** Phase 6 — provision GCP/Azure.

---

## Multi-cloud parity — Phase 6 (2026-06-03)

**Goal:** Terraform plan/apply/destroy for GCP and Azure BYOC via `/api/provision`.

**Completed:**
- `terraform/gcp` (GCS), `terraform/azure` (Blob), `terraform_roots.py`.
- `resolve_provision_terraform_env`, engine forces TF for non-AWS.
- `provision_catalog.py`, `ProvisionConfig.csp`, wizard provider UI.
- 260 pytest green.

**Next:** Phase 7 — pricing / docs closure.

---

## Multi-cloud parity — Phase 7 (2026-06-03)

**Goal:** Cross-cutting polish per parity plan — platform health, docs, Phase 27 closure.

**Completed:**
- `cloud_connectivity` on public platform status (env probes per CSP/feature).
- Profile avatar upload explicit 501; `PRICING_DATA_SOURCE.md`, `VM_MULTI_CLOUD_SCOPE.md`.
- Razorpay navigates to `/billing/success` and `/billing/cancel`.
- `AI_CONTEXT_BACKEND.md` tri-cloud refresh; Tier I E2E playbook; DEC-028.

**Outcome:** Phases **0–7** complete. Deferred: 27.1 CloudFormation UI, 27.2 bucket migration wizard, Azure VM Compute.

---

## Multi-cloud parity — Phase 2 (2026-06-03)

**Goal:** Cost analysis + budgets behave like AWS when GCP/Azure billing credentials exist.

**Completed:**
- Settings: `GCP_BILLING_DATASET_ID`, `GCP_BILLING_TABLE_ID`, `AZURE_SUBSCRIPTION_ID`.
- `billing_config.py` / `billing_setup.py` — resolve + persist BYOC billing fields.
- APIs: `GET /api/cost/setup/{provider}`, `PUT /api/cost/setup/gcp`, `PUT /api/cost/setup/azure`.
- `resolve_azure_credentials` exposes Cost Management fields; manager uses shared config helpers.
- Cost routes return `configured` + `group_by_supported`; billing probe no longer marks demo as “live” when off.
- Cost Analysis page: setup wizard panel, `getApiErrorMessage`, AWS-only granularity note.
- Tests: `test_billing_setup.py`, `test_billing_setup_api.py`; 243 pytest green.

**Next:** Phase 3 — BYOC verify + discovery parity.

---

## Multi-cloud parity — Phase 1 (2026-06-03)

**Goal:** Standard storage tri-cloud hardening — same UX as AWS when credentials exist.

**Completed:**
- `storage_tiers.py` — shared hot/warm/cold names (ML labels + provider API classes); tiering uses `normalize_provider`.
- `storage_errors.py` — `missing_config` payloads for GCP/Azure sync; `restore_not_supported` (501).
- Restore API: `POST /restore/{csp}/{filename}` (AWS Glacier); legacy `/restore-aws/` alias; DEC-024.
- Uploader maps accept short GCP/Azure class names; integration tests for GCP/Azure upload/delete/download/sync/restore.
- Frontend: `getApiErrorMessage` includes `setup_steps`; StoragePage uses structured errors; restore uses CSP-aware path (AWS-only button).
- Matrix + DECISIONS updated.

**Verification:** `pytest -q` → 236 passed.

**Next:** Phase 2 — cost/billing GCP BigQuery + Azure Cost Management.

---

## Multi-cloud parity — Phase 0 (2026-06-03)

**Goal:** Single source of truth for tri-cloud parity before feature phases 1–7.

**Completed:**
- Added `docs/cloud/MULTI_CLOUD_PARITY_MATRIX.md` (area matrix + per-endpoint checklist with phase ownership).
- Added `docs/cloud/CREDENTIAL_CONTRACT.md` (platform `.env`, BYOC fields, manual smoke steps).
- Removed stale duplicate package `backend/cost/` (no imports; canonical `app/cost/`).
- Introduced `app/cloud/providers.py` with `normalize_provider()` / `normalize_provider_key()`; wired storage upload to accept aliases (`aws`, `gcp`, etc.).
- Tests: `test_cloud_providers.py`, `test_cloud_routing.py`, extended `test_storage_api.py` (GCP upload smoke).
- Paused Phase 20.5.10 (branch protection) per parity plan; tracking docs updated.

**Verification:** `pytest -q` → 218 passed.

**Next:** Phase 1 — storage tri-cloud hardening (tiering audit, restore API, frontend errors).

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

---

## 2026-06-14 — Phases 25–30: Mobile friendliness + Desktop download

**Phase 25:** Standardized zenith-modal breakpoints (480/768), mobile rules for plan-upgrade drawer (bottom sheet + scroll lock), secure-upload-wizard, cards, dashboard-polish; UI_UX_AUDIT mobile checklist.

**Phase 26:** Rolled `data-card-table` + `data-label` to FileList, SecureFileList, Cost Analysis, Team member grid, Admin tables, Provision cost estimate.

**Phase 27:** Mobile 3-step tips sheet (OnboardingTour), provision sticky actions, settings BYOC stacking, VM header actions; Playwright dashboard bottom-nav + manual_testing 6.13–6.14.

**Phase 28:** `desktop/` Electron package loading `https://rajverse.me`; README + root docs.

**Phase 29:** `/download` page, `releases.json`, `detectPlatform.js`, marketing nav/footer/sitemap, `desktop-release.yml` GitHub Actions matrix.

**Phase 30:** `docs/desktop/INSTALL.md`, `SIGNING.md`, Trust Center desktop section, `electron-updater` stub in packaged builds.

**Git:** six commits on `stage` (Phases 25–30).

---

## 2026-07-11 — Post–Stage 1 polish: UX, notifications, help, desktop v0.1.4

**Password UX (8-char minimum):**
- Added `PasswordRequirementsPanel.jsx` + `password-requirements.css` — live checklist on register, reset, security-settings
- Frontend: `formValidation.js`, `passwordPolicy.js`, `clientEncryption.js` aligned to min 8
- Backend: `password_policy.py`, `user_model.py`, `routes_password_reset.py` — min 8 with strength rules

**Action feedback (notifications):**
- Rewrote `utils/notifications.js` — top-right React Toastify banners + notification bell entries
- `ToastContainer` in `App.jsx` for public pages; `useNotifications` hook for dashboard pages
- Migrated: `SecuritySettingsPage`, `TeamPage`, `SupportPage`, admin pages, `FileList`, `SecureFileList`, `EncryptionChoiceModal`, `ContactPage`, `SupportTicketPage`

**Help & support unification:**
- `HelpCenterPage.jsx` — tabs: Help articles | My tickets (`?tab=tickets`)
- New `SupportTicketsSection.jsx`; `SupportPage.jsx` redirects to `/help?tab=tickets`
- `PATHS.help` → `/help`, `PATHS.support` → `/help?tab=tickets`
- `ProfileDropdown.jsx` — single “Help & support” item; compact CSS (no scroll bleed-through)
- `dashboardNavConfig.jsx` — sidebar “Help & Support” → `/help`

**Production fixes:**
- `SettingsPage.jsx` — missing `CloudProviderLogo` import (rajverse.me crash)
- API proxy through rajverse.me; cold-start login warm-up; admin portal gate for platform owner

**Desktop v0.1.4:**
- Bumped `desktop/package.json` to 0.1.4; pre-updated `frontend/public/releases.json`
- Tag `desktop-v0.1.4` → CI built DMG, EXE, AppImage, deb; CI committed checksums to `releases.json`
- Fixed `frontend/package-lock.json` out-of-sync (desktop-release `npm ci` failure on first attempt)

**Lint / scripts:**
- `SecuritySettingsPage` — `fetchSecuritySettings` wrapped in `useCallback`
- `AdminOverviewPage` — removed unused `notifyAdminSuccess` import
- Bash launch scripts: `start_all.sh`, `backend/scripts/start-celery.sh`, `docs/setup/setup_cost_features.sh`

**Git:** `stage` @ `97171c0` (commits `47e20fb` … `97171c0`)

