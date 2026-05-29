# PROGRESS.md — Task Tracker

> **Startup:** read `STATUS.md` only (not this file unless updating active task).
> **Full PRE-PHASE:** fill `## 🔴 Active Task` before code (never leave empty while work is in flight).
> **Full POST-PHASE:** finalize with `STATUS.md`, then commit + push. **Lightweight fix:** skip if active task unchanged.
> Narratives → `PROGRESS_HISTORY.md` only (never duplicate here or in chat).
> Last Updated: 2026-05-29

---

## 🛑 STANDING ANTI-TASKS

- Do NOT refactor `SecurityPage.jsx` to use `api.js`
- Do NOT delete stubs in `backend/app/aws/`, `providers/`, `queue/`, `errors/`
- Do NOT run `npm audit fix --force`
- Do NOT change **Zenith** / **ZenithApp** branding
- Do NOT use Redux/Zustand or paid services
- Do NOT commit `backend/.env`

---

## 📋 Task Template

```
## 🔴 Active Task
**[Name]** | Status: IN PROGRESS | Started: YYYY-MM-DD
Scope: [...] | Do NOT touch: [...] | Done when: [...]
```

---

## 🔴 Active Task

**None** — Enterprise dashboard UI/UX pass 5 **COMPLETE** (2026-05-29). See `PROGRESS_HISTORY.md` and `UI_UX_AUDIT_2026.md` Pass 5.

---

## 🗺️ Phase Summary

| Phase | Status | Notes |
|-------|--------|-------|
| 1–3 | ✅ | UI polish, BYOC, Mission Control dashboard, settings |
| 4 | 🔲 partial | Storage sync ✅; cost/VM/admin items remain |
| 5–10 | ✅ | ML foundation → hardening, demo runbook |
| 11–11b | ✅ | Terraform provision, OPA, drift, RBAC, audit |
| **12** | **✅** | SSE-S3 + browser CSE + auto SSE + sessions + benchmarks |

### ✅ UI/UX platform polish (2026-05-29) — complete

Waves 0–5 + **pass 3**: `dashboard-polish.css`, `CostHubNav`, `PageHeader` on Storage/Settings/Profile/Cost Analysis, cost page layout fix (no nested 100vh), Pass 3 gap table in `UI_UX_AUDIT_2026.md`.

### Phase 12 checklist

- [x] `clientEncryption.js` (PBKDF2 + AES-CBC)
- [x] `sensitive_file_detector.py` + upload encrypt flow
- [x] SSE-S3 dual-bucket + UI badges SSE / CSE
- [x] Secure vault AWS sync
- [x] Auto SSE-S3 when sensitive (no modal for default path)
- [x] Session geolocation + device fingerprint
- [x] Detector benchmark tests + labeled dataset
- [ ] KMS — **out of scope**

### Product readiness (post–Phase 12)

- [ ] Backend re-validation schemas for all forms (partial — auth/forms done)
- [x] CI/CD (pytest + eslint + build) — `.github/workflows/ci.yml`
- [x] Expanded tests (46 pytest: session, BYOC, storage, security, benchmark)

---

## 🔍 Open Issues

| Issue | Status |
|-------|--------|
| Sidebar `/dashboard/costs` and `/dashboard/compute` dead links | Open — add routes or remove links |
| 39 empty stub files | Open — build or document |
| CI/CD | Not active |

Fixed issues (CORS, .env in git, dashboard stats, admin self-delete, login validation) → `PROGRESS_HISTORY.md`

---

## Report parity

High-level report vs code matrix lives in `PROGRESS_HISTORY.md` (§ Report vs Code). Phase 5 contracts: `DECISIONS.md` + `backend/app/ml/acceptance.py`.
