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
| **Storage restore** | Glacier (`POST /restore-aws/{filename}`) | Not implemented | Not implemented | `routes_storage.py` | 1 |
| **Cost / budgets** | Full + CE grouping | Code path; needs BigQuery export + env | Code path; needs subscription + SP | `app/cost/manager.py`, `billing_status.py` | 2 |
| **BYOC** | Full + verify + buckets | Connect + resolver; **no step-1 verify** | Same | `app/byoc/routes_byoc.py`, `credential_resolver.py` | 3 |
| **Security vault** | Full (S3 SSE dual) | UI filter only | UI filter only | `app/security/routes_security.py` | 4 |
| **VM / monitoring** | EC2 via provision only | **Full VM API** | None | `app/vm/manager.py`, `gcp_runtime.py` | 5 |
| **Provision** | TF + Boto3 | None | None | `app/provision/engine_resolver.py`, `backend/terraform/` | 6 |
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
| `POST /restore-aws/{filename}` | ✅ | ❌ | ❌ | Phase 1: rename or 501 for non-AWS |

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
| `POST /verify-credentials` | ✅ | ❌ | ❌ | Phase 3 |
| `GET /aws-buckets` | ✅ | ❌ | ❌ | Phase 3: GCP/Azure list parity |
| `resolve_credentials()` for TF | ✅ | ❌ | ❌ | Phase 3 / 6 |

### Security (`/api/security`)

| Endpoint | AWS | GCP | Azure | Notes |
|----------|-----|-----|-------|-------|
| Secure upload / list / sync | ✅ | ❌ | ❌ | Phase 4 |
| OPA `aws_security.rego` | ✅ | — | — | Phase 4 stubs for GCP/Azure |

### VM (`/api/vm`)

| Endpoint | AWS | GCP | Azure | Notes |
|----------|-----|-----|-------|-------|
| Lifecycle / clusters / metrics | 🟡 | ✅ | ❌ | Phase 5 |

### Provision (`/api/provision`)

| Endpoint | AWS | GCP | Azure | Notes |
|----------|-----|-----|-------|-------|
| Plan / apply / destroy / drift | ✅ | ❌ | ❌ | Phase 6 |
| Engine resolver | boto3 \| terraform (AWS only) | — | — | |

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
| 1 | — | — |
