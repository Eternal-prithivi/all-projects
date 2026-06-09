# Trust, encryption, and data custody

**Audience:** Users, security reviewers, and operators evaluating Zenith’s Secure Vault and BYOC.  
**Last updated:** 2026-06-10

This document is the **single source of truth** for what Zenith can and cannot see, how secrets are protected, and how encryption modes differ.

---

## Summary (plain language)

| Topic | What Zenith does |
|-------|------------------|
| **Your cloud account (BYOC)** | You connect AWS, GCP, or Azure with keys or IAM role. Credentials are **encrypted field-by-field** before MongoDB storage. Zenith decrypts them **only in memory** to call your cloud APIs. |
| **Zenith platform storage** | Files live in Zenith-operated buckets/containers configured in server `.env` / platform catalog. Standard cloud encryption-at-rest applies. |
| **Server-side encryption (SSE)** | Zenith encrypts files using the cloud provider’s managed keys (e.g. S3 SSE). Zenith operators with platform access **could** access ciphertext via cloud APIs; your data stays in **your chosen** bucket when using BYOC. |
| **Client-side encryption (CSE)** | File is encrypted **in your browser** with **your password** before upload. The password **never** hits Zenith’s API. Zenith stores only ciphertext. **We cannot read the file without your password.** |
| **2FA** | Secure Vault requires verified TOTP before list/upload/download/delete. |

---

## Deployment modes

### Platform mode

- Zenith uses **platform credentials** from server configuration.
- Storage and secure vault paths are fixed per cloud in the [platform storage catalog](../cloud/PLATFORM_STORAGE_REGIONS.md).
- Suitable for demos, managed SaaS, and users who do not bring their own cloud account.

### BYOC (Bring Your Own Cloud)

- You connect **your** AWS, GCP, or Azure account in **Settings → BYOC**.
- **Two-step connect:** verify credentials → configure storage + secure + replica bucket/container names (auto-created if missing).
- Storage page uses your **storage** bucket/container; Security page uses your **secure** bucket/container (and optional **replica** for backup/archive).
- **Hybrid:** You may connect BYOC for one cloud (e.g. AWS) while Zenith platform credentials serve GCP/Azure.

See [CREDENTIAL_CONTRACT.md](../cloud/CREDENTIAL_CONTRACT.md) for resolver behavior.

---

## BYOC credential protection

### What we store

Per cloud, MongoDB document `byoc_credentials` holds:

- Connection metadata (bucket names, regions, `secure_dual_write`, etc.) — **not secret**
- `credentials` object — **each secret field encrypted independently**

Examples of encrypted fields:

| Cloud | Encrypted fields |
|-------|------------------|
| AWS (keys) | `access_key_id`, `secret_access_key` |
| AWS (IAM role) | `role_arn`, `external_id` |
| GCP | `service_account_json`, optional billing dataset/table IDs |
| Azure | `account_key`, optional Cost Management `client_secret`, etc. |

Non-secret fields like `account_name`, `region`, or `role_arn` may appear in plaintext on the record where they are identifiers, not bearer secrets.

### How encryption works

Implementation: `backend/app/byoc/encryption.py`

| Property | Detail |
|----------|--------|
| Algorithm | **AES-256-GCM** (authenticated encryption) |
| Key derivation | 256-bit key from application `SECRET_KEY` (SHA-256) |
| Per-field nonce | **Unique 96-bit random nonce** per encrypt operation |
| Storage format | `zenith:enc:v1:<base64(nonce ‖ ciphertext ‖ tag)>` |
| Double encryption | **Prevented** — already-encrypted values are not re-encrypted |
| Incremental updates | **merge_and_encrypt_credentials** — empty incoming fields keep existing encrypted values; only provided fields are re-encrypted |

Credentials are decrypted **only inside the backend process** when resolving storage clients, sync, or provision — never returned in API responses or written to logs.

### What we do **not** do (today)

- BYOC secrets are **not** in plaintext in the database.
- API responses from `/byoc/connect` and `/byoc/status` do **not** echo secrets.
- Production should use a **dedicated encryption key or KMS** (see [professional_standard.md](../testing/professional_standard.md) Tier F — CMK path). Current design uses `SECRET_KEY` derivation suitable for single-tenant / staging; rotate `SECRET_KEY` only with a documented re-encryption migration.

### Your responsibilities (BYOC)

- Use **least-privilege** IAM / service accounts (policy templates in Settings).
- Prefer **IAM role** (AWS) over long-lived access keys when possible.
- Rotate keys in your cloud console and **re-connect** in Zenith to update stored credentials.
- Never commit `.env` or service account JSON to git.

Technical detail: [BYOC_CREDENTIAL_ENCRYPTION.md](./BYOC_CREDENTIAL_ENCRYPTION.md)

---

## Secure Vault encryption modes

### 1. Unencrypted (after explicit skip)

- Sensitive scan may flag a file; user can skip encryption with acknowledgment.
- File is stored in the secure vault path without extra application-layer encryption.
- Cloud provider encryption-at-rest still applies.

### 2. Server-side encryption (SSE)

- Zenith uploads to your secure bucket/container with provider-managed encryption (e.g. S3 SSE-S3 / SSE-KMS).
- **Zenith and cloud admins** with sufficient IAM can access object bytes.
- Optional **replica** copy in a second bucket/region for durability; sync UI deduplicates replica rows.

### 3. Client-side encryption (CSE) — zero-knowledge

**Supported today:** AWS secure vault upload path (GCP/Azure return 501 for browser CSE upload).

| Step | Where it happens |
|------|------------------|
| User chooses password | Browser only |
| PBKDF2 (100k iter, SHA-256) + AES-256-CBC | Browser (`frontend/src/utils/clientEncryption.js`) |
| Ciphertext upload | `POST /api/security/upload-client-encrypted` |
| Password on wire | **Never** — API accepts ciphertext blob only |
| Download | Browser fetches ciphertext; user enters password locally to decrypt |

**Trust statement:** For CSE files, Zenith stores **only ciphertext**. Without the user’s password, Zenith platform administrators cannot recover plaintext. If the password is lost, the file is **not recoverable**.

Legacy implementation notes: [CLIENT_SIDE_ENCRYPTION.md](./CLIENT_SIDE_ENCRYPTION.md) (some server-side Celery paths described there are superseded by browser-first CSE on AWS).

---

## Archive and replica vault

- **Replicated (badge):** Active file has a copy in primary + replica vault (dual-write).
- **Archived:** Object moved from **primary → replica** vault; download/delete blocked until **Restore**.
- **Restore:** Copy back to primary and remove replica copy to avoid double billing.

Applies to AWS, GCP, and Azure (platform and BYOC) when replica targets are configured.

See [SECURE_VAULT_REPLICATION.md](../cloud/SECURE_VAULT_REPLICATION.md).

---

## API and logging practices

- Secure routes guarded by `require_2fa`.
- BYOC connect/test/verify validate credentials without persisting plaintext in responses.
- Application logs use structured messages with **usernames and bucket names**, not secret values.
- Pre-signed download URLs are time-limited.

---

## Comparison table (for security reviews)

| Question | SSE | CSE | BYOC credentials |
|----------|-----|-----|------------------|
| Can Zenith read content? | Yes (with cloud access) | **No** (no password) | N/A (metadata only) |
| Can cloud provider read content? | Yes (they hold keys) | Only ciphertext | N/A |
| Can user lose access? | If cloud/IAM revoked | If password forgotten | If keys rotated without re-connect |
| Data location | User bucket (BYOC) or platform | Same | Secrets in Zenith DB encrypted |

---

## Related documents

| Document | Purpose |
|----------|---------|
| [BYOC_CREDENTIAL_ENCRYPTION.md](./BYOC_CREDENTIAL_ENCRYPTION.md) | Implementation and rotation |
| [CLIENT_SIDE_ENCRYPTION.md](./CLIENT_SIDE_ENCRYPTION.md) | CSE API and UI flow |
| [BYOC_IMPLEMENTATION.md](../BYOC_IMPLEMENTATION.md) | Product architecture |
| [CREDENTIAL_CONTRACT.md](../cloud/CREDENTIAL_CONTRACT.md) | Platform vs BYOC resolver |
| [DEPLOYMENT_SECRETS.md](../setup/DEPLOYMENT_SECRETS.md) | Production env vars |
| [CREDENTIAL_ROTATION.md](../setup/CREDENTIAL_ROTATION.md) | Rotation runbook |

---

## FAQ

**Does Zenith sell or train on my files?**  
No — files stay in your BYOC account or configured platform buckets. This is the architectural intent; contractual terms are in your legal/trust pages.

**Is BYOC required for maximum privacy?**  
BYOC keeps **data** in your account. **CSE** is required if you do not want Zenith to be *able* to read file contents (AWS CSE today).

**What happens if I disconnect BYOC?**  
Zenith stops using your credentials; encrypted credential documents are deactivated per disconnect flow. Objects already in your cloud remain yours.

**Is this SOC2 / HIPAA certified?**  
Not claimed in this document. See enterprise backlog for compliance roadmap.
