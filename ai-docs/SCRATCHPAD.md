# SCRATCHPAD.md

## ✅ Last Known Good State

**Status:** COMPLETE (2026-06-11)

**Phase 22 — SaaS pages polish (zero/low-cost)** shipped.

**Key paths:**
- Copy SSOT: `frontend/src/data/productFacts.js`, `frontend/src/config/billingConstants.js`
- Backend: `dashboard/cost_snapshots.py`, `GET /api/dashboard/cost-trend`, `POST /api/support/tickets`, `DELETE /api/organizations/invites/{email}`
- Pages: `DashboardPage`, `HelpCenterPage`, `BillingPage`, `SupportPage`, `TeamPage`, `CostAnalysisEnhancedPage`
- Tests: `test_dashboard_cost_trend.py`, org revoke + support create in integration tests
- Manual QA: `docs/testing/manual_testing.md` rows 6.4–6.10

**Prior (Phase 20):** Trust docs + BYOC encryption hardening.

**Quality gates:** `pytest tests/integration/test_dashboard_cost_trend.py tests/integration/test_organizations_api.py tests/integration/test_support_api.py -q`; `cd frontend && npm run build`

---

## Step list (completed)

- [x] productFacts + Help/marketing pricing rewrite
- [x] Billing FX constant + API plan names
- [x] Overview honesty + cost-trend Mongo snapshots
- [x] Cost Analysis cleanup + CostHubNav dedup
- [x] Team revoke/copy + Support in-app tickets + Admin polish
- [x] manual_testing.md + ai-docs context updates
