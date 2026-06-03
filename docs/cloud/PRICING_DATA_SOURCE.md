# Cloud pricing data source (Cost Simulator)

**Last updated:** 2026-06-03 (Multi-cloud parity Phase 7)

## Summary

`GET /api/pricing` serves **static reference tables** for AWS, GCP, and Azure — not live Price List / Retail Prices API calls.

| Provider | Module | Live API |
|----------|--------|----------|
| AWS | `app/pricing/pricing_fetcher.py` | Placeholder boto3 Pricing client; values are hardcoded fallbacks |
| GCP | Same | Approximate static USD rates |
| Azure | Same | Approximate static USD rates |

## Cache

- MongoDB collection `pricing_cache`, refreshed weekly via Celery `update_pricing_cache` (re-inserts static bundle).
- `POST /api/pricing/refresh` — manual admin refresh.

## Use cases

- **Cost Simulator** (`CostSimulatorPage.jsx`) — comparative estimates only.
- **Not** used for customer billing invoices (Razorpay / subscription) or Cost Explorer / BigQuery / Azure Consumption live data.

For live spend, use **Cost Analysis** (`/api/cost/*`) with provider billing credentials per [CREDENTIAL_CONTRACT.md](./CREDENTIAL_CONTRACT.md).
