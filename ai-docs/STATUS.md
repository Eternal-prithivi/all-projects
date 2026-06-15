# STATUS.md — Live Project Snapshot

**Last Updated:** 2026-06-15 (Stage 1 — production beta **COMPLETE**)

---

## Identity

| Milestone | **Stage 1 — Production Beta** · **COMPLETE** |
|-----------|-----------------------------------------------|
| Phases | 25–30 Mobile + Desktop · COMPLETE |
| Stage 1 closeout | CI green · onboarding · cache · performance · branded desktop icons |

---

## Active Task

**None** — Stage 1 fully delivered; ready for Stage 2 (signing, Redis cache, BFF) when prioritized

---

## Health

| Check | Status |
|-------|--------|
| CI (`stage`) | green — lint, pytest, Playwright, security-audit, docker-scan |
| Deploy Stage | auto on CI pass → Vercel (frontend) + Render (backend) |
| Desktop CI | `desktop-v0.1.1` + icon.icns/ico pipeline in `brand:assets` |
| Frontend lint | `eslint . --max-warnings 0` |
| Frontend build | `vite build` with vendor chunk split |
| Render keep-alive | scheduled ping every 5 min |
| Signing | unsigned beta — see `docs/desktop/SIGNING.md` |

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

- **Tag:** `desktop-v0.1.1` (rebuild with branded icons via CI or `desktop-v0.1.2` when re-tagged)
- **Page:** `/download` on rajverse.me
- **Assets:** `Zenith-0.1.1.dmg`, `Zenith.Setup.0.1.1.exe`, `Zenith-0.1.1.AppImage`, `zenith-desktop_0.1.1_amd64.deb`
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
