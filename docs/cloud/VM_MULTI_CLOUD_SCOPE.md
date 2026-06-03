# VM multi-cloud scope

**Last updated:** 2026-06-03 (Multi-cloud parity Phase 7)

## Supported today

| CSP | Lifecycle API | Metrics | Notes |
|-----|---------------|---------|-------|
| **AWS** | ✅ EC2 via `aws_manager.py` | ✅ CloudWatch (`aws_metrics.py`) | BYOC or platform IAM |
| **GCP** | ✅ GCE via `gcp_runtime.py` | ✅ GCP Monitoring | BYOC SA needs Compute roles |
| **Azure** | ❌ **501 not_supported** | ❌ | Explicit defer — Compute SDK not wired |

## API contract

- Pass `csp` (`AWS`, `GCP`, `Azure`) on VM requests or query params.
- Azure returns HTTP **501** with `code: not_supported` and a link to this doc.

## Future work (backlog)

- Azure Compute provider (`vm/providers/azure_provider.py`) + Azure Monitor metrics.
- Per-CSP machine-type catalogs in `CREDENTIAL_CONTRACT.md`.

See also: [MULTI_CLOUD_PARITY_MATRIX.md](./MULTI_CLOUD_PARITY_MATRIX.md), DEC-026.
