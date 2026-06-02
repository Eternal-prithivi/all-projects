# AI_CONTEXT_BACKEND.md — Backend Architecture & Source Map

> Read this for any backend, API, database, Celery, or ML task.
> **Last Updated: 2026-05-29** — BYOC credential routing matrix added.

---

## 🏗 Project Overview (Brief)

**Zenith** — FastAPI + Python backend, MongoDB Atlas, Celery + CloudAMQP.
25 route files, 16 mounted routers, Celery background tasks, ML ensemble, WebSocket notifications.

For frontend context → read `AI_CONTEXT_FRONTEND.md`

---

## 📦 Backend Modules (`backend/app/`)

### ✅ Fully Implemented

| Module | Route File(s) | Key Files | Notes |
|--------|--------------|-----------|-------|
| **auth** | `routes_auth.py`, `routes_password_reset.py` | `auth_service.py`, `auth_utils.py`, `auth_controller.py`, `password_reset_service.py` | JWT login, register, forgot/reset password (email link + SMS OTP), recovery contacts |
| **users** | `routes_users.py`, `routes_profile.py`, `routes_settings.py` | `user_model.py` | Profile edit, recovery contacts, settings preferences, BYOC, theme, currency, audit log |
| **security** | `routes_security.py`, `routes_2fa.py` | `encryption_handler.py`, `tasks_alerts.py` | 2FA, secure vault, **SSE-S3** on server-side path — **Phase 12:** auto SSE, **browser CSE**, detector (`PHASE_12_SECURITY_RESEARCH_PARITY.md` §2–§3) |
| **storage** | `routes_storage.py` | `cloud_credentials.py`, `optimizer.py`, `uploader.py`, `manager.py`, `tasks.py`, `tiering_tasks.py`, `models_storage.py` | ML ensemble analysis, multi-cloud upload/download/delete, nightly lifecycle tiering; **BYOC** via `credential_resolver` |
| **vm** | `routes_vm.py`, `routes_admin_cleanup.py` | `manager.py`, `nlp_workload.py`, `models.py`, `metrics_collector.py`, `migration_recommender.py`, `workload_guidance.py`, `tasks.py` | NLP workload classification → five-cluster assignment, VM lifecycle, metrics, migration |
| **cost** | `routes_cost.py`, `routes_forecast.py`, `routes_anomaly.py`, `routes_export.py` | `manager.py`, `forecasting.py`, `tasks_anomaly.py` | Decay-weighted linear regression forecast, Z-score anomaly detection, CSV export |
| **ml** | `routes_feedback.py` | `storage_ensemble.py`, `feedback.py`, `retraining.py`, `repository.py`, `models.py`, `acceptance.py`, `sample_datasets.py`, `tasks_feedback.py` | RF+XGBoost ensemble, feedback outcome evaluation, guarded self-retraining |
| **byoc** | `routes_byoc.py` | `credential_resolver.py`, `encryption.py` | Connect/test/disconnect AWS IAM + STS AssumeRole, AES-256-GCM credential encryption |
| **admin** | `routes_admin.py` | — | Full user CRUD (create/delete/role/bulk), audit log query, CSV export, self-protection guards |
| **billing** | `routes_billing.py` | — | Free plan display, billing history |
| **payments** | `routes_payments.py` | — | Razorpay payment orders |
| **pricing** | `routes_pricing.py` | `pricing_fetcher.py`, `tasks.py` | Live cloud pricing fetch |
| **budgets** | `routes_budgets.py` | `models.py`, `tasks.py` | Budget alerts |
| **contact** | `routes_contact.py` | `email_service.py` | Contact form → Gmail SMTP, security alert emails, password reset emails |
| **dashboard** | `routes_dashboard.py` | — | Stats endpoint (partially hardcoded — see Known Issues) |
| **websockets** | `routes_ws.py` | `connection_manager.py` | JWT-authenticated WS, per-user connection pool, Celery→WS notification bridge |
| **setup** | `routes_setup.py` | — | First-time DB index setup |

### ⚠️ Empty Stubs — Do NOT Delete

| Path | Files |
|------|-------|
| `backend/app/aws/` | `cost_explorer.py`, `ec2_scaling.py`, `s3_operations.py` |
| `backend/app/providers/` | `azure_operations.py`, `gcp_operations.py` |
| `backend/app/queue/` | `sns_notifications.py`, `sqs_jobs.py` |
| `backend/app/errors/` | `ec2_errors.py`, `general_errors.py`, `s3_errors.py` |
| `backend/app/database/` | `dynamodb_client.py` |
| `backend/app/security/` | `sensitive_file_detector.py` — **empty; Phase 12 implement**. `kms_encryption.py` — **empty; not required (SSE-S3 sufficient)**. `audit_logs.py` — stub |
| `backend/app/storage/` | `cost_estimator.py`, `storage_controller.py`, `storage_service.py` |
| `backend/app/dashboard/` | `dashboard_controller.py`, `dashboard_service.py`, `dashboard_utils.py` |
| `backend/app/users/` | `user_controller.py`, `user_service.py` |
| `backend/app/ml/` | `train_model.py` |

---

## 🗄 MongoDB Collections

Database: `CloudResourceOptimizationDB`

| Collection | Module | Key Fields |
|-----------|--------|-----------|
| `users` | auth, users, 2fa, admin | username, email, hashed_password, role, status, two_fa_*, recovery_email, phone, sessions[], activity_log[] |
| `files` | storage | filename, s3_key, owner_username, size_bytes, csp, storage_class, last_accessed_at, access_frequency_score, is_sensitive, is_encrypted, tier_*, lifecycle_* |
| `secure_files` | security | Same schema as `files`, separate 2FA-protected collection |
| `ml_predictions` | ml, storage | file metadata, predicted tier, ensemble confidence, expert_votes[], outcome, feedback_score |
| `ml_workload_descriptions` | vm, ml | workload_description, predicted_cluster, nlp_features, classifier_version, outcome |
| `admin_actions` | admin | admin_username, action, target_user, timestamp |
| `activity_log` | users | username, action, ip, user_agent, timestamp |
| `vm_assignments` | vm | username, vm_name, cluster_type, cluster_tier, assignment_date |
| `vm_metrics` | vm | vm_name, cpu_util, memory_util, disk_io, timestamp |
| `cost_data` | cost | username, csp, service, amount, date |
| `ml_feedback_snapshots` | ml | snapshot_date, eligible_samples, feedback_accuracy, deployment_ready |
| `storage_lifecycle_reports` | storage | date, actions_taken, priority_scores |
| `budgets` | budgets | username, monthly_limit, alerts |
| `byoc_credentials` | byoc | username, provider, encrypted_credentials, connection_status |

---

## 🔌 API Routes (Verified from `main.py`)

```python
/api/auth        → routes_auth.py (register, token/login)
/api/auth        → routes_password_reset.py (forgot-password, reset-password)
/auth            → routes_auth.py (legacy alias — duplicate, can be removed)
/api/users       → routes_users.py (GET /me)
/api             → routes_profile.py, routes_settings.py, routes_billing.py, routes_pricing.py
/api/dashboard   → routes_dashboard.py (stats, cost-trend)
/api/storage     → routes_storage.py (analyze, upload, files, download, delete, sync/aws)
/api/security    → routes_security.py (upload-secure, list-secure, download, delete, sync/aws)
/api/2fa         → routes_2fa.py (status, enable, finalize, verify, disable)
/api/vm          → routes_vm.py (request, release, clusters, assignment, analyze-workload, migrate)
/api             → routes_admin_cleanup.py (cleanup)
/api/cost        → routes_cost.py, routes_export.py, routes_forecast.py, routes_anomaly.py
/api/ml          → routes_feedback.py (evaluate, readiness, training-dataset, retrain)
/api/payments    → routes_payments.py (Razorpay orders)
/api/budgets     → routes_budgets.py
/api/byoc        → routes_byoc.py (connect, status, test, disconnect)
(no prefix)      → routes_admin.py (admin/dashboard, admin/users CRUD, audit-logs)
(no prefix)      → routes_contact.py
/ws              → routes_ws.py (WebSocket + notify bridge)
```

---

## 🛠 Backend Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | FastAPI (`app = FastAPI(title="Zenith API")`) |
| Language | Python 3.x |
| Database | MongoDB Atlas (pymongo) |
| Auth | JWT via `python-jose` (HS256), bcrypt via `passlib` |
| 2FA | `pyotp` + `qrcode` (TOTP, issuer `"ZenithApp"`) |
| Task Queue | Celery + CloudAMQP (RabbitMQ) |
| ML | scikit-learn (RF, LogisticRegression, NaiveBayes), XGBoost, joblib |
| NLP | TextBlob, spaCy (`en_core_web_sm`) |
| Cloud | boto3, google-cloud-storage, azure-storage-blob |
| Validation | Pydantic v2 + pydantic-settings |
| Email | Gmail SMTP (`smtplib`) via `contact/email_service.py` |
| SMS | Twilio (optional) |
| Encryption | BYOC credentials: AES-256-GCM. Secure vault: **SSE-S3** (`AES256`) for server-side; user-password path uses server `encryption_handler.py` — **Phase 12: browser CSE** (see `PHASE_12_SECURITY_RESEARCH_PARITY.md` §2–§3). **KMS not used.** |
| Payments | Razorpay |

---

## ⚙️ Environment Variables (`backend/.env`)

| Variable | Purpose |
|----------|---------|
| `MONGO_CONNECTION_STRING` | MongoDB Atlas URI |
| `SECRET_KEY` | JWT signing key |
| `ALGORITHM` | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | AWS IAM credentials |
| `S3_BUCKET_NAME` | Standard storage bucket |
| `SECURE_S3_BUCKET_NAME` | 2FA-protected secure uploads bucket |
| `REPLICA_S3_BUCKET_NAME` | Encrypted replication bucket |
| `CELERY_BROKER_URL` | CloudAMQP AMQPS URL |
| `GCP_SERVICE_ACCOUNT_JSON_PATH` | GCP service account key path |
| `GCP_BUCKET_NAME` | GCP storage bucket |
| `AZURE_STORAGE_ACCOUNT_NAME`, `AZURE_STORAGE_ACCOUNT_KEY`, `AZURE_CONTAINER_NAME` | Azure blob |
| `EMAIL_USERNAME`, `EMAIL_PASSWORD` | Gmail SMTP |
| `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` | Twilio SMS (optional) |
| `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` | Razorpay |
| `BYOC_ENCRYPTION_KEY` | AES key for BYOC credentials |

---

## Platform (public)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/platform/status` | Maintenance flag, DB health, `overall` status (no auth) |

Auth: `POST /api/auth/verify-email?token=` — marks `email_verified` when `email_verify_token` matches user.

**Notifications** (`/api/notifications`): paginated `GET ?limit&skip&read&type`, `GET /recent?limit=8`, create, mark read, delete — `user_notifications` (180d TTL).

**Provision governance** (`/api/provision`): `GET/POST/PUT/DELETE policy-rules/custom`, `PUT/DELETE policy-rules/builtin/{name}` (per-user overrides), `GET audit-log?limit=10&period_days`, `GET audit-log/export` — collections `provision_custom_policies`, `provision_policy_overrides`, `provision_audit_log` (90d TTL).

**Organizations** (`/api/organizations`): create org, members, invites, accept invite — single org per user.

**SSO** (`/api/auth/sso`): `GET providers`, `GET google/login`, `GET google/callback` — needs `GOOGLE_OAUTH_*` + `PUBLIC_API_URL` env.

---

## 🔧 How to Run Backend

```bash
cd backend && source .venv/bin/activate   # venv is at backend/.venv — NOT project root
uvicorn app.main:app --reload              # → http://localhost:8000 (Swagger: /docs)
celery -A app.celery_worker worker --loglevel=info   # Terminal 3
celery -A app.celery_worker beat --loglevel=info     # Terminal 4
python -m pytest -q                                   # 34 tests
```

---

## BYOC credential routing (2026-05-29)

When a user connects BYOC for a CSP, **that user's** API operations should use their credentials and bucket/account where noted below.

| Feature | AWS BYOC | GCP BYOC | Azure BYOC | Notes |
|---------|----------|----------|------------|-------|
| Storage upload/download/sync | Yes | Yes | Yes | `cloud_credentials.py` + `uploader.py` / `manager.py` |
| Secure vault (2FA) | Yes (`secure/{user}/` prefix in user bucket) | N/A (AWS-only vault) | N/A | Platform dual-bucket when no AWS BYOC |
| Cost Explorer / billing APIs | Yes | Yes (BigQuery export in user's project) | Platform SP only* | Azure BYOC stores storage keys only |
| Dashboard cost refresh | Yes | — | — | Per-user cache |
| VM cluster (Compute) | N/A | Yes** | N/A | Uses BYOC SA when `get_vm_user` context set |
| Terraform provision | Yes | — | — | `provision/byoc_credentials.py` (DEC-019) |
| Provision engine | Settings `provision_engine` | `boto3` \| `terraform` | boto3 default; full module parity via `boto3_modules/*` (DEC-022) |
| Zenith subscription billing | — | — | — | Razorpay/invoices — not customer cloud |

\* Azure cost still uses platform service principal until BYOC stores Cost Management credentials.  
\** GCP BYOC SA must include Compute roles; storage-only SAs will fail VM APIs.

Helpers: `app/storage/cloud_credentials.py`, `app/aws/cost_explorer.py`, `app/aws/s3_operations.py`.

---

## 🔑 Key Backend Patterns

### Routes → Service → DB
`routes_*.py` → service functions → `mongo_client.py`
**Exception:** `storage/` and `security/` routes call helpers directly (no controller layer yet).

### Auth Flow
1. Register → bcrypt hash → MongoDB `users`
2. Login → JWT (`sub: username`) → localStorage
3. `get_current_user()` decodes JWT → MongoDB lookup on every request
4. 2FA enabled: `mark_2fa_unverified()` on login → `require_2fa` dependency gates security endpoints
5. Sessions tracked in `users.sessions[]` — revokable from SecuritySettingsPage

### ML Pipeline
1. **Storage:** File metadata → 10-feature vector → Rule(30%) + RF(35%) + XGB(35%) → tier + CSP
2. **VM:** Text → TextBlob + spaCy NER + tech dictionaries → 5-cluster → tier sizing
3. **Feedback:** Outcome evaluated 7–30d → quality filter (score ≥ 0.5) → guarded retraining (requires +1% absolute gain)
4. **Artifacts:** `backend/app/ml/artifacts/storage_ensemble.joblib`, `workload_classifier.joblib`

### Storage Intelligence Flow
1. `POST /api/storage/analyze` → `optimizer.py` → ML ensemble → tier + cheapest CSP
2. `POST /api/storage/upload` → `uploader.py` → AWS/GCP/Azure
3. Nightly Celery Beat → `tiering_tasks.py` → five-factor lifecycle priority scoring
4. `POST /api/storage/sync/aws` → reconcile S3 → MongoDB

### Secure Vault Sync Flow
1. `POST /api/security/sync/aws` → list `SECURE_S3_BUCKET_NAME` under `{username}/` prefix
2. Insert missing rows into `secure_files` (encryption flags from S3 `head_object` when available)
3. Does not delete DB records or change S3 objects — same reconcile-only model as storage sync

---

## ⚠️ Known Backend Issues

| Issue | Location | Status |
|-------|----------|--------|
| Dashboard stats partially hardcoded | `routes_dashboard.py` | Needs real MongoDB aggregation |
| `CORS allow_origins=["*"]` | `main.py` | Restrict before public deployment |
| `routes_auth.py` mounted twice | `main.py` lines 121 + 133 | Legacy duplicate — safe to remove `/auth` alias |
| `.env` committed in first git commit | Git history | Rotate credentials before public repo |
| `auth_service.py.save` temp file | `backend/app/auth/` | Safe to delete |
