# Cloud Credential Contract

**Last updated:** 2026-06-03 (Phase 0)  
**Setup guide:** [../setup/CLOUD_CREDENTIAL_SETUP_GUIDE.md](../setup/CLOUD_CREDENTIAL_SETUP_GUIDE.md)  
**Env template:** `backend/.env.example`

Provider strings in APIs should use canonical form **`AWS`**, **`GCP`**, **`Azure`** (see `app/cloud/providers.py`). Billing probes and Mongo BYOC status keys use lowercase **`aws`**, **`gcp`**, **`azure`**.

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
| Compute | EC2 via BYOC or platform keys (TBD) | `GCP_PROJECT_ID`, `GCP_ZONE`, SA JSON | Subscription + SP (TBD) |
| Metrics | CloudWatch (TBD) | GCP Monitoring (live) | Azure Monitor (TBD) |

### Provision (Phase 6+)

| Variable | AWS | GCP | Azure |
|----------|-----|-----|-------|
| Terraform / SDK | AWS keys in TF env | GCP SA + project | Azure SP + subscription |
| BYOC | `resolve_credentials(username, "AWS")` | GCP/Azure TF shape Phase 3 | |

### Security vault (Phase 4+)

| Variable | AWS | GCP | Azure |
|----------|-----|-----|-------|
| Primary + replica | Secure + replica S3 buckets | GCS buckets (planned) | Blob containers (planned) |

---

## BYOC Mongo fields (`byoc_credentials`)

Common: `username`, `csp` (`AWS`|`GCP`|`Azure`), `is_active`, `connection_method`.

### AWS

| Field | Purpose |
|-------|---------|
| `access_key_id`, `secret_access_key` | API access |
| `storage_bucket_name`, `secure_bucket_name`, `replica_bucket_name` | Layout |
| `region` / `primary_region` | Upload + TF |

### GCP

| Field | Purpose |
|-------|---------|
| `service_account_json` (encrypted) | API access |
| `bucket_name` / `gcp_bucket_name` | Storage + sync |

### Azure

| Field | Purpose |
|-------|---------|
| `connection_string` or account + key | Blob storage |
| `container_name` | Storage + sync |
| Cost Management: tenant, client id/secret, subscription (Phase 2+) | Billing reads beyond storage |

---

## Per-service resolver entry points

| Service | Resolver functions |
|---------|-------------------|
| Storage | `resolve_aws_credentials`, `resolve_gcp_credentials`, `resolve_azure_credentials` |
| Cost | Same + BYOC record for Azure billing fields |
| BYOC status | `get_byoc_status(username)` → `aws`, `gcp`, `azure` |
| Provision (future) | `resolve_credentials(username, provider)` |
| VM GCP | `gcp_runtime` + BYOC GCP record |

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
