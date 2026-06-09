# Multi-Cloud Parity Matrix

**Last updated:** 2026-06-10 (BYOC tri-cloud connect wizard + trust docs)  
**Plan:** Multi-cloud parity Phases 0–7  
**Credential detail:** [CREDENTIAL_CONTRACT.md](./CREDENTIAL_CONTRACT.md)

Success criterion (every phase): With valid platform `.env` or per-user BYOC, the feature behaves like today’s AWS path — no silent AWS-only failures when the user selects GCP or Azure.

---

## Area summary

| Area | AWS | GCP | Azure | Key modules | Phase |
|------|-----|-----|-------|-------------|-------|
| **Storage (standard)** | Full | Full | Full | `app/storage/uploader.py`, `cloud_credentials.py`, `routes_storage.py` | 1 |
| **Storage restore** | Glacier (`POST /restore/AWS/{filename}`) | ARCHIVE reclassify | Archive rehydration | `routes_storage.py`, `manager.py` | 1 ✅ |
| **Cost / budgets** | Full + CE grouping | BigQuery + setup wizard | Cost Management + setup wizard | `app/cost/manager.py`, `billing_config.py` | 2 ✅ |
| **BYOC** | Full + 2-step verify + buckets | Full + 2-step verify + buckets | Full + 2-step verify + containers | `app/byoc/routes_byoc.py`, `credential_resolver.py`, `encryption.py` | 3 ✅ |
| **Security vault** | Full (S3 SSE dual) | Full | Full | `app/security/routes_security.py` | 4 ✅ |
| **VM / monitoring** | **Full VM API** (EC2) | **Full VM API** (GCE) | None | `aws_manager.py`, `manager.py`, `vm_provider.py` | 5 ✅ |
| **Provision** | TF + Boto3 | TF (GCS) | TF (Blob) | `terraform/`, `provision_catalog.py` | 6 ✅ |
| **Pricing** | Static table | Static table | Static table | `pricing_fetcher.py`, `PRICING_DATA_SOURCE.md` | 7 ✅ |

---

## Endpoint checklist (maintained per phase)

Legend: ✅ implemented · 🟡 partial · ❌ missing · 🔒 AWS-only today

### Storage (`/api/storage`)

| Endpoint | AWS | GCP | Azure | Notes |
|----------|-----|-----|-------|-------|
| `POST /analyze` | ✅ | ✅ | ✅ | CSP-agnostic ML |
| `POST /upload` | ✅ | ✅ | ✅ | `csp` form field; use `normalize_provider()` |
| `GET /files` | ✅ | ✅ | ✅ | Filter by stored `csp` |
| `GET /download/{filename}` | ✅ | ✅ | ✅ | Dispatches by record `csp` |
| `DELETE /delete/{filename}` | ✅ | ✅ | ✅ | Dispatches by record `csp` |
| `POST /sync/aws` | ✅ | — | — | |
| `POST /sync/gcp` | — | ✅ | — | |
| `POST /sync/azure` | — | — | ✅ | |
| `POST /restore/{csp}/{filename}` | ✅ AWS Glacier | ✅ GCP ARCHIVE | ✅ Azure Archive | Uses file `cloud_bucket` + region/account; legacy `/restore-aws/` alias |
| Nightly lifecycle tier change | ✅ | ✅ | ✅ | `tiering_tasks.py` passes recorded bucket/region; skips `is_sensitive` |

### Cost (`/api/cost`)

| Endpoint | AWS | GCP | Azure | Notes |
|----------|-----|-----|-------|-------|
| `GET /aws` | ✅ | — | — | |
| `GET /gcp` | — | 🟡 | — | Needs `GCP_BILLING_*` |
| `GET /azure` | — | — | 🟡 | Needs Azure Cost Management creds |
| `GET /billing-status` | ✅ | ✅ | ✅ | Tri-cloud probe |
| Budgets / export / forecast | ✅ | 🟡 | 🟡 | Phase 2 |

### BYOC (`/api/byoc`)

| Endpoint | AWS | GCP | Azure | Notes |
|----------|-----|-----|-------|-------|
| `POST /connect` | ✅ | ✅ | ✅ | Storage + secure + replica; auto-create |
| `POST /test` | ✅ | ✅ | ✅ | |
| `POST /verify-credentials` | ✅ | ✅ | ✅ | Step 1 → suggested names |
| `POST /check-bucket-name` | ✅ | — | — | AWS |
| `POST /check-gcp-bucket` | — | ✅ | — | |
| `POST /check-azure-container` | — | — | ✅ | |
| `GET /aws-buckets?surface=` | ✅ | — | — | `storage` \| `security` |
| `GET /gcp-buckets?surface=` | — | ✅ | — | |
| `GET /azure-containers?surface=` | — | — | ✅ | |
| Credential encryption at rest | ✅ | ✅ | ✅ | AES-256-GCM per field — `encryption.py` |
| `resolve_credentials()` for TF | ✅ | ✅ | ✅ | BYOC only |

### Security (`/api/security`)

| Endpoint | AWS | GCP | Azure | Notes |
|----------|-----|-----|-------|-------|
| Secure upload / list / sync / download / delete | ✅ | ✅ | ✅ | Phase 4 ✅ |
| `POST /security/sync/{csp}` | ✅ | ✅ | ✅ | Phase 4 ✅ |
| Secure primary + replica vault | ✅ | ✅ | ✅ | BYOC + platform; archive/restore |
| Browser CSE upload | ✅ | ❌ | ❌ | AWS-only (501 others) |
| OPA security rego | ✅ | stub | stub | `aws_security`, `gcp_security`, `azure_security` |

### VM (`/api/vm`)

| Endpoint | AWS | GCP | Azure | Notes |
|----------|-----|-----|-------|-------|
| Lifecycle / clusters / metrics | ✅ | ✅ | ❌ (501) | Phase 5 ✅ |
| `csp` on request / assignment | ✅ | ✅ | — | Query or JSON body |
| CloudWatch / GCP Monitoring metrics | ✅ | ✅ | — | `aws_metrics.py`, `metrics_collector.py` |

### Provision (`/api/provision`)

| Endpoint | AWS | GCP | Azure | Notes |
|----------|-----|-----|-------|-------|
| Plan / apply / destroy / drift | ✅ | ✅ | ✅ | Templates: static-site, backend-app, serverless-db per CSP |
| Provision templates | 3 (S3, VPC+EC2, DynamoDB) | 3 (GCS, GCE+VPC, Firestore) | 3 (Blob, VM+VNet, Cosmos) | Legacy keys static-gcs / static-blob kept |
| `GET /templates?csp=` / `GET /modules?csp=` | ✅ | ✅ | ✅ | Per-provider catalog |
| Engine resolver | boto3 \| terraform | sdk \| terraform | sdk \| terraform | SDK = GCS/Blob fast path (Settings → Boto3) |
| Scheduled drift | ✅ BYOC per CSP | ✅ | ✅ | Celery uses `resolve_provision_terraform_env` |

---

## Stale / misleading code (tracking)

| Item | Action | Status |
|------|--------|--------|
| Duplicate `backend/cost/` (AWS placeholders) | Remove; canonical `app/cost/` | Phase 0 ✅ |
| `resolve_credentials()` returns `None` for non-AWS | Extend in Phase 3 | Phase 3 ✅ |
| Mixed `"AWS"` / `"aws"` / `"GCP"` in APIs | `app/cloud/providers.py` | Phase 0 ✅ |

---

## Phase completion log

| Phase | Matrix updated | Date |
|-------|----------------|------|
| 0 | Initial matrix + contract | 2026-06-03 |
| 1 | Restore route, tier names, missing_config sync, tests | 2026-06-03 |
| 2 | Billing Settings fields, setup APIs, cost UI wizard | 2026-06-03 |
| 3 | BYOC verify tri-cloud, bucket/container discovery, TF resolver | 2026-06-03 |
| 7 | Platform cloud_connectivity, docs closure, Phase 27 checklist | 2026-06-03 |
