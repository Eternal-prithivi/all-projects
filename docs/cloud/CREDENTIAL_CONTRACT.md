# Cloud Credential Contract

**Last updated:** 2026-06-03 (Phase 7)  
**Setup guide:** [../setup/CLOUD_CREDENTIAL_SETUP_GUIDE.md](../setup/CLOUD_CREDENTIAL_SETUP_GUIDE.md)  
**Env template:** `backend/.env.example`

Provider strings in APIs should use canonical form **`AWS`**, **`GCP`**, **`Azure`** (see `app/cloud/providers.py`). Billing probes and Mongo BYOC status keys use lowercase **`aws`**, **`gcp`**, **`azure`**.

### Availability rules (`GET /api/cloud/availability`) — hybrid

| Mode | When | Providers shown | Credentials used per CSP |
|------|------|-----------------|--------------------------|
| **Platform** | No BYOC | All platform-configured CSPs | Platform `.env` |
| **BYOC** | BYOC only, no platform config | Connected CSPs only | BYOC |
| **Hybrid** | ≥1 BYOC + platform has other CSPs | **Union** of connected + platform-configured | BYOC if connected, else platform |

Example: AWS BYOC only → user can still upload to GCP/Azure using **Zenith platform** keys; AWS uploads use **their** BYOC.

UI pages use this endpoint. Backend returns **403** if a CSP is neither connected nor platform-available.

`GET /byoc/storage-targets` returns per-provider bucket/container paths with `credential_source: byoc | platform`.

---

## Platform `.env` (Zenith defaults)

### Storage

| Variable | AWS | GCP | Azure |
|----------|-----|-----|-------|
| Bucket / container | `S3_BUCKET_NAME`, `REGULAR_S3_BUCKET_NAME` | `GCP_BUCKET_NAME` | `AZURE_STORAGE_CONTAINER_NAME` |
| Access | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` | `GCP_SERVICE_ACCOUNT_JSON_PATH`, `GCP_PROJECT_ID` | `AZURE_STORAGE_CONNECTION_STRING` or account + key |
| Secure vault | `SECURE_S3_BUCKET_NAME`, replica region helpers | GCS bucket from BYOC/platform | Azure container from BYOC/platform |

### Cost / billing

| Variable | AWS | GCP | Azure |
|----------|-----|-----|-------|
| Billing read | Same AWS keys (Cost Explorer) | `GCP_BILLING_DATASET_ID`, `GCP_BILLING_TABLE_ID`, SA JSON | `AZURE_SUBSCRIPTION_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET` |
| In-app setup | — | `PUT /api/cost/setup/gcp` (requires GCP BYOC) | `PUT /api/cost/setup/azure` (requires Azure BYOC) |
| Status | `GET /api/cost/billing-status` | `GET /api/cost/setup/gcp` | `GET /api/cost/setup/azure` |
| Demo | `DEMO_MODE=true` mocks all three | | |

### VM (Phase 5+)

| Variable | AWS | GCP | Azure |
|----------|-----|-----|-------|
| Compute | EC2 via BYOC or platform keys (`aws_runtime`) | `GCP_PROJECT_ID`, `GCP_ZONE`, SA JSON | Subscription + SP (planned) |
| Metrics | CloudWatch (`aws_metrics.py`) | GCP Monitoring (`metrics_collector.py`) | Azure Monitor (planned) |

### Provision (Phase 6+)

| Variable | AWS | GCP | Azure |
|----------|-----|-----|-------|
| Terraform / SDK | AWS keys in TF env | GCP SA + project | Azure SP + subscription |
| BYOC | `resolve_credentials(username, "AWS")` | GCP/Azure TF shape Phase 3 | |

### Security vault (Phase 4 ✅)

| Variable | AWS | GCP | Azure |
|----------|-----|-----|-------|
| Primary + replica | Secure + replica S3 buckets | GCS secure + replica buckets | Blob secure + replica containers |
| Replication doc | `SECURE_VAULT_REPLICATION.md` | Same (tri-cloud) | Same |

---

## BYOC Mongo fields (`byoc_credentials`)

Common: `username`, `csp` (`AWS`|`GCP`|`Azure`), `is_active`, `connection_method`, `secure_dual_write`.

**Secrets:** Stored under `credentials` — each value encrypted with AES-256-GCM (`app/byoc/encryption.py`). See [TRUST_AND_ENCRYPTION.md](../security/TRUST_AND_ENCRYPTION.md).

### AWS

| Field | Purpose |
|-------|---------|
| `credentials.access_key_id`, `credentials.secret_access_key` (encrypted) | API access |
| `credentials.role_arn`, `credentials.external_id` (encrypted) | IAM role method |
| `storage_bucket_name`, `secure_bucket_name`, `replica_bucket_name` | Layout |
| `region` / `primary_region`, `replica_region` | Upload + TF |

### GCP

| Field | Purpose |
|-------|---------|
| `credentials.service_account_json` (encrypted) | API access |
| `storage_bucket_name`, `secure_bucket_name`, `replica_bucket_name` | Layout |
| `gcp_primary_location`, `gcp_replica_location` | Bucket regions |

### Azure

| Field | Purpose |
|-------|---------|
| `credentials.account_name`, `credentials.account_key` (encrypted) | Blob storage |
| `storage_container_name`, `secure_container_name`, `replica_container_name` | Layout |
| `credentials.subscription_id`, `tenant_id`, `client_id`, `client_secret` (encrypted) | Cost Management (optional) |

---

## Per-service resolver entry points

| Service | Resolver functions |
|---------|-------------------|
| Storage | `resolve_aws_credentials`, `resolve_gcp_credentials`, `resolve_azure_credentials` |
| Cost | Same + BYOC record for Azure billing fields |
| BYOC status | `get_byoc_status(username)` → `aws`, `gcp`, `azure` |
| Provision (future) | `resolve_credentials(username, provider)` |
| VM GCP | `gcp_runtime` + BYOC GCP record |
| VM AWS | `aws_runtime` + `resolve_aws_credentials()` |

---

## Manual smoke checklist (when accounts exist)

### Storage only (after Phase 1)

1. Set `.env` or BYOC for one CSP.
2. `POST /api/storage/upload` with `csp=AWS|GCP|Azure`.
3. `POST /api/storage/sync/{aws|gcp|azure}`.
4. List, download, delete.

### Billing (after Phase 2)

1. Configure billing vars for CSP.
2. `GET /api/cost/billing-status` → `live: true`.
3. `GET /api/cost/gcp` or `/azure` with date range.

---

## Phase 0 validation (no cloud accounts)

- CI: mocked integration tests in `backend/tests/integration/`.
- Docs: this file + [MULTI_CLOUD_PARITY_MATRIX.md](./MULTI_CLOUD_PARITY_MATRIX.md).
