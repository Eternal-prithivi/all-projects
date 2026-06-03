# VM multi-cloud scope

**Last updated:** 2026-06-03

## Supported today

| CSP | Lifecycle API | Metrics | Notes |
|-----|---------------|---------|-------|
| **AWS** | ✅ EC2 via `aws_manager.py` | ✅ CloudWatch (`aws_metrics.py`) | BYOC or platform IAM |
| **GCP** | ✅ GCE via `manager.py` / `gcp_runtime.py` | ✅ GCP Monitoring | BYOC SA needs Compute roles |
| **Azure** | ✅ Compute via `azure_manager.py` | ✅ Simulated / Monitor-ready (`azure_metrics.py`) | BYOC or platform service principal |

## API contract

- Pass `csp` (`AWS`, `GCP`, `Azure`) on VM requests or query params.
- Azure requires **service principal** fields (`subscription_id`, `tenant_id`, `client_id`, `client_secret`) in BYOC or platform `.env`, plus a **resource group** with at least one **subnet** (`AZURE_RESOURCE_GROUP`, default `zenith-rg`).
- Storage-only Azure BYOC (account + key) enables storage/cost; VM assignment uses simulated pools until Compute credentials are added.

## Cluster VM names

| CSP | Example pool VM |
|-----|-----------------|
| AWS | `general-aws-vm-1` |
| GCP | `general-vm-1` |
| Azure | `general-azure-vm-1` |

Provision with `POST /api/vm/provision?csp=Azure` to create tagged VMs in your resource group.

See also: [MULTI_CLOUD_PARITY_MATRIX.md](./MULTI_CLOUD_PARITY_MATRIX.md), [CREDENTIAL_CONTRACT.md](./CREDENTIAL_CONTRACT.md).
