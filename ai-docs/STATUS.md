# STATUS.md — Live Project Snapshot

**Last Updated:** 2026-05-29

---

## Identity

| Field | Value |
|-------|--------|
| Project | CloudResourceOptimizationPlatform (**Zenith**) |
| Phase | **17** in progress |
| Last major complete | Phase 16 — BYOC credential routing (storage, security, cost, VM GCP) |

---

## 🔴 Active Task

**Phase 17 — AWS BYOC two-step connect (three buckets)**

| Done | Two-step Settings wizard (verify → buckets), `/byoc/verify-credentials`, `/byoc/check-bucket-name`, `/byoc/storage-targets`, three-bucket connect + resolver, Storage/Security destination banners |
| Next | Phase 2: replica dual-write hardening, CloudFormation template, bucket migration UI |

---

## Health

| Check | Status |
|-------|--------|
| Backend pytest | Run after pull (`cd backend && pytest -q`) |
| Frontend build | Run `cd frontend && npm run build` after pull |

---

## Critical Warnings

1. `backend/.env` — never commit
2. Product name **Zenith** — do not rebrand without asking
3. GCP BYOC for VMs requires Compute API roles on the service account
