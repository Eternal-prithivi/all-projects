# STATUS.md — Live Project Snapshot

**Last Updated:** 2026-06-14 (Phases 25–30 complete)

---

## Identity

| Phase | **30** Desktop signing prep · **COMPLETE** |
| Prior | Phases 25–29 Mobile + download · COMPLETE |

---

## 🔴 Active Task

**None** — awaiting user QA or `desktop-v0.1.0` release tag

---

## Health

| Check | Status |
|-------|--------|
| Frontend build | pass |
| Desktop CI | `desktop-release.yml` on `desktop-v*.*.*` |
| Mobile E2E | `mobile-shell.spec.ts` (marketing + download + dashboard nav) |
| Signing | unsigned beta — see `docs/desktop/SIGNING.md` |

---

## Phase 25–30 summary

- **Mobile:** breakpoint consistency, card-table layouts, mobile onboarding tips, provision/settings/VM polish
- **Desktop:** Electron shell → rajverse.me; `/download`; GitHub Releases CI
- **Docs:** INSTALL.md, SIGNING.md, Trust Center, manual_testing 6.13–6.14

---

## Render notes (platform storage)

1. Upload `backend/config/platform_storage_catalog.json` as a **secret file** on Render (not in git).
2. Set env: `PLATFORM_STORAGE_CATALOG_JSON=config/platform_storage_catalog.json`, `PLATFORM_STORAGE_DEFAULT_SLUG=asia`.
3. Re-deploy backend after catalog or env changes.

See `docs/cloud/PLATFORM_STORAGE_REGIONS.md`.
