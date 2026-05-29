# SCRATCHPAD.md

**Status:** Phase 17 (AWS BYOC connect wizard) — implemented locally

**Task:** Phase 1 of BYOC bucket plan — two-step AWS connect + three buckets

**Summary:**
- Backend: `aws_bucket_helpers.py`, extended `routes_byoc` (verify, check-bucket, storage-targets, connect tests all buckets), `credential_resolver` + `resolve_secure_aws_storage` for dedicated secure/replica buckets
- Frontend: Settings two-step flow (access keys + IAM role), `ByocStorageTargetBanner` on Storage + Security pages
- Old BYOC records with single `bucket_name` still work via resolver fallbacks

**Next:** Phase 2 replica dual-write tests, IAM CloudFormation, migration job UI
