# Secure vault replication (tri-cloud)

## AWS (implemented)

Zenith secure vault on AWS uses **dual-bucket SSE-S3** via `put_secure_object_dual` in `app/storage/cloud_credentials.py`:

- Primary: `SECURE_S3_BUCKET_NAME` (or BYOC bucket with `secure/{username}/` prefix)
- Replica: configured replica region/bucket (`REPLICA_REGION_DEFAULT` helpers)

## GCP and Azure (Phase 4)

Phase 4 adds **single-region** secure vault on GCS and Azure Blob:

- Objects live under `secure/{username}/` on platform buckets, or `{username}/` when BYOC uses the shared storage bucket/container.
- Server-side encryption uses provider defaults (GCS/Azure managed keys).
- **Cross-region replication is deferred** — no automatic dual-write for GCP/Azure in this release.

## Future work

- Optional GCS dual-bucket or Azure GRS replication aligned with `docs/security/REPLICATION_STRATEGY.md`
- OPA policies in `gcp_security.rego` / `azure_security.rego` wired into provision validation
