# AI_CONTEXT_FRONTEND.md — Frontend Architecture & Source Map

> Read this for any frontend, UI, CSS, component, or routing task.
> **Last Updated: 2026-06-09** — Phase 19 platform storage regions + page refresh UX.

---

## 🏗 Project Overview (Brief)

**Zenith** — React 19 + Vite 7 frontend, glassmorphic Mission Control dashboard.
60+ pages, 4 React Contexts, Recharts, React Router DOM v6, Zenith design system.

For backend context → read `AI_CONTEXT_BACKEND.md`

---

## 📁 Frontend Structure (`frontend/src/`)

### Contexts (4 total — no Redux/Zustand)

| File | Purpose |
|------|---------|
| `AuthContext.jsx` | ★ JWT token in localStorage, `isAuthenticated`, `user`, `token`, `login()`, `logout()` |
| `ThemeContext.jsx` | Dark/Light/Auto theme switching — saves to DB, applies CSS class to `<html>` |
| `PreferencesContext.jsx` | Currency symbol, date format, timezone — feeds dashboard number/date display |
| `NotificationContext.jsx` | Real-time WebSocket notifications — bell badge count, toast on new events |

### Pages — Public (no auth required)

| Route | Page File |
|-------|----------|
| `/` | `HomePage.jsx` — landing / marketing |
| `/login` | `LoginPage.jsx` |
| `/register` | `RegisterPage.jsx` |
| `/forgot-password` | `ForgotPasswordPage.jsx` |
| `/reset-password` | `ResetPasswordPage.jsx` |
| `/contact` | `ContactPage.jsx` — creates ticket; shows `ZN-…` + track link |
| `/support/ticket` | `SupportTicketPage.jsx` — guest OTP lookup + thread |
| `/about` | `AboutPage.jsx` |
| `/features` | `FeaturesPage.jsx` |
| `/help` | `HelpCenterPage.jsx` — 26 FAQs, search, 6 categories |
| `/legal/terms` | `TermsOfServicePage.jsx` |
| `/legal/privacy` | `PrivacyPolicyPage.jsx` |
| `/legal/cookies` | `CookiePolicyPage.jsx` |
| `/legal/dpa` | `DpaPage.jsx` |
| `/trust` | `TrustCenterPage.jsx` |
| `/status` | `StatusPage.jsx` — polls `GET /api/platform/status` |
| `/verify-email` | `VerifyEmailPage.jsx` — `POST /api/auth/verify-email?token=` |
| `/pricing` | `PublicPricingPage.jsx` — shared `data/marketingPricing.js` |
| `/docs` | `DocsHubPage.jsx` — links to Swagger + Help |
| `/session-expired` | `SessionExpiredPage.jsx` |
| `/billing/success`, `/billing/cancel` | `BillingSuccessPage.jsx`, `BillingCancelPage.jsx` |
| `/access-denied` | `AccessDeniedPage.jsx` |
| `/500` | `ServerErrorPage.jsx` |
| `/503` | `ServiceUnavailablePage.jsx` |
| `*` | `NotFoundPage.jsx` — animated 404 with particles |

**Global shell:** `App.jsx` mounts `CookieConsent` + `MaintenanceGate` (redirects to `/503` when `maintenance_mode`).

### Pages — Dashboard (`/dashboard/*`, protected by `<ProtectedRoute>`)

| Route | Page File | Notes |
|-------|----------|----|
| `/dashboard` | `DashboardPage.jsx` | Bento grid, Mission Control layout, greeting |
| `/dashboard/costs` | `CostAnalysisEnhancedPage.jsx` | Cost hub sub-nav (simulator, optimization, billing) |
| `/dashboard/simulator` | `CostSimulatorPage.jsx` | |
| `/dashboard/optimization` | `CostOptimizationPage.jsx` | |
| `/dashboard/billing` | `BillingPage.jsx` | |
| `/dashboard/pricing` | `PricingPage.jsx` | |
| `/dashboard/storage` | `StoragePage.jsx` | Uses `AuthContext` — tanjiro mock removed ✅ |
| `/dashboard/vmcluster` | `VMClusterPage.jsx` | |
| `/dashboard/security` | `SecurityPage.jsx` | 2FA vault + `syncAwsSecureBucket()` via `api.js` named exports |
| `/dashboard/security-settings` | `SecuritySettingsPage.jsx` | |
| `/dashboard/profile` | `ProfilePage.jsx` | |
| `/dashboard/settings` | `SettingsPage.jsx` | Infrastructure provisioning engine (Boto3/Terraform); Preferences + Restart Tour |
| `/dashboard/notifications` | `NotificationsPage.jsx` | Paginated history; All/Unread tabs; type filters |
| `/dashboard/team` | `TeamPage.jsx` | Org create, invites, members |
| `/dashboard/support` | `SupportPage.jsx` | Logged-in ticket list + chat thread (10s poll + WS) |
| `/invite/:token` | `AcceptInvitePage.jsx` | Accept team invite |
| `/auth/sso/callback` | `SsoCallbackPage.jsx` | OAuth redirect handler |

### Pages — Admin (`/admin/*`, role-guarded)

| Route | Page File |
|-------|----------|
| `/admin` | `AdminOverviewPage.jsx` |
| `/admin/provision-roles` | `AdminProvisionRolesPage.jsx` |
| `/admin/users` | `AdminUsersPage.jsx` |
| `/admin/analytics` | `AdminAnalyticsPage.jsx` |
| `/admin/payments` | `AdminPaymentsPage.jsx` |
| `/admin/system` | `AdminSystemPage.jsx` |
| `/admin/settings` | `AdminSettingsPage.jsx` |
| `/admin/test` | `AdminTestPage.jsx` |
| `/admin/support` | `AdminSupportPage.jsx` | Support inbox — reply, status |

---

## 🧩 Key Components

| File | Purpose |
|------|---------|
| `dashboard/DashboardLayout.jsx` | Root dashboard layout — Sidebar + Header + `<Outlet>` + OnboardingTour |
| `dashboard/Sidebar.jsx` | 56px icon rail, hover-expands to 220px, mobile bottom tab bar |
| `dashboard/Header.jsx` | Top bar — search trigger (⌘K), notifications bell, profile dropdown |
| `dashboard/StatCard.jsx` | Bento-grid card — sizes: `lg` (2×2), `md` (1×1), `sm` |
| `dashboard/SparklineChart.jsx` | Recharts AreaChart wrapper — gold gradient |
| `dashboard/ProgressRing.jsx` | SVG ring — `percentage`, `color`, `size` props |
| `OnboardingTour.jsx` | 7-step guided tour (react-joyride v3) — shows once per user |
| `admin/AdminLayout.jsx` | Admin panel layout — AdminHeader + AdminSidebar + `<Outlet>` |
| `support/SupportThreadPanel.jsx` | Shared chat-style ticket thread (bubbles, composer, optimistic send) |
| `support/SupportWsBridge.jsx` | Single WS per layout; dispatches support events to event bus |
| `ProtectedRoute.jsx` | Auth guard — redirects to `/login` if not authenticated |
| `ErrorBoundary.jsx` | React error boundary |
| `GlobalSearch.jsx` | Cmd+K search modal |
| `KeyboardShortcuts.jsx` | `?` keyboard shortcuts modal |
| `QuickActions.jsx` | Floating quick action buttons |
| `Breadcrumbs.jsx` | Route-aware breadcrumbs |
| `LoadingSpinner.jsx`, `Skeletons.jsx`, `LazyLoadFallback.jsx` | Loading states |
| `NotificationBell.jsx` | Header bell — recent 8, Today/Earlier groups, glass dropdown |
| `EmptyState.jsx` | Reusable empty state with icon + message |
| `ui/PageHeader.jsx` | Kicker + title + subtitle; optional `actions` + `onRefresh` |
| `ui/PageRefreshButton.jsx` | Console-style page refresh control (used via PageHeader) |
| `CloudDestinationPanel.jsx` | Multi-CSP storage destination stack (AWS + GCP + Azure) |
| `BucketRegionSelector.jsx` | AWS S3 bucket + region picker |
| `GcpBucketSelector.jsx` | GCS bucket picker (platform catalog or BYOC) |
| `AzureContainerSelector.jsx` | Azure Blob container picker |
| `BucketSelectorLoading.jsx` | Gold indeterminate bar while bucket lists load/reload |
| `PlatformRegionPills.jsx` | Platform region slug pills (`asia`, `us`, …) |
| `StorageRegionScopeBar.jsx` | Region context bar between upload and file list |
| `IndeterminateProgressBar.jsx` | Sliding gold progress bar (toasts, bucket selectors) |

### Hooks (storage & refresh)

| File | Purpose |
|------|---------|
| `usePageRefresh.js` | `runPageRefresh()` — loading toast + success/error for page-level refresh |
| `useAwsBuckets.js` | AWS bucket discovery; `reloadToken` triggers reload with gold bar |
| `useGcpBuckets.js` | GCS bucket discovery (static catalog in platform mode) |
| `useAzureContainers.js` | Azure container discovery (static catalog in platform mode) |
| `usePlatformStorageRegions.js` | Platform multi-region metadata from AWS catalog endpoint |

**Page refresh pattern:** Every dashboard and admin page uses `PageHeader` `onRefresh` + `usePageRefresh`. Refresh reloads **that page only** — not a global app reload. Storage/Security also bump `catalogReloadToken` to reload all CSP destination panels.

---

## 🎨 Styling System

- All CSS lives in `frontend/src/styles/` — **one file per page/component**
- Design tokens in `frontend/src/index.css` — never hardcode colors or spacing
- Full token reference → `DESIGN_SYSTEM.md`

### Key tokens to always use:
```css
--bg-base           /* deep space black background */
--bg-card           /* frosted glass card background */
--gold-primary      /* #d4af37 — main accent */
--text-primary      /* near-white text */
--text-secondary    /* grey text */
--border-default    /* rgba(255,255,255,0.08) */
--radius-lg         /* 14px */
--shadow-gold       /* gold glow on hover */
```

### CSS file upgrade status:
✅ Upgraded: `index.css`, `dashboard.css`, `dashboard-enhanced.css`, `sidebar.css`, `auth.css`, `login.css`, `home.css`, `storage.css`, `profile.css`, `vmcluster.css`, `global-search.css`, `onboarding.css`
⚠️ Needs audit: `settings.css` (partial), `billing.css`, `costanalysis.css` (partial), `security-settings.css`

---

## 🛠 Frontend Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | React 19.1.1 |
| Build | Vite 7 |
| Routing | React Router DOM v6 (`createBrowserRouter`) |
| HTTP | Axios via `frontend/src/api.js` (interceptors + auth header) |
| HTTP exception | `SecurityPage.jsx` only — uses raw `fetch()`, intentional |
| Notifications | React Toastify + custom WS via `NotificationContext` |
| Charts | Recharts (sparklines, area charts) |
| Icons | React Icons (`react-icons/fa`) + custom SVG `Icons.jsx` |
| State | React Context only (4 contexts) — no Redux/Zustand |
| Language | JavaScript (JSX) — **NOT TypeScript** |
| Onboarding | react-joyride v3 (`{ Joyride }` named export) |

---

## 🔗 Routing Setup

All routes defined in `frontend/src/main.jsx` via `createBrowserRouter`:

```
Public routes → no wrapper
  /login, /register, /forgot-password, /reset-password
  /, /contact, /about, /features, /help, /support
  /legal/terms, /legal/privacy
  /access-denied, /500, /503, *

Dashboard routes → <ProtectedRoute> → <DashboardLayout>
  /dashboard → DashboardPage
  /dashboard/costs, /simulator, /optimization, /billing, /pricing
  /dashboard/storage, /vmcluster, /security, /security-settings
  /dashboard/profile, /settings

Admin routes → <ProtectedRoute> → <AdminLayout> (role-guarded)
  /admin, /admin/users, /analytics, /payments, /system, /settings, /test
```

---

## 🔑 Key Frontend Patterns

### Page → api.js → AuthContext (standard pattern)
```jsx
import { useAuth } from '../context/AuthContext.jsx';
import { apiClient } from '../api.js';

function MyPage() {
  const { token, user } = useAuth();
  const response = await apiClient.get('/some/endpoint');
}
```
`api.js` automatically adds `Authorization: Bearer <token>` header via interceptor.

### SecurityPage Pattern
`SecurityPage.jsx` imports named helpers from `api.js` (including `syncAwsSecureBucket`) and uses inline `<style>` for page layout.
Do not refactor to a shared CSS file unless the user explicitly requests it.

### New Page Checklist
1. Create `frontend/src/pages/MyNewPage.jsx`
2. Create `frontend/src/styles/mynewpage.css`
3. Import CSS in the page file
4. Add route to `frontend/src/main.jsx`
5. Use `AuthContext` + `api.js` for all HTTP calls
6. Use Zenith design tokens from `index.css` — never hardcode colors
7. Add `data-tour` attributes if the page should be included in onboarding

---

## ⚠️ Known Frontend Issues

| Issue | Location | Status |
|-------|----------|--------|
| `SecurityPage.jsx` inline `<style>` block | `pages/SecurityPage.jsx` | Intentional page-scoped CSS — do NOT extract without request |
| `settings.css` partially upgraded | `styles/settings.css` | Rest needs audit |
| `billing.css` not audited | `styles/billing.css` | May have old hardcoded colors |
| `costanalysis.css` partially upgraded | `styles/costanalysis.css` | Deeper table/report styling needs work |
| Lint warnings (28) | Various | All pre-existing, not caused by recent changes |
