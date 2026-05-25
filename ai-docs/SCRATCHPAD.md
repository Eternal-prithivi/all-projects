# SCRATCHPAD.md — Mid-Task Resume State

> Use this to capture incomplete work so you can resume exactly where you left off.
> Clear the Resume State section when a task is fully complete.
> **Always update Last Known Good State at the end of every session.**

---

## 🔍 Drift Detection Protocol

**Every 5th session**, the agent must perform a quick internal consistency audit before starting work.
This prevents small inaccuracies from building up across sessions.

### How to know if this is a 5th session
Check `AUDIT_LOG.md` — count the entries since the last audit entry marked `[DRIFT AUDIT]`.
If 5 or more entries have passed since the last audit (or no audit has ever been done), run the audit now.

### The Audit Checklist

```
[ ] PROGRESS.md — Is the Active Task still accurate? Are all "completed" items truly done?
[ ] SCRATCHPAD.md — Does Last Known Good State match what's in the codebase right now?
[ ] AUDIT_LOG.md — Does it have a recent entry? No entries = session-end protocol was skipped.
[ ] DECISIONS.md — Are any "Planned" decisions now implemented? Update them.
[ ] AI_MASTER.md — Is the project phase still correct? Are the Quick Tech Facts still accurate?
[ ] Module headers — Do any file-level DO NOT comments contradict current code reality?
```

### What to do with findings
- Fix any inaccuracies BEFORE starting the actual task
- Log the audit result in `AUDIT_LOG.md` with `[DRIFT AUDIT]` tag
- If major inaccuracy found: briefly tell the user what was corrected

### Drift Audit Log (most recent first)
| Date | Session | Findings | Fixed? |
|------|---------|----------|--------|
| 2026-05-25 | Antigravity | Initial setup — no prior drift to detect | N/A |

---

## ✅ Last Known Good State

> Updated: 2026-05-25 | Agent: Antigravity

| Check | Status |
|-------|--------|
| Backend tests | ✅ 34/34 passing (`python -m pytest -q`) |
| Frontend build | ✅ Passes (~2s, `npm run build`) |
| Frontend lint | ✅ 0 errors / 28 warnings (all pre-existing) |
| Dev server ports | Backend `:8000`, Frontend `:5173` |
| Last verified feature | Onboarding tour — shows once only, all 7 steps work |
| Last verified fix | Tour welcome modal no longer re-pops on navigation |

**To re-verify:** `cd backend && source .venv/bin/activate && python -m pytest -q` then `cd frontend && npm run build`

---

## 🔄 Current Resume State

**Last completed task:** Onboarding tour implementation + AI docs cleanup + staleness audit.

**Status:** COMPLETE — no active task in progress.

**What was done (Antigravity, 2026-05-25):**
1. Implemented guided onboarding tour (`react-joyride`, 7 steps): sidebar nav → global search → cost card → storage → VMs → quick actions → help center.
2. Created `OnboardingTour.jsx` with custom Zenith glassmorphism tooltips, welcome modal, localStorage tracking.
3. Created `onboarding.css` matching design system (gold accent, glass cards, progress dots, animations).
4. Added "Restart Tour" button to Settings > Preferences.
5. Deleted 2 redundant AI docs (AGENT_SESSION_TEMPLATE, AI_SYSTEM_PROMPT). ai-docs now 8 files.
6. Full staleness audit: rewrote AI_CONTEXT.md (7 modules → 25 route files reality), updated AI_RULES, DECISIONS (5 "Planned" → "Implemented"), AI_MASTER critical warnings.
7. Fixed login button bug, completed Copilot code audit, rewrote PROFESSIONAL_IMPROVEMENTS.md.

**Verification:** Frontend build passes (~2s), lint 0 errors / 28 warnings, backend 34/34 tests.

## Suggested Next Tasks (from PROFESSIONAL_IMPROVEMENTS.md)

1. **Security hardening** — restrict CORS origins, add `.env.example` (🔴 High priority, 30 min)
2. **Backend test expansion** — admin CRUD, BYOC, storage integration tests (🟡 Medium, 2–3 days)
3. **CI/CD pipeline** — GitHub Actions for pytest + eslint + build (🟡 Medium, 1 day)
4. **Real dashboard stats** — connect overview cards to MongoDB aggregation (🟢 Low, 1–2 days)

## Historical Notes (carried forward)

**Automated retraining notes:** `backend/app/ml/retraining.py` performs guarded self-retraining from eligible user feedback. Candidate artifacts staged under `backend/app/ml/artifacts/candidates/`, deployed only if +1% absolute or +2% relative gain. Celery Beat runs weekly Sunday 03:30 UTC.

**ML artifacts:** `storage_ensemble.joblib` (13,824 sample dataset), `workload_classifier.joblib` (600 samples, TF-IDF soft-voting ensemble). Artifacts in `backend/app/ml/artifacts/`.

---

> 📌 **Drift Reminder:** Check `AUDIT_LOG.md` entry count since last `[DRIFT AUDIT]` tag. If 5+ sessions have passed, run the drift checklist above before starting work.

_Last updated: 2026-05-25_
