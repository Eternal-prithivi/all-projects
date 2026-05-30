# Branch protection (recommended)

Require the **CI** workflow to pass before merging into protected branches.

## GitHub settings

1. **Settings → Branches → Branch protection rules**
2. Add rules for `main`, `stage`, and optionally `develop`
3. Enable:
   - **Require a pull request before merging**
   - **Require status checks to pass before merging**
   - Status check: **`backend`**, **`frontend`**, **`terraform-validate`**, **`playwright`** (after Phase 20.5.2)
   - After Phase 20.5.1: require CI to pass before merge; deploy runs only after CI (see `PHASE_20_5_CI_GATES.md`)

## What CI runs

| Job | Working directory | Command |
|-----|-----------------|---------|
| backend | `backend/` | `pytest -q` (MongoDB 7 service, `zenith_test` DB) |
| frontend | `frontend/` | `npm run lint`, `npm test`, `npm run build` |
| terraform-validate | `backend/terraform/` | `terraform validate` |

## CD workflows

- **Stage:** `.github/workflows/deploy-stage.yml` — push to `stage` (configure `RENDER_DEPLOY_HOOK` and Vercel secrets)
- **Production:** `.github/workflows/deploy-production.yml` — manual `workflow_dispatch` or version tags only

Do not bypass required checks for routine merges.
