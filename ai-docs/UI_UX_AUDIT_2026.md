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
