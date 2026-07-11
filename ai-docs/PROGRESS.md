# PROGRESS.md — Task Tracker

> **Last Updated:** 2026-07-11

---

## 🔴 Active Task

**None** — **Stage 1 (Production Beta) COMPLETE** (2026-06-15); post–Stage 1 polish **COMPLETE** (2026-07-11)

---

## Post–Stage 1 polish ✅ (2026-06-27 — 2026-07-11)

- [x] **Password UX** — `PasswordRequirementsPanel`; 8-char minimum (frontend `passwordPolicy.js` + backend `password_policy.py`)
- [x] **Notifications** — visible toasts + bell via `notifications.js`; migrated security, team, support, admin, file upload flows
- [x] **Help & support** — unified `/help` with tickets tab; `SupportTicketsSection`; profile dropdown + nav links updated
- [x] **Production fixes** — Settings `CloudProviderLogo` import; API proxy / cold-start login; admin portal gate
- [x] **Desktop v0.1.4** — version bump, `releases.json`, GitHub Release (DMG/EXE/AppImage/deb), lockfile CI fix
- [x] **Launch scripts** — bash audit (`start_all.sh`, `start-celery.sh`, `setup_cost_features.sh`)
- [x] **Lint** — `SecuritySettingsPage` hook deps; `AdminOverviewPage` unused import removed

---

## Stage 1 — Production Beta Closeout ✅

- [x] **CI** — Playwright admin API + sidebar smoke; Redis service in playwright job; desktop-release git stash/rebase
- [x] **Onboarding** — Per-user tour keys; Getting Started checklist; Settings Restart Tour → dashboard
- [x] **Cache** — Billing per-user cache; authenticated cost cache clear; cloud availability 5m TTL; `CACHING_GUIDE.md`, `ONBOARDING_GUIDE.md`, `ADR_001_CACHING_STRATEGY.md`
- [x] **Performance** — Slim dashboard fetch (3 critical + deferred); billing-status 30m cache; GET `/stats` no cloud refresh; Mongo indexes; Vite manualChunks; lazy joyride + recharts
- [x] **Desktop icons** — `png2icons` → `icon.icns` / `icon.ico`; electron-builder platform icons; prebuild hooks
- [x] **Admin** — AdminLayout loading spinner while user resolves

---

## Phase 25–30 — Mobile + Desktop Download ✅

- [x] **25** — Mobile breakpoint consistency, modal/drawer/wizard CSS
- [x] **26** — data-card-table on core data pages
- [x] **27** — Dense pages, mobile onboarding tips, E2E, manual_testing 6.13–6.14
- [x] **28** — Electron live-site shell (`desktop/`)
- [x] **29** — `/download` page, releases.json, desktop-release CI
- [x] **30** — Signing docs, electron-updater stub, Trust Center copy

---

## Phase 22 — SaaS pages polish (zero/low-cost) ✅
