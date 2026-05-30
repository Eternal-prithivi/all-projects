# Zenith testing guide

## Policy and roadmap

**How we test and what to add next:** [TESTING_POLICY.md](./TESTING_POLICY.md)

Related:

- [BRANCH_PROTECTION.md](./BRANCH_PROTECTION.md) — required CI checks
- [STAGING.md](./STAGING.md) — Phase 20.14 staging environment
- [MONGODB_ATLAS.md](./MONGODB_ATLAS.md) — Phase 20.15 Atlas migration
- [TERRAFORM_CI.md](./TERRAFORM_CI.md) — Phase 20.16 Terraform in CI

## Layout

| Path | Purpose |
|------|---------|
| `backend/tests/test_*.py` | Unit tests (mocks, no HTTP) |
| `backend/tests/integration/test_*_api.py` | API integration tests (`TestClient` + MongoDB) |
| `backend/tests/conftest.py` | Shared fixtures, test DB, auth helpers |
| `frontend/src/**/*.test.js` | Frontend unit tests (Vitest) |
| `frontend/e2e/specs/` | Playwright end-to-end specs |
| `backend/scripts/seed_e2e_admin.py` | Fixed admin user for E2E (`e2e_admin`) |

### Integration test files

| File | Domain |
|------|--------|
| `test_auth_api.py` | Register, login, JWT, email verify gate |
| `test_admin_api.py` | Admin RBAC, audit export |
| `test_byoc_api.py` | GCP + AWS BYOC (mocked cloud) |
| `test_storage_api.py` | List, upload, analyze, sync |
| `test_security_api.py` | 2FA guards, client-encrypted upload |
| `test_organizations_api.py` | Orgs, invites |
| `test_auth_password_api.py` | Password reset, verify email |
| `test_notifications_api.py` | Notifications |
| `test_platform_api.py` | Public status, maintenance |
| `test_billing_api.py` | Invoices (mocked costs) |
| `test_settings_api.py` | Preferences GET/PUT |
| `test_profile_api.py` | Sessions list |

### E2E specs

| Spec | Journey |
|------|---------|
| `auth.spec.ts` | Login form + login → dashboard |
| `byoc-settings.spec.ts` | Settings requires auth |
| `byoc-validation.spec.ts` | GCP BYOC inline validation (mock Pro) |
| `admin.spec.ts` | Admin login → system health |

## Backend — run locally

```bash
cd backend
export MONGO_CONNECTION_STRING=mongodb://localhost:27017
export MONGO_DB_NAME=zenith_test
python -m pytest -q
```

Integration only:

```bash
python -m pytest tests/integration -q -m integration
```

Coverage:

```bash
python -m pytest -q --cov=app --cov-report=term-missing
```

## Frontend unit

```bash
cd frontend && npm test
```

## Frontend E2E (Playwright)

**Prerequisites:** Mongo on `:27017`, API on `:8000`, optional `python scripts/seed_e2e_admin.py` for admin spec.

```bash
# Terminal 1 — API
cd backend && uvicorn app.main:app --reload

# Terminal 2 — seed admin (once)
python scripts/seed_e2e_admin.py

# Terminal 3 — Vite
cd frontend && npm run dev

# Terminal 4 — tests
cd frontend
export PLAYWRIGHT_API_URL=http://127.0.0.1:8000
npm run test:e2e
```

Default admin E2E user: `e2e_admin` / `SecurePass1` (override with `E2E_ADMIN_USERNAME`, `E2E_ADMIN_PASSWORD`).

## CI

- **backend** job: MongoDB 7, `pytest` + coverage artifact
- **playwright** job: starts API + seeds `e2e_admin`, runs Playwright (`continue-on-error` until stable)

## Markers

- `@pytest.mark.integration` — needs MongoDB; uses `zenith_test` (cleared between tests)

## Expected counts (Mongo up)

| Suite | Approx. |
|-------|---------|
| Backend unit | ~94 |
| Backend integration | ~39 |
| Backend total (Mongo up) | ~133 |
| Frontend unit | 7 |
| Playwright | 5+ |

Without Mongo: integration tests **skip**; unit tests still pass.

## Do not

- Point tests at production MongoDB or real cloud credentials
- Import route modules at test collection time without test DB wiring — `conftest._rebind_route_databases` must include any module with `DB = get_database()` at import (e.g. `routes_byoc`, **`credential_resolver`**)
