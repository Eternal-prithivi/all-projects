# BYOC credential encryption — technical reference

**Module:** `backend/app/byoc/encryption.py`  
**Consumers:** `routes_byoc.py`, `credential_resolver.py`, `billing_setup.py`  
**User-facing trust summary:** [TRUST_AND_ENCRYPTION.md](./TRUST_AND_ENCRYPTION.md)

---

## Design goals

1. **Confidentiality at rest** — no plaintext secrets in MongoDB.
2. **Field-level encryption** — each secret (`secret_access_key`, `service_account_json`, `account_key`, …) encrypted separately with its own nonce.
3. **Authenticated encryption** — AES-GCM detects tampering.
4. **Idempotent encrypt** — reconnect or retry must not double-encrypt.
5. **Incremental merge** — partial credential updates keep unchanged fields.

---

## Wire format

### Version 1 (current)

```
zenith:enc:v1:<base64( nonce_12_bytes || ciphertext || gcm_tag )>
```

- **Nonce:** 12 random bytes per encryption (never reused for same key).
- **Key:** `SHA-256(SECRET_KEY)` → 32-byte AES key.
- **Associated data:** none (`None` in GCM).

### Legacy (pre-2026-06)

Base64 blob without prefix. `decrypt_credential()` and `is_encrypted_credential()` still accept legacy values.

---

## API surface

| Function | Purpose |
|----------|---------|
| `encrypt_credential(plaintext)` | Encrypt one string; no-op if already encrypted |
| `decrypt_credential(encrypted)` | Decrypt v1 or legacy blob |
| `is_encrypted_credential(value)` | Detect encrypted vs plaintext |
| `encrypt_credentials_dict(dict)` | Encrypt all non-empty string values |
| `decrypt_credentials_dict(dict)` | Decrypt encrypted fields only |
| `merge_and_encrypt_credentials(existing, incoming)` | Incremental store on connect |

---

## Connect flow

`POST /api/byoc/connect` builds a plaintext `credentials_to_encrypt` dict per CSP, then:

```python
encrypted_creds = merge_and_encrypt_credentials(
    _existing_byoc_credentials(username, csp),
    credentials_to_encrypt,
)
```

- **First connect:** all provided fields encrypted.
- **Reconnect:** only non-empty fields in the request are re-encrypted; omitted secrets keep prior ciphertext.

Resolver path (`get_user_cloud_credentials` → `decrypt_credentials_dict`) decrypts in memory before boto3 / GCS / Azure SDK calls.

---

## Security boundaries

| In scope | Out of scope (future / ops) |
|----------|----------------------------|
| AES-256-GCM at rest | AWS KMS / GCP Cloud KMS envelope (Tier F 26.2) |
| Per-field nonces | HSM-backed master key |
| No secrets in API responses | Automated key rotation without re-connect |
| Merge on connect | Org-level CMK per tenant |

---

## Operations

### Rotate application `SECRET_KEY`

1. **Do not** rotate without a migration script — existing ciphertext becomes undecryptable.
2. Planned approach: decrypt with old key, re-encrypt with new key for all `byoc_credentials.credentials` documents.

### Rotate user cloud keys

1. User creates new key in AWS/GCP/Azure console.
2. User re-runs BYOC connect in Settings with new values.
3. `merge_and_encrypt_credentials` replaces only submitted fields.

### Verify encryption in MongoDB

```javascript
// credentials.secret_access_key should start with zenith:enc:v1:
db.byoc_credentials.findOne({ username: "...", csp: "AWS" }, { credentials: 1 })
```

Never paste production ciphertext into tickets.

---

## Tests

`backend/tests/test_byoc_encryption.py` — roundtrip, idempotency, unique nonces per field, merge behavior, legacy format.
