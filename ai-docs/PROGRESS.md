# PROGRESS.md — Task Tracker

> **Last Updated:** 2026-06-11

---

## 🔴 Active Task

_None — Phase 22 complete._

---

## Phase 22 — SaaS pages polish (zero/low-cost) ✅

- [x] **22.1** — `productFacts.js` + Help/marketing INR copy SSOT
- [x] **22.2** — `billing_constants` FX + BillingPage API plan names
- [x] **22.3** — Dashboard honesty (status, storage cap, budgets, team, attention strip)
- [x] **22.4** — `cost_snapshots` + `GET /dashboard/cost-trend` (Mongo read on load)
- [x] **22.5** — Cost Analysis cleanup; CostHubNav without duplicate Billing
- [x] **22.6** — Team invite revoke + copy; Support `POST /tickets`; Admin test dev-only
- [x] **22.7** — `manual_testing.md` 6.4–6.10 + integration tests + build

---

## Phase 20 — Trust docs + BYOC encryption ✅

- [x] **20.1** — `docs/security/TRUST_AND_ENCRYPTION.md` (BYOC, SSE, CSE custody)
- [x] **20.2** — `docs/security/BYOC_CREDENTIAL_ENCRYPTION.md` (technical)
- [x] **20.3** — `encryption.py` v1 prefix, idempotent encrypt, `merge_and_encrypt_credentials`
- [x] **20.4** — `test_byoc_encryption.py` + routes merge on connect
- [x] **20.5** — Docs index, parity matrix, CREDENTIAL_CONTRACT, ai-docs context

---

## Phase 19 — Platform storage regions + page refresh UX ✅

- [x] **19.1** — `platform_storage_catalog.py` + example JSON + unit tests
- [x] **19.2** — Static AWS/GCP/Azure discovery from catalog (no live list on platform page load)
- [x] **19.3** — Upload/sync `region_slug` + scoped stale removal in sync/list
- [x] **19.4** — `CloudDestinationPanel`, region pills, `StorageRegionScopeBar`
- [x] **19.5** — Page-level `PageRefreshButton` on all dashboard + admin pages
- [x] **19.6** — Gold `BucketSelectorLoading` for AWS/GCP/Azure on reload
- [x] **19.7** — Docs + pytest 320 + build + push `stage`

---

## Phase 18d — Support Chat UX ✅

Chat-style thread UI + 10s poll + WS refresh. No live chat.

- [x] **18d.1** — `ws_notify.py` + wire customer/agent WS events
- [x] **18d.2** — Integration tests for WS notify
- [x] **18d.3** — Shared `SupportThreadPanel` + `SupportMessageBubble` + `supportFormat`
- [x] **18d.4** — `useSupportThreadPoll` + `useSupportThreadWs` + event bus
- [x] **18d.5** — Refactor SupportPage, SupportTicketPage, AdminSupportPage
- [x] **18d.6** — CSS polish (sticky composer, pending state, mobile)
- [x] **18d.7** — POST docs + pytest/build + push

---

## Phase 18c — Async Support Tickets ✅

- [x] All 18c items complete (see PROGRESS_HISTORY.md)

---

## Multi-cloud parity

| Phase | Status |
|-------|--------|
| **0–7** | ✅ Complete |
