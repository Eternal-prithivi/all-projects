from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict
import numpy as np
from datetime import datetime, timedelta
from sklearn.linear_model import LinearRegression
import logging

from app.auth.auth_utils import get_current_user
from app.cost.manager import get_aws_cost_and_usage, get_gcp_billing_data, get_azure_billing_data

router = APIRouter()
logger = logging.getLogger(__name__)

def extract_daily_costs(cost_data: dict) -> List[float]:
    """Extract daily cost values from API response"""
    results = cost_data.get("data", {}).get("ResultsByTime", [])
    costs = []
    for item in results:
        amount = float(item.get("Total", {}).get("UnblendedCost", {}).get("Amount", 0))
        costs.append(amount)
    return costs

def forecast_costs(historical_costs: List[float], days_ahead: int = 30) -> Dict:
    """Use linear regression to forecast future costs"""
    if len(historical_costs) < 7:
        raise ValueError("Need at least 7 days of historical data for forecasting")
    
    # Prepare training data
    X = np.array(range(len(historical_costs))).reshape(-1, 1)
    y = np.array(historical_costs)
    
    # Train model
    model = LinearRegression()
    model.fit(X, y)
    
    # Make predictions
    future_X = np.array(range(len(historical_costs), len(historical_costs) + days_ahead)).reshape(-1, 1)
    predictions = model.predict(future_X)
    
    # Calculate confidence metrics
    historical_std = np.std(historical_costs)
    recent_avg = np.mean(historical_costs[-7:]) if len(historical_costs) >= 7 else np.mean(historical_costs)
    
    return {
        "forecasted_costs": [max(0, float(p)) for p in predictions],  # Ensure non-negative
        "average_daily_cost": float(recent_avg),
        "total_forecast": float(max(0, sum(predictions))),
        "confidence_interval": {
            "lower": float(max(0, sum(predictions) - 1.96 * historical_std * np.sqrt(days_ahead))),
            "upper": float(sum(predictions) + 1.96 * historical_std * np.sqrt(days_ahead))
        },
        "trend": "increasing" if model.coef_[0] > 0 else "decreasing",
        "daily_change_rate": float(model.coef_[0])
    }

@router.get("/forecast/{provider}")
async def get_cost_forecast(
    provider: str,
    days_ahead: int = 30,
    demo_mode: bool = False
):
    """Get cost forecast for the next N days based on historical data"""
    try:
        # Set end_date for all modes
        end_date = datetime.utcnow()
        
        # DEMO MODE: Generate synthetic data to test ML model
        if demo_mode:
            logger.info("Demo mode enabled - generating synthetic cost data with upward trend")
            # Generate 90 days of synthetic data with increasing trend
            base_cost = 10.0  # Start at $10/day
            daily_increase = 0.15  # Increase by $0.15 per day
            noise_level = 2.0  # Random variation
            
            historical_costs = []
            for day in range(90):
                # Linear trend + random noise
                cost = base_cost + (daily_increase * day) + np.random.uniform(-noise_level, noise_level)
                historical_costs.append(max(0.01, cost))  # Ensure positive
            
            logger.info(f"Generated {len(historical_costs)} days of demo data. First: ${historical_costs[0]:.2f}, Last: ${historical_costs[-1]:.2f}")
        else:
            # Fetch last 90 days of data for better prediction
            start_date = end_date - timedelta(days=90)
            
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            
            # Get historical data
            if provider == "aws":
                historical_data = get_aws_cost_and_usage(start_str, end_str, "DAILY")
            elif provider == "gcp":
                historical_data = get_gcp_billing_data(start_str, end_str)
            elif provider == "azure":
                historical_data = get_azure_billing_data(start_str, end_str)
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
                "note": "Limited historical data available. Using simple average-based forecast."
            }
        
        # Generate forecast
        forecast_result = forecast_costs(historical_costs, days_ahead)
        
        # Add metadata
        forecast_result["provider"] = provider
        forecast_result["forecast_start_date"] = end_date.strftime("%Y-%m-%d")
        forecast_result["forecast_end_date"] = (end_date + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        forecast_result["historical_days_used"] = len(historical_costs)
        
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
