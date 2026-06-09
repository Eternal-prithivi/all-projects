# Platform multi-region storage

Platform (non-BYOC) users pick **one region** at upload time. Bucket/container lists on the Storage page come from **server config only** — no `list_buckets` / `list_containers` API calls on page load for AWS, GCP, or Azure.

BYOC users keep live bucket/container discovery. **Page refresh** (header button on Storage/Security) reloads all CSP panels; there is no per-cloud refresh button inside bucket selectors.

## Region slugs

| Slug     | Label         | AWS region   | GCP location   | Azure region (example) |
| -------- | ------------- | ------------ | -------------- | ---------------------- |
| `asia`   | Asia          | `ap-south-1` | `ASIA-SOUTH1`  | `centralindia`         |
| `us`     | United States | `us-east-1`  | `US-EAST1`     | `eastus`               |
| `europe` | Europe        | `eu-west-1`  | `EUROPE-WEST1` | `westeurope`           |
| `africa` | Africa        | `af-south-1` | `AFRICA-SOUTH1`| `southafricanorth`     |

## Bucket naming convention

Create one destination per slug per cloud:

- **AWS:** `zeneith-storage-{slug}` (e.g. `zeneith-storage-asia`)
- **GCP:** `zeneith-main-{slug}` in the configured project
- **Azure:** storage account `zenithstorage{slug}` + container `zenith-storage` (four accounts, one per region)

## Configuration

1. Copy `backend/config/platform_storage_catalog.example.json` to a deploy-specific path (e.g. `backend/config/platform_storage_catalog.json`).
2. Fill in real bucket names and Azure account keys (keep keys in env/Render secrets, not in git).
3. Set in `.env` or Render dashboard:

```bash
PLATFORM_STORAGE_CATALOG_JSON=config/platform_storage_catalog.json
# optional default when UI has no session selection:
PLATFORM_STORAGE_DEFAULT_SLUG=asia
```

**Legacy single-bucket deploys:** leave `PLATFORM_STORAGE_CATALOG_JSON` unset. Zenith falls back to `REGULAR_S3_BUCKET_NAME`, `GCP_BUCKET_NAME`, and `AZURE_*` — one region, no region pills.

**GCP / Azure uploads** still require platform service account / storage keys in `.env`; only **listing** is static.

## Manual test checklist

1. **Page load (platform mode):** Open Storage. Confirm server logs show **no** GCP `list_buckets` or Azure `list_containers` calls.
2. **Region pills:** With catalog configured, confirm four region pills (Asia, US, Europe, Africa) and one bucket/container per CSP when a pill is selected.
3. **Upload:** Pick `europe`, upload to AWS, GCP, and Azure. Confirm file metadata `cloud_bucket` and `region` match the Europe catalog entry.
4. **Sync:** Sync each selected bucket; files appear in the table filtered by `cloud_bucket`.
5. **BYOC:** Connect BYOC for a CSP. Confirm live discovery and existing region filters still work.
6. **Page refresh:** Use header **Refresh** on Storage. Confirm gold loading bar on AWS, GCP, and Azure panels, then buckets/containers listed.
7. **Sync after delete:** Delete a file in the cloud console, sync the bucket — file count in Zenith should match (region-scoped stale removal).
