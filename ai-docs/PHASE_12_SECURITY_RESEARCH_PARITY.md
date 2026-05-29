# Phase 12 — Security Research Paper Parity (Hybrid Encryption & Threat Detection)

> **Reference:** `research paper Major 6 pages-2.pdf` (6-page paper: *Hybrid Encryption and Intelligent Pattern-Matching Architecture*)  
> **Status:** 🔲 **NEXT PHASE — NOT STARTED**  
> **Depends on:** Phase 11 complete; existing Security page shell (`SecurityPage.jsx`), `routes_security.py`, `routes_2fa.py`, `EncryptionChoiceModal.jsx`  
> **Budget constraint:** Zero-cost / free-tier only — see `AI_RULES.md` (KMS free tier limits, no paid threat-intel APIs)

---

## 1. Purpose

The research paper describes Zenith’s **Security Management Service** as a unified layer: RFC 6238 2FA, **hybrid dual encryption** (SSE-KMS + zero-knowledge CSE), **automated sensitive-data detection**, cross-region replication (CRR), and **session auditing with device fingerprint + geolocation**.

The codebase has a **working Security page UI** and partial backend flows, but several paper-critical behaviors are **missing, stubbed, or implemented differently**. Phase 12 closes that gap so demos, screenshots, and evaluation metrics align with the paper (Tables 1–2, Figure 2, Section 4–5).

---

## 2. What Exists Today (Baseline)

| Area | Current implementation | Paper claim |
|------|------------------------|-------------|
| Security page | Upload, scan, encryption choice modal, list, download, delete, AWS sync | Figure 2: auto KMS + manual mode |
| 2FA | `pyotp` TOTP, issuer `ZenithApp`, `valid_window=1` | RFC 6238, ~90s drift tolerance |
| Server-side encrypt | `ServerSideEncryption='AES256'` on `put_object` | **AWS KMS**, AES-256-**GCM**, auto on detection |
| Client-side encrypt | PBKDF2-SHA256 100k + AES-256-CBC in `encryption_handler.py` | Same algorithms, but **zero-knowledge in browser** |
| Sensitive scan | Inline regex in `routes_security.py` (CC + keywords) | CC + PII + **private IP ranges**; Table 1 metrics |
| Replication | Dual `put_object` to primary + replica bucket | **AWS CRR** (e.g. us-east-1 → us-west-2) |
| Session audit | User-Agent label + IP; `location: "Local network"` | **Device fingerprint + geolocation** |
| Stubs | `kms_encryption.py`, `sensitive_file_detector.py`, `audit_logs.py` empty | Fully implemented modules |

---

## 3. Gap Analysis — Must Implement (Paper Parity)

### 3.1 Hybrid dual encryption (highest priority)

| # | Paper requirement | Current gap | Deliverable |
|---|-------------------|-------------|-------------|
| E1 | **Server-Side Encryption via AWS KMS** (AES-256-GCM, cloud-managed keys, FIPS narrative) | Uses SSE-S3 (`AES256`), not KMS; `kms_encryption.py` empty | Implement `kms_encryption.py`: KMS key id / alias, `SSEKMSKeyId` on upload; document free-tier key usage |
| E2 | **Automatic SSE-KMS** when sensitive data is detected | Upload stops at “awaiting encryption choice”; user must always choose | On `is_sensitive=True`, default path: encrypt with KMS + upload **without** blocking modal (paper Table 2: “Automatic” integration) |
| E3 | **Optional manual encryption** (operator control) | “Encrypt manually” checkbox exists but does not match paper’s KMS-auto + manual override story | Align UX: auto-KMS for flagged files; manual checkbox forces choice modal or CSE |
| E4 | **True zero-knowledge Client-Side Encryption** | Password sent to API; encryption runs **on server** | Browser **Web Crypto** (or equivalent): derive key with PBKDF2, encrypt before upload; server stores ciphertext only; never log password |
| E5 | **CSE only after detection or user opt-in** | Partially true | Enforce paper flow: non-sensitive + no manual flag → plain or SSE-KMS per policy; sensitive → auto KMS unless user selects CSE |
| E6 | Security UI shows encryption type | List shows Encrypted / Normal / Action Required | Add badges: `SSE-KMS`, `CSE`, `None` (match paper screenshots / Table 2) |
| E7 | Encryption overhead metadata | Not surfaced | Store/display 32-byte salt+IV overhead note for CSE files |

### 3.2 Automated sensitive data detection

| # | Paper requirement | Current gap | Deliverable |
|---|-------------------|-------------|-------------|
| D1 | Detect **credit cards** (13–16 digits) | Basic regex present | Move to `sensitive_file_detector.py`; Luhn optional (reduce false positives) |
| D2 | Detect **PII** (broader patterns) | Only keyword list | Add email, SSN-style, phone patterns (configurable) |
| D3 | Detect **private IP ranges** (RFC1918) | **Not implemented** | Add 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16 matchers |
| D4 | **Mandatory encryption workflow** for flagged files | Modal choice; can delay upload | Block persist to S3 unencrypted when flagged (paper: preemptive block) |
| D5 | **Evaluation metrics** (Table 1) | No benchmark suite | Add `backend/tests/test_sensitive_detection_benchmark.py` with ~50-case fixture; target paper ballpark (76% accuracy documented as baseline, improve FPR) |
| D6 | Reduce false positives (35% FPR in paper) | Technical docs trigger keywords | Context-aware rules or allowlist for `.md`/`.log` in docs mode (optional stretch) |

### 3.3 2FA (RFC 6238)

| # | Paper requirement | Current gap | Deliverable |
|---|-------------------|-------------|-------------|
| A1 | RFC 6238 TOTP HMAC-SHA1 | Implemented via `pyotp` | Document compliance in code comments |
| A2 | **90-second drift tolerance** | `valid_window=1` (≈3×30s steps — verify/document) | Explicit constant `TOTP_VALID_WINDOW` + unit test; document “90s total window” in UI/help |
| A3 | Verification **10–20 ms** | Not measured | Add lightweight timing log or test (optional benchmark note for paper) |

### 3.4 Session auditing & compliance visibility

| # | Paper requirement | Current gap | Deliverable |
|---|-------------------|-------------|-------------|
| S1 | **Device fingerprint** in MongoDB | User-Agent string only | Collect stable fingerprint hash (UA + screen/lang optional from frontend header) — privacy-preserving |
| S2 | **Geolocation** on sessions | Hardcoded `"Local network"` in `routes_auth.py` | Free geo: IP → country/city via offline DB or single free API with cache; store on login |
| S3 | Audit integration with Security Settings | Activity log exists | Ensure security events (encrypt, download, sync) append to same audit stream |

### 3.5 Cross-region replication (CRR)

| # | Paper requirement | Current gap | Deliverable |
|---|-------------------|-------------|-------------|
| R1 | **AWS CRR** (~N. Virginia → Oregon, ~15 min eventual consistency) | Application-level dual `put_object` to `SECURE_S3_BUCKET` + `REPLICA_S3_BUCKET` | Configure **S3 CRR** on secure bucket (or document BYOC); app writes primary only, replication async |
| R2 | Eleven-nines / DR narrative | Implied by dual bucket | Document actual regions from `.env`; demo checklist |
| R3 | Replica on delete | Dual delete in code | Keep consistent if staying dual-write; if CRR-only, delete primary only |

---

## 4. Security Page — UI/UX Checklist (Figure 2)

- [ ] After sensitive scan: **auto-encrypt with KMS** and show success (no forced modal unless user chose manual/CSE).
- [ ] **“Encrypt manually”** opens CSE path or advanced choice (paper: optional operator control).
- [ ] File table columns: **Encryption type** (KMS / CSE / None), **Replication status** (optional).
- [ ] Download: CSE still requires password modal; KMS/SSE uses presigned URL.
- [ ] Help text explaining trade-off (Table 2): automation vs zero-knowledge.
- [ ] Keep **Sync with Bucket (AWS)** for secure vault metadata reconcile (implemented 2026-05-29).

---

## 5. Project-Wide Inconsistencies (Paper vs Codebase)

| Topic | Research paper / report | Codebase reality | Action in Phase 12 |
|-------|-------------------------|------------------|-------------------|
| SSE algorithm | KMS + **AES-256-GCM** | SSE-S3 **AES256** | Switch to SSE-KMS + document |
| CSE location | Client/browser zero-knowledge | Server-side `encryption_handler.py` | Move CSE to frontend crypto |
| Detection module | Dedicated intelligent engine | Empty `sensitive_file_detector.py` | Centralize + test |
| Auto-encrypt on detect | Automatic KMS | User choice modal | Change default pipeline |
| CRR | Managed AWS replication | Dual upload in app | Prefer CRR or document deviation |
| Session geo | Geolocation stored | `"Local network"` placeholder | Implement IP geo |
| AI docs | “Security largely done” (`PROGRESS` §4.4) | Gaps above | Update all AI docs after implementation |
| Full report PDF | 97-page `Major Project latest22- Report-5.pdf` | Broader scope than 6-page paper | Phase 12 scoped to **security paper only**; other report items stay in backlog |
| `kms_encryption.py` listed in AI_CONTEXT | Module exists | **Empty file** | Implement or remove from “exists” lists until done |

---

## 6. Suggested Implementation Order

1. **E1 + E2 + D1–D4** — KMS + detector module + auto-encrypt pipeline (backend + minimal UI).
2. **E4 + E6 + E7** — Browser CSE + UI badges (frontend-heavy).
3. **D5** — Benchmark tests + README metrics for paper Table 1.
4. **S1 + S2 + S3** — Session fingerprint + geolocation.
5. **R1–R3** — CRR configuration + docs (infra; may be `.env`/Terraform note only on free tier).
6. **A2 + A3** — 2FA tolerance tests + doc.

---

## 7. Done Criteria (Phase 12 Complete)

- [ ] Sensitive upload with flagged PII/CC/IP → **automatic SSE-KMS** upload without mandatory modal.
- [ ] User can still choose **CSE** with password; ciphertext uploaded; server cannot decrypt.
- [ ] `sensitive_file_detector.py` and `kms_encryption.py` implemented (no empty stubs).
- [ ] Detection benchmark test file runs in CI (`pytest`).
- [ ] Session records show **IP + geo + device fingerprint** (not `"Local network"` only).
- [ ] AI docs (`AI_MASTER`, `PROGRESS`, `AI_CONTEXT_*`, `DECISIONS`) reflect **implemented** state.
- [ ] Demo script: one server-side KMS sample file + one client-side encrypted sample (paper Section 4 output comparison).

---

## 8. Out of Scope (Paper “Future Work”)

- AI-driven behavioral anomaly detection  
- Blockchain immutable audit logs  
- Semantic/contextual ML for sensitive detection (paper suggests as improvement beyond 76% baseline)

---

## 9. Files Expected to Change

**Backend:** `app/security/routes_security.py`, `encryption_handler.py`, `kms_encryption.py`, `sensitive_file_detector.py`, `routes_2fa.py`, `auth/routes_auth.py`, `storage/tasks.py`, tests  
**Frontend:** `SecurityPage.jsx`, `EncryptionChoiceModal.jsx`, optional `utils/clientEncryption.js`, `api.js`  
**Infra/docs:** `.env.production.example`, `ai-docs/*`, optional `docs/SECURITY_DEMO.md`
