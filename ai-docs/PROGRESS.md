# PROGRESS.md — Task Tracker

> **Startup:** read `STATUS.md` only (not this file unless updating active task).
> **Full POST-PHASE:** update with `STATUS.md`. **Lightweight fix:** skip if active task unchanged.
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

**Phase 12: Security Research Paper Parity**

| | |
|--|--|
| Status | **IN PROGRESS** \| Started: 2026-05-29 |
| Done | Browser CSE, sensitive scan, encrypt modal, SSE-S3 dual-bucket, secure vault AWS sync |
| Open | Session geo/fingerprint, detector benchmarks, auto SSE default for sensitive |
| Spec | `PHASE_12_SECURITY_RESEARCH_PARITY.md` |
| Resume | `SCRATCHPAD.md` |

---

## 🗺️ Phase Summary

| Phase | Status | Notes |
|-------|--------|-------|
| 1–3 | ✅ | UI polish, BYOC, Mission Control dashboard, settings |
| 4 | 🔲 partial | Storage sync ✅; cost/VM/admin items remain |
| 5–10 | ✅ | ML foundation → hardening, demo runbook |
| 11–11b | ✅ | Terraform provision, OPA, drift, RBAC, audit |
| **12** | **🔲 active** | SSE-S3 + browser CSE + detection + sessions |

### Phase 12 checklist

- [x] `clientEncryption.js` (PBKDF2 + AES-CBC)
- [x] `sensitive_file_detector.py` + upload encrypt flow
- [x] SSE-S3 dual-bucket + UI badges SSE / CSE
- [x] Secure vault AWS sync
- [ ] Auto SSE-S3 when sensitive (no modal for default path)
- [ ] Session geolocation + device fingerprint
- [ ] Detector benchmark tests
- [ ] KMS — **out of scope**

### Product readiness (post–Phase 12)

- [ ] Backend re-validation schemas for all forms
- [ ] CI/CD (pytest + eslint + build)
- [ ] Expanded integration tests

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
