# PROGRESS.md — Task Tracker

> Last Updated: 2026-05-29

---

## 🔴 Active Task

**None** — Phase 15 **COMPLETE** (2026-05-29).

---

## Phase Summary

| Phase | Status |
|-------|--------|
| 14c | ✅ Governance UI, BYOC gate |
| **15** | **✅** Theme sync, header toggle, BYOC subscription lookup fix |

### Phase 15 delivered

- [x] `ThemeSync` loads saved theme from `/api/settings/` on login
- [x] Settings theme select auto-persists; header sun/moon quick toggle
- [x] Dashboard shell uses CSS tokens (sidebar/header) for light mode
- [x] ToastContainer follows `effectiveTheme`
- [x] BYOC eligibility queries `username` OR `user_id` in subscriptions
- [x] `test_settings_preferences.py` (4 tests); pytest **73** total
