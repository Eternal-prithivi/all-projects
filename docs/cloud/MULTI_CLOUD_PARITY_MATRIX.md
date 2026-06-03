# Multi-Cloud Parity Matrix

**Last updated:** 2026-06-03 (Phase 0)  
**Plan:** Multi-cloud parity Phases 0–7  
**Credential detail:** [CREDENTIAL_CONTRACT.md](./CREDENTIAL_CONTRACT.md)

Success criterion (every phase): With valid platform `.env` or per-user BYOC, the feature behaves like today’s AWS path — no silent AWS-only failures when the user selects GCP or Azure.

---

## Area summary

| Area | AWS | GCP | Azure | Key modules | Phase |
|------|-----|-----|-------|-------------|-------|
| **Storage (standard)** | Full | Full | Full | `app/storage/uploader.py`, `cloud_credentials.py`, `routes_storage.py` | 1 |
| **Storage restore** | Glacier (`POST /restore/AWS/{filename}`) | 501 not_supported | 501 not_supported | `routes_storage.py` | 1 ✅ |
| **Cost / budgets** | Full + CE grouping | BigQuery + setup wizard | Cost Management + setup wizard | `app/cost/manager.py`, `billing_config.py` | 2 ✅ |
| **BYOC** | Full + verify + buckets | Connect + resolver; **no step-1 verify** | Same | `app/byoc/routes_byoc.py`, `credential_resolver.py` | 3 |
| **Security vault** | Full (S3 SSE dual) | Full | Full | `app/security/routes_security.py` | 4 ✅ |
| **VM / monitoring** | **Full VM API** (EC2) | **Full VM API** (GCE) | None | `aws_manager.py`, `manager.py`, `vm_provider.py` | 5 ✅ |
| **Provision** | TF + Boto3 | TF (GCS) | TF (Blob) | `terraform/`, `provision_catalog.py` | 6 ✅ |
| **Pricing** | Static table | Static table | Static table | `app/pricing/pricing_fetcher.py` | — (documented, non-live) |

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
| `POST /restore/{csp}/{filename}` | ✅ AWS | 501 | 501 | Legacy `/restore-aws/` → AWS; DEC-024 |

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
| `POST /connect` | ✅ | ✅ | ✅ | |
| `POST /test` | ✅ | ✅ | ✅ | |
| `POST /verify-credentials` | ✅ | ✅ | ✅ | Phase 3 ✅ |
| `GET /aws-buckets` | ✅ | — | — | AWS |
| `GET /gcp-buckets` + `POST …/discover` | — | ✅ | — | Phase 3 ✅ |
| `GET /azure-containers` + `POST …/discover` | — | — | ✅ | Phase 3 ✅ |
| `resolve_credentials()` for TF | ✅ | ✅ | ✅ | Phase 3 ✅ (BYOC only) |

### Security (`/api/security`)

| Endpoint | AWS | GCP | Azure | Notes |
|----------|-----|-----|-------|-------|
| Secure upload / list / sync / download / delete | ✅ | ✅ | ✅ | Phase 4 ✅ |
| `POST /security/sync/{csp}` | ✅ | ✅ | ✅ | Phase 4 ✅ |
| AWS dual-bucket replica | ✅ | — | — | GCP/Azure replica deferred |
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
| Plan / apply / destroy / drift | ✅ | ✅ | ✅ | Phase 6 ✅ |
| `GET /templates?csp=` / `GET /modules?csp=` | ✅ | ✅ | ✅ | Per-provider catalog |
| Engine resolver | boto3 \| terraform | terraform only | terraform only | GCP/Azure require TF |

---

## Stale / misleading code (tracking)

| Item | Action | Status |
|------|--------|--------|
| Duplicate `backend/cost/` (AWS placeholders) | Remove; canonical `app/cost/` | Phase 0 ✅ |
| `resolve_credentials()` returns `None` for non-AWS | Extend in Phase 3 | Open |
| Mixed `"AWS"` / `"aws"` / `"GCP"` in APIs | `app/cloud/providers.py` | Phase 0 ✅ |

---

## Phase completion log

| Phase | Matrix updated | Date |
|-------|----------------|------|
| 0 | Initial matrix + contract | 2026-06-03 |
| 1 | Restore route, tier names, missing_config sync, tests | 2026-06-03 |
| 2 | Billing Settings fields, setup APIs, cost UI wizard | 2026-06-03 |
| 3 | BYOC verify tri-cloud, bucket/container discovery, TF resolver | 2026-06-03 |
