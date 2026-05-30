# SCRATCHPAD.md

**Status:** COMPLETE (2026-05-30)

**Done:** Testing policy + README links; gap tests (storage analyze, security upload, settings/profile API, BYOC AWS, E2E admin/BYOC); Phase 20.14–16 docs; CI seeds `e2e_admin`; fixed `credential_resolver` rebind in conftest (AWS BYOC status flake).

**LKGS:** 133 backend tests green with Mongo; integration 39; see `docs/testing/TESTING_POLICY.md`.

## Next session

1. `git pull` on `stage`
2. `PROGRESS.md` → **Phase 21** (observability)
3. Optional: ratchet coverage %; make Playwright required in CI when stable

**Local:**

```bash
cd backend && .venv/bin/python -m pytest -q
cd frontend && npm test && npm run test:e2e  # API :8000 + seed_e2e_admin
```
