# PROGRESS.md — Task Tracker

> **Last Updated:** 2026-06-03

---

## 🔴 Active Task

**None** — Phase 6 complete. **Next:** Phase 7 (pricing parity / docs).

---

## Multi-cloud parity

| Phase | Status |
|-------|--------|
| **0–6** | ✅ Complete |
| **7** | ⬜ |

---

## Phase 6 — Provision GCP/Azure ✅

- [x] **6.1** — `terraform/gcp`, `terraform/azure`, `terraform_roots.py`
- [x] **6.2** — `resolve_provision_terraform_env`, `TerraformRunner` cloud env
- [x] **6.3** — `provision_catalog.py`, `csp` on plan/apply/deployments
- [x] **6.4** — `ProvisionDeployWizard` + `ProvisionPage` provider UX
- [x] **6.5** — DEC-027, matrix, tests (260 pytest)

---

## Phase 5 — VM AWS parity ✅

- [x] **5.1** — `aws_manager.py` + `aws_runtime.py` (EC2 lifecycle)
- [x] **5.2** — `vm_provider.py` dispatch; `csp` on assignments
- [x] **5.3** — CloudWatch metrics (`aws_metrics.py`)
- [x] **5.4** — `VMClusterPage` provider toolbar + API `csp`
- [x] **5.5** — DEC-026, matrix, integration tests (257 pytest)

---

## Phase 4 — Secure vault tri-cloud ✅

- [x] **4.1** — `secure_vault.py` (`SecureGcpStorage`, `SecureAzureStorage`, vault helpers)
- [x] **4.2** — `routes_security.py` provider dispatch + `POST /sync/{csp}`
- [x] **4.3** — `SecurityPage.jsx` + `api.js` (`syncSecureVault`, upload `csp`)
- [x] **4.4** — DEC-025, `SECURE_VAULT_REPLICATION.md`, OPA stubs
- [x] **4.5** — Integration tests + matrix update

---

## Phase 3 — BYOC ✅

- [x] **3.1** — `/verify-credentials` for GCP + Azure
- [x] **3.2** — `gcp-buckets` / `azure-containers` discover + list
- [x] **3.3** — `resolve_credentials()` for GCP/Azure Terraform env
- [x] **3.4** — Settings BYOC verify + bucket/container pickers
- [x] **3.5** — Integration + resolver tests
