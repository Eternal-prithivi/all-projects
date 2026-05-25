# AI_MASTER.md — Mandatory Startup Protocol

> ⚡ Every AI agent MUST read this file first. No exceptions. No code before reading.

---

## 🚀 Startup Flow (Run Every Session)

### Step 1 — Read These Files in Order
All files are in the `ai-docs/` folder:
```
1. ai-docs/AI_MASTER.md        ← you are here (includes project summary + context routing)
2. ai-docs/AI_RULES.md         ← constraints + what not to do (resource limits + zero-cost rules)
3. ai-docs/PROGRESS.md         ← current task + standing anti-tasks + backlog
4. ai-docs/SCRATCHPAD.md       ← Last Known Good State + mid-task resume state
5. ai-docs/DECISIONS.md        ← WHY architecture is the way it is (Before You Code checklist at top)
```

### Step 1b — Pick Your Context File (based on task type)
```
Frontend, UI, CSS, components, pages, routing  →  ai-docs/AI_CONTEXT_FRONTEND.md
Backend, API routes, database, Celery, ML, auth →  ai-docs/AI_CONTEXT_BACKEND.md
Full-stack task touching both                   →  read both
```

### Step 2 — Check Active Task
- Open `PROGRESS.md` → find `## 🔴 Active Task`
- If there is one → resume it using notes in `SCRATCHPAD.md`
  - **If SCRATCHPAD has no resume notes for that task:** re-read the task description in PROGRESS.md, check which files it mentioned, then ask the user: *"I see an active task but no resume notes. Should I start fresh or do you want to describe where to pick up?"*
- If none → ask the user what to work on next

### Step 3 — Mandatory Onboarding Confirmation (before touching ANY code)

**Output this exact block before writing or editing a single file:**

```
📋 CONTEXT LOADED
─────────────────────────────────────────
Phase:           [Current project phase from AI_MASTER.md]
Last completed:  [Last completed task from PROGRESS.md]
Active task:     [What you're about to work on]
Active constraint: [One relevant rule from AI_RULES.md that applies to this task]
Conflicts found: [Any conflict between the task and the docs — or write "None detected"]
─────────────────────────────────────────
```

> This is not optional. If an agent skips this block, context was not loaded correctly.
> The user can reject any work done by an agent that skipped this step.


---

## 🔄 Session End Protocol (Required Before Stopping)

Every session MUST end with ALL of the following — in this order:

```
[ ] 1. Quality gates passed (lint + tests if applicable)
[ ] 2. PROGRESS.md updated — task status, what was done, what's next
[ ] 3. AUDIT_LOG.md appended — new entry with SESSION_ID + summary
[ ] 4. SCRATCHPAD.md updated — resume instructions OR cleared if task complete
[ ] 5. Git commit + push to stage branch
```

### Step 5 — Git Commit & Push (exact commands)

```bash
# From project root
git add ai-docs/ backend/ frontend/src/ docs/ render.yaml PROFESSIONAL_IMPROVEMENTS.md

# Verify no .env or secrets staged
git diff --cached --name-only | grep -E "\.env|secret|zenith-backend" && echo "⛔ STOP — sensitive file staged" || echo "✅ Safe to commit"

# Commit with a descriptive message
git commit -m "feat/fix/docs: [short description of what was done]

- [bullet 1: main change]
- [bullet 2: files changed]
- [bullet 3: outcome/test result]"

# Push to stage branch
git push origin stage
```

### Commit message rules
- Prefix: `feat:` (new feature), `fix:` (bug fix), `docs:` (docs only), `chore:` (cleanup)
- First line: max 72 characters
- Body: bullet list of what changed and why
- **NEVER** include `.env`, `node_modules/`, `zenith-backend.env`, or `*.backup` in the commit

### If push fails
- Check `git remote -v` — remote should be `https://github.com/Eternal-prithivi/all-projects.git`
- If auth fails: user needs to re-authenticate GitHub credentials locally
- Do NOT force-push — always use `git push origin stage` (no `--force`)


## 🏗 Project Identity
| Field         | Value                                                              |
|---------------|--------------------------------------------------------------------| 
| Project       | CloudResourceOptimizationPlatform (branded as **Zenith**)          |
| Type          | Monorepo — React 19 Frontend + FastAPI Backend                     |
| Purpose       | Multi-cloud resource optimization: intelligent storage tiering, VM cluster management, NLP workload classification, cost analysis, 2FA-secured file handling, ML-driven predictions |
| Cloud Targets | AWS (primary), GCP, Azure — multi-cloud storage + compute          |
| Database      | MongoDB Atlas (`CloudResourceOptimizationDB`)                      |
| Task Queue    | Celery + CloudAMQP (RabbitMQ)                                     |
| Phase         | **PHASE 10 COMPLETE** — Report-aligned VM taxonomy, decay-weighted cost forecast, ML feedback loop, benchmark script, frontend UI polish, and final handoff. |
| Budget        | **ZERO-COST** — Student project. Free-tier only. See `AI_RULES.md` for details. |
| Reference Doc | `Major Project latest22- Report-5.pdf` (97-page report describes full intended system) |
| Last Updated  | 2026-05-25                                                        |

### Quick Tech Facts
- **Frontend:** React 19 + Vite 7, 60+ pages, glassmorphic Mission Control dashboard
- **Backend:** FastAPI + Python, 25 route files, 16 routers, Celery background tasks
- **Database:** MongoDB Atlas (`CloudResourceOptimizationDB`), 14 collections
- **Auth:** JWT (HS256), bcrypt, 2FA TOTP (issuer: `ZenithApp`)
- **ML:** RF+XGBoost storage ensemble, NLP VM workload classifier, guarded self-retraining
- **Queue:** Celery + CloudAMQP (RabbitMQ)
- **Cloud:** AWS S3 (primary), GCP Cloud Storage, Azure Blob Storage
- Venv at `backend/.venv/` — NOT project root
- Language: Python 3.x backend, JavaScript (JSX) frontend — NOT TypeScript
- Tests: 34 backend (`python -m pytest -q`), lint: 0 errors
- CORS: `allow_origins=["*"]` — restrict before public deployment

---

## 🚨 CRITICAL: Project Recovery Context

**What happened:** The developer's laptop was repaired, causing data loss. The codebase was incomplete compared to the project report. A full gap analysis was performed on 2026-05-23, and recovery work has rebuilt the major report modules through Phase 9.

**Recovery approach:** Get existing features running first (Done), then rebuild missing modules one by one to match the report. Phases 1-9 are core complete. See `PROGRESS.md` for the current roadmap and remaining hardening work.

### What WORKS (exists in code):
- Auth (JWT + 2FA), BYOC (Bring Your Own Cloud via IAM/STS), Multi-cloud storage (AWS/GCP/Azure), ensemble storage tiering, Celery tiering/feedback/security tasks, secure file vault, WebSocket notifications, VM workload NLP classification, five-cluster VM assignment, cost analysis/forecast/anomaly APIs, dashboard/settings/profile/security UX, and benchmark validation scripts.

### Remaining Report Gaps / Hardening:
- Optional real model artifact retraining/hot-swap after enough feedback data exists.
- Larger benchmark datasets from real cloud/user telemetry instead of mostly synthetic validation.
- Final demo runbook, screenshots, and end-to-end handoff verification.
- Redis cache layer remains optional; current Celery broker is CloudAMQP, not Redis.
- Production security hardening remains: rotate exposed/stale credentials and restrict CORS before public deployment.

### What's BROKEN (needs fixing before running):
- ~~Python venv has NO packages installed (only pip)~~ (Fixed)
- ~~All cloud credentials are stale/expired~~ (MongoDB, CloudAMQP, Gmail fixed. AWS/GCP/Azure pending individual user setup)
- ~~GCP key file path is wrong~~ (Fixed)
- ~~Settings UI toggles (Theme, notifications, currency) save to DB but currently have no effect~~ (Fixed in Phase 3 — ThemeContext, PreferencesContext, and Coming Soon badges added).

---

## 📁 File Directory

All AI context files live in the **`ai-docs/`** folder at the project root:

| File                       | Purpose                            |
|----------------------------|------------------------------------| 
| `ai-docs/AI_MASTER.md`             | This file — startup protocol + project summary + context routing |
| `ai-docs/AI_CONTEXT_FRONTEND.md`   | Frontend: pages, components, contexts, routing, CSS system |
| `ai-docs/AI_CONTEXT_BACKEND.md`    | Backend: routes, modules, MongoDB, ML, Celery, env vars |
| `ai-docs/AI_RULES.md`              | Hard constraints + code standards + resource limits |
| `ai-docs/PROGRESS.md`              | Task tracker — standing anti-tasks + active task + backlog |
| `ai-docs/SCRATCHPAD.md`            | Last Known Good State + mid-task resume state |
| `ai-docs/AUDIT_LOG.md`             | Per-session activity log (append-only, immutable) |
| `ai-docs/DECISIONS.md`             | Architecture decisions — Before You Code checklist at top |
| `ai-docs/DESIGN_SYSTEM.md`         | Styling rules, design tokens, Mission Control layout — read before any UI work |
| `Major Project latest22- Report-5.pdf` | Full project report (97 pages) — stays in project root |

---

## 🤖 How to Start a New AI Session

Paste this at the start of every new AI session:

```
Continue CloudResourceOptimizationPlatform (Zenith) — IMPLEMENTATION MODE.

Read ai-docs/AI_MASTER.md and follow the startup protocol exactly.
Also read ai-docs/PROGRESS.md and ai-docs/SCRATCHPAD.md.

Current task: [describe task here]
─── OR ─── check ai-docs/PROGRESS.md and ai-docs/SCRATCHPAD.md and resume from where the last agent left off.

Based on the task above, decide the following before starting:
- If the task involves any frontend, UI, CSS, or components → read ai-docs/DESIGN_SYSTEM.md first.
- If the task involves any architectural, structural, or module-level changes → read ai-docs/DECISIONS.md first.
- If the task is to resume or continue from a previous session → treat ai-docs/SCRATCHPAD.md as your primary starting point.

Follow ai-docs/AI_RULES.md at all times. Do not skip the session-end protocol.
```

### ⚠️ Always scope your task (takes 30 seconds, saves 40% tokens):

Add these 3 lines to any task you describe:
```
Scope: [which pages/files are in scope — e.g. "DashboardPage and DashboardLayout only"]
Do NOT touch: [files explicitly out of scope — e.g. "SecurityPage.jsx, any ML files"]
Done when: [clear finish line — e.g. "build passes, feature works, no new lint errors"]
```

**Example of a well-scoped task:**
```
Current task: Add a loading skeleton to the VM Cluster page
Scope: VMClusterPage.jsx and vmcluster.css only
Do NOT touch: StoragePage.jsx, SecurityPage.jsx, any backend files
Done when: Skeleton shows while data loads, build passes, no new lint errors
```

### What the agent MUST do at session end (non-negotiable):
- `PROGRESS.md` — update task status and what was done
- `AUDIT_LOG.md` — append a new entry (SESSION_ID format: YYYYMMDD-HHMMSS)
- `SCRATCHPAD.md` — update Last Known Good State + clear or write resume state
- **If new backend routes were added this session** → update the API Routes table in `ai-docs/AI_CONTEXT_BACKEND.md`
- **If new frontend pages or components were added this session** → update the Pages/Components sections in `ai-docs/AI_CONTEXT_FRONTEND.md`


---

## ⚠️ Critical Warnings

1. ❌ **`backend/.env` contains live cloud credentials — NEVER commit it.** It was already committed in the first git push — rotate all credentials before making the repo public.
2. **The app is branded "Zenith"** — FastAPI title is `"Zenith API"`, sidebar says `"Zenith"`, 2FA issuer is `"ZenithApp"`. Do NOT change branding without asking.
3. **Empty stub files still exist** — `aws/`, `providers/`, `queue/`, `errors/`, and several others. Do NOT delete them — they represent planned architecture. See `AI_CONTEXT_BACKEND.md` for the full stub list.
4. **SecurityPage.jsx has its own inline API functions** — it does NOT use `api.js`. This is a known pattern deviation. See `AI_CONTEXT_FRONTEND.md`.
5. **`CORS allow_origins=["*"]`** in `main.py` — restrict before any public deployment.
6. **Venv is at `backend/.venv/`** — NOT `venv/` at the project root. Use `backend/.venv/bin/python` and `backend/.venv/bin/pytest`.
7. **`routes_auth.py` is mounted twice** (`/api/auth` and `/auth`) in `main.py` — legacy duplicate, the `/auth` alias can be removed if needed.
