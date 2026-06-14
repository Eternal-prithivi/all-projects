# STATUS.md — Live Project Snapshot

**Last Updated:** 2026-06-14 (Phase 29 download page)

---

## Identity

| Phase | **29** Desktop download page + CI · **COMPLETE** |
| Prior | Phase 25–27 Mobile · Phase 28 Electron shell · COMPLETE |

---

## 🔴 Active Task

**Phase 30 — Desktop signing prep (optional)** — `IN PROGRESS` (started 2026-06-14)

- **Scope:** INSTALL.md, trust copy, signing guide — no paid certs required yet
- **Done when:** Docs explain signing path; Trust Center links download

---

## Health

| Check | Status |
|-------|--------|
| Frontend build | pass (Phase 29) |
| Desktop CI | `desktop-release.yml` on `desktop-v*.*.*` tags |
| E2E | mobile-shell includes `/download` |

---

## Phase 29 summary

- `/download` page, `releases.json`, nav/footer/sitemap
- `desktop-release.yml` matrix → GitHub Releases
- `detectPlatform.js`, `DESKTOP_DOWNLOAD_FAQ` in productFacts

---

## Render notes (platform storage)

1. Upload `backend/config/platform_storage_catalog.json` as a **secret file** on Render (not in git).
2. Set env: `PLATFORM_STORAGE_CATALOG_JSON=config/platform_storage_catalog.json`, `PLATFORM_STORAGE_DEFAULT_SLUG=asia`.
3. Re-deploy backend after catalog or env changes.

See `docs/cloud/PLATFORM_STORAGE_REGIONS.md`.
