# Zenith manual testing playbook (GCP + Azure + AWS)

**Owner workflow:** Connect credentials → test features one by one → **approve cost before any paid step**.

**Cost gate:** Agents and humans must follow `.cursor/rules/cloud-testing-cost-gate.mdc`.

**Last updated:** 2026-06-04

---

## Cost tiers (use in every “can we test X?” question)

| Tier | Meaning | Examples |
|------|---------|----------|
| **$0** | No meaningful cloud bill expected | BYOC verify, tiny file upload, demo cost pages |
| **Low** | Cents to ~$2 if cleaned up same day | One static-site provision + destroy; one e2-micro/B1s for a few hours |
| **Medium** | ~$2–10 if forgotten overnight | backend-app stack left running; second VM |
| **High** | $10+ | Cosmos DB, many VMs, wrong GCP region, Performance cluster VMs |

---

## Phase 0 — Prerequisites (local)

- [ ] Backend: `uvicorn` on `:8000`, frontend `npm run dev` on `:5173`
- [ ] MongoDB running (Atlas or local)
- [ ] `backend/.env`: `DEMO_MODE=true`, `USE_REAL_METRICS=false`
- [ ] **BYOC unlock (local dev):** set `PLATFORM_OWNER_USERNAMES=your_zenith_username` and restart backend (or Pro/Enterprise plan)
- [ ] GCP + Azure **budget alerts** in each portal (e.g. $5–10/month)

---

## Phase 1 — Link credentials (website)

See chat guide or `docs/setup/CLOUD_CREDENTIAL_SETUP_GUIDE.md`.

**Website path:** Login → **Dashboard → Settings** → **Bring Your Own Cloud** → Connect **GCP** / **Azure**.

**Per cloud minimum for storage tests:**

| Cloud | Required in Settings |
|-------|---------------------|
| **GCP** | Paste full **Service Account JSON** → Verify → pick **bucket** → Test → Complete connection |
| **Azure** | **Storage account name** + **key** + **container** → Verify → Test → Complete connection |

**Later (VM tests on Azure):** also fill Subscription ID, Tenant ID, Client ID, Client secret (app registration with VM permissions).

---

## Phase 2 — Feature checklist (mark Pass/Fail)

### $0 — No approval needed

| # | Feature | Route | GCP | Azure | AWS |
|---|---------|-------|-----|-------|-----|
| 2.1 | Platform status | `/status` | ○ | ○ | ○ |
| 2.2 | BYOC connected | Settings | ○ | ○ | ○ |
| 2.3 | Storage upload/list/download/delete | `/dashboard/storage` | ○ | ○ | ○ |
| 2.4 | Secure vault (2FA on) | `/dashboard/security` | ○ | ○ | ○ |
| 2.5 | Cost hub (demo) | `/dashboard/costs` | ○ | ○ | ○ |
| 2.6 | Simulator / optimization | `/dashboard/simulator` | ○ | ○ | ○ |
| 2.7 | Profile, settings, notifications | dashboard | ○ | ○ | ○ |
| 2.8 | Support tickets | `/contact` → `/support/ticket` → `/admin/support` | ○ | ○ | ○ |

**2.8 Support tickets:** Submit contact form → note `ZN-…` in toast/email → open `/support/ticket`, enter ref + email → OTP → view thread → reply. Logged-in: `/dashboard/support`. Admin: `/admin/support` → reply (customer email + optional WS notification).

### Low — **Ask user before each cloud**

| # | Feature | Est. cost | Notes |
|---|---------|-----------|-------|
| 3.1 | Provision static-site | $0* | *Within 5 GB storage free tier |
| 3.2 | VM Cluster General (2–4 hrs) | $0–2 | GCP e2-micro us-central1; Azure B1s if 12-mo free |

### Medium / High — **Ask user; explain clearly**

| # | Feature | Est. cost |
|---|---------|-----------|
| 4.1 | Provision backend-app | Low–medium if VM left on |
| 4.2 | Provision Cosmos / Firestore DB | Azure Cosmos ~$5+; Firestore varies |
| 4.3 | VM Performance / AI cluster | Medium+ |
| 4.4 | Live billing (`DEMO_MODE=false`) | Low API usage |

---

## After each paid test — cleanup

1. Provision → **Destroy** deployment  
2. VM Cluster → **Stop** → release/delete  
3. Cloud console: no RUNNING VMs, no stray disks/public IPs  

---

## Session log (copy per test day)

```
Date:
Feature tested:
Cloud:
Cost tier: $0 / Low / Medium / High
User approved paid test: Yes / No
Result: Pass / Fail
Resources to delete:
```
