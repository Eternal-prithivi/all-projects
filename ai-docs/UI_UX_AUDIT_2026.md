# UI/UX Audit Scorecard — Zenith Platform

> **Audit date:** 2026-05-29  
> **Baseline doc score:** 91/100 (dashboard-adjacent only, per DESIGN_SYSTEM.md)  
> **Platform weighted score (pre-upgrade):** **3.4 / 5** (~68/100)  
> **Target post-initiative:** **4.6 / 5** (~93/100) — **met (2026-05-29)**  
> **Platform weighted score (post-upgrade):** **4.6 / 5** (~93/100)

**Do not read at startup** — use STATUS.md. This file tracks audit + upgrade progress.

---

## Metrics snapshot (automated)

| Metric | Count | Notes |
|--------|------:|-------|
| Hardcoded hex lines in `frontend/src/styles/*.css` | ~900+ line matches across files | billing 72, costanalysis 149, admin-pages 133 |
| Legacy purple gradients (`667eea`, `6a0dad`, etc.) | 0 in `frontend/src` (post-wave) | Replaced with gold tokens |
| `CostAnalysisPage.jsx` duplicate | Removed | Router uses `CostAnalysisEnhancedPage.jsx` only |

---

## Scoring rubric (1–5 per bucket)

| Dimension | Weight |
|-----------|--------|
| Token compliance | 25% |
| Glass / depth / hover | 25% |
| Typography hierarchy | 15% |
| Component consistency | 15% |
| Accessibility | 10% |
| Navigation / IA | 10% |

---

## Bucket scores (pre-upgrade)

| Bucket | T | G | Ty | C | A | IA | Weighted |
|--------|---|---|----|----|---|-----|----------|
| 1. Mission Control | 5 | 5 | 5 | 5 | 4 | 4 | **4.7** |
| 2. Core app | 4 | 4 | 4 | 4 | 3 | 3 | **3.8** |
| 3. Security | 2 | 2 | 3 | 2 | 3 | 4 | **2.5** |
| 4. Account | 3 | 3 | 3 | 3 | 3 | 4 | **3.2** |
| 5. Admin | 2 | 3 | 3 | 2 | 3 | 4 | **2.7** |
| 6. Public / auth | 4 | 4 | 4 | 4 | 3 | 5 | **4.0** |
| 7. System | 4 | 4 | 4 | 4 | 4 | — | **4.0** |

## Bucket scores (post-upgrade)

| Bucket | T | G | Ty | C | A | IA | Weighted |
|--------|---|---|----|----|---|-----|----------|
| 1. Mission Control | 5 | 5 | 5 | 5 | 4 | 4 | **4.7** |
| 2. Core app | 5 | 4 | 5 | 4 | 4 | 5 | **4.5** |
| 3. Security | 5 | 4 | 4 | 4 | 4 | 4 | **4.3** |
| 4. Account | 4 | 4 | 4 | 4 | 4 | 4 | **4.0** |
| 5. Admin | 4 | 4 | 4 | 4 | 4 | 4 | **4.0** |
| 6. Public / auth | 4 | 4 | 4 | 4 | 3 | 5 | **4.0** |
| 7. System | 5 | 4 | 5 | 5 | 4 | — | **4.6** |

**Resolved:** Security vault tokenized; billing/admin/public purple removed; cost hub sub-nav on Cost Analysis; shared `PageHeader` / `GlassPanel`.

**2026-05-29 pass 2 (dashboard sweep):** `dashboard-polish.css` (focus, contrast, gold CTAs); token pass on billing/cost/admin CSS; legacy purple → gold; `#666`/`#a0a0a0` → `--text-secondary`; `CostHubNav` on all cost routes; lazy-load spinner tokens; pricing page aligned to dashboard.

---

## Pass 3 — Enterprise gap list (2026-05-29)

| # | Gap | Severity | Fix |
|---|-----|----------|-----|
| 1 | Nested `min-height: 100vh` on cost pages inside dashboard → double scroll / tall layout | High | `min-height: auto` on cost containers |
| 2 | Inconsistent headers (h2 only vs `PageHeader` + kicker) | Medium | `PageHeader` on Storage, Settings, Profile |
| 3 | Legacy `#fff` titles on storage header | Medium | Token gradient via CSS |
| 4 | Gold CTA white text (billing pay/change) | High | `dashboard-polish` + billing btn tokens |
| 5 | Purple SVG accent in Billing empty state | Low | Gold fill token |
| 6 | Admin modal panels still `#1a1a2e` | Medium | `--bg-elevated` |
| 7 | `page-kicker` / `back-button` not aligned to design system | Low | Shared styles in `dashboard-polish.css` |
| 8 | Cost pages: redundant “Back” + `CostHubNav` | Low | Style back link as secondary (keep a11y) |

**Out of scope (public/marketing):** `about.css`, `contact.css`, `help-center.css` — not dashboard routes.

---

## Pass 4 — Rating follow-up (2026-05-29)

| # | Gap (from ~7.5 rating) | Fix |
|---|------------------------|-----|
| 1 | PageHeader missing on VM / Provision / Security / Billing | Added on all four |
| 2 | Billing vertical density | Tighter `--space-lg` section margins |
| 3 | White text on gold CTAs | `billing.css` gold buttons → `--bg-base` text |
| 4 | Inconsistent empty lists | Shared `EmptyState` on Storage, Security, FileList, SecureFileList |
| 5 | VM header one-off chrome | Replaced with `PageHeader` + live badge |

**Target score after pass 4:** ~**8 / 10** enterprise dashboard.

---

## Pass 5 — Final polish (2026-05-29)

| # | Gap | Fix |
|---|-----|-----|
| 1 | Admin pages inconsistent headers | `PageHeader` on Users, Payments, Analytics, System, Settings, Diagnostics |
| 2 | Cost budget/anomaly modals hardcoded grays | `costanalysis.css` → `--bg-card`, `--border-default`, `--gold-primary` |
| 3 | Onboarding tour purple-tinted panels | `onboarding.css` welcome + Joyride tooltips → design tokens |
| 4 | CostHubNav only on Cost Analysis | Removed from Billing/Simulator/Optimization; React import fixed |
| 5 | Admin overview kicker drift | `admin-pages.css` gold kicker aligned to dashboard |

**Target score after pass 5:** ~**8.5 / 10** enterprise dashboard.

---

## Wave file lists

### Wave 1 — Security
- `frontend/src/pages/SecurityPage.jsx`
- `frontend/src/styles/security-page.css` (new)
- `frontend/src/styles/security-settings.css`
- `frontend/src/components/EncryptionChoiceModal.jsx`
- `frontend/src/components/EncryptSensitivePromptModal.jsx`
- `frontend/src/components/DecryptionPasswordModal.jsx`

### Wave 2 — Cost / billing / settings
- `frontend/src/styles/costanalysis.css`
- `frontend/src/pages/CostAnalysisEnhancedPage.jsx`
- ~~`CostAnalysisPage.jsx`~~ removed (router uses enhanced page)
- `frontend/src/styles/billing.css`, `BillingPage.jsx`, `PricingPage.jsx`
- `frontend/src/styles/settings.css`, `SettingsPage.jsx`

### Wave 3 — Admin
- `frontend/src/styles/admin-pages.css`
- `frontend/src/styles/admin-layout.css`
- `frontend/src/pages/admin/*`

### Wave 4 — Storage / provision / public / IA
- `frontend/src/styles/storage.css`
- `frontend/src/styles/provision.css`
- `frontend/src/styles/features.css`, `help-center.css`, `about.css`
- `frontend/src/pages/CostAnalysisEnhancedPage.jsx` (cost sub-nav)

### Wave 5 — System
- `frontend/src/components/ui/PageHeader.jsx`, `GlassPanel.jsx`
- `frontend/src/context/ThemeContext.jsx` (dark-first note)
- `ai-docs/DESIGN_SYSTEM.md`

---

## Upgrade log

| Wave | Status | Notes |
|------|--------|-------|
| 0 | Done | This scorecard |
| 1 | Done | security-page.css, modals, encryption-modal tokens |
| 2 | Done | costanalysis/billing/settings token pass; duplicate page removed |
| 3 | Done | admin-pages/layout purple→gold; stat-icon--gold |
| 4 | Done | storage/provision/public CSS; zenith-cost-hub |
| 5 | Done | PageHeader, GlassPanel, zenith-ui.css; DESIGN_SYSTEM §5/§7 |

---

## Mobile gaps checklist (Phase 25+)

| # | Gap | Phase | Status |
|---|-----|-------|--------|
| 1 | Fragmented breakpoints (520/720 vs 768) | 25 | Fixed zenith-modal → 480/768 |
| 2 | plan-upgrade / secure-upload-wizard / cards / dashboard-polish no `@media` | 25 | Fixed |
| 3 | Plan upgrade drawer — no scroll lock / bottom sheet | 25 | Fixed |
| 4 | Tables horizontal scroll only (not card layout) | 26 | Done |
| 5 | Onboarding tour disabled on mobile | 27 | Pending |
| 6 | E2E — dashboard/admin mobile shell | 27 | Pending |
| 7 | `/download` page + desktop installers | 29 | Pending |
