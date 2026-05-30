# DECISIONS.md — Architecture Decision Log (Verified)

> Record all significant architectural or design decisions here. Append only.
> **Read before making ANY structural, module-level, or library change.**

---

## ⚡ Before You Code — Quick Checklist

> Use this first. Only read the full entries below if you need detail.

| Scenario | Decision | See |
|----------|----------|-----|
| Adding a new database? | MongoDB only — no Postgres, DynamoDB, Redis | DEC-002 |
| Choosing a storage provider? | AWS S3 primary, GCP/Azure secondary | DEC-003 |
| Adding frontend state management? | React Context ONLY — no Redux, no Zustand | DEC-012 |
| Changing ML model or retraining? | Guarded retraining — don't auto-deploy, must beat +1% absolute gain | DEC-008, DEC-017 |
| Changing auth or JWT? | HS256, `python-jose`, bcrypt via `passlib`, 30-min expiry | DEC-004 |
| Adding a new npm package? | Must be free-tier, zero cost — check before installing | DEC-006 |
| Changing background tasks? | Celery + CloudAMQP (RabbitMQ) — no Redis queue | DEC-007 |
| Adding a new frontend page? | Use `api.js` (axios) + `AuthContext` — never raw `fetch()` | DEC-012 |
| **Adding a new backend route?** | Match existing module pattern: router in `routes_*.py`, Pydantic model, `get_current_user()` dependency. Add route to AI_CONTEXT_BACKEND.md Routes table at session end. | DEC-001 |
| Changing storage tiering logic? | Five-factor priority scoring in `tiering_tasks.py` — don't simplify | DEC-009 |
| Structural backend changes? | Controller → Service → DB pattern — match existing modules | DEC-001 |
| Deploying to production? | Not yet — restrict CORS first, rotate `.env` credentials | DEC-006 |
| Renaming "Zenith" or changing branding? | DON'T — 2FA issuer, API title, sidebar all use "Zenith"/"ZenithApp" | DEC-010 |
| Working on SecurityPage.jsx? | Uses `api.js` named exports + inline `<style>`; Phase 12 encryption work per research paper | DEC-018, DEC-020 |
| Security encryption (paper vs code)? | Phase 12: **SSE-S3** (no KMS) + **browser CSE** — see `PHASE_12_SECURITY_RESEARCH_PARITY.md` §2–§3 | DEC-020 |
| Adding/modifying provisioning? | Terraform modules in `backend/terraform/`, API in `app/provision/`, BYOC credentials for AWS auth | DEC-019 |
| Cloud API call for a logged-in user? | Resolve credentials via `credential_resolver` / `cloud_credentials.py` — see BYOC matrix in `AI_CONTEXT_BACKEND.md` | DEC-021 |

---

### [DEC-001] Monorepo Structure with Separate Frontend and Backend
- **Date**: 2025-08-11
- **Status**: Accepted
- **Context**: Need a rich UI and a powerful API backend with different tech stacks.
- **Decision**: Monorepo with `frontend/` (React + Vite) and `backend/` (FastAPI + Python) as separate sub-projects. Each has its own `package.json` / `requirements.txt`.
- **Consequences**: AI agents must be aware of which directory they're working in. No shared package management.

---

### [DEC-002] MongoDB Atlas as Primary Database
- **Date**: 2025-08-11
- **Status**: Accepted
- **Context**: Cloud resource metadata varies across providers — needs flexible schema.
- **Decision**: MongoDB Atlas with pymongo. Database name: `CloudResourceOptimizationDB`. **14 active collections** (expanded from original 3 as modules were built): `users`, `files`, `secure_files`, `ml_predictions`, `ml_workload_descriptions`, `admin_actions`, `activity_log`, `vm_assignments`, `vm_metrics`, `cost_data`, `ml_feedback_snapshots`, `storage_lifecycle_reports`, `budgets`, `byoc_credentials`. No ORM — direct collection access through `database/mongo_client.py`.
- **Consequences**: No SQL migrations. All DB access must go through collection getter functions. `MongoDB` singleton class pattern at module level. See `AI_RULES.md` → Database section for the full active collection list.

---

### [DEC-003] JWT for Authentication (Stateless)
- **Date**: 2025-08-26
- **Status**: Accepted
- **Context**: Need auth that works across stateless API and potential microservices.
- **Decision**: JWT via `python-jose` (HS256). Passwords hashed with `bcrypt` via `passlib.CryptContext`. Token payload: `{"sub": username}`. Token URL: `/api/auth/token` using OAuth2PasswordRequestForm. Token stored in browser localStorage.
- **Consequences**: No server-side sessions. `get_current_user()` dependency decodes JWT on every request. Frontend uses `AuthContext.jsx` to manage token state.

---

### [DEC-004] Celery + CloudAMQP for Async Tasks
- **Date**: 2025-09-05
- **Status**: Accepted
- **Context**: Sensitive file scanning and encryption can take seconds. Storage tier optimization runs on huge datasets. These must not block API responses.
- **Decision**: Celery with CloudAMQP (hosted RabbitMQ) as broker. Two task modules: `storage/tasks.py` (file processing) and `storage/tiering_tasks.py` (nightly optimization). Beat schedule: nightly at 00:00 UTC.
- **Consequences**: Tasks must create their own MongoClient and boto3 clients (fork safety — prevents SIGSEGV). After task completion, call `POST /ws/notify/{user_id}` to push WebSocket updates. Note: task definitions live in `storage/`, not `queue/` (the `queue/` module files are empty stubs).

---

### [DEC-005] WebSocket Notifications
- **Date**: 2025-09-23
- **Status**: Accepted
- **Context**: Frontend needs to know when background Celery tasks complete (e.g., file scan done, encryption complete).
- **Decision**: FastAPI native WebSocket at `/ws/status?token=...`. JWT auth via query parameter. `ConnectionManager` class maintains per-user active connections. Celery tasks call internal `POST /ws/notify/{user_id}` endpoint to bridge async task→WebSocket.
- **Consequences**: Frontend must handle WebSocket reconnects. SecurityPage.jsx connects to WS and re-fetches file list on "job_complete" messages.

---

### [DEC-006] Multi-Cloud Storage (AWS + GCP + Azure)
- **Date**: 2025-09-05
- **Status**: Accepted
- **Context**: Platform aims to optimize across cloud providers, not just AWS.
- **Decision**: Three cloud SDKs: `boto3` (AWS), `google-cloud-storage` (GCP), `azure-storage-blob` (Azure). Upload/download/delete/tier-change functions in `storage/uploader.py` and `storage/manager.py`. Each function handles CSP-specific API calls.
- **Consequences**: Config needs credentials for all three clouds. Storage class names differ across CSPs (e.g., "STANDARD_IA" vs "NEARLINE" vs "Cool"). `optimizer.py` scoring algorithm picks the cheapest option per tier.

---

### [DEC-007] Intelligent File Placement (Model 1)
- **Date**: 2025-09-06
- **Status**: Accepted
- **Context**: Users shouldn't need to know which cloud provider or storage tier to use.
- **Decision**: Scoring algorithm in `storage/optimizer.py` considers: user priority (cost/performance/balanced), user intent (active/infrequent/archival), filename keywords (backup, archive, log), file type, file size. Classifies into hot/warm/cold tier, then picks cheapest CSP for that tier. Returns recommendation + all options so user can override.
- **Consequences**: Frontend shows recommendation modal with override dropdown. The `options_by_csp` dict allows looking up the correct service name when user overrides CSP choice.

---

### [DEC-008] Two-Factor Authentication on Security Endpoints
- **Date**: 2025-10-07
- **Status**: Accepted
- **Context**: Secure file vault handles sensitive documents. Need extra protection beyond JWT.
- **Decision**: TOTP-based 2FA via `pyotp` and `qrcode`. Issuer name: "ZenithApp". Three user fields: `two_fa_secret`, `two_fa_enabled`, `two_fa_verified`. Login resets `two_fa_verified` to False. `require_2fa` dependency enforces verification before accessing security endpoints. 2FA routes mounted at `/api/2fa/`.
- **Consequences**: Users who enable 2FA must verify code each login session before accessing secure storage. Frontend SecurityPage gates all content behind 2FA verification screen.

---

### [DEC-009] Separate Collections for Standard and Secure Files
- **Date**: 2025-10-07
- **Status**: Accepted
- **Context**: Secure files have different access controls (2FA), different S3 buckets, and additional processing (scanning, encryption, replication).
- **Decision**: Two MongoDB collections: `files` (standard multi-cloud uploads) and `secure_files` (2FA-protected uploads). Both use the same `FileMetadata` Pydantic model from `models_storage.py`.
- **Consequences**: Must use correct collection getter (`get_files_collection()` vs `get_secure_files_collection()`). Tiering tasks only operate on `files` collection.

---

### [DEC-010] Three S3 Buckets Architecture
- **Date**: 2025-10-15
- **Status**: Accepted
- **Context**: Need separation between standard storage and secure storage, plus disaster recovery for encrypted files.
- **Decision**: Three AWS S3 buckets:
  1. `zeneith-storage-bucket` — standard multi-cloud file storage (S3_BUCKET_NAME)
  2. `zenith-secure-files` — 2FA-protected secure uploads (SECURE_S3_BUCKET_NAME)
  3. `zeneith-secure-files-secondary2` — encrypted file replication in us-east-1 (REPLICA_S3_BUCKET_NAME)
- **Consequences**: Secure file deletion must clean up both primary and replica buckets. Encryption + replication handled by Celery task `process_secure_file`.

---

### [DEC-011] Branded as "Zenith"
- **Date**: 2025-08-11
- **Status**: Accepted
- **Context**: Project needed a product identity.
- **Decision**: Product name is "Zenith". FastAPI app title: `"Zenith API"`. Sidebar header: "Zenith". 2FA issuer: "ZenithApp". Landing page: "Welcome to Zenith".
- **Consequences**: All user-facing strings use "Zenith". Do not change without user permission.

---

### [DEC-012] Recovery Strategy: Option A — Run Existing, Then Rebuild Missing
- **Date**: 2026-05-23
- **Status**: Accepted
- **Context**: Laptop repair caused data loss. The current codebase is incomplete — 5 major modules documented in the 97-page project report are entirely missing (`app/vm/`, `app/cost/`, ML ensemble, NLP classification, feedback retraining). Python venv has no packages. All cloud credentials are stale/expired.
- **Decision**: Recover in phases: (1) Get existing features running locally, (2) Reconnect cloud services one by one, (3) Rebuild missing modules per the report, (4) Clean up and polish. No full rewrite — preserve all existing working code.
- **Consequences**: Must create new cloud accounts for all services. Missing modules must be built from scratch following the report's exact specifications (algorithms, inputs, outputs). The report's `main.py` (Appendix B) showing `routes_vm`, `routes_cost`, `routes_ml` is the target architecture.

---

### [DEC-013] ML Ensemble Architecture (Per Report §4.2)
- **Date**: 2026-05-23
- **Status**: ✅ Implemented (Phase 7, 2026-05-24)
- **Decision**: Rule-based (30%) + Random Forest (35%) + XGBoost (35%) weighted ensemble. Artifacts: `backend/app/ml/artifacts/storage_ensemble.joblib` (trained on 13,824 samples). Implemented in `ml/storage_ensemble.py`, integrated into `storage/optimizer.py`.

---

### [DEC-014] NLP Workload Classification (Per Report §4.1)
- **Date**: 2026-05-23
- **Status**: ✅ Implemented (Phase 6, 2026-05-24)
- **Decision**: TextBlob + spaCy `en_core_web_sm` + custom tech dictionaries + negation detection + confidence boost. Trained workload classifier artifact: `backend/app/ml/artifacts/workload_classifier.joblib` (TF-IDF soft-voting ensemble: LogisticRegression + NaiveBayes + RandomForest, trained on 600 samples). Implemented in `vm/nlp_workload.py`.

---

### [DEC-015] VM Cluster Management Module (Per Report §4.3)
- **Date**: 2026-05-23
- **Status**: ✅ Implemented (Phase 9, 2026-05-24)
- **Decision**: `app/vm/` module with NLP-driven 5-cluster assignment (General/Storage/Memory/Performance/AI-ML), tier sizing (Micro/Small/Medium/Standard), `S_eff_v1` efficiency scoring, migration support, local/demo mode without GCP credentials. Frontend at `/dashboard/vmcluster`. Key files: `routes_vm.py`, `manager.py`, `nlp_workload.py`, `models.py`, `metrics_collector.py`, `migration_recommender.py`.

---

### [DEC-016] Cost Analysis Module (Per Report Appendix B)
- **Date**: 2026-05-23
- **Status**: ✅ Implemented (Phase 9, 2026-05-24)
- **Decision**: `app/cost/` with cost breakdown, forecasting (decay-weighted linear regression), Z-score anomaly detection, and CSV export. Four route files: `routes_cost.py`, `routes_forecast.py`, `routes_anomaly.py`, `routes_export.py`. Frontend pages: `/dashboard/costs`, `/dashboard/simulator`, `/dashboard/optimization`.

---

### [DEC-017] Feedback-Driven Retraining (Per Report §4.5)
- **Date**: 2026-05-23
- **Status**: ✅ Implemented (Phase 8, 2026-05-24)
- **Decision**: Outcome evaluation (7–30 day window), data quality filtering (feedback_score ≥ 0.5), guarded retraining (requires +1% absolute or +2% relative gain to deploy), Celery Beat weekly Sunday 03:30 UTC. Manual trigger: `POST /api/ml/feedback/retrain`. Candidate artifacts staged under `ml/artifacts/candidates/` before deployment. Implemented in `ml/feedback.py`, `ml/retraining.py`, `ml/tasks_feedback.py`.

---

### [DEC-018] SecurityPage.jsx Intentional Pattern Deviation
- **Date**: 2026-05-25
- **Status**: Accepted (known, intentional)
- **Context**: SecurityPage.jsx was built before the centralized `api.js` + `AuthContext` pattern was established. It has its own inline `fetch()` functions and handles auth tokens directly.
- **Decision**: Leave SecurityPage.jsx using its own inline API pattern. Do NOT refactor it to use `api.js` unless the user explicitly requests it as a task. The risk of breaking 2FA flows, WebSocket handling, and secure file gating is high.
- **Consequences**: When modifying SecurityPage.jsx, follow the existing inline pattern. When creating NEW pages, always use `api.js` + `AuthContext`. Any agent that sees raw `fetch()` in SecurityPage should not treat it as a bug — it is intentional.
- **DO NOT**: Silently refactor SecurityPage.jsx to use `api.js` as part of any other task.

---

### [DEC-019] Terraform Infrastructure Provisioning Integration
- **Date**: 2026-05-25
- **Status**: ✅ Implemented (Phase 11)
- **Context**: The standalone `aws-provision-using-terraform` project provides 7 Terraform modules (VPC, EC2, S3, IAM, CloudWatch, Billing, DynamoDB), a dual policy engine (YAML + OPA), drift detection, and cost estimation. User decided to integrate this into Zenith as a native feature.
- **Decision**: **Backend merge + Zenith-native React frontend.** Terraform module files copied into `backend/terraform/`. New `app/provision/` module wraps Terraform CLI as subprocess calls. BYOC credentials are injected as environment variables for terraform commands. Each deployment gets its own workspace directory (`backend/terraform_workspaces/{id}/`). MongoDB `provision_deployments` collection stores deployment state. Daily drift checks via Celery Beat at 06:00 UTC.
- **Key files**: `app/provision/routes_provision.py` (10 endpoints at `/api/provision`), `terraform_runner.py` (CLI wrapper), `policy_checker.py` (YAML + OPA), `cost_estimator.py` (Infracost + built-in table), `drift_detector.py`, `tasks.py` (Celery Beat), `ProvisionPage.jsx` (4-step wizard).
- **Dependencies**: Terraform CLI (checked on server startup — returns 503 if missing). Infracost CLI (optional — falls back to built-in lookup table). OPA CLI (optional — YAML rules run regardless).
- **Consequences**: The original `aws-provision-using-terraform` project remains standalone. The Terraform files inside Zenith are a copy, not a submodule. Policy rules can be independently updated. The provisioning page is at `/dashboard/provision`.
- **DO NOT**: Run `terraform apply` without a prior successful policy check. Do NOT store AWS credentials in MongoDB — they're resolved per-request via BYOC and passed as env vars.

---

### [DEC-020] Phase 12 — Security Research Paper as Acceptance Source
- **Date**: 2026-05-29 (updated 2026-05-29 — SSE not KMS; browser CSE gap documented)
- **Status**: Planned (not implemented)
- **Context**: The 6-page research paper describes hybrid encryption (server-managed + zero-knowledge CSE), detection, CRR, and session auditing. Zenith today has: **SSE-S3** (`ServerSideEncryption='AES256'`) on the server-side encryption path, a **mislabeled** “client-side” path that encrypts on the **server** (password in API), sensitive scan inline in `routes_security.py`, dual-bucket replicate. **Browser client-side encryption architecture is completely missing.** `sensitive_file_detector.py` is an empty stub. `kms_encryption.py` is an empty stub and **not needed for Phase 12**.
- **Decision**: **Phase 12** acceptance criteria are in `ai-docs/PHASE_12_SECURITY_RESEARCH_PARITY.md`.
  - **Server-side:** Use **SSE-S3 only** — sufficient for the product. **Do not implement AWS KMS** in Phase 12.
  - **Client-side:** Build **browser** zero-knowledge CSE (Web Crypto); do not call server-side password encryption “client-side architecture.”
- **Consequences**: Docs and UI must say **SSE** / **SSE-S3**, not KMS. Auto-encrypt on sensitive detect uses SSE-S3. CSE requires new `clientEncryption.js` and API changes.
- **DO NOT**: Implement KMS or require `kms_encryption.py` for Phase 12. Do not claim zero-knowledge while sending passwords to `/choose-encryption` or `/decrypt-download`.

---

### [DEC-022] Dual provision engine — Boto3 vs Terraform (user Settings)
- **Date**: 2026-05-30 (parity completed 2026-05-30)
- **Status**: ✅ Implemented
- **Context**: Terraform plan/apply on Render free tier is slow and OOM-prone; users need explicit engine choice and boto3 parity with all Terraform modules.
- **Decision**: `users.settings.preferences.provision_engine` = `boto3` (default) | `terraform`. Boto3 handlers live in `app/provision/boto3_modules/` (vpc, ec2, s3, iam, cloudwatch, dynamodb, **billing**) orchestrated by `boto3_composer.py`. Parity targets `backend/terraform/modules/*` (same resource names where applicable). S3 static **file upload** is out of scope — neither engine uploads HTML.
- **Key files**: `boto3_modules/*`, `boto3_composer.py`, `boto3_drift.py`, `engine_resolver.py`, `routes_provision.py`.
- **Consequences**: Billing via boto3 uses AWS Budgets API (`us-east-1`); requires `budgets:*` on BYOC keys (same as Terraform). DynamoDB PITR/SSE, IAM instance profile, VPC `MapPublicIpOnLaunch` implemented in boto3.
- **DO NOT**: Auto-force engine by template. Do not claim S3 website/file upload without adding it to Terraform first.

---

### [DEC-021] BYOC Credential Routing Per User (Platform-Wide)
- **Date**: 2026-05-29
- **Status**: Accepted (implemented)
- **Context**: After AWS BYOC connect, some features still used Zenith platform S3 keys and buckets. Users expect storage, secure vault, cost, and (where applicable) VM operations to run against **their** cloud accounts.
- **Decision**: Centralize client construction in `app/storage/cloud_credentials.py`. All user-scoped routes pass `username` into cost/security/storage helpers. Secure AWS vault uses `secure/{username}/` prefix inside the BYOC bucket; platform users keep dedicated `SECURE_S3_BUCKET_NAME` + replica. VM GCP uses `app/vm/gcp_runtime.py` request context when BYOC GCP SA is present.
- **Consequences**: Scheduled Celery jobs without a user context (e.g. `check_cost_anomalies`) still use platform credentials. Azure cost requires platform service principal until BYOC stores Cost Management SP fields.
- **DO NOT**: Hardcode `settings.AWS_ACCESS_KEY_*` or `REGULAR_S3_BUCKET_NAME` in user-scoped upload/download paths. Do not assume secure vault is always a separate platform bucket when AWS BYOC is active.
