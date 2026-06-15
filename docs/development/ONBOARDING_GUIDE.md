# Zenith User Onboarding Guide

> **Audience:** Product developers and operators who need to understand, modify, or extend
> the first-time user experience.

---

## Overview

Zenith's onboarding is multi-layered. Each layer activates at the right moment so new users
discover value progressively rather than being overwhelmed on day one.

```
Login → Dashboard → Welcome modal → Tour → Getting Started checklist → Contextual banners
```

---

## Layer 1 — Welcome modal + guided tour (dashboard, desktop)

**File:** `frontend/src/components/OnboardingTour.jsx`  
**Mounted in:** `DashboardLayout.jsx` (persists across all dashboard navigation)

### What it does

1. 1.5 s after the user's first visit to `/dashboard`, a welcome modal appears:
   - Desktop: glassmorphism overlay with "Start Tour" / "I'll explore on my own"
   - Mobile: 3-card tips sheet (bottom nav · upload · help)
2. If the user starts the tour, a 7-step `react-joyride` walkthrough highlights:
   - Sidebar navigation
   - Global search (`⌘K`)
   - Cost overview card
   - Storage card
   - VM health card
   - Quick actions
   - Help center
3. Tour state is persisted in **localStorage keyed per username**:
   - `zenith_onboarding_complete_{username}` — tour completed or finished
   - `zenith_onboarding_dismissed_{username}` — user clicked Skip / X

### Per-user keys

Keys are suffixed with `_{username}` so each account on a shared device gets its own
tour state. Legacy keys without a suffix are also cleared when the user restarts the tour.

### Restart tour

`SettingsPage.jsx` → Preferences section → **Restart Tour** button:
- Clears both localStorage keys (user-specific + legacy)
- Shows a success toast
- Navigates the user back to `/dashboard` (tour triggers automatically)

### Adding / changing tour steps

Edit the `steps` array in `OnboardingTour.jsx`. Each step needs a `target` (CSS selector
or `data-tour` attribute) and JSX `content`. Always set `disableBeacon: true` to avoid
the manual click-to-start requirement.

### Mobile tips

Joyride is disabled on narrow viewports. Instead, `mobileTips` (3 cards) replace the
full tour. They are advanced with Next / completed with "Got it".

---

## Layer 2 — Getting Started checklist (dashboard, all devices)

**Component:** `GettingStartedCard` inside `DashboardPage.jsx`

### What it shows

A card with a progress bar and 4 actionable steps, displayed above the bento grid on the
dashboard. Each step links to the relevant page:

| Step | Completion signal | Target path |
|------|------------------|-------------|
| Connect your cloud | `byocConnected.length > 0` | `/dashboard/settings#byoc` |
| Analyze your costs | `localStorage[zenith_visited_costs_{username}]` | `/dashboard/costs` |
| Upload a file | `stats.total_files > 0` | `/dashboard/storage` |
| Request a VM | `stats.active_vms > 0` | `/dashboard/vmcluster` |

Steps that are complete show a green checkmark and are crossed out.

### Dismissal

A `✕` dismiss button stores `zenith_gs_dismissed_{username}` in localStorage so the card
is never shown again for that account.

### Extending the checklist

Add entries to the `GS_STEPS` array in `DashboardPage.jsx`. Each step needs:
- `id` — unique string used as the completion key
- `label` / `description` / `icon` — display content
- `path` — where to navigate when the user clicks the step

To add a backend-driven completion signal, derive it from `stats` (returned by
`GET /api/dashboard/stats`) or a new dedicated field.

---

## Layer 3 — Team member onboarding card (`TeamPage.jsx`)

Shows a 3-step checklist (connect cloud → refresh costs → cost analysis) to users who:
- have `role === 'member'` in their organisation, AND
- joined ≤ 14 days ago

Dismissed per-user via localStorage key `zenith_team_onboarding_dismissed_{username}`.

**Gap:** Organisation owners / admins do not get an equivalent card. Consider adding one
with admin-specific steps (invite team members, configure billing export, review security).

---

## Layer 4 — Cloud readiness banners (contextual)

These appear throughout the app when a feature requires configuration the user has not
completed yet.

| Component | Trigger | Target |
|-----------|---------|--------|
| `CloudAvailabilityBanner` | No cloud provider configured at all | Settings |
| `CloudCapabilityBanner` | Connected CSP lacks a specific feature (e.g. GCP billing export) | Settings anchor |
| `ByocStorageTargetBanner` | Explains where files land (BYOC vs platform) | Informational |
| `FeatureLockedState` | Full-page lock when a cost feature cannot work without setup | Settings |

These are automatic — they read from `CloudAvailabilityContext` and render without any
user action.

---

## Layer 5 — Empty states

Every list page renders a contextual `EmptyState` component when data is absent:

| Page | Empty state message |
|------|---------------------|
| Storage | "No files yet — upload your first file to get ML tier recommendations" |
| VM Cluster | "No VMs assigned — describe your workload to request one" |
| Security | "Vault is empty — upload your first secure file" |
| Billing | "No invoices yet — costs appear after your first billing period" |
| Notifications | "All caught up — nothing to show" |

`EmptyState` accepts an optional `actionLabel` + `onAction` to render a CTA button.

---

## Layer 6 — BYOC setup guides

`ByocSetupGuidePanel.jsx` provides collapsible step-by-step guides for:
- GCP billing export configuration
- Azure Service Principal setup

It is embedded in `SettingsPage.jsx` within each BYOC section and also available at the
dedicated `/dashboard/help/byoc-setup` route.

---

## Layer 7 — Help Center

`HelpCenterPage.jsx` at `/help` hosts a searchable FAQ across 6 categories:
- Getting Started, Billing & Plans, Virtual Machines, Storage & Files, Security, Account

Updated from `frontend/src/data/productFacts.js` (`buildHelpFaqs()`).

---

## Onboarding state reference

| localStorage key | Written by | Cleared by |
|-----------------|-----------|-----------|
| `zenith_onboarding_complete_{u}` | `OnboardingTour` (tour finished/skipped) | Restart Tour button |
| `zenith_onboarding_dismissed_{u}` | `OnboardingTour` (user dismissed) | Restart Tour button |
| `zenith_gs_dismissed_{u}` | `GettingStartedCard` dismiss button | — (permanent) |
| `zenith_team_onboarding_dismissed_{u}` | `TeamPage` card dismiss | — (permanent) |
| `zenith_visited_costs_{u}` | `CostAnalysisPage` on mount | — |

---

## Testing onboarding

1. Open the browser DevTools → Application → Local Storage → clear `zenith_onboarding_*` keys
   for your username.
2. Navigate to `/dashboard` — the welcome modal should appear after ~1.5 s.
3. Click **Start Tour** and step through all 7 steps.
4. Go to Settings → Preferences → **Restart Tour** — toast appears and you are redirected
   to `/dashboard` where the tour starts again.
5. To test the Getting Started card: clear `zenith_gs_dismissed_{username}` and reload.
6. To test Team onboarding: ensure your account is a member of an org joined within 14 days,
   then clear `zenith_team_onboarding_dismissed_{username}`.

---

## Operators: disabling the tour in automated tests

The Playwright E2E suite does not trigger the tour because:
- The auth flow seeds `cachedUser` directly in sessionStorage (bypasses the welcome modal timer)
- `localStorage` is empty in fresh browser contexts — tour would show but tests do not visit
  `/dashboard` in a context where tour targets exist

If future E2E tests visit `/dashboard` and need to suppress the tour, set both keys in
`localStorage` before navigating:

```ts
await page.evaluate((u) => {
  localStorage.setItem(`zenith_onboarding_complete_${u}`, 'true');
  localStorage.setItem(`zenith_onboarding_dismissed_${u}`, 'true');
  localStorage.setItem(`zenith_gs_dismissed_${u}`, '1');
}, username);
```
