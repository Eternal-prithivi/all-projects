# AI_RULES.md — Hard Constraints & Development Standards

> These rules are non-negotiable. Read before writing any code.
> Last Updated: 2026-05-25

---

## ⚖️ CONFLICT RESOLUTION PROTOCOL

**When the task instruction contradicts something in DECISIONS.md, AI_RULES.md, or any other ai-docs file — do NOT silently pick one. Follow this priority order:**

### Priority (highest → lowest)
| Priority | Source | Example |
|----------|--------|---------|
| 1 — Highest | `AI_RULES.md` hard constraints | "Never commit .env", "No paid services" |
| 2 | `DECISIONS.md` architectural decisions | "Never merge files and secure_files collections" |
| 3 | Module-level `# DO NOT:` comments in source files | "Don't remove require_2fa() from security routes" |
| 4 | Task instruction (what the user asked for) | "Refactor the storage routes" |

### What to do when there's a conflict
- **If the task directly contradicts Priority 1 or 2:** → **STOP.** State the conflict clearly. List what the task asks for vs. what the rule says. Ask the user to confirm before proceeding.
- **If the task contradicts Priority 3 (file-level DO NOT):** → **Flag it first.** Briefly explain the conflict in 1–2 lines. Then ask: *"Should I proceed and override this rule, or find a different approach?"*
- **If two doc files contradict each other:** → State the conflict, say which one you're following and why, then proceed.

### Example conflicts to watch for
- Task says *"refactor SecurityPage to use apiClient"* → conflicts with `AI_RULES.md §Known Pattern Deviation`. → Flag it.
- Task says *"merge files and secure_files into one collection"* → conflicts with `DECISIONS.md` rule. → Stop and ask.
- Task says *"add a Redis cache"* → conflicts with Zero-Cost Budget Constraint. → Stop and ask.
- Task says *"remove the /auth legacy alias"* → conflicts with `main.py` DO NOT comment. → Flag it.

### What NOT to do
- ❌ Do NOT silently pick the task over the rule
- ❌ Do NOT silently pick the rule and do something different than asked
- ❌ Do NOT assume the user knows about the conflict — they may not
- ✅ Always surface the conflict explicitly before taking action

---


## 🖥️ CRITICAL: Machine Resource Limit

**The dev machine has 18GB RAM. Max 2 concurrent heavy background tasks at any time.**
- Heavy tasks: `pip install`, `uvicorn`, `npm install`, `pytest` on large suites, `celery worker`
- Light tasks (safe to run in parallel): `grep`, `curl`, `cat`, file reads, `ls`
- Running 4+ heavy tasks simultaneously crashed the machine on 2026-05-23 — do not repeat this.
- When in doubt, run tasks sequentially and wait for each to complete.

---

## 💰 CRITICAL: Zero-Cost Budget Constraint

**The developer is a student with NO budget.** All implementation decisions MUST prioritize free-tier services:
- **AWS Free Tier**: S3 (5GB), Lambda (1M requests), STS (free), IAM (free)
- **GCP Free Tier**: Compute (e2-micro), Cloud Storage (5GB), 1M API calls
- **MongoDB Atlas**: Free M0 cluster (512MB)
- **CloudAMQP**: Free plan (1M messages/month)
- **No paid services** unless explicitly approved by the user
- **Avoid** Redis (use MongoDB or in-memory caching), paid monitoring (use logs), paid email services (use Gmail SMTP)
- **Avoid** S3 Event Notifications → SNS/SQS (requires public endpoint + costs). Use on-demand sync instead.
- **Terraform provisioning**: Default budget $1/month, all templates use free-tier resources. Policy engine blocks non-free-tier instance types.

## 📉 Token & Doc Discipline (anti-waste)

| Rule | Why |
|------|-----|
| ❌ Do not re-read `AI_MASTER.md` every message | Once per Cursor thread; Tier A = `STATUS` + `SCRATCHPAD` only |
| ❌ Do not read `AUDIT_LOG.md` or `PROGRESS_HISTORY.md` at startup | Append-only; use `STATUS` for live state |
| ❌ Do not paste long session narratives in chat | ≤5 bullets to user; detail → `PROGRESS_HISTORY.md` |
| ❌ Do not duplicate narratives in `PROGRESS.md` | Active task + checklist only |
| ✅ Use **Lightweight PRE/POST** for one-file trivial fixes | See `AI_MASTER.md` — skip claim rewrite + skip audit/history |
| ✅ **PRE writes tracking docs before code** | `STATUS` + `PROGRESS` + `SCRATCHPAD` (+ phase doc) — not only at session end |
| ✅ **`git commit` + `git push` after Full POST** | When product code or `ai-docs/` changed — backup to GitHub; skip only if user said no push or no changes |

---

## ❌ What NOT to Do

| Rule | Why |
|------|-----|
| ❌ No broad refactors unless explicitly requested | Preserve existing architecture |
| ❌ No hardcoded credentials or secrets | Real keys exist in `backend/.env` — use pydantic_settings only |
| ❌ No destructive git operations without permission | Protect history |
| ❌ No `var` in JavaScript | Use `const`/`let` only |
| ❌ No leaving TODO comments untracked | Add to `PROGRESS.md` backlog |
| ❌ No skipping session-end protocol | Continuity breaks without it |
| ❌ No modifying existing AUDIT_LOG entries | Append only — log is immutable |
| ❌ No bypassing Pydantic validation in FastAPI routes | All inputs must be validated models |
| ❌ No direct MongoDB calls outside proper modules | Use `mongo_client.py` helpers or create new collection getters |
| ❌ No changing the "Zenith" branding without asking | FastAPI title, sidebar, 2FA issuer all use "Zenith" |
| ❌ No removing empty stub files without user permission | They represent planned architecture — some will be rebuilt per the report |
| ❌ No committing `backend/.env` | It contains cloud credentials — NEVER commit |
| ❌ No deviating from the project report architecture | The 97-page report is the source of truth for missing modules |
| ❌ No implementing ML/VM/Cost modules without checking report first | Report sections §4.1-§4.5 describe exact algorithms, inputs, outputs |
| ❌ No installing new `pip` or `npm` packages without telling the user | State the package name and reason BEFORE installing — user must approve paid or heavy dependencies |
| ❌ Never assume a service is running or a package is installed | Always verify: check venv is active, backend is up, Celery is running, etc. before writing code that depends on them |
| ❌ **No writing code before claiming the task in STATUS.md + PROGRESS.md + SCRATCHPAD.md** | Mid-task handoff requires IN PROGRESS in docs. See AI_MASTER.md Step 3. |
| ❌ No adding new API routes without updating `ai-docs/AI_CONTEXT_BACKEND.md` routes table | Other agents use that table to know what endpoints exist — stale table causes duplicate routes |
| ❌ No adding new frontend pages/components without updating `ai-docs/AI_CONTEXT_FRONTEND.md` | Same reason — the context files are the living map of the codebase |

## 🧭 Product-Readiness Definitions

- Form validation means validating user-entered fields inside the app before submit, plus matching backend checks. It does not mean embedding Google Forms or another third-party form product unless the user explicitly asks for that.
- Treat CI/CD and testing work as future backlog items until `PROGRESS.md` marks them complete. Do not imply those pipelines or tests exist if they have not been added yet.
- For any new form, implement required checks, format/range validation, inline error messaging, disabled submit states while invalid, and server-side validation parity.

---


## ✅ Backend Rules (FastAPI / Python)

### Code Style
- Python 3.10+ syntax
- Type hints on all function signatures
- Use `async def` for all route handlers
- Use Pydantic models for all request/response schemas
- Use `pydantic_settings.BaseSettings` for env config (the `Settings` class in `utils/config.py`)
- All business logic in `app/<module>/` — not inline in routes

### Auth
- JWT created with `python-jose`, algorithm HS256
- Password hashing: `passlib.CryptContext(schemes=["bcrypt"])`
- Token URL: `/api/auth/token` (OAuth2PasswordRequestForm)
- Token payload: `{"sub": username}`
- `get_current_user()` dependency in `auth_utils.py` — use this for protected endpoints
- `require_2fa()` dependency — use this for security endpoints

### Database
- All DB access through `app/database/mongo_client.py` or collection getter functions
- Singleton pattern: `mongodb_client = MongoDB()` created at module level
- Collection getters: `get_users_collection()`, `get_files_collection()`, `get_secure_files_collection()`
- Celery tasks MUST create their OWN MongoClient inside the task (fork safety)
- Database name: `CloudResourceOptimizationDB`
- **Active collections:** `users`, `files`, `secure_files`, `ml_predictions`, `ml_workload_descriptions`, `admin_actions`, `activity_log`, `vm_assignments`, `vm_metrics`, `cost_data`, `ml_feedback_snapshots`, `storage_lifecycle_reports`, `budgets`, `byoc_credentials`, `provision_deployments`

### Celery Tasks
- Tasks defined in `app/storage/tasks.py` and `app/storage/tiering_tasks.py`
- Celery app config in `app/celery_worker.py`
- Tasks must create their own boto3 and MongoClient instances (no sharing across forks)
- Tasks must be idempotent
- Beat schedule: nightly at 00:00 UTC (storage), plus daily drift check at 06:00 UTC (provisioning)
- After task completes: call `POST /ws/notify/{user_id}` to push WebSocket update

### Multi-Cloud Storage
- Upload functions in `app/storage/uploader.py` (upload_to_aws, upload_to_gcp, upload_to_azure)
- Download/delete/tier-change in `app/storage/manager.py`
- Optimizer scoring in `app/storage/optimizer.py` — **currently ONLY rule-based (Expert #1)**
- **ML Experts #2 (Random Forest) and #3 (XGBoost) must be rebuilt** — see report §4.2
- All three CSPs (AWS, GCP, Azure) use different APIs — follow existing patterns
- AWS: `boto3.client('s3')`, GCP: `google-cloud-storage`, Azure: `BlobServiceClient`

### S3 Buckets (3 buckets total)
| Bucket | Purpose | Config Key |
|--------|---------|------------|
| `zeneith-storage-bucket` | Standard multi-cloud file storage | `S3_BUCKET_NAME` |
| `zenith-secure-files` | 2FA-protected secure uploads | `SECURE_S3_BUCKET_NAME` |
| `zeneith-secure-files-secondary2` | Encrypted file replication backup | `REPLICA_S3_BUCKET_NAME` |

---

## ✅ Frontend Rules (React / Vite)

### Code Style
- Use functional components only (no class components)
- Use hooks for state and side effects
- Use `async/await` — no raw `.then()` chains
- Component files: PascalCase (`UserCard.jsx`)
- Hook files: camelCase prefixed with `use` (`useAuth.js`)

### Known Pattern Deviation: SecurityPage Only
- `SecurityPage.jsx` still has its **own inline API functions** using raw `fetch()` instead of `api.js`
- **When modifying SecurityPage**: follow the existing inline pattern OR refactor to use `api.js` + `AuthContext` (if user requests)
- **StoragePage.jsx is now fixed**: it uses real `AuthContext` and `api.js` — the old `"tanjiro"` mock was removed
- **When creating NEW pages**: always use the centralized `api.js` + `AuthContext` pattern


### Routing
- All routes defined in `main.jsx` via `createBrowserRouter`
- Protected routes wrapped in `<ProtectedRoute>` which checks `useAuth().isAuthenticated`
- Dashboard area uses `<DashboardLayout>` with `<Outlet>` for nested routes
- **All major routes are now built:** `/dashboard/costs`, `/dashboard/vmcluster`, `/dashboard/storage`, `/dashboard/security`, `/dashboard/billing`, `/dashboard/settings`, `/dashboard/profile`, `/dashboard/security-settings` all exist
- Admin panel at `/admin/*` — role-guarded via `AdminLayout`
- Public pages: `/`, `/login`, `/register`, `/forgot-password`, `/reset-password`, `/contact`, `/about`, `/features`, `/help`, `/legal/terms`, `/legal/privacy`

### State Management
- Auth state: React Context (`AuthContext.jsx`) — token in localStorage
- No Redux, no Zustand

### Styling
- CSS files in `frontend/src/styles/`
- SecurityPage uses inline CSS-in-JS (a `pageStyles` template string injected via `<style>` tag)
- Follow whatever pattern the page already uses

---

## 💬 Task Completion Response Format (Token Efficiency Rule)

After completing ANY task, provide exactly this — nothing more unless asked:

```
✅ Changed:  [one line — what file/feature was changed]
📌 Why:      [one line — reason for the change]
🧪 Test:     [one line — what to run or click to verify it works]
```

**Do NOT** write:
- Paragraph summaries of what you did
- Lists of every file you touched
- Explanations of how the code works
- "Let me know if you have any questions"

> The user will ask follow-up questions if they need more. Unsolicited explanation wastes tokens.

---

## ✅ Quality Gates

### Backend
```bash
cd backend
source .venv/bin/activate       # venv is at backend/.venv, NOT project root venv/
python -m pytest -q             # 34 tests as of 2026-05-25
```

### Frontend
```bash
cd frontend
npm run lint                    # ESLint check — target: 0 errors
npm run build                   # Vite production build — must pass
```

### ❌ Failure Instructions (mandatory)

| Gate fails | What to do |
|------------|-----------|
| `pytest` fails | Fix the failing test(s) **before ending the session**. Do NOT mark the task complete. Do NOT leave broken tests. |
| `npm run build` fails | Fix the build error **before ending the session**. Do NOT mark the task complete. |
| `npm run lint` has errors | Fix all lint **errors** before ending the session. Warnings are acceptable if pre-existing. |
| Cannot fix in current session | Write the exact failure message in `SCRATCHPAD.md` → Resume State. Mark task as `Partial` in `AUDIT_LOG.md`. Tell the user explicitly. |

> ⚠️ **A task is NOT done until all quality gates pass.** "It works locally" is not a quality gate.

### Checklist Before Every Session End

**Full POST-PHASE** (normal tasks):
- [ ] No `.env` files committed
- [ ] `STATUS.md` + `PROGRESS.md` updated (match PRE claim → COMPLETE or partial resume)
- [ ] Phase/theme doc `## Current session` closed or cleared
- [ ] Long narrative → `PROGRESS_HISTORY.md` (not chat / not PROGRESS)
- [ ] `AUDIT_LOG.md` entry appended (≤5 bullets) — append only, never required to read
- [ ] `SCRATCHPAD.md` = `COMPLETE` or explicit `NOT YET DONE` resume steps
- [ ] `git commit` + `git push` (branch e.g. `stage`) — report hash in chat
- [ ] Chat summary ≤5 bullets

**Lightweight POST-PHASE** (trivial one-file fix): lint/test if needed; skip AUDIT_LOG + PROGRESS_HISTORY unless user asked

---

## 🏛 Architecture Decisions to Preserve

1. **Monorepo layout** — `frontend/` and `backend/` are separate; don't merge them
2. **FastAPI for backend** — do NOT introduce Flask or Django
3. **MongoDB Atlas as primary DB** — no SQL migration
4. **Celery + CloudAMQP for async tasks** — do NOT use background threads
5. **JWT stateless auth** — no server-side sessions (but session tracking per report §4.4.4)
6. **React 19 + Vite** — do NOT downgrade or switch bundler
7. **Multi-cloud storage** — AWS, GCP, Azure treated equally via uploader/manager pattern
8. **2FA gate on security routes** — `require_2fa` dependency must be used on all security endpoints
9. **Separate `files` and `secure_files` MongoDB collections** — do NOT merge them
10. **Ensemble ML architecture** — Rule-based (30%) + Random Forest (35%) + XGBoost (35%) weighted voting — per report §4.2
11. **NLP workload classification** — TextBlob + spaCy + custom tech dictionaries — per report §4.1
12. **VM cluster types** — General, Storage, Memory, Performance, AI/ML with tier sizing (Micro/Small/Medium/Standard) — per report §4.3
13. **Feedback-driven retraining** — closed-loop with outcome evaluation, quality filtering, conservative deployment — per report §4.5
14. **Defense-in-depth security** — scanning + dual encryption + 2FA + replication + session management + audit logging — per report §4.4

---

## 📄 Reference Document

The **project report** (`Major Project latest22- Report-5.pdf`, 97 pages) is the authoritative specification for:
- **§4.1** — NLP-Enhanced Workload Classification (TextBlob, spaCy, tech dictionaries, negation detection)
- **§4.2** — Ensemble ML Storage Tier Prediction (Rule-based + RF + XGBoost, weighted voting)
- **§4.3** — VM Lifecycle Management (auto-scaling, migration, priority scoring)
- **§4.4** — Multi-Layered Security (scanning, encryption, 2FA, session management, audit logs)
- **§4.5** — Feedback-Driven Model Retraining (outcome evaluation, quality filtering, conservative deployment)
- **§5.9** — Infrastructure specs (FastAPI, MongoDB Atlas M10, Redis, Celery, React 19)

Always check the report before implementing any missing module.

---

## 🗄️ Storage Architecture — Important Notes

### How file tracking works
- Files uploaded via Zenith → stored in S3/GCP/Azure → **metadata saved to MongoDB `files` or `secure_files` collection**
- Storage page reads from **MongoDB only**, NOT directly from the cloud bucket
- If a user adds files directly to their bucket (outside Zenith), **Zenith will NOT show them**

### Planned: "Sync with Bucket" feature
- Add a "Sync" button on Storage page that calls `s3.list_objects_v2()` → compares with MongoDB → reconciles
- S3 LIST requests are effectively free (~$0.005/1000 requests)
- No background workers needed (no Celery cost)
- This is the free-tier-friendly approach — do NOT use S3 Event Notifications + SNS (requires public endpoint + costs money)

### Old data cleanup (2026-05-24)
- All old `files` (5 records) and `secure_files` (2 records) from terminated AWS/GCP accounts were deleted
- Both collections are now empty — fresh start for new accounts
