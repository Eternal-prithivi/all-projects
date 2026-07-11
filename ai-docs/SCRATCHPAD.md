# SCRATCHPAD.md

## 🔄 Current Resume State

**Status:** COMPLETE (2026-07-11)

**Post–Stage 1 polish:** password UX (8-char min), toast notifications, unified help/support, settings crash fix, desktop v0.1.4 release, ESLint green — all delivered and pushed to `stage`.

**Next (Stage 2 — when user asks):** Desktop code signing; Redis app cache; dashboard BFF endpoint.

**Ops:** Cloud account migration → `CLOUD_ACCOUNT_MIGRATION_GUIDE.md` · All services → `SERVICES_REFERENCE.md`

---

## ✅ Last Known Good State

**Post–Stage 1 polish** (2026-07-11)

- Password: `PasswordRequirementsPanel`; backend `password_policy.py` min 8; register/reset/security-settings
- Notifications: `utils/notifications.js` toasts + bell; `useNotifications` hook; public `ToastContainer` in `App.jsx`
- Help: `/help` tabs (articles | tickets); `SupportTicketsSection`; `PATHS.support` → `/help?tab=tickets`
- Desktop: `desktop-v0.1.4` on GitHub Releases; `releases.json` checksums committed by CI
- CI: frontend `package-lock.json` synced for desktop-release `npm ci`; lint 0 warnings
- Production: `SettingsPage` CloudProviderLogo import; profile dropdown CSS compact

**Git:** `stage` @ `97171c0`

**Verify locally:**
```bash
cd backend && .venv/bin/python -m pytest -q
cd frontend && npm run lint && npm run build
cd frontend && npm run test:e2e
```
