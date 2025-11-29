# Cost Analysis Setup Guide

This guide explains how to configure cost tracking for AWS, GCP, and Azure in the Cloud Resource Optimization Platform.

## AWS Cost Explorer (Already Configured ✅)

AWS cost tracking is fully integrated and uses Cost Explorer API.

**Prerequisites:**
- AWS Access Key and Secret Key with Cost Explorer permissions
- IAM policy: `arn:aws:iam::aws:policy/AWSBillingReadOnlyAccess`

**Configuration in .env:**
```bash
AWS_ACCESS_KEY_ID=your_key_here
AWS_SECRET_ACCESS_KEY=your_secret_here
AWS_REGION=us-east-1
```

## GCP BigQuery Billing Setup

GCP cost tracking requires BigQuery billing export to be enabled.

### Step 1: Enable Cloud Billing API
1. Go to [GCP Console APIs](https://console.cloud.google.com/apis/library)
2. Search for "Cloud Billing API"
3. Click "Enable"

### Step 2: Set Up BigQuery Billing Export
1. Go to [Billing Export](https://console.cloud.google.com/billing/export)
2. Select your billing account
3. Click "Edit Settings" for BigQuery Export
4. Choose or create a BigQuery dataset (e.g., `billing_dataset`)
5. Note the table name (e.g., `gcp_billing_export_v1_XXXXXX`)

### Step 3: Grant Permissions to Service Account
```bash
# Grant BigQuery Data Viewer role
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:YOUR_SERVICE_ACCOUNT@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataViewer"
```

### Step 4: Install Dependencies
```bash
cd backend
source venv/bin/activate
pip install google-cloud-bigquery
```

### Step 5: Update .env
```bash
# Add to backend/.env
GCP_PROJECT_ID=your-project-id
GCP_SERVICE_ACCOUNT_JSON_PATH=/path/to/service-account.json
GCP_BILLING_DATASET_ID=billing_dataset
GCP_BILLING_TABLE_ID=gcp_billing_export_v1_XXXXXX
```

### Step 6: Test
Restart the backend server and select GCP from the Cost Analysis dropdown. You should see real billing data!

---

## Azure Cost Management Setup

Azure cost tracking uses the Consumption Management API.

### Step 1: Create Service Principal
```bash
# Login to Azure
az login

# Create Service Principal
az ad sp create-for-rbac --name "cost-management-reader" --role "Cost Management Reader" --scopes /subscriptions/YOUR_SUBSCRIPTION_ID

# Save the output - you'll need:
# - appId (AZURE_CLIENT_ID)
# - password (AZURE_CLIENT_SECRET)
# - tenant (AZURE_TENANT_ID)
```

### Step 2: Grant Cost Management Reader Role
```bash
# If not done in Step 1, assign the role:
az role assignment create \
  --assignee YOUR_APP_ID \
  --role "Cost Management Reader" \
  --scope /subscriptions/YOUR_SUBSCRIPTION_ID
```

### Step 3: Install Dependencies
```bash
cd backend
source venv/bin/activate
pip install azure-identity azure-mgmt-consumption
```

### Step 4: Update .env
```bash
# Add to backend/.env
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-app-id
AZURE_CLIENT_SECRET=your-client-secret
```

### Step 5: Test
Restart the backend server and select Azure from the Cost Analysis dropdown. You should see real billing data!

---

## Troubleshooting

### GCP: "BigQuery library not installed"
**Solution:**
```bash
cd backend
source venv/bin/activate
pip install google-cloud-bigquery
pip freeze > requirements.txt
```

### GCP: "Table not found" error
**Solution:**
- Verify BigQuery billing export is enabled
- Check table name matches `GCP_BILLING_TABLE_ID` in .env
- Ensure billing data exists for the selected date range

### Azure: "Azure SDK not installed"
**Solution:**
```bash
cd backend
source venv/bin/activate
pip install azure-identity azure-mgmt-consumption
pip freeze > requirements.txt
```

### Azure: "Unauthorized" or 403 errors
**Solution:**
- Verify Service Principal has "Cost Management Reader" role
- Check credentials in .env match Azure Portal
- Ensure subscription ID is correct

### General: Backend not starting
**Solution:**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

---

## Data Refresh Rates

- **AWS**: Cost Explorer data has 8-24 hour delay
- **GCP**: BigQuery export updates every 24 hours
- **Azure**: Consumption API has 8-24 hour delay

Cost data is not real-time - expect delays of 1-2 days for finalized costs.

---

## Cost Optimization Tips

Once billing data is flowing, the platform shows:
- ✅ Total costs across providers
- ✅ Cost breakdown by service
- ✅ Daily/monthly spending trends
- ✅ Top 10 most expensive services

**Next Steps:**
1. Set up budget alerts (coming soon)
2. Enable cost forecasting with ML models
3. Create custom cost allocation tags
4. Schedule regular cost reports

---

## Support

For issues or questions:
- Check [API Reference](./api_reference.md)
- Review [Architecture](./architecture.md)
- Open an issue on GitHub
