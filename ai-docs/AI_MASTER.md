# AI_MASTER.md — Agent Protocol

> **This file is the rulebook, not the live state.**  
> Live phase, task, health → `STATUS.md` · Resume breadcrumbs → `SCRATCHPAD.md`  
> **Read this file once per Cursor thread** — then follow the phases from memory. Do **not** re-open it every message.

---

## Token discipline (anti-waste) — enforced

| Risk | Rule |
|------|------|
| Re-reading `AI_MASTER.md` every turn | **Once per thread only.** Tier A startup = `STATUS.md` + `SCRATCHPAD.md` only. |
| Reading `AUDIT_LOG.md` / `PROGRESS_HISTORY.md` at startup | **Forbidden** unless user says "debug continuity" or drift audit (count entries only — see `SCRATCHPAD.md`). |
| Long write-ups in chat | **Max 5 bullets** in the final reply; put detail in `PROGRESS_HISTORY.md` at POST-PHASE. |
| Long write-ups in `PROGRESS.md` | **Active task + checklist only** — narratives go to `PROGRESS_HISTORY.md`. |
| Full PRE-PHASE for trivial edits | Use **Lightweight path** below (1 file, no API/architecture/security). |

---

## Lifecycle (always in order)

```
PRE-PHASE  →  load context, claim task in docs, confirm — NO product code yet
EXECUTE    →  implement scoped work; follow AI_RULES.md when in doubt
POST-PHASE →  tests/lint, update docs, audit log — before you stop
```

**Golden rule:** No edits to `backend/`, `frontend/`, or `docs/` implementation files until PRE-PHASE is complete.

---

## PRE-PHASE — Before any task or code change

Use **Full PRE-PHASE** (below) for features, multi-file work, API/security/ML, or phase tasks.  
Use **Lightweight PRE-PHASE** for trivial single-file edits (see end of this section).

### 1. Load context (Tier A — every session)

| Read | When |
|------|------|
| `STATUS.md` | **Every session / every thread start** |
| `SCRATCHPAD.md` | **Every session / every thread start** |
| `AI_MASTER.md` | **First agent turn in thread only** — not on follow-up messages |

**Never read at startup:** `AUDIT_LOG.md`, `AUDIT_LOG_ARCHIVE_*.md`, `PROGRESS_HISTORY.md`, full `docs/`.

**Tier B** — read only if the task needs it (see routing table in `STATUS.md`):

- UI → `DESIGN_SYSTEM.md` + `AI_CONTEXT_FRONTEND.md`
- API/ML/DB → `AI_CONTEXT_BACKEND.md`
- Structure/architecture → `DECISIONS.md` (Before You Code checklist)
- Budget, conflicts, hard limits → `AI_RULES.md`
- Phase 12 security → `PHASE_12_SECURITY_RESEARCH_PARITY.md`

### 2. Resolve what you are doing

- If `STATUS.md` / `SCRATCHPAD.md` show **IN PROGRESS** → resume from first `NOT YET DONE` step in SCRATCHPAD.
- If active task exists but SCRATCHPAD is empty → read `PROGRESS.md` active section, then ask the user whether to resume or restart.
- If no active task → ask the user **or** use the task they gave in chat.

**Scope every task** (in chat and in docs):

```
Scope:       [files/pages in scope]
Do NOT touch: [explicit exclusions]
Done when:   [measurable finish line]
```

### 3. Claim the task in docs (mandatory before code)

Update these **before** touching product code:

| File | What to write |
|------|----------------|
| `STATUS.md` | Active task name, `IN PROGRESS`, started timestamp, scope / do-not / done-when |
| `PROGRESS.md` | Same under `## 🔴 Active Task` |
| `SCRATCHPAD.md` | `## 🔄 Current Resume State`: plan, files to touch, steps as `NOT YET DONE` |

**Example SCRATCHPAD step list:**

```
Status: IN PROGRESS (started: 2026-05-29 14:00)
Plan: Auto SSE on sensitive upload. Files: routes_security.py, SecurityPage.jsx
- [ ] Step 1: Default SSE path when scan hits — NOT YET DONE
- [ ] Step 2: Manual test upload — NOT YET DONE
- [ ] Step 3: Update STATUS + PROGRESS — NOT YET DONE
```

If resuming an existing **IN PROGRESS** task with valid SCRATCHPAD notes, you may skip rewriting claim text but must still output the confirmation block (step 4).

### 4. Confirm in chat (mandatory before code)

Output this block once per session (or once per new task):

```
📋 PRE-PHASE COMPLETE
─────────────────────────────────────────
Phase:            [from STATUS.md]
Active task:      [name + IN PROGRESS or resuming]
Scope / Done when:[one line each]
Docs updated:     STATUS + PROGRESS + SCRATCHPAD — [Done | Skipped — resuming]
Tier B loaded:    [files read, or "none needed"]
Conflicts:        [None | describe — see AI_RULES conflict protocol]
─────────────────────────────────────────
```

If the user’s request conflicts with `AI_RULES.md` or `DECISIONS.md`, **stop** and ask before EXECUTE.

### Lightweight PRE-PHASE (trivial changes only)

**Qualifies when ALL are true:**

- One file (or one line in one file): typo, comment, formatting, tiny bugfix
- No new routes, env vars, dependencies, security logic, or phase scope change
- User did not ask for a new feature or audit trail

**Do:**

1. Read Tier A only (`STATUS.md` + `SCRATCHPAD.md`) — do **not** re-read `AI_MASTER.md`
2. Do **not** rewrite `STATUS.md` / `PROGRESS.md` claim blocks if the active task is unchanged
3. One chat line instead of the full block: `Lightweight: [file] — [one-line intent]`
4. Proceed to EXECUTE

**Do not use Lightweight** for Phase 12 security, auth, BYOC, ML, Terraform, or multi-file refactors.

---

## EXECUTE — Implementation

- Stay inside **Scope**; do not expand unless the user agrees.
- Obey **Standing anti-tasks** in `STATUS.md`.
- New `pip` / `npm` packages → state name + reason; get approval if non-free or heavy.
- Max **2 concurrent heavy processes** on dev machine (pytest, uvicorn, npm install, celery) — see `AI_RULES.md`.

**Commands (reference):**

```bash
cd backend && .venv/bin/python -m pytest -q
cd frontend && npm run lint && npm run build
```

---

## POST-PHASE — After the task (before you stop)

Use **Full POST-PHASE** after normal tasks. Use **Lightweight POST-PHASE** only if you used Lightweight PRE-PHASE.

### Lightweight POST-PHASE

- [ ] Lint/test **only if** the file type requires it (JS → lint; Python logic → pytest)
- [ ] **Skip** `PROGRESS_HISTORY.md`, **skip** `AUDIT_LOG.md` unless user asked to log it
- [ ] **Skip** rewriting `STATUS.md` / `PROGRESS.md` if the active task did not change
- [ ] Optional: one-line note in `SCRATCHPAD.md` LKGS if verification mattered

### Full POST-PHASE

Run in order. Do not end the session with an incomplete checklist.

### 1. Quality gates

- [ ] Backend: `pytest` (if backend touched)
- [ ] Frontend: `npm run lint` (if frontend touched)
- [ ] Build passes if UI changed

### 2. Update docs

| File | Action |
|------|--------|
| `STATUS.md` | Task status, what’s done / open, refresh health row if you ran tests |
| `PROGRESS.md` | Match STATUS; update Phase checklist `[x]` / `[ ]` |
| `SCRATCHPAD.md` | If **complete**: `Status: COMPLETE`, clear step list, refresh **Last Known Good State**. If **partial**: update steps (`DONE` / `NOT YET DONE`) |
| `PROGRESS_HISTORY.md` | Append long “what was completed” narrative **only here** — never in chat or `PROGRESS.md` |
| `AUDIT_LOG.md` | **Append only** at session end (≤5 bullets). **Never read** at startup. Archive if >12 entries → `AUDIT_LOG_ARCHIVE_2026.md` |

### 3. Context files (only if changed this session)

- [ ] New backend routes → `AI_CONTEXT_BACKEND.md` API table
- [ ] New pages/components → `AI_CONTEXT_FRONTEND.md`
- [ ] New architecture decision → `DECISIONS.md`

### 4. Chat reply (Full POST-PHASE only)

- Summarize in **≤5 bullets** for the user.
- Do **not** paste session narratives — they belong in `PROGRESS_HISTORY.md`.

### 5. Git (optional — not every session)

**Default: no commit, no push** unless the user says e.g. “commit”, “push”, or “end of phase / ready for backup”.

```bash
git add ai-docs/ backend/ frontend/src/ docs/ render.yaml PROFESSIONAL_IMPROVEMENTS.md
git diff --cached --name-only | grep -E '\.env|secret|zenith-backend' && echo '⛔ STOP' || echo '✅ OK'
git commit -m 'feat|fix|docs: summary

- change 1
- change 2'
git push origin stage   # never --force
```

Never commit: `backend/.env`, `node_modules/`, `*.backup`.

---

## Session starter (paste for new chats)

**Full copy-paste templates (PDF + Markdown):** `ai-docs/ZENITH_AI_SESSION_PROMPTS.pdf` · `ai-docs/ZENITH_AI_SESSION_PROMPTS.md`

```
Zenith — follow ai-docs/AI_MASTER.md (PRE → EXECUTE → POST).

Read Tier A: STATUS.md + SCRATCHPAD.md.

Task: [describe]
Scope: [...] | Do NOT touch: [...] | Done when: [...]
```

---

## ai-docs index (quick reference)

| File | When |
|------|------|
| `STATUS.md` | Every session — live snapshot |
| `SCRATCHPAD.md` | Every session — resume / LKGS |
| `AI_MASTER.md` | Protocol — **read once per thread** |
| `PROGRESS.md` | Active task + checklist only (update on task change) |
| `PROGRESS_HISTORY.md` | **Append only** — never read at startup |
| `AI_RULES.md` | Constraints, conflicts, zero-cost |
| `DECISIONS.md` | Before structural changes |
| `AI_CONTEXT_*.md` | Module maps when editing that stack |
| `AUDIT_LOG.md` | **Append only** — never read at startup |

PDFs (project root): full report + Phase 12 security paper — use when spec is unclear.

---

## Non-negotiables (protocol level)

1. **PRE-PHASE before code** — claim in STATUS + PROGRESS + SCRATCHPAD.
2. **Never commit `backend/.env`** — rotate credentials before any public repo.
3. **Brand: Zenith / ZenithApp** — do not rename without user approval.
4. **POST-PHASE before stop** — SCRATCHPAD must say `COMPLETE` or show exact resume steps; never leave silent `IN PROGRESS` when work is done.
5. **No startup reads** of `AUDIT_LOG.md` or `PROGRESS_HISTORY.md` — Tier A is `STATUS` + `SCRATCHPAD` only.
6. **Git** — commit/push only when the user asks or at a agreed milestone — not after every AI stop.

*Protocol version: 2026-05-29 · Live data always wins over this file — trust `STATUS.md`.*
