from celery import shared_task
from datetime import datetime, timedelta
import numpy as np
import logging

from app.database.mongo_client import get_database
from app.cost.manager import get_aws_cost_and_usage, get_gcp_billing_data, get_azure_billing_data

logger = logging.getLogger(__name__)
DB = get_database()
anomalies_collection = DB["cost_anomalies"]

def detect_anomaly_zscore(costs: list, threshold: float = 2.0) -> dict:
    """Detect anomalies using Z-score method"""
    if len(costs) < 7:
        return {"is_anomaly": False, "reason": "Insufficient data"}
    
    costs_array = np.array(costs)
    mean = np.mean(costs_array)
    std = np.std(costs_array)
    
    if std == 0:
        return {"is_anomaly": False, "reason": "No variation in costs"}
    
    latest_cost = costs[-1]
    z_score = (latest_cost - mean) / std
    
    is_anomaly = abs(z_score) > threshold
    
    return {
        "is_anomaly": is_anomaly,
        "z_score": float(z_score),
        "mean": float(mean),
        "std": float(std),
        "latest_cost": float(latest_cost),
        "deviation_percentage": float(((latest_cost - mean) / mean * 100) if mean > 0 else 0),
        "severity": "critical" if abs(z_score) > 3 else "warning" if abs(z_score) > 2 else "normal"
    }

@shared_task(name="check_cost_anomalies")
def check_cost_anomalies():
    """Daily Celery task to check for cost anomalies across all providers"""
    logger.info("Starting cost anomaly detection...")
    
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        providers = ["aws", "gcp", "azure"]
        anomalies_found = []
        
        for provider in providers:
            try:
                # Fetch cost data
                if provider == "aws":
                    cost_data = get_aws_cost_and_usage(start_str, end_str, "DAILY")
                elif provider == "gcp":
                    cost_data = get_gcp_billing_data(start_str, end_str)
                elif provider == "azure":
                    cost_data = get_azure_billing_data(start_str, end_str)
                else:
                    continue
                
                # Extract daily costs
                results = cost_data.get("data", {}).get("ResultsByTime", [])
                costs = [float(item.get("Total", {}).get("UnblendedCost", {}).get("Amount", 0)) for item in results]
                
                if len(costs) < 7:
                    logger.warning(f"Insufficient cost data for {provider}")
                    continue
                
                # Detect anomaly
                anomaly_result = detect_anomaly_zscore(costs)
                
                if anomaly_result["is_anomaly"]:
                    anomaly_doc = {
                        "provider": provider,
                        "detected_at": datetime.utcnow(),
                        "date": end_date.strftime("%Y-%m-%d"),
                        "cost": anomaly_result["latest_cost"],
                        "expected_cost": anomaly_result["mean"],
                        "deviation_percentage": anomaly_result["deviation_percentage"],
                        "severity": anomaly_result["severity"],
                        "z_score": anomaly_result["z_score"],
                        "acknowledged": False
                    }
                    
                    # Store in database
                    anomalies_collection.insert_one(anomaly_doc)
                    anomalies_found.append(anomaly_doc)
                    
                    logger.warning(f"Cost anomaly detected for {provider}: ${anomaly_result['latest_cost']:.2f} "
                                 f"(expected ${anomaly_result['mean']:.2f}, deviation {anomaly_result['deviation_percentage']:.1f}%)")
            
            except Exception as e:
                logger.error(f"Error checking anomalies for {provider}: {str(e)}")
        
        logger.info(f"Anomaly detection complete. Found {len(anomalies_found)} anomalies.")
        return {"anomalies_found": len(anomalies_found), "details": anomalies_found}
    
    except Exception as e:
        logger.error(f"Error in anomaly detection task: {str(e)}")
        return {"error": str(e)}
