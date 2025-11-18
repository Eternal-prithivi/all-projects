# backend/app/cost/manager.py

import boto3
from datetime import datetime, timedelta
from typing import List, Dict, Any

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

# --- Placeholder for GCP Cost Functions (to be added) ---
def get_gcp_billing_data(start_date: str, end_date: str) -> Dict[str, Any]:
    return {"message": "GCP cost data not available."}

# --- Placeholder for Azure Cost Functions (to be added) ---
def get_azure_billing_data(start_date: str, end_date: str) -> Dict[str, Any]:
    return {"message": "Azure cost data not available."}
