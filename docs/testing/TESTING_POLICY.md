# Zenith testing policy

How we test, what “done” means, and how to grow coverage without a test file per source module.

## Principles

1. **Risk over volume** — Auth, admin/RBAC, BYOC, storage, security/2FA, orgs, billing, and password flows get API integration tests first.
2. **Test pyramid** — Many unit tests (mocks), fewer HTTP integration tests (Mongo + `TestClient`), minimal Playwright golden paths.
3. **One domain per integration file** — `tests/integration/test_<domain>_api.py` only; do not mirror every `routes_*.py`.
4. **No production data** — Use `zenith_test` and `MONGO_DB_NAME=zenith_test`; never point tests at Atlas/production.
5. **Regression rule** — Production bug fix includes a test in the existing domain file before merge.

## Definition of done (per PR)

| Change type | Required test |
|-------------|----------------|
| Auth / JWT / 2FA | Extend `test_auth_api.py` or `test_security_api.py` |
| Admin / RBAC | `test_admin_api.py` |
| BYOC | `test_byoc_api.py` (mock cloud; no live AWS/GCP) |
| Storage upload/analyze/sync | `test_storage_api.py` |
| Security vault | `test_security_api.py` |
| Orgs / invites | `test_organizations_api.py` |
| Settings / profile API | `test_settings_api.py` / `test_profile_api.py` |
| Pure helper logic | Existing or new `tests/test_*.py` with mocks |
| UI validation only | `frontend/src/**/*.test.js` or Playwright if user journey |
| CSS / copy-only | Manual check; no new test file |

## Current inventory (approx.)

| Layer | Files | Cases (Mongo up) |
|-------|-------|------------------|
| Backend unit | ~30 `tests/test_*.py` | ~94 |
| Backend integration | 13 `tests/integration/test_*_api.py` | ~39 |
| Frontend unit | 4 Vitest files | 7 |
| E2E | 4 Playwright specs | 5+ |

See [TESTING.md](./TESTING.md) for commands and layout.

## Maturity snapshot

| Area | Status |
|------|--------|
| P0 API (auth, admin, BYOC, storage, security, orgs, password) | **Strong** — integration suite in place |
| Settings / profile / sessions API | **Started** — `test_settings_api.py`, `test_profile_api.py` |
| Unit helpers (BYOC, provision, ML) | **Moderate** |
| E2E user journeys | **Early** — login→dashboard, BYOC validation, admin system health |
| Coverage threshold in CI | **Artifact only** — ratchet % over time |
| Load / contract / chaos | **Deferred** (Phase 25) |

## Roadmap (next quarters)

**Now (maintain)**

- Keep CI green: `pytest`, `npm test`, Playwright (API + Vite).
- Extend **existing** integration files when touching a domain.

**Next (high signal)**

- Raise Playwright from `continue-on-error` to required when stable 2–4 weeks.
- Coverage gate: start ~40% backend, increase quarterly.
- Fix app pattern: avoid `DB = get_database()` at import in route modules (use call-time `get_database()`).

**Later**

- Staging smoke job against deployed `stage` URL.
- Contract tests for public API if external integrators appear.
- Staging / Atlas / Terraform CI docs: [STAGING.md](./STAGING.md), [MONGODB_ATLAS.md](./MONGODB_ATLAS.md), [TERRAFORM_CI.md](./TERRAFORM_CI.md).

## Anti-patterns

- Do not add `test_<every_route>.py` at repo root.
- Do not import route modules at pytest collection time without test DB wired (see `conftest._rebind_route_databases`, including `app.byoc.credential_resolver` for BYOC status reads).
- Do not hit real cloud APIs in CI.
- Do not disable rate limits only in one limiter — auth uses module-level `Limiter` instances.

## References

- Runbook: [TESTING.md](./TESTING.md)
- CI / branch protection: [BRANCH_PROTECTION.md](./BRANCH_PROTECTION.md)
- Agent protocol: `ai-docs/AI_MASTER.md` (POST-PHASE: run tests before stop)
