# Phase 12 — Security Research Paper Parity

> **Status:** Core complete (2026-05-29). Optional: production geo IP service SLA, new-device email alerts.  
> **Live task / resume:** `STATUS.md` + `SCRATCHPAD.md` only — do not duplicate session state here.

## Acceptance criteria

| Item | Status |
|------|--------|
| SSE-S3 dual-bucket upload | Done |
| Browser CSE (Web Crypto, password not on wire) | Done |
| Sensitive scan (CC, credentials, email, private IP) | Done |
| Auto SSE-S3 when sensitive (no modal by default) | Done |
| Session geolocation + device fingerprint | Done |
| Detector benchmark dataset + script | Done |
| AWS KMS | **Out of scope** — SSE-S3 only |

## Auto SSE flow

1. `POST /api/security/upload-secure` scans file.
2. If sensitive and not `encrypt_manual` and not `always_ask_encryption` → `_persist_sse_secure_file`.
3. UI shows success toast (`status: auto_encrypted_sse`).

## Benchmark

```bash
cd backend && .venv/bin/python scripts/security_detector_benchmark.py
```

Dataset: `app/security/datasets/sensitive_scan_labeled.json`

## Replication

See [docs/security/REPLICATION_STRATEGY.md](../docs/security/REPLICATION_STRATEGY.md).
