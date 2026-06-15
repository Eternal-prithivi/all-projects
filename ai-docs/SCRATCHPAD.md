# SCRATCHPAD.md

## 🔄 Current Resume State

**Status:** COMPLETE (2026-06-15)

**Stage 1 — Production Beta:** CI, onboarding, cache, performance, desktop branded icons — all delivered and pushed to `stage`.

**Next (Stage 2 — when user asks):** Desktop code signing; tag `desktop-v0.1.2` with rebuilt branded installers; Redis app cache; dashboard BFF endpoint.

---

## ✅ Last Known Good State

**Stage 1 closeout** (2026-06-15)

- CI: Playwright green; desktop-release workflow fixed
- Onboarding: `OnboardingTour.jsx`, `GettingStartedCard`, `ONBOARDING_GUIDE.md`
- Cache: billing/cost/availability fixes; `CACHING_GUIDE.md`, `ADR_001_CACHING_STRATEGY.md`
- Performance: `DashboardPage.jsx` deferred loads; `billing_status.py` cache; `routes_dashboard.py` Mongo aggregation
- Desktop: `generate-brand-assets.mjs` → icns/ico; `desktop/package.json` prebuild + platform icons
- Docs: `STATUS.md`, `PROGRESS.md`, `PROGRESS_HISTORY.md` updated

**Git:** `stage` @ latest push — verify CI + Vercel + Render after push

**Verify locally:**
```bash
cd backend && .venv/bin/python -m pytest -q
cd frontend && npm run lint && npm run build
cd frontend && npm run test:e2e
```
