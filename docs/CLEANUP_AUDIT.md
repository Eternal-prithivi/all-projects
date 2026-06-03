# Cleanup audit (June 2026)

Review of files removed in `chore(cleanup): phase 1` and `phase 2` (`c5fef02`, `6cfbc62`).

## Summary

- **Runtime / product:** No critical backend or frontend feature was permanently lost. Replacements already existed for footer, 2FA, admin, and cost pages.
- **Restored in follow-up:** BYOC storage banner, `GlassPanel`, GCP demo doc, `PROFESSIONAL_IMPROVEMENTS.md` redirect, `start_backend_test.sh`.
- **Intentionally not restored:** Duplicate PDFs/logos, obsolete AWS stub package, redundant deployment guide, one-off dev shell scripts.

## Phase 1 — code (`c5fef02`)

| Path | Verdict |
|------|---------|
| `backend/app/aws/*` | Safe — no imports in codebase |
| `backend/app/auth/auth_controller.py` | Safe — unused |
| `backend/app/auth/auth_service.py.save` | Safe — editor backup |
| `frontend/src/components/Footer.jsx` | Safe — use `components/layout/Footer.jsx` |
| `frontend/src/components/security/Enable2FA.jsx` | Safe — inline in `SecurityPage.jsx` |
| `frontend/src/pages/AdminDashboardPage.jsx` | Safe — `pages/admin/AdminOverviewPage.jsx` etc. |
| `frontend/src/styles/admin-dashboard.css` | Safe — admin uses shared dashboard styles |
| `frontend/src/styles/login.css`, `register.css` | Safe — auth pages use `auth-pages.css` / global tokens |
| `frontend/src/components/ByocStorageTargetBanner.jsx` | **Restored** — helps BYOC users see bucket/prefix |
| `frontend/src/components/ui/GlassPanel.jsx` | **Restored** — matches `zenith-ui.css` + design docs |

## Phase 2 — docs & assets (`6cfbc62`)

| Path | Verdict |
|------|---------|
| `docs/deployment/DEPLOYMENT_GUIDE.md` | Superseded by `PRODUCTION_DEPLOYMENT_GUIDE.md` |
| `docs/development/GCP_DEMO_SETUP.md` | **Restored** |
| `PROFESSIONAL_IMPROVEMENTS.md` | **Redirect stub** at repo root |
| `docs/cost-analysis/COST_*` (3 files) | Redundant with `COST_ANALYSIS_IMPLEMENTATION.md` |
| `docs/development/CACHING_*.md` (3 files) | Consolidated into `CACHING_GUIDE.md` |
| `docs/technical/DEMO_RUNBOOK.md` | Moved to `docs/DEMO_RUNBOOK.md` (index updated) |
| `frontend/NOTIFICATION_*.md` | UI docs only; notifications work in app |
| `start_backend_test.sh` | **Restored** |
| Logo drafts / PDF exports | Safe to omit from git |

## How to re-check after future cleanups

```bash
# List deletions in last N commits
git log --diff-filter=D --summary -10

# Search for broken references to a removed path
rg 'OldFileName' --glob '*.{md,jsx,py,ts}'
```

## Related

- [Later Developments.md](../Later%20Developments.md) — deferred work checklist  
- [TESTING.md](./testing/TESTING.md) — how to verify nothing regressed  
