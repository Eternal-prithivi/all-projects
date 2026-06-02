from fastapi import APIRouter, HTTPException, Depends
from typing import Dict
import numpy as np
from datetime import datetime, timedelta
import logging

from app.cost.manager import get_aws_cost_and_usage, get_gcp_billing_data, get_azure_billing_data
from app.cost.forecasting import extract_daily_costs, forecast_costs
from app.config.demo_mode import is_demo_mode, MockDataGenerator, log_demo_mode_call
from app.users.routes_users import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/forecast/{provider}")
async def get_cost_forecast(
    provider: str,
    days_ahead: int = 30,
    demo_mode: bool = False,
    user: dict = Depends(get_current_user),
):
    """Get cost forecast for the next N days based on historical data"""
    try:
        # Set end_date for all modes
        end_date = datetime.utcnow()
        
        use_demo = is_demo_mode() or demo_mode
        if use_demo:
            log_demo_mode_call(f"Cost forecast ({provider})")
            historical_costs = MockDataGenerator.mock_forecast_historical_days(90)
            logger.info(
                "Forecast demo data: %s days, first=$%.2f last=$%.2f",
                len(historical_costs),
                historical_costs[0],
                historical_costs[-1],
            )
        else:
            # Fetch last 90 days of data for better prediction
            start_date = end_date - timedelta(days=90)
            
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            
            # Get historical data
            if provider == "aws":
                historical_data = get_aws_cost_and_usage(
                    user.username, start_str, end_str, "DAILY"
                )
            elif provider == "gcp":
                historical_data = get_gcp_billing_data(user.username, start_str, end_str)
            elif provider == "azure":
                historical_data = get_azure_billing_data(user.username, start_str, end_str)
            else:
                raise HTTPException(status_code=400, detail="Invalid provider")
            
            # Extract costs
            historical_costs = extract_daily_costs(historical_data)
        
        if len(historical_costs) < 7:
            # Return a simple forecast based on available data
            avg_cost = np.mean(historical_costs) if historical_costs else 0.01
            return {
                "forecasted_costs": [float(avg_cost) for _ in range(days_ahead)],
                "average_daily_cost": float(avg_cost),
                "total_forecast": float(avg_cost * days_ahead),
                "confidence_interval": {
                    "lower": float(avg_cost * days_ahead * 0.8),
                    "upper": float(avg_cost * days_ahead * 1.2)
                },
                "trend": "stable",
                "daily_change_rate": 0.0,
                "provider": provider,
                "forecast_start_date": end_date.strftime("%Y-%m-%d"),
                "forecast_end_date": (end_date + timedelta(days=days_ahead)).strftime("%Y-%m-%d"),
                "historical_days_used": len(historical_costs),
                "model_type": "average_baseline",
                "note": "Limited historical data available. Using simple average-based forecast.",
                "demo_mode": use_demo,
            }
        
        # Generate forecast
        forecast_result = forecast_costs(historical_costs, days_ahead)
        
        # Add metadata
        forecast_result["provider"] = provider
        forecast_result["forecast_start_date"] = end_date.strftime("%Y-%m-%d")
        forecast_result["forecast_end_date"] = (end_date + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        forecast_result["historical_days_used"] = len(historical_costs)
        forecast_result["demo_mode"] = use_demo
        
        return forecast_result
        
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error generating forecast: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate forecast: {str(e)}")

@router.get("/forecast/all")
async def get_all_providers_forecast(
    days_ahead: int = 30
):
    """Get cost forecasts for all providers"""
    try:
        forecasts = {}
        
        for provider in ["aws", "gcp", "azure"]:
            try:
                forecast = await get_cost_forecast(provider, days_ahead)
                forecasts[provider] = forecast
            except Exception as e:
                logger.warning(f"Could not generate forecast for {provider}: {str(e)}")
                forecasts[provider] = {"error": str(e)}
        
        return forecasts
    except Exception as e:
        logger.error(f"Error generating forecasts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate forecasts: {str(e)}")
