# Zenith — AI Session Prompt Templates

> Copy-paste at the **start** of a new Cursor thread. Protocol: `AI_MASTER.md` · Rules: `AI_RULES.md`

---

## Full feature / phase task (recommended)

```
Zenith — follow ai-docs/AI_MASTER.md strictly (PRE → EXECUTE → POST → git push).

1) PRE (before any product code):
   - Read STATUS.md + SCRATCHPAD.md
   - Update STATUS.md, PROGRESS.md, SCRATCHPAD.md (IN PROGRESS, NOT YET DONE steps)
   - Update phase/theme doc if applicable (PHASE_12_*, UI_UX_AUDIT_2026.md → ## Current session)
   - Output 📋 PRE-PHASE COMPLETE in chat

2) EXECUTE:
   Task: [describe]
   Scope: [...] | Do NOT touch: [...] | Done when: [...]

3) POST (before you stop):
   - pytest / lint / build as needed
   - Finalize STATUS, PROGRESS, SCRATCHPAD, phase doc
   - Append PROGRESS_HISTORY.md + AUDIT_LOG.md
   - git commit + git push to GitHub (stage or current branch)
   - Chat: ≤5 bullets + Git: pushed <branch> @ <hash>
```

---

## Resume interrupted work

```
Zenith — resume from SCRATCHPAD.md (AI_MASTER PRE → EXECUTE → POST).

Read STATUS.md + SCRATCHPAD.md. If IN PROGRESS, continue from first NOT YET DONE step.
Do not rewrite claim unless scope changed. Still commit + push at POST if you change files.
```

---

## Docs-only / protocol update

```
Zenith — ai-docs only. PRE: claim in STATUS + SCRATCHPAD. POST: AUDIT_LOG + git push.
Do not touch backend/ or frontend/ unless I say so.
```

---

## Explicit no-push (exception)

```
Zenith — follow AI_MASTER but skip git push this session (local only).
```

---

*Markdown companion to `ZENITH_AI_SESSION_PROMPTS.pdf` · Protocol version 2026-05-29b*
