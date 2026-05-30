# Zenith frontend

React 19 + Vite application.

## Scripts

| Command | Purpose |
|---------|---------|
| `npm run dev` | Local dev server (`:5173`) |
| `npm run build` | Production build |
| `npm run test` | Vitest unit tests |
| `npm run test:e2e` | Playwright E2E (needs API on `:8000`) |
| `npm run lint` | ESLint |

## Testing

See [../docs/testing/TESTING.md](../docs/testing/TESTING.md) and [../docs/testing/TESTING_POLICY.md](../docs/testing/TESTING_POLICY.md).

E2E specs live in `e2e/specs/`. Admin tests use `e2e_admin` / `SecurePass1` after `backend/scripts/seed_e2e_admin.py`.
