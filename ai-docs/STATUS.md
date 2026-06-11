# STATUS.md — Live Project Snapshot

**Last Updated:** 2026-06-11 (SaaS pages polish — Overview, Help, Support, Team, Billing)

---

## Identity

| Phase | **22** SaaS pages polish (zero/low-cost) · **COMPLETE** |
| Prior | Phase 21 Provision intent wizard + GCP/Azure SDK parity · COMPLETE |

---

## 🔴 Active Task

_None — Phase 22 shipped 2026-06-11. Next task TBD._

---

## Health

| Check | Status |
|-------|--------|
| Backend pytest | ✅ integration: org revoke, support create ticket, dashboard cost-trend |
| Frontend build | ✅ green (2026-06-11) |
| E2E playbook | `docs/testing/manual_testing.md` (rows 6.4–6.10) |
| Trust docs | `docs/security/TRUST_AND_ENCRYPTION.md` |
| Render deploy branch | `stage` → auto-deploy |

---

## Phase 22 summary

- **Trust copy:** `frontend/src/data/productFacts.js` — Help, marketing pricing, billing labels (INR)
- **Overview:** platform status banner, plan-based storage cap, budget/team cards, cost trend from Mongo (`/api/dashboard/cost-trend`)
- **Support:** `POST /api/support/tickets` + in-app New ticket UI
- **Team:** `DELETE /api/organizations/invites/{email}`, copy invite link, billing callout
- **Cost:** CostHubNav deduped; demo-safe refresh-only sparkline snapshots

---

## Render notes (platform storage)

1. Upload `backend/config/platform_storage_catalog.json` as a **secret file** on Render (not in git).
2. Set env: `PLATFORM_STORAGE_CATALOG_JSON=config/platform_storage_catalog.json`, `PLATFORM_STORAGE_DEFAULT_SLUG=asia`.
3. Re-deploy backend after catalog or env changes.

See `docs/cloud/PLATFORM_STORAGE_REGIONS.md`.
