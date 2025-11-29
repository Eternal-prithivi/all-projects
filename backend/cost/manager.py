# backend/app/cost/manager.py

import boto3
from datetime import datetime, timedelta
from typing import List, Dict, Any

from app.utils.config import settings

print("DEBUG in manager.py: app.cost.manager module is being loaded.") # Diagnostic line
print("DEBUG in manager.py: About to define get_aws_cost_and_usage. Current global scope before function:", list(globals().keys())) # Diagnostic line

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
    print("GCP cost function not yet implemented.")
    return {"message": "GCP cost data not available."}

# --- Placeholder for Azure Cost Functions (to be added) ---
def get_azure_billing_data(start_date: str, end_date: str) -> Dict[str, Any]:
    print("Azure cost function not yet implemented.")
    return {"message": "Azure cost data not available."}

print("DEBUG in manager.py: After defining all functions. Current global scope after functions:", list(globals().keys())) # Diagnostic line

if __name__ == "__main__":
    print("\n--- Running manager.py as a script for testing ---")
    print(f"Functions available in manager.py's __main__ scope: {list(globals().keys())}")
    if 'get_aws_cost_and_usage' in globals():
        print("SUCCESS: 'get_aws_cost_and_usage' is defined when manager.py is run directly.")
    else:
        print("FAILURE: 'get_aws_cost_and_usage' is NOT defined when manager.py is run directly.")

    # Try to call a placeholder if defined
    try:
        result = get_gcp_billing_data("2023-01-01", "2023-01-02")
        print(f"Test call to get_gcp_billing_data: {result}")
    except NameError as e:
        print(f"Could not call get_gcp_billing_data: {e}")
# --- END TEMPORARY TEST BLOCK ---