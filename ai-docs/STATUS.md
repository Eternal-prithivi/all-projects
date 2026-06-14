# STATUS.md — Live Project Snapshot

**Last Updated:** 2026-06-14 (One-shot completion — production beta)

---

## Identity

| Phase | **30** Desktop signing prep · **COMPLETE** |
| Prior | Phases 25–29 Mobile + download · COMPLETE |

---

## Active Task

**None** — production beta ready; `desktop-v0.1.1` tagged with Zenith branded icons

---

## Health

| Check | Status |
|-------|--------|
| CI (`stage`) | green after one-shot push (lint, pytest, security-audit, docker-scan) |
| Deploy Stage | auto-runs when CI passes → Vercel + Render |
| Desktop CI | `desktop-v0.1.1` — branded DMG/EXE/AppImage/deb on GitHub Releases |
| Frontend lint | `eslint . --max-warnings 0` |
| Render keep-alive | scheduled ping every 5 min |
| Signing | unsigned beta — see `docs/desktop/SIGNING.md` |

---

## Desktop downloads

- **Tag:** `desktop-v0.1.1`
- **Page:** `/download` on rajverse.me (release availability via GitHub API)
- **Assets:** `Zenith-0.1.1.dmg`, `Zenith.Setup.0.1.1.exe`, `Zenith-0.1.1.AppImage`, `zenith-desktop_0.1.1_amd64.deb`
- macOS build is **arm64** (Apple Silicon)

---

## Render manual checklist (cannot automate)

| Item | Action |
|------|--------|
| Platform storage catalog | Upload `backend/config/platform_storage_catalog.json` as a **secret file** on Render; set `PLATFORM_STORAGE_CATALOG_JSON` + `PLATFORM_STORAGE_DEFAULT_SLUG=asia` |
| Deploy secrets | Confirm GitHub secrets: `RENDER_DEPLOY_HOOK`, `VERCEL_*` — see `docs/setup/DEPLOYMENT_SECRETS.md` |
| Optional uptime | Set `UPTIME_API_URL` repo secret to enable scheduled health checks in `uptime.yml` |
| Cold starts | Expected on free tier; keep-alive mitigates but first wake can take 1–2 min |

See `docs/cloud/PLATFORM_STORAGE_REGIONS.md` for catalog details.

---

## Phase 25–30 summary

- **Mobile:** breakpoint consistency, card-table layouts, mobile onboarding tips, provision/settings/VM polish
- **Desktop:** Electron shell → rajverse.me; `/download`; GitHub Releases CI; Zenith icons in v0.1.1+
- **Docs:** INSTALL.md, SIGNING.md, Trust Center, manual_testing 6.13–6.14

---

## Out of scope (intentional)

- Apple/Windows code signing (unsigned beta)
- Intel macOS DMG (CI builds arm64 only)
