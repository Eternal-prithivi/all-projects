# STATUS.md — Live Project Snapshot

**Last Updated:** 2026-06-10 (Trust docs + BYOC encryption hardening)

---

## Identity

| Phase | **20** Trust narrative + BYOC credential encryption · **COMPLETE** |
| Prior | Phase 19 Platform multi-region storage + page refresh UX · COMPLETE |

---

## 🔴 Active Task

_None — Phase 20 shipped 2026-06-10. Next task TBD._

---

## Health

| Check | Status |
|-------|--------|
| Backend pytest | ✅ encryption + layout tests pass (`test_byoc_encryption.py`) |
| Frontend build | ✅ green (2026-06-09) |
| E2E playbook | `docs/testing/manual_testing.md` |
| Trust docs | `docs/security/TRUST_AND_ENCRYPTION.md` |
| Render deploy branch | `stage` → auto-deploy |

---

## Render notes (platform storage)

1. Upload `backend/config/platform_storage_catalog.json` as a **secret file** on Render (not in git).
2. Set env: `PLATFORM_STORAGE_CATALOG_JSON=config/platform_storage_catalog.json`, `PLATFORM_STORAGE_DEFAULT_SLUG=asia`.
3. Re-deploy backend after catalog or env changes.

See `docs/cloud/PLATFORM_STORAGE_REGIONS.md`.
