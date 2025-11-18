# Cost Analysis - Quick Start Guide

## TL;DR

✅ **AWS**: Already working - just select AWS and fetch costs  
⚙️ **GCP**: Requires BigQuery billing export setup  
⚙️ **Azure**: Requires Service Principal with Cost Management Reader role

---

## Quick Test (AWS)

1. Start backend:
   ```bash
   cd backend
   source ../venv/bin/activate
   uvicorn app.main:app --reload
   ```

2. Start frontend:
   ```bash
   cd frontend
   npm run dev
   ```

3. Navigate to: `http://localhost:5173/dashboard/costs`

4. Select **AWS**, choose dates, click **Fetch Costs** ✅

---

## Enable GCP Billing (5 minutes)

```bash
# 1. Enable BigQuery billing export
open https://console.cloud.google.com/billing/export

# 2. Add to backend/.env
GCP_BILLING_DATASET_ID=your_dataset
GCP_BILLING_TABLE_ID=gcp_billing_export_v1_XXXXXX

# 3. Restart backend
pkill -f uvicorn
cd backend && source ../venv/bin/activate && uvicorn app.main:app --reload
```

Done! Select **GCP** in the dashboard and fetch costs.

---

## Enable Azure Billing (5 minutes)

```bash
# 1. Create Service Principal (if not already done)
az ad sp create-for-rbac --name "cost-reader" --role "Cost Management Reader" --scopes /subscriptions/YOUR_SUB_ID

# 2. Add to backend/.env (if not already there)
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-app-id
AZURE_CLIENT_SECRET=your-client-secret

# 3. Restart backend
pkill -f uvicorn
cd backend && source ../venv/bin/activate && uvicorn app.main:app --reload
```

Done! Select **Azure** in the dashboard and fetch costs.

---

## What You'll See

### When Configured ✅
- Total cost for date range
- Average daily spending
- Top 10 services by cost
- Daily cost timeline
- Service breakdown with percentages

### When NOT Configured ⚙️
- Setup instructions
- Documentation links
- Required environment variables
- Step-by-step guide

---

## Troubleshooting

**"Module not found" errors:**
```bash
cd /path/to/project
source venv/bin/activate
pip install google-cloud-bigquery azure-identity azure-mgmt-consumption
```

**Backend won't start:**
```bash
# Make sure venv is activated
source venv/bin/activate

# Check what's listening on port 8000
lsof -i :8000

# Kill existing process
pkill -f uvicorn
```

**No data showing:**
- Check date range (billing data has 24-hour delay)
- Verify credentials in .env
- Check backend logs for errors

---

## Full Documentation

- Setup Guide: `docs/COST_ANALYSIS_SETUP.md`
- Implementation Details: `docs/COST_ANALYSIS_IMPLEMENTATION.md`
- API Reference: `docs/api_reference.md`

---

## Current State

```
✅ AWS Cost Explorer - Working out of the box
✅ GCP BigQuery - Real API, needs billing export setup
✅ Azure Consumption API - Real API, needs Service Principal
✅ Unified response format
✅ Service breakdown for all providers
✅ Time series visualization
✅ Graceful error handling
```

**Ready for production!** 🚀
