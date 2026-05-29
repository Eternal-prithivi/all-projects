# Cloud cost guardrails

Protect trial credits and avoid surprise bills while developing Zenith.

## Google Cloud (new account)

- **$300 trial (USD)** applies for eligible new accounts (90 days) — separate from **₹1,000 UPI prepayment** some Indian accounts require to activate billing.
- Prefer **credit/debit card** signup if you want to avoid the ₹1,000 UPI minimum; card verification is often a small hold that is refunded.
- Until billing is **Active**, APIs (Compute, Storage) may fail — use `DEMO_MODE=true` in `backend/.env` for zero-cost UI testing.

### After billing is active

1. **Budget alert**: Billing → Budgets & alerts → e.g. 50% / 90% of ₹ or $ budget.
2. **Zone**: `us-central1-a`, machine type `e2-micro` (defaults in config).
3. **Stop VMs** when not testing — GCP Console → Compute Engine → Stop, or Zenith VM Cluster stop/delete.
4. **One project** for Zenith dev; delete unused disks and static IPs.

Setup steps: `CLOUD_CREDENTIAL_SETUP_GUIDE.md` (GCP section).

## AWS

- Enable **AWS Budgets** and **Cost Anomaly Detection** (Billing console).
- Use separate dev IAM user with least privilege; rotate keys per `CREDENTIAL_ROTATION.md`.
- BYOC IAM role avoids long-lived keys when possible.

## Zenith app controls

| Setting | Effect |
|---------|--------|
| `DEMO_MODE=true` | Mock data, no real cloud API charges |
| `USE_REAL_METRICS=false` | Simulated VM metrics (default) |
| `PERFORMANCE_CLUSTER_MAX_VMS=2` | Caps VM provisioning |

## When you are not using GCP tomorrow

You do **not** need GCP API keys for **Phase 19** work (CORS, docs, Sentry, audit export). Connect GCP when you resume storage/VM testing.
