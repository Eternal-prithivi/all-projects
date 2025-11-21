# Demo Mode Configuration for Student Project
# Set DEMO_MODE=true in .env to use mock data instead of real API calls

from typing import Dict, Any
from datetime import datetime, timedelta
import random
from app.utils.config import settings

# Enable demo mode via settings (loaded from .env)
DEMO_MODE = settings.DEMO_MODE

class MockDataGenerator:
    """Generate realistic mock data for demo purposes (zero API cost)"""
    
    @staticmethod
    def mock_aws_cost_data(start_date: str, end_date: str, granularity: str = "DAILY") -> Dict[str, Any]:
        """Mock AWS Cost Explorer response"""
        if not DEMO_MODE:
            return None
            
        # Generate realistic cost data
        days = (datetime.strptime(end_date, "%Y-%m-%d") - datetime.strptime(start_date, "%Y-%m-%d")).days
        
        results = []
        for i in range(days):
            date = (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=i)).strftime("%Y-%m-%d")
            next_date = (datetime.strptime(start_date, "%Y-%m-%d") + timedelta(days=i+1)).strftime("%Y-%m-%d")
            
            # Realistic daily cost ($10-50/day)
            daily_cost = round(random.uniform(10, 50), 2)
            
            results.append({
                "TimePeriod": {"Start": date, "End": next_date},
                "Total": {
                    "UnblendedCost": {"Amount": str(daily_cost), "Unit": "USD"}
                },
                "Groups": [
                    {
                        "Keys": ["Amazon EC2"],
                        "Metrics": {"UnblendedCost": {"Amount": str(round(daily_cost * 0.6, 2)), "Unit": "USD"}}
                    },
                    {
                        "Keys": ["Amazon S3"],
                        "Metrics": {"UnblendedCost": {"Amount": str(round(daily_cost * 0.3, 2)), "Unit": "USD"}}
                    },
                    {
                        "Keys": ["AWS CloudTrail"],
                        "Metrics": {"UnblendedCost": {"Amount": str(round(daily_cost * 0.1, 2)), "Unit": "USD"}}
                    }
                ]
            })
        
        return {
            "ResultsByTime": results,
            "ResponseMetadata": {"RequestId": "mock-request-id"}
        }
    
    @staticmethod
    def mock_gcp_vm_metrics(vm_name: str) -> Dict[str, Any]:
        """Mock GCP VM metrics"""
        if not DEMO_MODE:
            return None
        
        return {
            "vm_name": vm_name,
            "cpu_usage": round(random.uniform(20, 80), 1),
            "memory_usage": round(random.uniform(30, 70), 1),
            "disk_io_mb": round(random.uniform(50, 200), 1),
            "network_io_mb": round(random.uniform(20, 100), 1),
            "active_users": random.randint(0, 3),
            "uptime_hours": round(random.uniform(1, 24), 1),
            "estimated_cost_usd": round(random.uniform(0.01, 0.50), 4),
            "status": "RUNNING",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def mock_budget_status(budget_amount: float) -> float:
        """Mock current spending for budget"""
        if not DEMO_MODE:
            return None
        
        # Return 60-90% of budget (realistic)
        return round(budget_amount * random.uniform(0.6, 0.9), 2)
    
    @staticmethod
    def mock_cost_forecast(provider: str, days_ahead: int = 30) -> Dict[str, Any]:
        """Mock cost forecast"""
        if not DEMO_MODE:
            return None
        
        base_cost = random.uniform(500, 1500)
        daily_increase = base_cost * 0.02  # 2% increase per day
        
        predictions = []
        for i in range(days_ahead):
            date = (datetime.utcnow() + timedelta(days=i+1)).strftime("%Y-%m-%d")
            predicted_cost = base_cost + (daily_increase * i)
            predictions.append({
                "date": date,
                "predicted_cost": round(predicted_cost, 2),
                "confidence_lower": round(predicted_cost * 0.9, 2),
                "confidence_upper": round(predicted_cost * 1.1, 2)
            })
        
        return {
            "provider": provider,
            "predictions": predictions,
            "total_predicted": round(sum(p["predicted_cost"] for p in predictions), 2),
            "daily_average": round(sum(p["predicted_cost"] for p in predictions) / days_ahead, 2),
            "trend": "increasing",
            "confidence_interval": 95
        }


# Helper function to check if demo mode is enabled
def is_demo_mode() -> bool:
    """Check if demo mode is enabled"""
    return DEMO_MODE


# Helper to log demo mode usage
def log_demo_mode_call(api_name: str):
    """Log when mock data is used instead of real API"""
    if DEMO_MODE:
        print(f"🎭 DEMO MODE: Using mock data for {api_name} (zero cost)")

