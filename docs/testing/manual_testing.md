# Zenith — manual testing checklist

**GCP · Azure · AWS** · Platform keys in `backend/.env`

**How to use:** Change `[ ]` → `[x]` in the **Done** column (or cloud columns) when each test passes. In Cursor preview, click the checkbox to strike through the line.

**Cost gate:** **ASK** rows need approval before running (VM, Provision Apply, live billing).

**Last updated:** 2026-06-11

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
| - [ ] | 3.11 | ML analyze → tier + CSP + expert votes | `/dashboard/storage` | - [ ] | - [ ] | - [ ] | Recommendation modal shows ensemble breakdown (+ RL note when applied) |
| - [ ] | 3.12 | Multi-region lifecycle (backdate `last_accessed_at`) | `/dashboard/storage` | - [ ] | - [ ] | - [ ] | Nightly job or manual trigger moves file using **recorded** `cloud_bucket` + region (not default env bucket) |
| - [ ] | 3.13 | Archive restore → download | `/dashboard/storage` | - [ ] | - [ ] | - [ ] | Cold/archive file: Restore button → 202 → download succeeds after rehydration |
| - [ ] | 3.14 | Sensitive file skips auto-tier | DB + lifecycle job | - [ ] | - [ ] | - [ ] | `is_sensitive=true` file unchanged after demotion window |
| - [ ] | 3.15 | Lifecycle policy at upload | upload wizard step 4 | - [ ] | - [ ] | - [ ] | Review step shows policy cards; suggested badge matches priority/intent |
| - [ ] | 3.16 | Pending demotion notification | bell + Storage | - [ ] | - [ ] | - [ ] | After lifecycle job: warning with Keep hot / Snooze / Move now |
| - [ ] | 3.17 | Settings lifecycle defaults | `/dashboard/settings` | - [ ] | - [ ] | - [ ] | Default policy + notice days save and apply to new uploads |
| - [ ] | 3.18 | Storage health bar | `/dashboard/storage` | - [ ] | - [ ] | - [ ] | Grade A–D, lifetime savings, pending moves visible |
| - [ ] | 3.19 | Upload cost forecast | upload wizard step 4 | - [ ] | - [ ] | - [ ] | 12-month keep-hot vs policy + tri-cloud $/month table |
| - [ ] | 3.20 | Per-file Zenith insight | file table column | - [ ] | - [ ] | - [ ] | Click insight — policy, blockers, savings, inactive days |

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
| - [ ] | 4.9 | Vault health bar | `/dashboard/security` | - [ ] | - [ ] | - [ ] | Grade A–D + metrics load |
| - [ ] | 4.10 | Per-file insight panel | `/dashboard/security` | - [ ] | - [ ] | - [ ] | Expand row shows reasons/steps |
| - [ ] | 4.11 | Upload cost preview | Secure upload wizard | - [ ] | - [ ] | - [ ] | Tri-cloud $/month updates |
| - [ ] | 4.12 | Encryption pending notification | Notification bell | - [ ] | - [ ] | - [ ] | Encrypt now / Dismiss |
| - [ ] | 4.13 | Stale file notification | Notification bell | - [ ] | - [ ] | - [ ] | Archive / Snooze / Delete |
| - [ ] | 4.14 | Secure vault defaults | `/dashboard/settings` | - [ ] | - [ ] | - [ ] | Encryption/CSP/replication prefs save |
| - [ ] | 4.15 | Archive / restore vault | `/dashboard/security` | - [ ] | - [ ] | - [ ] | **Archive** moves file primary→replica; **Restore** copies back; filter **Archived** lists replica-only files |
| - [ ] | 4.16 | ML-assisted scan | Secure upload wizard | - [ ] | - [ ] | - [ ] | ML risk score on scan step |
| - [ ] | 4.17 | Skip encryption after scan | Secure upload wizard | - [ ] | - [ ] | - [ ] | Third option + ack checkbox; file listed as unencrypted |
| - [ ] | 4.18 | Vault destination disclosure | `/dashboard/security` | - [ ] | - [ ] | - [ ] | Platform: collapsed “Vault storage locations”; BYOC: per-CSP secure picker (AWS/GCP/Azure) + disclosure |
| - [ ] | 4.21 | BYOC connect 2-step wizard | `/dashboard/settings` | - [ ] | - [ ] | - [ ] | Verify credentials → storage + secure + replica names; auto-create; dual-write toggle |
| - [ ] | 4.22 | Trust docs accuracy | `docs/security/TRUST_AND_ENCRYPTION.md` | - [ ] | - [ ] | - [ ] | Matches live SSE/CSE/BYOC behavior |
| - [ ] | 4.19 | GCP/Azure dedicated secure buckets | `/dashboard/security` | - [ ] | - [ ] | - [ ] | Vault cards show `zenith-secure-gcp` / `zenith-secure` not storage buckets |
| - [ ] | 4.20 | Fixed replica (no region picker) | Secure upload wizard | - [ ] | - [ ] | - [ ] | Replication toggle only; no replica region dropdown |

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
| - [ ] | 6.4 | Overview platform status | `/dashboard` | Banner shows demo or operational (not always hardcoded green) |
| - [ ] | 6.5 | Cost trend refresh | `/dashboard` | Click Refresh on cost card → 7-day sparkline appears (demo OK) |
| - [ ] | 6.6 | Help pricing accuracy | `/help` | Plans show ₹0 / ₹499 / ₹1,499 / ₹4,999 INR (not USD) |
| - [ ] | 6.7 | Help topic deep link | `/help?topic=billing` | Billing FAQ category pre-selected |
| - [ ] | 6.8 | In-app support ticket | `/dashboard/support` | New ticket → thread opens with reference code |
| - [ ] | 6.9 | Team invite revoke | `/dashboard/team` | Pending invite → Revoke removes row |
| - [ ] | 6.10 | Billing help links | `/dashboard/billing` | Support ticket + billing FAQ links work |

---

## Phase 7 — VM Cluster (**ASK** — approve before each cloud)

**7×4 expansion checklist** (repeat per CSP × platform region: `asia`, `us`, `europe`, `africa`):

| Done | Check | Pass when |
|------|-------|-----------|
| - [ ] | Pool shows 7 clusters × 4 slots | `/api/vm/pool` or request modal slot picker |
| - [ ] | Topology ring + cluster tabs | 7 tabs; selected cluster shows 4 ring nodes |
| - [ ] | Click unprovisioned slot | Config modal shows catalog spec (`NOT_PROVISIONED`) |
| - [ ] | Request + release | VM terminates in cloud console on release |
| - [ ] | Database / Network NLP | Workload with PostgreSQL → database; gateway → network |

| Done | # | Step | Route | Cloud | Est. cost | Pass when |
|------|---|------|-------|-------|-----------|-----------|
| - [ ] | 7.0 | **Approval received** | — | GCP | ASK | You said yes before testing |
| - [ ] | 7.1 | Workload analyze | `/dashboard/vmcluster` | GCP | $0–2 | Suggestion shown (any of 7 clusters) |
| - [ ] | 7.2 | Request VM (any cluster) | `/dashboard/vmcluster` | GCP | $0–2 | VM assigned/created with tiered slot name |
| - [ ] | 7.3 | Verify in GCP console | console | GCP | — | Real VM, IP not `N/A` |
| - [ ] | 7.4 | Stop + cleanup | app + console | GCP | — | No running VMs |
| - [ ] | 7.5 | **Approval received** | — | Azure | ASK | You said yes |
| - [ ] | 7.6 | VM — request, release, cleanup | `/dashboard/vmcluster` | Azure | $0–2 | No running VMs after release |
| - [ ] | 7.7 | **Approval received** | — | AWS | ASK | You said yes |
| - [ ] | 7.8 | VM — request, release, cleanup | `/dashboard/vmcluster` | AWS | $0–2 | No running VMs after release |
| - [ ] | 7.9 | Region pills | `/dashboard/vmcluster` | All | $0 | Asia/US/Europe/Africa updates pool `compute_target` |
| - [ ] | 7.10 | Transfer modal | `/dashboard/vmcluster` | All | $0–2 | All 7 clusters + 4 slots listed |

---

## Phase 8 — Provision (**ASK** before Apply)

**Build wizard (5 steps):** Intent → Cloud compare → Configure → Review → Build. Success modal shows handoff links; destroy stays on **Manage** tab.

| Done | # | Test | Route | Cloud | Est. cost | Pass when |
|------|---|------|-------|-------|-----------|-----------|
| - [ ] | 8.1 | Manage / Activity / Policies tabs | `/dashboard/provision` | All | $0 | Tabs load; **Build** tab shows intent-first wizard |
| - [ ] | 8.1a | Intent step — NLP suggestion | Build tab step 0 | All | $0 | Typing a goal returns template + follow-ups |
| - [ ] | 8.1b | Tri-cloud compare cards | Build tab step 1 | All | $0 | AWS/GCP/Azure cost + fit cards; selecting one sets CSP |
| - [ ] | 8.1c | Configure — env tag + disk | Build tab step 2 | All | $0 | Environment selector + boot disk GB when VM enabled |
| - [ ] | 8.1d | Review — plain-English summary | Build tab step 3 | All | $0 | Bullets + policy gate + cost table before plan |
| - [ ] | 8.1e | Success handoff + Terraform export | Build tab step 4–5 | All | $0 | After apply: success modal with VM/Storage/Security/Cost links; Download Terraform when available |
| - [ ] | 8.1f | Intent auto-applies template flags | Build tab step 0→1 | All | $0 | After NLP suggestion, Step 1 Next enabled without re-clicking template |
| - [ ] | 8.1g | GCP backend-app — SDK plan (no Terraform) | Build tab | GCP | $0 | Settings engine Boto3; plan shows Cloud SDK fast path for GCE+VPC |
| - [ ] | 8.1h | Azure backend-app — SDK plan (no Terraform) | Build tab | Azure | $0 | Settings engine Boto3; plan shows Cloud SDK fast path for VM+VNet |
| - [ ] | 8.1i | Disk size affects deploy | Configure step | AWS/GCP/Azure | ASK | Boot disk GB from wizard reflected in created VM volume |
| - [ ] | 8.2 | static-site — plan only | `/dashboard/provision` | GCP | $0 | Plan succeeds |
| - [ ] | 8.3 | static-site — apply + destroy | `/dashboard/provision` | GCP | Low | Resources gone |
| - [ ] | 8.4 | static-site — plan only | `/dashboard/provision` | Azure | $0 | Plan succeeds |
| - [ ] | 8.5 | static-site — apply + destroy | `/dashboard/provision` | Azure | Low | Resources gone |
| - [ ] | 8.6 | static-site — plan only | `/dashboard/provision` | AWS | $0 | Plan succeeds |
| - [ ] | 8.7 | static-site — apply + destroy | `/dashboard/provision` | AWS | Low | Resources gone |
| - [ ] | 8.8 | backend-app — apply + destroy | `/dashboard/provision` | One | Medium | Destroyed same day |

---

## Phase 6.11 — Team cloud health (Phase 23)

| Done | # | Action | Where | Pass when |
|------|---|--------|-------|-----------|
| - [ ] | 6.11a | Org summary metrics | `/dashboard/team` | Members, org spend, VMs, storage visible |
| - [ ] | 6.11b | Admin sees per-member spend | Team page as owner | All member rows show spend/VMs |
| - [ ] | 6.11c | Member privacy | Team page as member | Other members' spend hidden; own row + org total visible |
| - [ ] | 6.11d | Invite with role + email | Team → Create invite | Link copied; email if SMTP configured |
| - [ ] | 6.11e | Transfer ownership | Team → Make owner | Old owner becomes admin |
| - [ ] | 6.11f | Org budget settings | Team settings (admin) | Budget bar updates on summary |
| - [ ] | 6.11g | Provision approval gate | Provision plan as member | Over-threshold returns approval required |
| - [ ] | 6.11h | Dashboard team card | Overview | Shows org monthly spend when in org |

---

## Phase 6.12 — Org billing & shared resources (Phase 24)

| Done | # | Action | Where | Pass when |
|------|---|--------|-------|-----------|
| - [ ] | 6.12a | Org seats card | `/dashboard/team` | Plan, seats used/available, renew date; Manage billing link for admin |
| - [ ] | 6.12b | Org billing checkout | `/dashboard/billing` as owner | Organization panel; seat stepper; Razorpay checkout (or mock in dev) |
| - [ ] | 6.12c | Member inherits org plan | Billing or Overview as member | `/my-subscription` shows org plan; personal checkout blocked |
| - [ ] | 6.12d | Seat guard on invite accept | Team with full seats | Accept invite returns 402; UI shows add seats message |
| - [ ] | 6.12e | Admin sees all org VMs | VM Cluster as admin | Toggle “Show all team resources”; cards show org + creator |
| - [ ] | 6.12f | Member sees own resources only | VM Cluster as member | Only own VMs; org label on cards |

---

## Phase 6.13 — Mobile UX (Phases 25–27)

| Done | # | Action | Where | Pass when |
|------|---|--------|-------|-----------|
| - [ ] | 6.13a | Bottom nav | `/dashboard` at 390px width | Overview, Storage, Infrastructure, Cost tabs visible; More opens sheet |
| - [ ] | 6.13b | Card tables | Storage file list, Billing history | Rows stack as labeled cards; no horizontal page overflow |
| - [ ] | 6.13c | Modals / drawers | Billing upgrade, VM request modal | Full-width or bottom sheet; dismiss works |
| - [ ] | 6.13d | Mobile tips | First visit `/dashboard` on phone | 3-step tips sheet appears (or skip); does not block forever |
| - [ ] | 6.13e | Settings BYOC | `/dashboard/settings` mobile | Credential fields stack; connect buttons ≥44px tap target |
| - [ ] | 6.13f | Provision wizard | `/dashboard/provision` deploy flow | Step indicator scrolls; sticky Back/Next above bottom nav |
| - [ ] | 6.13g | Marketing nav | `/`, `/features` | Hamburger opens drawer with Features, About, Contact, Help |

---

## Phase 6.14 — Desktop download (Phases 28–29)

| Done | # | Action | Where | Pass when |
|------|---|--------|-------|-----------|
| - [ ] | 6.14a | Download page | `/download` | Platform cards for macOS, Windows, Linux; browser fallback CTA |
| - [ ] | 6.14b | Nav links | Footer + marketing nav | Download link present |
| - [ ] | 6.14c | Electron dev | `desktop/` package | `npm run dev` opens native window loading rajverse.me |
| - [ ] | 6.14d | Release tag | `desktop-v*.*.*` push | GitHub Release with DMG, EXE, AppImage/deb artifacts |

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
