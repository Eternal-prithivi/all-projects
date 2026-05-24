# AI_MASTER.md — Mandatory Startup Protocol

> ⚡ Every AI agent MUST read this file first. No exceptions. No code before reading.

---

## 🚀 Startup Flow (Run Every Session)

### Step 1 — Read These Files in Order
All files are in the `ai-docs/` folder:
```
1. ai-docs/AI_MASTER.md        ← you are here
2. ai-docs/AI_CONTEXT.md       ← full architecture + tech stack + every module
3. ai-docs/AI_RULES.md         ← constraints + what not to do
4. ai-docs/PROGRESS.md         ← current task + what's done + backlog + RECOVERY ROADMAP
5. ai-docs/SCRATCHPAD.md       ← mid-task resume state (if any)
```

### Step 2 — Check Active Task
- Open `PROGRESS.md` → find `## 🔴 Active Task`
- If there is one → resume it using notes in `SCRATCHPAD.md`
- If none → ask the user what to work on next

### Step 3 — Confirm Before Starting
Say: _"Loaded context. Current task: [task]. Ready to proceed."_

---

## 🔄 Session End Protocol (Required Before Stopping)

Every session MUST end with:
```
[ ] PROGRESS.md updated — task status, what was done, what's next
[ ] AUDIT_LOG.md appended — new entry with SESSION_ID + summary
[ ] SCRATCHPAD.md updated — resume instructions OR cleared if task complete
[ ] Quality gates passed (lint + tests if applicable)
```

---

## 🏗 Project Identity
| Field         | Value                                                              |
|---------------|--------------------------------------------------------------------| 
| Project       | CloudResourceOptimizationPlatform (branded as **Zenith**)          |
| Type          | Monorepo — React 19 Frontend + FastAPI Backend                     |
| Purpose       | Multi-cloud resource optimization: intelligent storage tiering, VM cluster management, NLP workload classification, cost analysis, 2FA-secured file handling, ML-driven predictions |
| Cloud Targets | AWS (primary), GCP, Azure — multi-cloud storage + compute          |
| Database      | MongoDB Atlas (`CloudResourceOptimizationDB`)                      |
| Task Queue    | Celery + CloudAMQP (RabbitMQ)                                     |
| Phase         | **PHASE 3 COMPLETE** — Settings functional (theme, preferences, billing). Next: Phase 4 (Platform Features). |
| Budget        | **ZERO-COST** — Student project. Free-tier only. See `AI_RULES.md` for details. |
| Reference Doc | `Major Project latest22- Report-5.pdf` (97-page report describes full intended system) |
| Last Updated  | 2026-05-24                                                        |

---

## 🚨 CRITICAL: Project Recovery Context

**What happened:** The developer's laptop was repaired, causing data loss. The current codebase is INCOMPLETE compared to what the project report describes. A full gap analysis was performed on 2026-05-23. Recovery Phase 1 & 2 are complete.

**Recovery approach:** Get existing features running first (Done), then rebuild missing modules one by one to match the report. Phase 1 (UI Polish), Phase 2 (Backend/BYOC), Phase 2.5 (Mission Control Dashboard), and Phase 3 (Settings Functionality) are all complete. See `PROGRESS.md` for full roadmap.

### What WORKS (exists in code):
- Auth (JWT + 2FA), BYOC (Bring Your Own Cloud via IAM/STS), Multi-cloud storage (AWS/GCP/Azure), Rule-based tier optimizer, Celery tiering tasks, Secure file vault, WebSocket notifications, Frontend (Home/Login/Register/Dashboard/Storage/Security/Settings/404 pages). API is fully verified (25/25 endpoints passing).

### What's MISSING (described in report, no code exists):
- **`app/vm/` module** — VM cluster management, NLP-based assignment, auto-scaling
- **`app/cost/` module** — Cost analysis, cost breakdown by CSP
- **ML Ensemble Pipeline** — Random Forest + XGBoost ensemble (89.3% accuracy target)
- **NLP Classification** — TextBlob + spaCy workload description parsing
- **Feedback-Driven Retraining** — Continuous learning loop with outcome evaluation
- **Redis cache layer** — Not in requirements or code
- **Database indexes** — `ensure_indexes()` function missing
- **Session management + activity logging** — Described in report but not implemented

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
| `ai-docs/AI_MASTER.md`             | This file — startup protocol       |
| `ai-docs/AI_CONTEXT.md`            | Architecture, tech stack, folder map, every module's purpose |
| `ai-docs/AI_RULES.md`              | Hard constraints + code standards  |
| `ai-docs/AI_SYSTEM_PROMPT.md`      | Quality prompt for AI sessions     |
| `ai-docs/PROGRESS.md`              | Task tracker — what's done/next + RECOVERY ROADMAP |
| `ai-docs/SCRATCHPAD.md`            | Mid-task resume state              |
| `ai-docs/AUDIT_LOG.md`             | Per-session activity log           |
| `ai-docs/AGENT_SESSION_TEMPLATE.md`| Template for AUDIT_LOG entries     |
| `ai-docs/DECISIONS.md`             | Architecture decisions log         |
| `ai-docs/DESIGN_SYSTEM.md`         | Styling rules, design tokens, Mission Control layout specs (bento grid, nav rail, charts) |
| `Major Project latest22- Report-5.pdf` | Full project report (97 pages) — stays in project root |

---

## 🤖 How to Start a New AI Chat

Paste this at the start of every new AI session:

```
Continue CloudResourceOptimizationPlatform (Zenith) — IMPLEMENTATION MODE.
Read ai-docs/AI_MASTER.md and follow the startup protocol.
Current task: [describe task or say "check ai-docs/PROGRESS.md"].
Follow ai-docs/AI_RULES.md at all times.
Reference: The 97-page project report describes the full intended system. ai-docs/PROGRESS.md has the roadmap.
```

---

## ⚠️ Critical Warnings

1. **The app is branded "Zenith"** — the FastAPI title is `"Zenith API"`, sidebar says `"Zenith"`, 2FA issuer is `"ZenithApp"`. Do NOT change branding without asking.
2. **MAJOR MODULES ARE MISSING** — `app/vm/`, `app/cost/`, ML ensemble pipeline, NLP classification — these must be REBUILT to match the project report.
3. **Many backend modules are empty stubs** — `aws/`, `ml/`, `providers/`, `queue/`, `errors/`, plus several more. See AI_CONTEXT.md and PROGRESS.md for full list.
4. **StoragePage.jsx and SecurityPage.jsx have their own inline API functions** — they do NOT use the centralized `api.js`. This is a known pattern deviation. See AI_CONTEXT.md.
5. **Credentials in `backend/.env` are STALE** — old accounts terminated. New credentials must be created for all services. NEVER expose credentials.
6. **The `.env` was committed to Git** in the first commit — if the repo is public, old credentials were exposed. Must be rotated.
7. **The report's `main.py` shows `routes_vm`, `routes_cost`, `routes_ml`** — these modules never existed in Git. They must be built from scratch based on the report.

