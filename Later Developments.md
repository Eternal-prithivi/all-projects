# Later Developments

**Purpose:** Things we are **not doing right now**, but should not forget. Check this file when you plan the next improvement sprint.

**Last updated:** 2026-06-03

---

## How to use this file

- Each item has: **what it is**, **why later**, **how you’ll know it’s done**, and **where to read more**.
- When you finish an item, move it to a “Completed” section at the bottom (with date) or delete it.

---

## Now vs later (quick summary)

| Topic | What we do **now** | What we do **later** |
|--------|-------------------|----------------------|
| Night jobs (Celery) | Run on **your Mac** while it’s on | Run on **Render** (`zenith-celery`, ~$7/month) |
| CI on GitHub | Runs on push/PR (see below) | **Enforce** before merge + before deploy |
| Deploy to Render | Often **auto-deploy on push** | Deploy **only** after green CI |

---

## 1. Background jobs on Render (`zenith-celery`) — deferred (cost)

### What it is

A second Render service that runs **scheduled tasks** while you sleep:

- Move old files to cheaper storage tiers  
- Cost anomaly checks  
- ML feedback / retrain  
- VM health / adaptive agent  

### Why not now

- Render **Background Worker** has **no free tier** on the setup screen (Starter ≈ **$7/month**).
- You chose to run these jobs on your **Mac** for now instead.

### What we do now (Mac)

1. Keep the main website on Render (`zenith-backend`) as today.  
2. On your Mac, open a **second Terminal** and run (only when testing or you want jobs to run):

```bash
cd /Users/a.prithiviraj/Documents/Projects/CloudResourceOptimizationPlatform/backend
source ../venv/bin/activate
./scripts/start-celery.sh
```

3. Leave that window open. Jobs run only while your Mac is on and that command is running.  
4. Uses the same `CELERY_BROKER_URL` from `backend/.env` (CloudAMQP).

**More detail:** [docs/enterprise/CELERY_DEPLOYMENT.md](docs/enterprise/CELERY_DEPLOYMENT.md)

### Done when (later on Render)

- [ ] `zenith-celery` service exists on Render (Starter or higher).  
- [ ] **All** environment variables from `zenith-backend` are copied to the worker (especially `CELERY_BROKER_URL`, Mongo, AWS).  
- [ ] Worker logs show **Live** and Beat schedule registered.  
- [ ] Admin → **System** shows Celery broker reachable (optional check).

**Code reference:** [render.yaml](render.yaml) (worker definition is already in the repo).

---

## 2. CI must pass **before** deploy to Render / Vercel — not fully enforced yet

### What it is

Today you want: **no deploy to staging** until GitHub CI is green (tests, lint, build, security scans).

### What exists today (checked in repo)

| Piece | Status | Plain English |
|-------|--------|----------------|
| CI workflow | **Yes** | [.github/workflows/ci.yml](.github/workflows/ci.yml) runs on push and on pull requests to `stage`. |
| Deploy-after-CI workflow | **Partial** | [.github/workflows/deploy-stage.yml](.github/workflows/deploy-stage.yml) runs **after** CI completes **successfully** on `stage`. |
| Render auto-deploy on push | **Often still on** | If Render is connected to GitHub `stage`, it may deploy **immediately on push**, **before or without** waiting for CI. |
| `RENDER_DEPLOY_HOOK` secret | **May be missing** | If not set in GitHub, deploy workflow **skips** backend deploy (message in workflow); Render auto-deploy may still run. |
| Vercel secrets | **May be missing** | Same for frontend; Vercel may still auto-deploy from its own Git integration. |

**Conclusion:** The **idea** is in the repo; the **full “CI first, then deploy only”** flow is **not guaranteed** until you change host settings and secrets.

### What to do later (checklist)

- [ ] **Render:** Turn **off** auto-deploy on push for `zenith-backend`.  
- [ ] **Vercel:** Turn **off** automatic production/staging deploy on every push to `stage` (or use preview-only).  
- [ ] **GitHub secrets:** Add `RENDER_DEPLOY_HOOK`, `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` (see [docs/setup/DEPLOYMENT_SECRETS.md](docs/setup/DEPLOYMENT_SECRETS.md)).  
- [ ] Optional: `STAGE_API_URL` for post-deploy smoke in `deploy-stage.yml`.  
- [ ] Verify: push bad code → CI fails → **staging does not update**; push good code → CI passes → **one** deploy runs.

**More detail:** [docs/testing/professional_standard.md](docs/testing/professional_standard.md) (Tier A1) and [docs/testing/PHASE_20_5_CI_GATES.md](docs/testing/PHASE_20_5_CI_GATES.md) (item 20.5.1).

### Done when

- Staging updates **only** after green CI (no double deploy from Render + GitHub both firing).

---

## 3. CI must pass **before** merging a PR into `stage` — not fully enforced yet

### What it is

You want: nobody can merge into `stage` until CI jobs pass (backend tests, frontend build, Terraform validate, Playwright, audits, etc.).

### What exists today (checked in repo)

| Piece | Status | Plain English |
|-------|--------|----------------|
| CI on pull requests | **Yes** | `ci.yml` runs when you open/update a PR **targeting** `stage` (or `main` / `develop`). |
| CI **blocks** merge automatically | **No** (by default) | GitHub will still let you merge unless you turn on **branch protection** in the GitHub website. |
| Branch protection doc | **Yes** | [docs/testing/BRANCH_PROTECTION.md](docs/testing/BRANCH_PROTECTION.md) explains how to enable it — **manual step**, not in code alone. |
| Direct push to `stage` | **May still work** | If you push straight to `stage` without a PR, CI runs but nothing **blocks** the push. |

**Conclusion:** CI **runs** on PRs; CI does **not yet guarantee** “must pass before merge” until you configure GitHub branch protection (and optionally require PRs).

### What to do later (checklist)

- [ ] GitHub → **Settings → Branches → Branch protection rule** for `stage`.  
- [ ] Enable **Require status checks to pass before merging**.  
- [ ] Required checks (match job names in Actions): `backend`, `frontend`, `terraform-validate`, `playwright`, `security-audit`, `docker-scan` (confirm exact names in latest CI run).  
- [ ] Optional but recommended: **Require a pull request before merging** (no direct push to `stage`).  
- [ ] Optional: **Require branches to be up to date** before merge.  
- [ ] Team habit: feature branch → PR → `stage` (not direct push).

**More detail:** [docs/testing/BRANCH_PROTECTION.md](docs/testing/BRANCH_PROTECTION.md) and [docs/testing/PHASE_20_5_CI_GATES.md](docs/testing/PHASE_20_5_CI_GATES.md) (items 20.5.10, 20.5.2).

### Done when

- A red CI run on a PR **cannot** be merged into `stage` until fixed.

---

## Other items already tracked elsewhere

For enterprise features (org tenancy, full federated ML, K8s, etc.), see:

- [docs/enterprise/IMPROVEMENT_BACKLOG.md](docs/enterprise/IMPROVEMENT_BACKLOG.md)  
- [docs/testing/professional_standard.md](docs/testing/professional_standard.md)  

---

## 4. June 2026 cleanup audit (deleted files review)

Commits `c5fef02` (phase 1) and `6cfbc62` (phase 2) removed ~7.5k lines. Most removals were **safe** (orphans, duplicates, draft logos). This section records what mattered and what we did.

| Deleted item | Impact today? | Action |
|--------------|---------------|--------|
| `backend/app/aws/*` | **None** — empty stubs; logic lives in `cost/`, `storage/`, `vm/` | Keep deleted |
| `auth_controller.py`, `auth_service.py.save` | **None** — unused / backup | Keep deleted |
| `Footer.jsx` (old path) | **None** — replaced by `components/layout/Footer.jsx` | Keep deleted |
| `Enable2FA.jsx` | **None** — 2FA UI lives in `SecurityPage.jsx` | Keep deleted |
| `AdminDashboardPage.jsx` + `admin-dashboard.css` | **None** — replaced by `pages/admin/*` | Keep deleted |
| `login.css`, `register.css`, `secure-upload.css` | **None** — styles merged into page/global CSS | Keep deleted |
| `CostAnalysisPage.jsx` | **None** — router uses `CostAnalysisEnhancedPage.jsx` | Keep deleted |
| `ByocStorageTargetBanner.jsx` | **UX** — showed BYOC vs platform bucket; API still exists | **Restored** + wired to Storage & Security |
| `GlassPanel.jsx` | **Design system** — CSS class still used | **Restored** (thin wrapper) |
| `DEPLOYMENT_GUIDE.md` | **Docs** — superseded by `PRODUCTION_DEPLOYMENT_GUIDE.md` | Keep deleted; index points to production guide |
| `PROFESSIONAL_IMPROVEMENTS.md` | **Docs** — many links in ai-docs | **Stub redirect** at repo root |
| `GCP_DEMO_SETUP.md` | **Docs** — VM demo setup | **Restored** under `docs/development/` |
| `start_backend_test.sh` | **Dev UX** — quick demo-mode backend | **Restored** (uses `scripts/dev-common.sh`) |
| Dev scripts (`check_demo_mode.sh`, etc.) | **Low** — optional; use pytest + `DEMO_MODE` in `.env` | Not restored (avoid clutter) |
| PDFs, draft Logos, `NOTIFICATION_*.md` | **None** for runtime | Keep deleted |
| `frontend/public/*.svg` duplicates | **None** — brand from `assets/brand/` + `generate-brand-assets.mjs` | Keep deleted |

**Full detail:** [docs/CLEANUP_AUDIT.md](docs/CLEANUP_AUDIT.md)

---

## Completed (move items here when done)

| Date | Item | Notes |
|------|------|--------|
| — | — | — |
