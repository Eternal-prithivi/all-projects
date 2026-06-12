# STATUS.md — Live Project Snapshot

**Last Updated:** 2026-06-12 (Provision page error handling fix)

---

## Identity

| Phase | **24** Shared org billing + resource ownership · **COMPLETE** |
| Prior | Phase 23 Team page cloud health · COMPLETE |

---

## 🔴 Active Task

**Provision page fixes** — `IN PROGRESS` (started 2026-06-12) — **issue 1 done** (validation error crash)

- **Fixed:** FastAPI validation arrays no longer crash React on provision panels
- **Open:** Awaiting additional provision issues from user

---

## Health

| Check | Status |
|-------|--------|
| Backend pytest | integration: org billing, seat guards, migrate-personal, resources summary |
| Frontend build | verify after provision fix |
| E2E playbook | `docs/testing/manual_testing.md` (rows 6.11–6.12) |
| Trust docs | `docs/security/TRUST_AND_ENCRYPTION.md` |
| Render deploy branch | `stage` → auto-deploy |

---

## Phase 24 summary

- **Org billing:** seat-based Razorpay checkout per org; `get_effective_subscription()` resolver; members inherit org plan; personal checkout blocked in org
- **APIs:** `/organizations/billing/*`, `/organizations/resources/summary`, `/organizations/resources/reassign`
- **ACL:** `resource_acl.py` — org_id + created_by on VM, storage, provision; admin all / member own
- **Quotas:** org-level VM and storage limits from org plan
- **UI:** Team seats card, Billing org panel, VM/Storage/Provision org labels + admin resource toggle
- **Migration:** lazy billing defaults, migrate-personal, `backfill_org_resources.py`
- **Docs:** `ai-docs/ORG_BILLING_ARCHITECTURE.md`

## Phase 23 summary (prior)

- **Team backend:** `organizations/service.py` — summary, recommendations, approvals, settings, invite email
- **Team UI:** metrics row, member spend table, org budget, approvals, onboarding
- **Governance:** provision plan gate when estimate exceeds org threshold (HTTP 202)

## Phase 22 summary (prior)

- **Trust copy:** `productFacts.js` — Help, marketing pricing, billing labels (INR)
- **Overview:** platform status, cost trend Mongo, budget/team cards
- **Support:** in-app New ticket UI

---

## Render notes (platform storage)

1. Upload `backend/config/platform_storage_catalog.json` as a **secret file** on Render (not in git).
2. Set env: `PLATFORM_STORAGE_CATALOG_JSON=config/platform_storage_catalog.json`, `PLATFORM_STORAGE_DEFAULT_SLUG=asia`.
3. Re-deploy backend after catalog or env changes.

See `docs/cloud/PLATFORM_STORAGE_REGIONS.md`.
