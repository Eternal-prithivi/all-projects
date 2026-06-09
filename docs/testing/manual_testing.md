# Zenith — manual testing checklist

**GCP · Azure · AWS** · Platform keys in `backend/.env`

**How to use:** Change `[ ]` → `[x]` in the **Done** column (or cloud columns) when each test passes. In Cursor preview, click the checkbox to strike through the line.

**Cost gate:** **ASK** rows need approval before running (VM, Provision Apply, live billing).

**Last updated:** 2026-06-09

---

## Cost tiers

| Tier | Meaning |
|------|---------|
| **$0** | No meaningful cloud bill (tiny files, demo cost UI) |
| **ASK** | Can charge money — get approval first |

---

## Phase 0 — Before you start ($0)

| Done | # | What to check | Where | Pass when |
|------|---|---------------|-------|-----------|
| - [x] | 0.1 | Backend running | `:8000` / `/docs` | API docs page opens |
| - [ ] | 0.2 | Frontend running | `:5173` | App home loads |
| - [ ] | 0.3 | Env keys in place | `backend/.env` | GCP + Azure (+ AWS); backend restarted |
| - [ ] | 0.4 | Demo mode on | `backend/.env` | `DEMO_MODE=true`, `USE_REAL_METRICS=false` |
| - [ ] | 0.5 | Logged in | `/login` | Dashboard opens |
| - [ ] | 0.6 | Platform status | `/status` | GCP/Azure storage show configured |
| - [ ] | 0.7 | Budget alerts | GCP + Azure portals | Alerts set (e.g. $5–10/mo) |

---

## Phase 1 — Public & account ($0)

| Done | # | Feature | Route | Pass when |
|------|---|---------|-------|-----------|
| - [ ] | 1.1 | Landing page | `/` | Page loads |
| - [ ] | 1.2 | Login | `/login` | Dashboard after sign-in |
| - [ ] | 1.3 | Logout | dashboard | Returns to logged-out state |
| - [ ] | 1.4 | About / Features / Help | `/about`, `/features`, `/help` | All load |
| - [ ] | 1.5 | Legal / Trust | `/legal/*`, `/trust` | All load |
| - [ ] | 1.6 | Public pricing | `/pricing` | Prices show |
| - [ ] | 1.7 | Status page | `/status` | Platform status shows |
| - [ ] | 1.8 | Contact form | `/contact` | Submit OK or clear error |
| - [ ] | 1.9 | 404 page | bad URL | Friendly not-found |

---

## Phase 2 — Profile & settings ($0)

| Done | # | Feature | Route | Pass when |
|------|---|---------|-------|-----------|
| - [ ] | 2.1 | Profile edit & save | `/dashboard/profile` | Changes persist |
| - [ ] | 2.2 | Theme (dark/light/auto) | `/dashboard/settings` | Theme applies |
| - [ ] | 2.3 | Preferences (currency, TZ) | `/dashboard/settings` | Saves without error |
| - [ ] | 2.4 | Security settings | `/dashboard/security-settings` | Page loads |
| - [ ] | 2.5 | Enable 2FA (TOTP) | security-settings | QR + code verify |
| - [ ] | 2.6 | Notifications | `/dashboard/notifications` | List loads |

---

## Phase 3 — Storage ($0)

| Done | # | Step | Route | GCP | Azure | AWS | Pass when |
|------|---|------|-------|-----|-------|-----|-----------|
| - [ ] | 3.1 | Select cloud in toolbar | `/dashboard/storage` | - [ ] | - [ ] | - [ ] | Correct provider selected |
| - [ ] | 3.2 | Upload small `.txt` (&lt; 1 MB) | `/dashboard/storage` | - [ ] | - [ ] | - [ ] | Success toast |
| - [ ] | 3.3 | File in list | `/dashboard/storage` | - [ ] | - [ ] | - [ ] | File visible |
| - [ ] | 3.4 | ML analyze / recommendation | `/dashboard/storage` | - [ ] | - [ ] | - [ ] | Recommendation shown |
| - [ ] | 3.5 | Download | `/dashboard/storage` | - [ ] | - [ ] | - [ ] | Content matches |
| - [ ] | 3.6 | Delete | `/dashboard/storage` | - [ ] | - [ ] | - [ ] | Gone from list |
| - [ ] | 3.7 | Sync bucket/container | `/dashboard/storage` | - [ ] | - [ ] | - [ ] | List matches cloud |
| - [ ] | 3.8 | Platform region pills (if catalog) | `/dashboard/storage` | - [ ] | - [ ] | - [ ] | One bucket/container per CSP per pill |
| - [ ] | 3.9 | Page header Refresh | `/dashboard/storage` | - [ ] | - [ ] | - [ ] | Gold bar on all three CSP panels; files + destinations reload |
| - [ ] | 3.10 | Sync after manual cloud delete | `/dashboard/storage` | - [ ] | - [ ] | - [ ] | Stale file removed from Zenith list |

---

## Phase 4 — Secure vault ($0) — 2FA required

| Done | # | Step | Route | GCP | Azure | AWS | Pass when |
|------|---|------|-------|-----|-------|-----|-----------|
| - [ ] | 4.1 | Open vault + pass 2FA | `/dashboard/security` | - [ ] | - [ ] | - [ ] | Vault UI loads |
| - [ ] | 4.2 | Upload small file | `/dashboard/security` | - [ ] | - [ ] | - [ ] | File listed |
| - [ ] | 4.3 | Sensitive file → encryption wizard | `/dashboard/security` | - [ ] | - [ ] | - [ ] | Wizard appears |
| - [ ] | 4.4 | Server-side encrypt + upload | `/dashboard/security` | - [ ] | - [ ] | - [ ] | Secure file listed |
| - [ ] | 4.5 | Vault sync | `/dashboard/security` | - [ ] | - [ ] | - [ ] | Sync succeeds |
| - [ ] | 4.6 | Download secure file | `/dashboard/security` | - [ ] | - [ ] | - [ ] | File downloads |
| - [ ] | 4.7 | Delete secure file | `/dashboard/security` | - [ ] | - [ ] | - [ ] | Removed |
| - [ ] | 4.8 | Browser CSE upload | `/dashboard/security` | n/a | n/a | - [ ] | AWS only; others 501 OK |

---

## Phase 5 — Cost & billing ($0 demo)

| Done | # | Feature | Route | GCP | Azure | AWS | Pass when |
|------|---|---------|-------|-----|-------|-----|-----------|
| - [ ] | 5.1 | Cost hub | `/dashboard/costs` | ○ | ○ | ○ | Charts load (demo) |
| - [ ] | 5.2 | Cost simulator | `/dashboard/simulator` | ○ | ○ | ○ | Inputs update numbers |
| - [ ] | 5.3 | Optimization | `/dashboard/optimization` | ○ | ○ | ○ | Page loads |
| - [ ] | 5.4 | Billing | `/dashboard/billing` | ○ | ○ | ○ | Page loads |
| - [ ] | 5.5 | Dashboard pricing | `/dashboard/pricing` | ○ | ○ | ○ | Page loads |
| - [ ] | 5.6 | Export CSV | `/dashboard/costs` | ○ | ○ | ○ | File downloads |

---

## Phase 6 — Dashboard & misc ($0)

| Done | # | Feature | Route | Pass when |
|------|---|---------|-------|-----------|
| - [ ] | 6.0 | Page header Refresh (any page) | dashboard pages | Header Refresh reloads that page only; loading toast |
| - [ ] | 6.1 | Main dashboard | `/dashboard` | Widgets load |
| - [ ] | 6.2 | Docs hub | `/docs` | Links work |
| - [ ] | 6.3 | Razorpay test checkout | `/dashboard/billing` | Lands on success/cancel page |

---

## Phase 7 — VM Cluster (**ASK** — approve before each cloud)

| Done | # | Step | Route | Cloud | Est. cost | Pass when |
|------|---|------|-------|-------|-----------|-----------|
| - [ ] | 7.0 | **Approval received** | — | GCP | ASK | You said yes before testing |
| - [ ] | 7.1 | Workload analyze | `/dashboard/vmcluster` | GCP | $0–2 | Suggestion shown |
| - [ ] | 7.2 | Request VM (General only) | `/dashboard/vmcluster` | GCP | $0–2 | VM assigned/created |
| - [ ] | 7.3 | Verify in GCP console | console | GCP | — | Real VM, IP not `N/A` |
| - [ ] | 7.4 | Stop + cleanup | app + console | GCP | — | No running VMs |
| - [ ] | 7.5 | **Approval received** | — | Azure | ASK | You said yes |
| - [ ] | 7.6 | VM General — request, stop, cleanup | `/dashboard/vmcluster` | Azure | $0–2 | No running VMs |
| - [ ] | 7.7 | **Approval received** | — | AWS | ASK | You said yes |
| - [ ] | 7.8 | VM General — request, stop, cleanup | `/dashboard/vmcluster` | AWS | $0–2 | No running VMs |

---

## Phase 8 — Provision (**ASK** before Apply)

| Done | # | Test | Route | Cloud | Est. cost | Pass when |
|------|---|------|-------|-------|-----------|-----------|
| - [ ] | 8.1 | Manage / Activity / Policies tabs | `/dashboard/provision` | All | $0 | Tabs load |
| - [ ] | 8.2 | static-site — plan only | `/dashboard/provision` | GCP | $0 | Plan succeeds |
| - [ ] | 8.3 | static-site — apply + destroy | `/dashboard/provision` | GCP | Low | Resources gone |
| - [ ] | 8.4 | static-site — plan only | `/dashboard/provision` | Azure | $0 | Plan succeeds |
| - [ ] | 8.5 | static-site — apply + destroy | `/dashboard/provision` | Azure | Low | Resources gone |
| - [ ] | 8.6 | static-site — plan only | `/dashboard/provision` | AWS | $0 | Plan succeeds |
| - [ ] | 8.7 | static-site — apply + destroy | `/dashboard/provision` | AWS | Low | Resources gone |
| - [ ] | 8.8 | backend-app — apply + destroy | `/dashboard/provision` | One | Medium | Destroyed same day |

---

## Phase 9 — Cleanup (after paid tests)

| Done | # | Action | Where | Pass when |
|------|---|--------|-------|-----------|
| - [ ] | 9.1 | Destroy provision deployments | `/dashboard/provision` | No active stacks |
| - [ ] | 9.2 | Stop/delete test VMs | VM Cluster + consoles | No RUNNING VMs |
| - [ ] | 9.3 | Delete test files | Storage + Security | Buckets tidy |
| - [ ] | 9.4 | GCP console check | `us-central1` | No stray VMs |
| - [ ] | 9.5 | Azure portal check | `zenith-rg` | No running VMs |

---

## Session log (copy per day)

| Field | Value |
|-------|-------|
| Date | |
| Feature | |
| Cloud | GCP / Azure / AWS / All |
| Cost tier | $0 / ASK |
| Approved paid test | Yes / No |
| Result | Pass / Fail |
| Notes | |
