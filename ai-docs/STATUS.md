# STATUS.md — Live Project Snapshot

**Last Updated:** 2026-07-11 (Post–Stage 1 polish + desktop v0.1.4)

---

## Identity

| Milestone | **Stage 1 — Production Beta** · **COMPLETE** |
|-----------|-----------------------------------------------|
| Phases | 25–30 Mobile + Desktop · COMPLETE |
| Post–Stage 1 | UX polish, notifications, help unification, desktop v0.1.4 · **COMPLETE** |

---

## Active Task

**None** — ready for Stage 2 (signing, Redis cache, BFF) when prioritized

---

## Health

| Check | Status |
|-------|--------|
| CI (`stage`) | green — lint (`--max-warnings 0`), pytest, Playwright, security-audit, docker-scan |
| Deploy Stage | auto on CI pass → Vercel (frontend) + Render (backend) |
| Desktop CI | `desktop-v0.1.4` — DMG, EXE, AppImage, deb on GitHub Releases |
| Frontend lint | `eslint . --max-warnings 0` — green @ `97171c0` |
| Frontend build | `vite build` with vendor chunk split |
| Render keep-alive | scheduled ping every 5 min |
| Signing | unsigned beta — see `docs/desktop/SIGNING.md` |

---

## Recent deliverables (2026-06-27 — 2026-07-11)

| Area | Done |
|------|------|
| **Password UX** | `PasswordRequirementsPanel`; min length **8** (frontend + backend policy); register, reset, security-settings aligned |
| **Notifications** | `notifications.js` — visible top-right toasts + bell; `ToastContainer` on public shell; migrated security, team, support, admin, file actions |
| **Help & support** | Unified `/help` (articles + `?tab=tickets`); `SupportTicketsSection`; `/dashboard/support` → redirect; profile dropdown compact (no scroll bleed) |
| **Production fixes** | `SettingsPage` `CloudProviderLogo` import; rajverse.me API proxy + cold-start login; admin portal gate for platform owner |
| **Desktop v0.1.4** | `desktop/package.json` + `releases.json`; tag `desktop-v0.1.4`; CI lockfile sync (`npm ci` in desktop-release) |
| **Launch scripts** | `start_all.sh`, `start-celery.sh`, `setup_cost_features.sh` — bash audit fixes |
| **Lint** | `SecuritySettingsPage` `useCallback` deps; removed unused `notifyAdminSuccess` in `AdminOverviewPage` |

---

## Stage 1 deliverables (2026-06-15)

| Area | Done |
|------|------|
| **CI / E2E** | Playwright admin smoke (API + sidebar); Redis in CI playwright job; desktop-release stash/rebase fix |
| **Onboarding** | Per-user tour keys; Getting Started checklist on dashboard; Restart Tour navigates to dashboard |
| **Cache** | Billing per-user cache; cost cache auth; cloud availability TTL; docs + ADR-001 |
| **Performance** | Dashboard 3-request critical path; deferred secondary fetches; billing-status 30m cache; Mongo indexes; no cloud refresh on GET `/stats` |
| **Desktop icons** | `icon.icns` + `icon.ico` from `assets/brand/zenith-icon.png`; prebuild hooks on all platforms |
| **Admin UX** | AdminLayout loading state while `/users/me` resolves |

---

## Desktop downloads

- **Tag:** `desktop-v0.1.4` (published 2026-07-11)
- **Page:** `/download` on rajverse.me — reads `frontend/public/releases.json`
- **Assets:** `Zenith-0.1.4.dmg`, `Zenith.Setup.0.1.4.exe`, `Zenith-0.1.4.AppImage`, `zenith-desktop_0.1.4_amd64.deb`
- macOS build is **arm64** (Apple Silicon)

---

## Render manual checklist (cannot automate)

| Item | Action |
|------|--------|
| Platform storage catalog | Upload `backend/config/platform_storage_catalog.json` as secret file; set `PLATFORM_STORAGE_CATALOG_JSON` + `PLATFORM_STORAGE_DEFAULT_SLUG=asia` |
| Deploy secrets | Confirm `RENDER_DEPLOY_HOOK`, `VERCEL_*` — see `docs/setup/DEPLOYMENT_SECRETS.md` |
| Optional uptime | Set `UPTIME_API_URL` for scheduled health checks |
| Cold starts | Free tier; keep-alive mitigates; first wake 1–2 min |

---

## Out of scope (Stage 2+)

- Apple/Windows code signing
- Intel macOS DMG
- Redis shared app cache / dashboard BFF endpoint
- React Query migration
