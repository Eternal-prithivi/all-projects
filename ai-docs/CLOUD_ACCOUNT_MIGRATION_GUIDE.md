# Cloud account migration guide (plain English)

> **Who this is for:** You run Zenith. This guide answers: *“I deleted my AWS, GCP, and Azure accounts and made new ones — what do I change so the app works the same?”*
>
> **Last updated:** 2026-07-11 (tailored to this repo’s deployment)  
> **Technical deep dive:** `docs/setup/CLOUD_CREDENTIAL_SETUP_GUIDE.md` · `docs/cloud/CREDENTIAL_CONTRACT.md`

---

## Your question, answered simply

**Yes — new accounts mean new credentials.** You create new access keys / service accounts in the new clouds, then paste them into the places Zenith reads them.

**For you (platform owner):** update **`backend/.env`** (laptop) and **Render** (production). That is almost everything.

**For advanced BYOC users:** they update **their own** credentials in **Settings → BYOC**. You do **not** do that for them. Their change is separate from your platform account change.

**You do not change:** MongoDB connection, `SECRET_KEY`, Razorpay, Twilio, Gmail, frontend/Vercel (no cloud keys there), or app code — **unless** your new AWS account has a **different account ID** (see [Code change](#step-7-code-change-only-if-aws-account-id-changes)).

---

## Your deployment profile (checked from this project)

These facts were read from your repo config — **no secrets listed here**.

| Setting | Your project today |
|---------|-------------------|
| **Multi-region storage** | **Yes** — 4 region pills (Asia, US, Europe, Africa) via `platform_storage_catalog.json` |
| **Google Sign-In** | **Off** — `GOOGLE_OAUTH_*` not set (email/password login only) |
| **Local dev cost mode** | `DEMO_MODE=true` (mock billing on laptop) |
| **Production cost mode** | `DEMO_MODE=false` in `zenith-backend.env` (live billing APIs when creds work) |
| **GCP project** | `zenith-dev-498414` |
| **Platform owner login** | `tanjiro` (enterprise via `PLATFORM_OWNER_USERNAMES`) |
| **BYOC** | Feature for Pro/Enterprise users in Settings — **not** where your platform keys live |

### Bucket / container names you must recreate (same names = app behaves the same)

Use these exact names in the **new** accounts so you only change credentials, not code.

**AWS (S3)**

| Purpose | Bucket name | Region |
|---------|-------------|--------|
| Main / Asia catalog | `zeneith-storage-bucket` | `ap-south-1` |
| US region | `zeneith-storage-us` | `us-east-1` |
| Europe region | `zeneith-storage-europe` | `eu-west-1` |
| Africa region | `zeneith-storage-africa` | `af-south-1` |
| Secure vault | `zenith-secure-files` | (primary region) |
| Secure replica | `zenith-secure-files-replica` or `zenith-secure-files-secondary2` | `us-east-1` |

**GCP (Cloud Storage)**

| Purpose | Bucket name |
|---------|-------------|
| US / default | `zenith-main-bucket` |
| Asia | `zeneith-main-asia` |
| Europe | `zeneith-main-europe` |
| Africa | `zeneith-main-africa` |
| Secure vault | `zenith-secure-gcp` |
| Secure replica | `zenith-secure-gcp-replica` |

**Azure (Blob)**

| Purpose | Storage account | Container |
|---------|-----------------|-----------|
| US / default | `zenithprithivi` | `zenith-main-bucket` |
| Asia | `zenithpriasia` | `zenith-storage` |
| Europe | `zenithprieu` | `zenith-storage` |
| Africa | `zenithpriafrica` | `zenith-storage` |
| Secure vault | (same accounts or dedicated) | `zenith-secure` |
| Secure replica | | `zenith-secure-replica` |

**Easiest way to create all of this:** run `backend/scripts/provision_platform_storage.py` after putting **new** platform keys in `.env` — it creates buckets and writes `platform_storage_catalog.json`.

---

## Main playbook: deleted all 3 platform accounts → new accounts

Follow these steps in order. This is the complete list for **your** setup.

### Step 1 — Create new cloud accounts and resources

In each new AWS / GCP / Azure account:

1. Create IAM user (AWS) / service account (GCP) / app registration + storage (Azure) with permissions for S3, GCS, Blob, EC2, etc. (same as before).
2. Create buckets and containers using the **names in the table above** (or run the provision script in Step 3).
3. Download **GCP service account JSON** → save as `backend/gcp-platform-key.json` (gitignored).

### Step 2 — Update `backend/.env` on your laptop

Open `backend/.env` and replace **only** the cloud blocks. Keep Mongo, `SECRET_KEY`, Celery, Razorpay, Twilio, Gmail as they are.

**AWS — update these lines:**

```
AWS_ACCESS_KEY_ID=          ← new key
AWS_SECRET_ACCESS_KEY=      ← new secret
S3_BUCKET_NAME=zeneith-storage-bucket
REGULAR_S3_BUCKET_NAME=zeneith-storage-bucket
PRIMARY_S3_REGION=ap-south-1
SECURE_S3_BUCKET_NAME=zenith-secure-files
REPLICA_S3_BUCKET_NAME=zenith-secure-files-replica
REPLICA_S3_REGION=us-east-1
```

**GCP — update these lines:**

```
GCP_PROJECT_ID=             ← new project ID
GCP_SERVICE_ACCOUNT_JSON_PATH=backend/gcp-platform-key.json
GCP_ZONE=us-central1-a
GCP_BUCKET_NAME=zenith-main-bucket
GCP_SECURE_BUCKET_NAME=zenith-secure-gcp
GCP_SECURE_REPLICA_BUCKET_NAME=zenith-secure-gcp-replica
```

**Azure — update these lines:**

```
AZURE_STORAGE_ACCOUNT_NAME=zenithprithivi
AZURE_STORAGE_ACCOUNT_KEY=  ← new key
AZURE_CONTAINER_NAME=zenith-main-bucket
AZURE_SECURE_CONTAINER_NAME=zenith-secure
AZURE_SECURE_REPLICA_CONTAINER_NAME=zenith-secure-replica
AZURE_SUBSCRIPTION_ID=      ← new subscription
AZURE_TENANT_ID=            ← new tenant
AZURE_CLIENT_ID=            ← new app registration
AZURE_CLIENT_SECRET=        ← new secret
AZURE_RESOURCE_GROUP=zenith-rg
AZURE_LOCATION=eastus
```

**Multi-region catalog — keep these lines:**

```
PLATFORM_STORAGE_CATALOG_JSON=config/platform_storage_catalog.json
PLATFORM_STORAGE_DEFAULT_SLUG=asia
```

### Step 3 — Regenerate the storage catalog (recommended)

From `backend/`:

```bash
# After .env has NEW credentials:
python scripts/provision_platform_storage.py
```

This creates regional buckets and rewrites `backend/config/platform_storage_catalog.json` with new Azure keys embedded per region.

**Manual alternative:** edit `platform_storage_catalog.json` yourself — update each region’s `account_key` for Azure (file is gitignored; never commit it).

### Step 4 — Test locally

```bash
cd backend && .venv/bin/python -m pytest -q
# Start API + frontend, then:
```

- [ ] Upload a small file on Storage (try AWS, GCP, Azure)
- [ ] Switch region pill (e.g. Asia → US) and upload again
- [ ] Secure vault upload (if 2FA on)
- [ ] Login still works (you did **not** change `SECRET_KEY`)

### Step 5 — Update Render (production)

For **zenith-api**, **zenith-celery**, and **zenith-provision**:

1. **Environment variables** — paste the same cloud variables as `.env` (use Render dashboard, not Git).
2. **GCP JSON** — upload new file as **Secret File**; set `GCP_SERVICE_ACCOUNT_JSON_PATH` to mount path (e.g. `/etc/secrets/gcp-key.json`).
3. **Catalog JSON** — upload new `platform_storage_catalog.json` as secret file; set `PLATFORM_STORAGE_CATALOG_JSON` to its path.
4. **Redeploy** all three services.

Helper: `python backend/scripts/export_render_env.py` builds a paste file from your local `.env` (output is gitignored).

**`render.yaml` secure names** — already set to `zenith-secure-gcp`, `zenith-secure`, etc. No change needed if you reused those bucket/container names.

### Step 6 — Verify production (rajverse.me)

- [ ] `https://rajverse.me` — login as `tanjiro`
- [ ] Storage upload on each cloud
- [ ] Region pills work
- [ ] Cost page loads (production uses `DEMO_MODE=false`)

### Step 7 — Code change (only if AWS account ID changes)

If your **new** AWS account is not `412628362844`, update two files and push:

| File | Change |
|------|--------|
| `backend/app/byoc/routes_byoc.py` | `ZENITH_AWS_ACCOUNT_ID = "YOUR_NEW_12_DIGIT_ID"` |
| `backend/terraform/backend.tf` | S3 state bucket name (create new state bucket in new account) |

This matters only for **BYOC users who connect via IAM role** — they must update their role trust policy to trust your new Zenith AWS account ID.

### Step 8 — Old data (expectations)

Deleting old cloud accounts **deletes old files**. MongoDB still has records pointing at old buckets — uploads/downloads for those old files will fail.

| Your choice | What to do |
|-------------|------------|
| **Start fresh** (typical after account deletion) | Nothing extra — new uploads work; old file rows in app may show errors until you delete them in the UI |
| **Keep old files** | You must copy objects to new buckets **before** deleting old accounts (`aws s3 sync`, `gsutil rsync`, AzCopy) — not automatic |

### What you do **not** need to change

| Item | Why |
|------|-----|
| MongoDB (`MONGO_*`) | Not a cloud provider account |
| `SECRET_KEY` | Changing it logs everyone out and breaks encrypted BYOC |
| Vercel / frontend | No cloud keys — only `VITE_API_URL` |
| Razorpay, Twilio, Gmail | Unrelated to AWS/GCP/Azure |
| BYOC users’ Settings | They manage their own cloud; separate from your platform keys |
| `GOOGLE_OAUTH_*` | Not configured in your project |

---

## BYOC users (advanced) — separate from your platform change

| Who | What they do when **their** cloud changes |
|-----|-------------------------------------------|
| Pro/Enterprise user | Settings → disconnect old BYOC → connect new credentials → Test connection |
| You (platform owner) | You use **platform** `.env` / Render — not BYOC — unless you personally connected BYOC in Settings too |

Your platform credential swap does **not** automatically update anyone’s BYOC. Each BYOC user fixes their own Settings.

---

## The big picture (reference)

Zenith platform credentials live in **two places you control**:

1. **Your computer** — `backend/.env` + `gcp-platform-key.json` + `platform_storage_catalog.json`
2. **Render** — same variables + secret file uploads

BYOC credentials live in **MongoDB** (per user, via Settings UI).

**The frontend website does not store cloud passwords or keys.**

---

## Two types of cloud access (reference)

| Type | Plain English | Where it lives | Who it affects |
|------|---------------|----------------|----------------|
| **Platform cloud** | Zenith’s shared keys — default for Free/Basic and platform storage | `backend/.env` + Render | All non-BYOC usage |
| **BYOC** | User connects their own cloud in Settings | MongoDB `byoc_credentials` | That user only |

---

## Other scenarios (reference)

| I want to… | Go to section |
|------------|---------------|
| Replace Zenith’s **AWS** platform account only | [AWS platform checklist](#aws-platform-checklist) |
| Replace Zenith’s **GCP** platform project only | [GCP platform checklist](#gcp-platform-checklist) |
| Replace Zenith’s **Azure** platform only | [Azure platform checklist](#azure-platform-checklist) |
| Change **my own** BYOC in Settings | [BYOC user checklist](#byoc-user-checklist-settings-ui) |
| Only **rotate keys** (same account) | [Key rotation only](#key-rotation-only-same-account) |

---

## Golden rules (do not skip)

1. **Never commit real keys to Git.** Files like `backend/.env`, `gcp-platform-key.json`, and `platform_storage_catalog.json` are gitignored on purpose.
2. **Update local AND production.** Changing only your laptop `.env` does not fix rajverse.me — you must update **Render** too.
3. **`SECRET_KEY` is not a cloud key** — but changing it logs everyone out **and** makes old BYOC encrypted data unreadable. Avoid changing it during a cloud migration unless you mean to.
4. **Bucket names must match reality.** If you create new buckets in the new account, update every env var and catalog entry that mentions the old name.
5. **Old files don’t move themselves.** MongoDB still remembers old `cloud_bucket` / `cloud_region`. New uploads work after migration; old files may need re-sync or data copy in the cloud console.
6. **After Render changes, redeploy** the backend (or trigger a deploy) so new env vars load.

---

## Where each setting lives

### A. Local development (`backend/.env`)

Copy template: `backend/.env.example` or `backend/.env.production.example`.

This is the **master list** the backend reads (`backend/app/utils/config.py`). Every platform cloud variable you care about is here.

### B. Production backend (Render dashboard)

Path: **Render → zenith-api (and zenith-celery, zenith-provision) → Environment**

- Paste the same variable **names** as `.env`, with production values.
- **GCP JSON file:** upload as a **Secret File** mounted at e.g. `/etc/secrets/gcp-key.json`, then set `GCP_SERVICE_ACCOUNT_JSON_PATH` to that path.
- **Storage catalog (optional):** upload `platform_storage_catalog.json` as a secret file; set `PLATFORM_STORAGE_CATALOG_JSON` to its path.

Helper script (generates a paste file from local `.env`):  
`backend/scripts/export_render_env.py` → `render-env-paste.env` (gitignored — do not commit).

### C. Production frontend (Vercel)

**Usually nothing cloud-related.** Vercel only needs:

- `VITE_API_URL` — where the API lives (e.g. `https://api.rajverse.me`)
- `VITE_SITE_URL` — public site URL

See `docs/setup/DEPLOYMENT_SECRETS.md`.

### D. Hardcoded bucket **names** in `render.yaml`

These are **not secrets** — they are fixed secure-vault names baked into the deploy config:

| Variable | Current value in repo |
|----------|----------------------|
| `GCP_SECURE_BUCKET_NAME` | `zenith-secure-gcp` |
| `GCP_SECURE_REPLICA_BUCKET_NAME` | `zenith-secure-gcp-replica` |
| `AZURE_SECURE_CONTAINER_NAME` | `zenith-secure` |
| `AZURE_SECURE_REPLICA_CONTAINER_NAME` | `zenith-secure-replica` |

If your **new** GCP/Azure account uses different secure vault names, update `render.yaml` **and** matching env vars on Render, then redeploy.

### E. App UI — BYOC (per user)

**Dashboard → Settings → Cloud connections (BYOC)**

Users paste AWS keys, GCP service account JSON, or Azure storage keys. Zenith encrypts and stores them in MongoDB. Changing cloud account = **disconnect old → connect new → Test connection**.

### F. MongoDB (automatic — you don’t edit by hand)

| Collection | What’s stored | After account change |
|------------|---------------|----------------------|
| `byoc_credentials` | Encrypted user cloud keys + bucket names | Reconnect BYOC in Settings |
| `files` / `secure_files` | Which bucket/region each file lives in | Old rows may point at old buckets |
| `provision_deployments` | Stack metadata | May need redeploy with new creds |

---

## AWS platform checklist

Use when Zenith’s **shared** AWS account changes (not BYOC-only users).

### Step 1 — Create resources in the **new** AWS account

In AWS Console (or CLI), create or note:

| What | Typical env variable | Notes |
|------|---------------------|-------|
| IAM access key + secret | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | Programmatic user with S3, EC2, Cost Explorer as needed |
| Main storage bucket | `S3_BUCKET_NAME` or `REGULAR_S3_BUCKET_NAME` | Standard uploads |
| Secure vault bucket | `SECURE_S3_BUCKET_NAME` | 2FA-protected files |
| Replica bucket | `REPLICA_S3_BUCKET_NAME` | Secure vault copy |
| Regions | `PRIMARY_S3_REGION`, `REPLICA_S3_REGION`, `AWS_REGION` | e.g. `ap-south-1`, `us-west-2` |

If you use **multi-region catalog**, create buckets per slug (e.g. `zeneith-storage-asia`) — see [Multi-region catalog](#multi-region-storage-catalog-extra-steps).

### Step 2 — Update `backend/.env`

```bash
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET_NAME=...
REGULAR_S3_BUCKET_NAME=...
SECURE_S3_BUCKET_NAME=...
REPLICA_S3_BUCKET_NAME=...
PRIMARY_S3_REGION=...
REPLICA_S3_REGION=...
```

Also update billing-related vars if you use live AWS cost (same keys usually work).

### Step 3 — Update Render

Same variable names → Render Environment for **zenith-api**, **zenith-celery**, **zenith-provision**.

### Step 4 — BYOC IAM role users (if any)

Some users connect AWS via **IAM role** instead of access keys. Zenith’s AWS account ID is hardcoded for trust policies:

- File: `backend/app/byoc/routes_byoc.py` → `ZENITH_AWS_ACCOUNT_ID = "412628362844"`
- Terraform state bucket: `backend/terraform/backend.tf` → `terraform-state-412628362844`

**If Zenith’s AWS account ID changes**, you must:

1. Update `ZENITH_AWS_ACCOUNT_ID` in code
2. Update `backend/terraform/backend.tf` bucket name (or create new state bucket)
3. Tell BYOC IAM users to update their role **trust policy** with the new Zenith account ID (Settings shows the template)
4. Commit, push, redeploy

If you only change **keys inside the same AWS account**, skip this step.

### Step 5 — Migrate old data (optional but recommended)

Copy objects from old S3 buckets to new buckets (AWS Console → S3 → Replication, or `aws s3 sync`). Old MongoDB file records still say old bucket names until you re-upload or run a DB cleanup.

### Step 6 — Verify

- [ ] Local: upload a test file on Storage (AWS)
- [ ] Local: sync AWS bucket
- [ ] Production: same on rajverse.me
- [ ] Cost page loads (if not `DEMO_MODE`)
- [ ] BYOC “Test connection” works for AWS BYOC users

---

## GCP platform checklist

Use when Zenith’s **shared** GCP project or service account changes.

### Step 1 — Create resources in the **new** GCP project

| What | Env variable | Notes |
|------|--------------|-------|
| Project ID | `GCP_PROJECT_ID` | e.g. `my-new-project-123` |
| Service account JSON key | `GCP_SERVICE_ACCOUNT_JSON_PATH` | Download JSON from IAM → Keys |
| Zone for VMs | `GCP_ZONE` | e.g. `us-central1-a` |
| Main bucket | `GCP_BUCKET_NAME` | Standard storage |
| Secure vault bucket | `GCP_SECURE_BUCKET_NAME` | Also in `render.yaml` as `zenith-secure-gcp` unless you change it |
| Secure replica | `GCP_SECURE_REPLICA_BUCKET_NAME` | `zenith-secure-gcp-replica` in `render.yaml` |
| Billing export (optional) | `GCP_BILLING_DATASET_ID`, `GCP_BILLING_TABLE_ID` | BigQuery billing export for Cost Analysis |

Save the JSON file as e.g. `backend/gcp-platform-key.json` (gitignored).

### Step 2 — Update `backend/.env`

```bash
GCP_PROJECT_ID=...
GCP_ZONE=...
GCP_SERVICE_ACCOUNT_JSON_PATH=backend/gcp-platform-key.json
GCP_BUCKET_NAME=...
GCP_SECURE_BUCKET_NAME=...
GCP_SECURE_REPLICA_BUCKET_NAME=...
GCP_BILLING_DATASET_ID=...   # if using live cost
GCP_BILLING_TABLE_ID=...
```

### Step 3 — Update Render

- Set all `GCP_*` env vars
- **Upload new JSON** as Secret File; point `GCP_SERVICE_ACCOUNT_JSON_PATH` to mount path (e.g. `/etc/secrets/gcp-key.json`)
- Delete old secret file from Render when confirmed working

### Step 4 — Update `render.yaml` (only if secure bucket **names** changed)

If new buckets are not named `zenith-secure-gcp` / `zenith-secure-gcp-replica`, edit `render.yaml` and redeploy.

### Step 5 — Google Sign-In (optional, separate from GCP storage)

If you use “Sign in with Google”, rotate in Google Cloud Console → OAuth client:

- `GOOGLE_OAUTH_CLIENT_ID`
- `GOOGLE_OAUTH_CLIENT_SECRET`

These are **not** the same as the storage service account.

### Step 6 — Verify

- [ ] Upload test file (GCP) locally and on production
- [ ] VM cluster can list/create (if enabled)
- [ ] Cost Analysis shows GCP data (if billing export configured)
- [ ] GCP BYOC users reconnect in Settings if they use their own project

---

## Azure platform checklist

Use when Zenith’s **shared** Azure storage or subscription changes.

### Step 1 — Create resources in the **new** Azure account

| What | Env variable | Notes |
|------|--------------|-------|
| Storage account name | `AZURE_STORAGE_ACCOUNT_NAME` | Blob storage |
| Storage account key | `AZURE_STORAGE_ACCOUNT_KEY` | Keys blade in portal |
| Main container | `AZURE_CONTAINER_NAME` | Standard uploads |
| Secure container | `AZURE_SECURE_CONTAINER_NAME` | `zenith-secure` in `render.yaml` |
| Secure replica | `AZURE_SECURE_REPLICA_CONTAINER_NAME` | `zenith-secure-replica` in `render.yaml` |
| Subscription ID | `AZURE_SUBSCRIPTION_ID` | Cost Management + VMs |
| Tenant ID | `AZURE_TENANT_ID` | Service principal |
| App (client) ID | `AZURE_CLIENT_ID` | Service principal |
| Client secret | `AZURE_CLIENT_SECRET` | Service principal |
| Resource group / region | `AZURE_RESOURCE_GROUP`, `AZURE_LOCATION` | Defaults: `zenith-rg`, `eastus` |

### Step 2 — Update `backend/.env`

Fill all `AZURE_*` variables above.

### Step 3 — Update Render

Same variables on all three backend services.

### Step 4 — Multi-region Azure (if used)

Azure keys for regional storage accounts may also live in:

- `backend/config/platform_storage_catalog.json` (per-region entries)
- `backend/config/azure_platform_keys.json` (slug → account key map)

Update **both** when rotating Azure storage accounts. Re-upload catalog to Render secret file.

### Step 5 — Verify

- [ ] Upload test file (Azure)
- [ ] Sync Azure container
- [ ] Cost page (if SP configured)
- [ ] Azure BYOC users reconnect in Settings

---

## Multi-region storage catalog (extra steps)

If users see **region pills** (Asia, US, Europe, Africa) on the Storage page, you use the platform catalog.

| File | Purpose |
|------|---------|
| `backend/config/platform_storage_catalog.example.json` | Template — safe to commit |
| `backend/config/platform_storage_catalog.json` | **Your real buckets + Azure keys** — gitignored |
| `backend/config/azure_platform_keys.json` | Optional Azure key sidecar — gitignored |

**Env vars:**

```bash
PLATFORM_STORAGE_CATALOG_JSON=config/platform_storage_catalog.json
PLATFORM_STORAGE_DEFAULT_SLUG=asia
```

**When you change cloud accounts:**

1. Create new buckets per region per cloud (see `docs/cloud/PLATFORM_STORAGE_REGIONS.md` naming).
2. Edit `platform_storage_catalog.json` with new bucket names and Azure keys.
3. Update `azure_platform_keys.json` if you use it.
4. Update `.env` + Render `PLATFORM_STORAGE_CATALOG_JSON` secret file.
5. Test each region pill with a small upload.

**If you don’t use multi-region:** leave `PLATFORM_STORAGE_CATALOG_JSON` empty. Zenith falls back to single buckets from `REGULAR_S3_BUCKET_NAME`, `GCP_BUCKET_NAME`, `AZURE_CONTAINER_NAME`.

---

## BYOC user checklist (Settings UI)

For **your own** connected cloud (or any Pro/Enterprise user), not the platform `.env`.

1. Sign in → **Settings** → **Cloud / BYOC** section.
2. **Disconnect** the old provider (or use update flow if available).
3. **Connect** with new credentials:
   - **AWS:** access keys *or* IAM role ARN + external ID
   - **GCP:** paste service account JSON; optionally add billing dataset/table for Cost
   - **Azure:** storage account + key; optionally add service principal for VM/Cost
4. Click **Test connection** — must pass before uploads work.
5. Re-enter **bucket/container names** if they changed in the new account.
6. For **Cost** (GCP/Azure): complete Tier 2 setup in Settings or Cost Analysis setup wizard.

**What breaks if you skip reconnect:**

| Feature | Symptom |
|---------|---------|
| Storage upload | “Missing config” or 403 |
| Security vault sync | Empty or errors |
| VMs / Provision | Locked or deploy fails |
| Cost Analysis | Demo data or “billing not configured” |

**Old files:** Records in MongoDB still reference old buckets. New uploads go to new buckets. Migrate data in the cloud console or re-upload important files.

---

## Key rotation only (same account)

Same AWS/GCP/Azure account, just new keys (security best practice).

| Cloud | What to do |
|-------|------------|
| **AWS** | IAM → new access key → update `.env` + Render → delete old key |
| **GCP** | IAM → Service account → Add key (JSON) → replace file + path → delete old key |
| **Azure** | Storage → Regenerate key → update `.env` + Render + catalog JSON if keys embedded there |
| **BYOC** | Settings → update credentials → Test connection |

Full runbook: `docs/setup/CREDENTIAL_ROTATION.md`

**Do not change `SECRET_KEY`** during a simple key rotation unless you intend to log everyone out and re-enter all BYOC credentials.

---

## Recommended order (all platform clouds)

If replacing AWS + GCP + Azure at once, do this order to reduce downtime:

```
1. Create all buckets / containers / IAM in new accounts (offline)
2. Update backend/.env locally — test with DEMO_MODE=false
3. Run local smoke: upload + sync on each CSP
4. Update Render env + secret files (GCP JSON, catalog JSON)
5. Update render.yaml if secure vault names changed
6. Deploy backend → wait for healthy /health/ready
7. Deploy frontend (usually no cloud changes)
8. Production smoke on rajverse.me
9. Notify BYOC users to reconnect if platform STS/IAM templates changed
10. Migrate old object data in cloud consoles (background)
```

---

## Old files and database — what to expect

| Situation | What users see | Fix |
|-----------|----------------|-----|
| New keys, **same buckets** | Everything keeps working | Nothing extra |
| New account, **new buckets**, old data not copied | Old files missing or download fails | Copy objects in S3/GCS/Azure; or re-upload |
| BYOC reconnected, bucket names changed | Sync shows fewer files | Re-sync; migrate cloud data |
| `SECRET_KEY` changed | Login works after re-login; BYOC decrypt fails | Restore old SECRET_KEY or users must reconnect BYOC |

Zenith does **not** auto-migrate terabytes of storage. Plan a one-time `aws s3 sync` / `gsutil rsync` / AzCopy if you need continuity.

---

## Code changes (rare — only if Zenith’s AWS account ID changes)

| File | What to change |
|------|----------------|
| `backend/app/byoc/routes_byoc.py` | `ZENITH_AWS_ACCOUNT_ID` |
| `backend/terraform/backend.tf` | S3 state `bucket` name and comments |

Commit and push to `stage` after edits. No frontend changes needed for cloud account swaps.

---

## Full verification checklist

Run after any migration.

### Local (`backend/.env` updated)

```bash
cd backend && .venv/bin/python -m pytest -q
# Start API + frontend, then manually:
```

- [ ] Login works
- [ ] **Storage:** upload + sync for AWS, GCP, Azure (one file each)
- [ ] **Security:** secure upload works (if 2FA enabled)
- [ ] **Settings → BYOC:** Test connection passes
- [ ] **Cost Analysis:** not stuck on demo (if live billing configured)
- [ ] **VM Cluster:** list VMs (if you use VMs)
- [ ] **Provision:** plan/apply smoke (if you use provision)

### Production (Render + Vercel)

- [ ] `https://api.rajverse.me/health/ready` → healthy
- [ ] `https://rajverse.me` login
- [ ] Upload on Storage (each CSP you use)
- [ ] Admin dashboard loads (`/admin`)
- [ ] No spike in Sentry errors (if configured)

---

## Quick reference — all platform env variables

### AWS

| Variable | Purpose |
|----------|---------|
| `AWS_ACCESS_KEY_ID` | API access |
| `AWS_SECRET_ACCESS_KEY` | API secret |
| `S3_BUCKET_NAME` | Primary bucket |
| `REGULAR_S3_BUCKET_NAME` | Standard storage alias |
| `SECURE_S3_BUCKET_NAME` | Secure vault |
| `REPLICA_S3_BUCKET_NAME` | Secure replica |
| `PRIMARY_S3_REGION` | Main region |
| `REPLICA_S3_REGION` | Replica region |

### GCP

| Variable | Purpose |
|----------|---------|
| `GCP_PROJECT_ID` | Project |
| `GCP_SERVICE_ACCOUNT_JSON_PATH` | Path to SA JSON file |
| `GCP_ZONE` | VM zone |
| `GCP_BUCKET_NAME` | Standard storage |
| `GCP_SECURE_BUCKET_NAME` | Secure vault |
| `GCP_SECURE_REPLICA_BUCKET_NAME` | Secure replica |
| `GCP_BILLING_DATASET_ID` | BigQuery billing (optional) |
| `GCP_BILLING_TABLE_ID` | BigQuery table (optional) |

### Azure

| Variable | Purpose |
|----------|---------|
| `AZURE_STORAGE_ACCOUNT_NAME` | Storage account |
| `AZURE_STORAGE_ACCOUNT_KEY` | Storage key |
| `AZURE_CONTAINER_NAME` | Standard container |
| `AZURE_SECURE_CONTAINER_NAME` | Secure vault |
| `AZURE_SECURE_REPLICA_CONTAINER_NAME` | Secure replica |
| `AZURE_SUBSCRIPTION_ID` | Subscription (cost/VM) |
| `AZURE_TENANT_ID` | Azure AD tenant |
| `AZURE_CLIENT_ID` | App registration |
| `AZURE_CLIENT_SECRET` | App secret |
| `AZURE_RESOURCE_GROUP` | Default RG |
| `AZURE_LOCATION` | Default region |

### Multi-region (optional)

| Variable | Purpose |
|----------|---------|
| `PLATFORM_STORAGE_CATALOG_JSON` | Path to region→bucket JSON |
| `PLATFORM_STORAGE_DEFAULT_SLUG` | Default region (`asia`, `us`, …) |

---

## Helper scripts

| Script | When to use |
|--------|-------------|
| `backend/scripts/export_render_env.py` | Build Render paste file from local `.env` |
| `backend/scripts/provision_platform_storage.py` | Create platform buckets + generate catalog (new deploy) |
| `backend/scripts/configure_azure_platform_catalog.py` | Wire Azure keys into catalog JSON |

---

## Related documentation

| Doc | Use when |
|-----|----------|
| `docs/setup/CLOUD_CREDENTIAL_SETUP_GUIDE.md` | First-time setup from scratch (~full recreation) |
| `docs/setup/CREDENTIAL_ROTATION.md` | Rotating keys without changing accounts |
| `docs/setup/DEPLOYMENT_SECRETS.md` | Render + Vercel env checklist |
| `docs/cloud/CREDENTIAL_CONTRACT.md` | Technical contract (platform vs BYOC) |
| `docs/cloud/PLATFORM_STORAGE_REGIONS.md` | Multi-region bucket naming |
| `docs/cloud/BYOC_OPTIONAL_SETUP.md` | Tier 1 / Tier 2 BYOC for users |
| `ai-docs/AI_CONTEXT_BACKEND.md` | Backend env var map for developers |
| `ai-docs/STATUS.md` | Render catalog upload reminder |
| `ai-docs/CLOUD_ACCOUNT_MIGRATION_GUIDE.md` | Owner checklist when switching AWS/GCP/Azure accounts |

---

## One-page cheat sheet (print this)

```
DELETED PLATFORM ACCOUNTS → NEW ACCOUNTS (your case)
──────────────────────────────────────────────────
□ Create new AWS/GCP/Azure accounts
□ Create buckets/containers (same names as guide table)
   OR run: python backend/scripts/provision_platform_storage.py
□ Put new keys in backend/.env (AWS_*, GCP_*, AZURE_*)
□ Replace backend/gcp-platform-key.json
□ Regenerate platform_storage_catalog.json
□ Test locally (upload + region pills)
□ Update Render env on all 3 services + upload GCP JSON + catalog JSON
□ Redeploy backend
□ If new AWS account ID → update routes_byoc.py + terraform/backend.tf
□ Test rajverse.me

DO NOT CHANGE
─────────────
□ SECRET_KEY, MONGO_*, Razorpay, Twilio, Gmail, Vercel

BYOC USERS (not you)
────────────────────
□ They update Settings themselves when THEIR cloud changes
```

---

*Guide version: 2026-07-11 · Maintained in `ai-docs/` for agent and owner continuity.*
