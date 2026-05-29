# Secure Vault Replication Strategy

Zenith stores secure vault objects in **two S3 buckets**:

- **Primary:** `SECURE_S3_BUCKET_NAME` (region `PRIMARY_S3_REGION`)
- **Replica:** `REPLICA_S3_BUCKET_NAME` (region `REPLICA_S3_REGION`)

Every SSE-S3 or client-encrypted upload uses `_put_secure_object_dual()` in `backend/app/security/routes_security.py`, which writes the same object key to both buckets.

## Why this matches the research paper

The 6-page paper describes **geographic resilience** and redundancy. Dual-bucket writes provide:

- Protection against single-bucket loss
- A clear CRR-style story for viva (without requiring AWS Cross-Region Replication configuration in Terraform)

## Sync

The **Sync with Bucket (AWS)** action on Security and Storage pages reconciles MongoDB metadata with S3 listings (`list_objects_v2`), similar to the free-tier-friendly approach in the main storage module.

## Not in scope

- Multi-region active-active failover
- Automatic geo-fencing of login sessions (see session geo in `session_utils.resolve_geo_location`)
