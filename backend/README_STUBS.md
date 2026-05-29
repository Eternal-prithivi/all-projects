# Backend Stub Modules — Intentional Placeholders

Per `ai-docs/AI_RULES.md`, do **not** delete these without an explicit architecture decision.

| Path | Purpose |
|------|---------|
| `app/aws/` | Legacy AWS helper namespace; active code uses `boto3` in `storage/` and `security/` |
| `app/providers/` | Future multi-provider factory; uploads use `storage/uploader.py` directly |
| `app/queue/` | Reserved for non-Celery queue adapters |
| `app/errors/` | Shared error types (partial adoption) |

## KMS note

`kms_encryption.py` is **not required** for Phase 12. Server-side encryption uses **SSE-S3 (`AES256`)** only.

## When to implement vs remove

1. Document the caller in `DECISIONS.md`.
2. Add tests before wiring production routes.
3. Remove only if grep shows zero imports.
