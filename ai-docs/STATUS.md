# STATUS.md — Live Project Snapshot

**Last Updated:** 2026-06-14 (Phase 25 PRE)

---

## Identity

| Phase | **25** Mobile foundation · **IN PROGRESS** |
| Prior | Phase 24 Shared org billing · COMPLETE |

---

## 🔴 Active Task

**Phase 25 — Mobile foundation** — `IN PROGRESS` (started 2026-06-14)

- **Scope:** Breakpoint consistency, modal/drawer/wizard CSS gaps, plan drawer mobile, UI_UX_AUDIT mobile checklist
- **Do NOT touch:** Card-table rollout (Phase 26), Electron/desktop (Phase 28+)
- **Done when:** iPhone 390px smoke on Overview/Storage/Billing/Settings — no page overflow; modals full-width; plan drawer usable

---

## Health

| Check | Status |
|-------|--------|
| Backend pytest | not required Phase 25 |
| Frontend build | verify after Phase 25 |
| E2E playbook | `docs/testing/manual_testing.md` |
| Render deploy branch | `stage` → auto-deploy |

---

## Phase 24 summary (prior)

- **Org billing:** seat-based Razorpay checkout per org; `get_effective_subscription()` resolver; members inherit org plan
- **ACL:** `resource_acl.py` — org_id + created_by on VM, storage, provision
- **UI:** Team seats card, Billing org panel, VM/Storage/Provision org labels

---

## Render notes (platform storage)

1. Upload `backend/config/platform_storage_catalog.json` as a **secret file** on Render (not in git).
2. Set env: `PLATFORM_STORAGE_CATALOG_JSON=config/platform_storage_catalog.json`, `PLATFORM_STORAGE_DEFAULT_SLUG=asia`.
3. Re-deploy backend after catalog or env changes.

See `docs/cloud/PLATFORM_STORAGE_REGIONS.md`.
