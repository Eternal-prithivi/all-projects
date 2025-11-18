# backend/app/cost/manager.py

import boto3
from datetime import datetime, timedelta
from typing import List, Dict, Any
import os

from app.utils.config import settings

# --- AWS Cost Explorer Functions ---

def get_aws_cost_and_usage(
    start_date: str, # Format 'YYYY-MM-DD'
    end_date: str,   # Format 'YYYY-MM-DD'
    granularity: str = 'DAILY', # 'DAILY', 'MONTHLY'
    metrics: List[str] = None, # e.g., ['UnblendedCost', 'UsageQuantity']
    group_by: List[Dict[str, str]] = None # e.g., [{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
) -> Dict[str, Any]:
    """
    Fetches cost and usage data from AWS Cost Explorer.

    Args:
        start_date: The start date for the report (inclusive), in 'YYYY-MM-DD' format.
        end_date: The end date for the report (inclusive), in 'YYYY-MM-DD' format.
        granularity: The granularity of the data. Can be 'DAILY' or 'MONTHLY'.
        metrics: A list of metrics to retrieve. Defaults to ['UnblendedCost'].
        group_by: A list of groups to aggregate the data by.
                  e.g., [{'Type': 'DIMENSION', 'Key': 'SERVICE'}]

    Returns:
        A dictionary containing the cost and usage data.
    """
    if metrics is None:
        metrics = ['UnblendedCost']

    # Initialize the AWS Cost Explorer client
    # Use the PRIMARY_S3_REGION for general AWS services like Cost Explorer
    client = boto3.client(
        'ce', # 'ce' is the service name for Cost Explorer
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.PRIMARY_S3_REGION # Use the primary region from settings
    )

    try:
        response = client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date,
                'End': end_date
            },
            Granularity=granularity,
            Metrics=metrics,
            GroupBy=group_by if group_by else []
        )
        return response
    except Exception as e:
        print(f"Error fetching AWS cost and usage data: {e}")
        raise # Re-raise the exception to be handled by the FastAPI route

# --- GCP Cost Functions with BigQuery ---
def get_gcp_billing_data(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Fetches GCP billing data from BigQuery billing export.
    
    Prerequisites:
    1. Enable BigQuery billing export in GCP Console
    2. Set GCP_BILLING_DATASET_ID and GCP_BILLING_TABLE_ID in .env
    3. Ensure service account has bigquery.dataViewer role
    """
    try:
        from google.cloud import bigquery
        from google.oauth2 import service_account
        
        # Check if BigQuery billing is configured
        dataset_id = getattr(settings, 'GCP_BILLING_DATASET_ID', None)
        table_id = getattr(settings, 'GCP_BILLING_TABLE_ID', None)
        
        if not dataset_id or not table_id:
            return {
                "message": "GCP billing not configured",
                "status": "missing_config",
                "error": "Set GCP_BILLING_DATASET_ID and GCP_BILLING_TABLE_ID in .env",
                "implementation_steps": [
                    "Enable BigQuery billing export: https://console.cloud.google.com/billing/export",
                    "Add to .env: GCP_BILLING_DATASET_ID=your_dataset",
                    "Add to .env: GCP_BILLING_TABLE_ID=gcp_billing_export_v1_XXXXX"
                ],
                "estimated_cost": 0.00,
                "currency": "USD"
            }
        
        # Initialize BigQuery client
        credentials_path = getattr(settings, 'GCP_SERVICE_ACCOUNT_JSON_PATH', None)
        if credentials_path and os.path.exists(credentials_path):
            credentials = service_account.Credentials.from_service_account_file(credentials_path)
            client = bigquery.Client(credentials=credentials, project=settings.GCP_PROJECT_ID)
        else:
            client = bigquery.Client(project=settings.GCP_PROJECT_ID)
        
        # Query billing data
        query = f"""
        SELECT
            service.description as service_name,
            SUM(cost) as total_cost,
            currency
        FROM `{settings.GCP_PROJECT_ID}.{dataset_id}.{table_id}`
        WHERE DATE(_PARTITIONTIME) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
        AND cost > 0
        GROUP BY service_name, currency
        ORDER BY total_cost DESC
        LIMIT 50
        """
        
        query_job = client.query(query)
        results = query_job.result()
        
        # Process results
        services = []
        total = 0.0
        currency = "USD"
        
        for row in results:
            services.append({
                "service": row.service_name or "Unknown",
                "cost": float(row.total_cost),
                "currency": row.currency or "USD"
            })
            total += float(row.total_cost)
            currency = row.currency or "USD"
        
        # Format response similar to AWS
        result_by_time = []
        
        # Get daily breakdown
        daily_query = f"""
        SELECT
            DATE(_PARTITIONTIME) as usage_date,
            SUM(cost) as daily_cost
        FROM `{settings.GCP_PROJECT_ID}.{dataset_id}.{table_id}`
        WHERE DATE(_PARTITIONTIME) BETWEEN DATE('{start_date}') AND DATE('{end_date}')
        GROUP BY usage_date
        ORDER BY usage_date
        """
        
        daily_job = client.query(daily_query)
        daily_results = daily_job.result()
        
        for row in daily_results:
            result_by_time.append({
                "TimePeriod": {
                    "Start": row.usage_date.strftime('%Y-%m-%d'),
                    "End": row.usage_date.strftime('%Y-%m-%d')
                },
                "Total": {
                    "UnblendedCost": {
                        "Amount": str(row.daily_cost),
                        "Unit": currency
                    }
                },
                "Groups": []
            })
        
        return {
            "ResultsByTime": result_by_time,
            "Services": services,
            "TotalCost": total,
            "Currency": currency,
            "DimensionValueAttributes": []
        }
        
    except ImportError:
        return {
            "message": "GCP BigQuery library not installed",
            "status": "missing_dependency",
            "error": "Run: pip install google-cloud-bigquery",
            "estimated_cost": 0.00,
            "currency": "USD"
        }
    except Exception as e:
        return {
            "message": f"GCP billing query failed: {str(e)}",
            "status": "error",
            "error": str(e),
            "estimated_cost": 0.00,
            "currency": "USD"
        }

# --- Azure Cost Functions with Consumption API ---
def get_azure_billing_data(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Fetches Azure billing data using Azure Consumption Management API.
    
    Prerequisites:
    1. Create Service Principal in Azure Portal
    2. Grant 'Cost Management Reader' role
    3. Set AZURE_SUBSCRIPTION_ID, AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET in .env
    """
    try:
        from azure.identity import ClientSecretCredential
        from azure.mgmt.consumption import ConsumptionManagementClient
        from datetime import datetime
        
        # Check if Azure credentials are configured
        subscription_id = getattr(settings, 'AZURE_SUBSCRIPTION_ID', None)
        tenant_id = getattr(settings, 'AZURE_TENANT_ID', None)
        client_id = getattr(settings, 'AZURE_CLIENT_ID', None)
        client_secret = getattr(settings, 'AZURE_CLIENT_SECRET', None)
        
        if not all([subscription_id, tenant_id, client_id, client_secret]):
            return {
                "message": "Azure billing not configured",
                "status": "missing_config",
                "error": "Set Azure credentials in .env",
                "implementation_steps": [
                    "Create Service Principal: az ad sp create-for-rbac --name cost-reader",
                    "Grant role: az role assignment create --assignee <app-id> --role 'Cost Management Reader'",
                    "Add to .env: AZURE_SUBSCRIPTION_ID, AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET"
                ],
                "estimated_cost": 0.00,
                "currency": "USD"
            }
        
        # Initialize Azure client
        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )
        
        consumption_client = ConsumptionManagementClient(credential, subscription_id)
        
        # Query usage details
        scope = f'/subscriptions/{subscription_id}'
        
        # Get usage aggregated by service
        usage_aggregates = consumption_client.usage_details.list(
            scope=scope,
            filter=f"properties/usageStart ge '{start_date}' and properties/usageEnd le '{end_date}'"
        )
        
        # Process results
        services_cost = {}
        daily_cost = {}
        total = 0.0
        currency = "USD"
        
        for item in usage_aggregates:
            # Aggregate by service
            service_name = item.consumed_service or "Unknown"
            cost = float(item.cost or 0)
            currency = item.currency or "USD"
            
            if service_name in services_cost:
                services_cost[service_name] += cost
            else:
                services_cost[service_name] = cost
            
            # Aggregate by day
            usage_date = item.date.strftime('%Y-%m-%d') if item.date else start_date
            if usage_date in daily_cost:
                daily_cost[usage_date] += cost
            else:
                daily_cost[usage_date] = cost
            
            total += cost
        
        # Format services
        services = [
            {"service": svc, "cost": cost, "currency": currency}
            for svc, cost in sorted(services_cost.items(), key=lambda x: x[1], reverse=True)[:50]
        ]
        
        # Format time series
        result_by_time = [
            {
                "TimePeriod": {"Start": date, "End": date},
                "Total": {
                    "UnblendedCost": {"Amount": str(cost), "Unit": currency}
                },
                "Groups": []
            }
            for date, cost in sorted(daily_cost.items())
        ]
        
        return {
            "ResultsByTime": result_by_time,
            "Services": services,
            "TotalCost": total,
            "Currency": currency,
            "DimensionValueAttributes": []
        }
        
    except ImportError:
        return {
            "message": "Azure SDK not installed",
            "status": "missing_dependency",
            "error": "Run: pip install azure-identity azure-mgmt-consumption",
            "estimated_cost": 0.00,
            "currency": "USD"
        }
    except Exception as e:
        return {
            "message": f"Azure billing query failed: {str(e)}",
            "status": "error",
            "error": str(e),
            "estimated_cost": 0.00,
            "currency": "USD"
        }
