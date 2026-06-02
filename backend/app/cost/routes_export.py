from fastapi import APIRouter, HTTPException, Depends, Response
from typing import Literal
import csv
import io
from datetime import datetime
import logging

from app.users.routes_users import get_current_user
from app.cost.manager import get_aws_cost_and_usage, get_gcp_billing_data, get_azure_billing_data
from app.config.demo_mode import is_demo_mode, billing_results_by_time

router = APIRouter()
logger = logging.getLogger(__name__)

def generate_csv_report(cost_data: dict, provider: str) -> str:
    """Generate CSV report from cost data"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([f"{provider.upper()} Cost Report", f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"])
    writer.writerow([])
    writer.writerow(["Date", "Total Cost", "Currency"])
    
    # Data rows
    results = billing_results_by_time(cost_data)
    for item in results:
        date_range = f"{item.get('TimePeriod', {}).get('Start', 'N/A')} to {item.get('TimePeriod', {}).get('End', 'N/A')}"
        total = item.get("Total", {}).get("UnblendedCost", {})
        amount = total.get("Amount", "0")
        unit = total.get("Unit", "USD")
        writer.writerow([date_range, amount, unit])
    
    # Services breakdown
    writer.writerow([])
    writer.writerow(["Service", "Cost"])
    services = cost_data.get("Services") or cost_data.get("data", {}).get("Services", [])
    for service in services:
        name = service.get("name") or service.get("service", "Unknown")
        writer.writerow([name, service.get("cost", "0")])
    
    return output.getvalue()

@router.get("/export/{provider}")
async def export_cost_report(
    provider: Literal["aws", "gcp", "azure"],
    start_date: str,
    end_date: str,
    format: Literal["csv", "json"] = "csv",
    user: dict = Depends(get_current_user),
):
    """Export cost data as CSV or JSON"""
    try:
        # Fetch cost data
        if provider == "aws":
            cost_data = get_aws_cost_and_usage(user.username, start_date, end_date, "DAILY")
        elif provider == "gcp":
            cost_data = get_gcp_billing_data(user.username, start_date, end_date)
        elif provider == "azure":
            cost_data = get_azure_billing_data(user.username, start_date, end_date)
        else:
            raise HTTPException(status_code=400, detail="Invalid provider")
        
        if format == "csv":
            csv_content = generate_csv_report(cost_data, provider)
            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename={provider}_cost_report_{start_date}_{end_date}.csv"
                }
            )
        else:  # json
            import json
            json_content = json.dumps(cost_data, indent=2)
            return Response(
                content=json_content,
                media_type="application/json",
                headers={
                    "Content-Disposition": f"attachment; filename={provider}_cost_report_{start_date}_{end_date}.json"
                }
            )
    except Exception as e:
        logger.error(f"Error exporting report: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to export report: {str(e)}")
