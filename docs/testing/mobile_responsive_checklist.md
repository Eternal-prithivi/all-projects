# Mobile responsive verification checklist

Use this matrix before marking **Mobile responsiveness** complete in the production deployment guide.

## Devices and viewports

| Target | Width | Browser |
|--------|-------|---------|
| Small phone | 320px | iOS Safari or Chrome device mode |
| Standard phone | 390px | Android Chrome or iOS Safari |
| Tablet | 768px | Safari / Chrome |

## Marketing / public

- [ ] Hamburger opens drawer; can reach Features, About, Contact, Help (or landing anchors)
- [ ] Login and Sign Up reachable from drawer
- [ ] No horizontal page scroll on home, features, contact, help
- [ ] Cookie banner does not cover primary CTAs on marketing pages

## Dashboard (logged in)

- [ ] Bottom tabs: Overview, Storage, Infrastructure, Costs visible without horizontal cram
- [ ] **More** sheet lists VM Cluster, Security, Team, Billing, Help, Settings, Admin (if admin)
- [ ] Header: search is icon-only; profile name hidden; no toolbar overflow at 320px
- [ ] Quick Actions FAB sits above bottom tab bar (no overlap)
- [ ] Cookie banner (if shown) sits above tab bar on dashboard routes
- [ ] Billing payment history readable as stacked cards (not only horizontal scroll)

## Admin

- [ ] Bottom tabs: Overview, Users, Payments + **More** for Analytics, System, Dashboard, Settings, Help
- [ ] Content padding clears fixed bottom nav

## Key flows

- [ ] Provision wizard shows step labels (abbreviated on narrow screens)
- [ ] Cost analysis filters stack vertically
- [ ] Storage action buttons stack on narrow screens
- [ ] Onboarding tour does not auto-start on viewports ≤768px

## Known gaps addressed (2026-06)

| Area | Issue | Fix location |
|------|--------|--------------|
| Admin tablet | `margin-left: 240px` broke flex layout at 1024px | Removed from `admin-layout.css` |
| Storage files | Wide table clipped on phone | `table-responsive-scroll` + `file-list.css` |
| BYOC wizard | Step pills overflow | `byoc-shared.css` |
| Cost hub | Sub-nav wraps awkwardly | `mobile-consistency.css` scroll row |
| Breadcrumbs | Long paths overflow header | Ellipsis in `mobile-consistency.css` |
| Toasts | Overlap notch / header | Safe-area in `toast-custom.css` + `mobile-consistency.css` |
| Features page | 720px breakpoint mismatch | Aligned to 768px in `features.css` |
| Marketing pages | Hero padding inconsistent | `marketing-shell.css` + `mobile-consistency.css` |
| Admin payments table | No scroll wrapper | `AdminPaymentsPage.jsx` + `table-container` |
| Security / Cost tables | Wide tables on phone | `table-responsive-scroll` wrappers |
| Notifications page | No mobile CSS | `notifications-page.css` |
| Docs / Status pages | Fixed padding, no mobile | `mobile-consistency.css` |
| Modals (storage, VM, security) | Could exceed viewport | `mobile-consistency.css` |

## Automated smoke (optional)

```bash
cd frontend && npx playwright test e2e/specs/mobile-shell.spec.ts
```
