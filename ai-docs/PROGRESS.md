# PROGRESS.md — Task Tracker

> **Last Updated:** 2026-06-03

---

## 🔴 Active Task

**None** — Phase 1 complete. **Next:** Multi-cloud parity **Phase 2** (cost / budgets / billing UX).

---

## Multi-cloud parity

| Phase | Theme | Status |
|-------|--------|--------|
| **0** | Foundation | ✅ Complete |
| **1** | Storage hardening | ✅ Complete |
| **2** | Cost / budgets | ⬜ Not started |
| **3–7** | BYOC → security → VM → provision → polish | ⬜ Not started |

---

## Phase 1 — Storage ✅

- [x] **1.1** — `storage_tiers.py` + lifecycle tier name alignment
- [x] **1.2** — GCP/Azure upload/delete/download/sync tests (mocked)
- [x] **1.3** — `missing_config` on GCP/Azure sync; BYOC resolvers unchanged paths
- [x] **1.4** — `POST /restore/{csp}/{filename}`; 501 for GCP/Azure; legacy `/restore-aws/`
- [x] **1.5** — `StoragePage` + `getApiErrorMessage` for structured errors
- [x] **1.6** — DEC-024, matrix update, 236 pytest

---

## Phase 20.5

Paused at **20.5.10**.
