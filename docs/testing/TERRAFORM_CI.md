# Terraform in CI (Phase 20.16)

## Current CI

Workflow `.github/workflows/ci.yml` job **terraform-validate**:

- `terraform init -backend=false`
- `terraform validate`

This runs on every PR; it does **not** apply infrastructure.

## Optional: plan on PR (read-only)

To add a non-blocking plan comment (requires AWS credentials secret — use read-only role):

```yaml
# Example step (not enabled by default — add when AWS_ROLE_ARN is configured)
- name: Terraform plan
  working-directory: backend/terraform
  env:
    AWS_ACCESS_KEY_ID: ${{ secrets.TF_PLAN_AWS_KEY_ID }}
    AWS_SECRET_ACCESS_KEY: ${{ secrets.TF_PLAN_AWS_SECRET }}
  run: |
    terraform init -backend=false
    terraform plan -input=false -no-color
```

**Policy:** PRs must pass `terraform validate`. Full `plan` is optional until sandbox AWS credentials exist.

## Local

```bash
cd backend/terraform
terraform init -backend=false
terraform validate
terraform plan   # only when AWS creds configured
```
