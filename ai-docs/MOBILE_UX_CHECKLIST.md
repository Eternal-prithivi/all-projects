# Mobile UX checklist (plain English)

> **Goal:** Zenith should feel like a professional SaaS app on phones and tablets — not a desktop site squeezed onto a small screen.
>
> **Breakpoint:** Primary mobile layout at **≤768px**; small phones at **≤480px**.
>
> **Last updated:** 2026-07-11

---

## How mobile works in Zenith

| Layer | What happens on mobile |
|-------|------------------------|
| **Marketing site** | Hamburger menu (`MobileMarketingNav`), landing-mobile.css |
| **Auth (login/register)** | Stacked layout, 16px inputs (no iOS zoom), full-width buttons (`auth-mobile.css`) |
| **Dashboard** | Left sidebar hidden → **bottom tab bar** (`MobileBottomNav`) + More sheet |
| **Admin** | Same bottom nav pattern (`AdminMobileBottomNav`) |
| **Tables** | `data-card-table` + `data-label` → each row becomes a card |
| **Scroll** | Page scrolls naturally on mobile (no trapped inner panes) — `mobile-consistency.css` |

---

## Feature-by-feature status

### Public / marketing

| Feature | Route | Mobile status | Notes |
|---------|-------|---------------|-------|
| Landing | `/` | ✅ | Hamburger, hero stacks, `landing-mobile.css` |
| Features, About, Contact | `/features`, `/about`, `/contact` | ✅ | Marketing shell + drawer nav |
| Pricing | `/pricing` | ✅ | Responsive pricing cards |
| Download | `/download` | ✅ | Platform tabs; E2E covered |
| Help center | `/help` | ✅ | Hub tabs scroll; FAQ accordion |
| Legal / Trust / Status | `/legal/*`, `/trust`, `/status` | ✅ | `mobile-consistency` padding |
| Docs hub | `/docs` | ✅ | Single-column grid |

### Authentication

| Feature | Route | Mobile status | Notes |
|---------|-------|---------------|-------|
| Login | `/login` | ✅ | Full-width form, touch targets; E2E covered |
| Register | `/register` | ✅ | Password requirements panel; E2E covered |
| Forgot password | `/forgot-password` | ✅ | Email/SMS toggle stacks |
| Reset password | `/reset-password` | ✅ | Uses `auth-page` layout |
| Verify email | `/verify-email` | ✅ | Centered card |
| Google SSO | login/register | ✅ | Optional; full-width button when enabled |

### Dashboard core

| Feature | Route | Mobile status | Notes |
|---------|-------|---------------|-------|
| Overview | `/dashboard` | ✅ | Bento grid → single column |
| Bottom navigation | all dashboard | ✅ | Overview, Storage, VMs, Security, More |
| Header | all dashboard | ✅ | Compact; search icon; bell; profile |
| Global search | ⌘K / header | ✅ | Full-width modal on mobile |
| Notifications bell | header | ✅ | Dropdown fits viewport |
| Profile menu | header | ✅ | Max-width capped |
| Breadcrumbs | all dashboard | ✅ | Horizontal scroll + ellipsis |
| Onboarding tour | first visit | ✅ | Mobile tips sheet (Phase 27) |
| Quick actions FAB | floating | ✅ | Positioned above bottom nav |

### Storage & files

| Feature | Route | Mobile status | Notes |
|---------|-------|---------------|-------|
| Storage upload | `/dashboard/storage` | ✅ | Region pills, CSP panels stack |
| File list table | Storage | ✅ | **2026-07-11:** `data-card-table` + labels |
| Sync / restore / delete | Storage | ✅ | Touch-sized action buttons |
| Upload wizard | modal | ✅ | Bottom-sheet style modal |

### Security vault

| Feature | Route | Mobile status | Notes |
|---------|-------|---------------|-------|
| Secure upload | `/dashboard/security` | ✅ | Wizard + 2FA modal |
| Secure file table | Security | ✅ | **2026-07-11:** `data-card-table` + labels |
| Encryption modals | Security | ✅ | Full-width on mobile |

### VMs

| Feature | Route | Mobile status | Notes |
|---------|-------|---------------|-------|
| VM cluster | `/dashboard/vmcluster` | ✅ | Header stacks; sticky actions |
| Health table | VM cluster | ✅ | **2026-07-11:** `data-card-table` on health card |
| Request / release VM | modals | ✅ | Full-width modals |

### Cost & billing

| Feature | Route | Mobile status | Notes |
|---------|-------|---------------|-------|
| Cost analysis | `/dashboard/costs` | ✅ | Cost hub scroll; `data-card-table` |
| Simulator / Optimization | sub-routes | ✅ | Forms stack |
| Billing | `/dashboard/billing` | ✅ | Layout stacks at 1024px; tabs at 640px |
| Razorpay checkout | external | ✅ | Razorpay hosted — mobile-native |

### Provision

| Feature | Route | Mobile status | Notes |
|---------|-------|---------------|-------|
| Provision hub | `/dashboard/provision` | ✅ | Wizard steps scroll horizontally |
| Deploy wizard | modal/flow | ✅ | Sticky actions above bottom nav |

### Settings & account

| Feature | Route | Mobile status | Notes |
|---------|-------|---------------|-------|
| Settings | `/dashboard/settings` | ✅ | Tabs scroll; BYOC forms stack |
| Security settings | `/dashboard/security-settings` | ✅ | Account hub nav scroll |
| Profile | `/dashboard/profile` | ✅ | Forms full width |
| BYOC setup help | dashboard help link | ✅ | Matrix table scrolls |

### Team & org

| Feature | Route | Mobile status | Notes |
|---------|-------|---------------|-------|
| Team page | `/dashboard/team` | ✅ | Member grid → card rows at 768px |
| Org billing / invites | Team | ✅ | Action rows wrap |

### Support

| Feature | Route | Mobile status | Notes |
|---------|-------|---------------|-------|
| Help + tickets | `/help?tab=tickets` | ✅ | `SupportTicketsSection` responsive |
| Contact | `/contact` | ✅ | Form stacks |

### Notifications

| Feature | Route | Mobile status | Notes |
|---------|-------|---------------|-------|
| Notification center | `/dashboard/notifications` | ✅ | Tabs scroll; items stack |
| Toasts | global | ✅ | Top offset for notch + header |

### Admin portal

| Feature | Route | Mobile status | Notes |
|---------|-------|---------------|-------|
| Admin overview | `/admin` | ✅ | Bottom nav + tables `data-card-table` |
| Users, Support, Payments | `/admin/*` | ✅ | Admin layout mobile padding |
| Analytics tables | `/admin/analytics` | ✅ | Horizontal scroll fallback |

---

## CSS files that govern mobile

| File | Role |
|------|------|
| `mobile-consistency.css` | Cross-app scroll, tables, modals, toasts |
| `mobile-nav.css` | Dashboard/admin bottom bar + More sheet |
| `mobile-marketing-nav.css` | Public site hamburger drawer |
| `auth-mobile.css` | Login/register/forgot/reset |
| `landing-mobile.css` | Homepage |
| `zenith-ui.css` | `data-card-table` card layout |
| `dashboard.css` | Content padding + bottom nav offset |
| `dashboard-enhanced.css` | Bento single column |

---

## Testing

```bash
cd frontend && npm run lint
cd frontend && npm run test:e2e -- e2e/specs/mobile-shell.spec.ts
```

Manual: Chrome DevTools → iPhone 14 Pro (390×844) or responsive mode at 768px.

---

## When adding a new page

1. Use `PageHeader` + existing layout wrappers.
2. Tables → add `data-card-table` class and `data-label` on every `<td>`.
3. Horizontal tab rows → `overflow-x: auto` + `min-height: var(--touch-min)`.
4. Modals → use `zenith-modal` or existing overlay classes (mobile rules apply automatically).
5. Add a line to this checklist.

---

*Companion: `UI_UX_AUDIT_2026.md` Phase 25–27 mobile items · E2E: `e2e/specs/mobile-shell.spec.ts`*
