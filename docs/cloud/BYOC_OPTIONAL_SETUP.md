# BYOC optional setup (Tier 2)

Zenith uses a **two-tier** Bring Your Own Cloud (BYOC) model.

## Tier 1 — Required to connect (storage)

| Cloud | Credentials |
|-------|-------------|
| AWS | Access keys or IAM role + S3 buckets |
| GCP | Service account JSON + GCS buckets |
| Azure | Storage account name + key + Blob containers |

After Tier 1, **Storage** and **Security** work immediately.

## Tier 2 — Recommended (skippable at connect)

| Cloud | Additional credentials | Unlocks |
|-------|------------------------|---------|
| GCP | BigQuery billing export dataset + table IDs | Cost analysis |
| Azure | Subscription + service principal (tenant, client ID, secret) | VMs, Provision, Cost |

Tier 2 is **never required** to finish storage connect. You can skip during the wizard and complete later in **Settings**.

## What stays blocked without Tier 2

| Cloud | Still works | Blocked |
|-------|-------------|---------|
| AWS | All features (single tier) | — |
| GCP | Storage, Security, VMs, Provision | Cost |
| Azure | Storage, Security | VMs, Provision, Cost |

Partial Tier 2 fields are **not saved** — provide all fields for a tier or none.

## GCP billing export

1. Open [Billing export](https://console.cloud.google.com/billing/export) and enable BigQuery export.
2. Note the **dataset ID** and **table ID** in BigQuery (e.g. `gcp_billing_export_v1_<ACCOUNT>`).
3. Grant your BYOC service account **BigQuery Data Viewer** on the export dataset.
4. Enter both IDs in Settings → BYOC → GCP, or during connect Step 3 (recommended).

## Azure service principal

1. Create an **App registration** in Microsoft Entra ID.
2. Create a **client secret** under Certificates & secrets.
3. Copy **Subscription ID**, **Tenant ID**, **Application (client) ID**, and the secret.
4. Assign subscription roles (e.g. Cost Management Reader; compute roles for VMs/Provision).
5. Enter all four values in Settings → BYOC → Azure, or during connect Step 3 (recommended).

## API

- `GET /api/byoc/setup-guides` — structured guide copy
- `PATCH /api/byoc/gcp/billing` — add billing export after connect
- `PATCH /api/byoc/azure/compute` — add service principal after connect
