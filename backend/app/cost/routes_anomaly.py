from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime
from bson import ObjectId
import logging

from app.auth.auth_utils import get_current_user
from app.database.mongo_client import get_database

router = APIRouter()
logger = logging.getLogger(__name__)

DB = get_database()
anomalies_collection = DB["cost_anomalies"]

@router.get("/anomalies")
async def get_anomalies(
    acknowledged: bool = None,
    provider: str = None
):
    """Get cost anomalies with optional filters"""
    try:
        query = {}
        if acknowledged is not None:
            query["acknowledged"] = acknowledged
        if provider:
            query["provider"] = provider
        
        anomalies = []
        cursor = anomalies_collection.find(query).sort("detected_at", -1).limit(100)
        
        for doc in cursor:
            doc["id"] = str(doc["_id"])
            doc.pop("_id", None)
            # Convert datetime to string
            doc["detected_at"] = doc["detected_at"].isoformat() if isinstance(doc["detected_at"], datetime) else doc["detected_at"]
            anomalies.append(doc)
        
        return anomalies
    except Exception as e:
        logger.error(f"Error fetching anomalies: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch anomalies: {str(e)}")

@router.put("/anomalies/{anomaly_id}/acknowledge")
async def acknowledge_anomaly(
    anomaly_id: str
):
    """Mark an anomaly as acknowledged"""
    try:
        result = anomalies_collection.update_one(
            {"_id": ObjectId(anomaly_id)},
            {"$set": {"acknowledged": True, "acknowledged_at": datetime.utcnow()}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Anomaly not found")
        
        return {"message": "Anomaly acknowledged"}
    except Exception as e:
        logger.error(f"Error acknowledging anomaly: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to acknowledge anomaly: {str(e)}")

@router.get("/anomalies/summary")
async def get_anomalies_summary():
    """Get summary of anomalies by provider and severity"""
    try:
        pipeline = [
            {"$match": {"acknowledged": False}},
            {"$group": {
                "_id": {"provider": "$provider", "severity": "$severity"},
                "count": {"$sum": 1},
                "total_cost": {"$sum": "$cost"}
            }}
        ]
        
        results = list(anomalies_collection.aggregate(pipeline))
        
        summary = {
            "total_unacknowledged": sum(r["count"] for r in results),
            "by_provider": {},
            "by_severity": {"critical": 0, "warning": 0, "normal": 0}
        }
        
        for result in results:
            provider = result["_id"]["provider"]
            severity = result["_id"]["severity"]
            count = result["count"]
            
            if provider not in summary["by_provider"]:
                summary["by_provider"][provider] = {"count": 0, "total_cost": 0}
            
            summary["by_provider"][provider]["count"] += count
            summary["by_provider"][provider]["total_cost"] += result["total_cost"]
            summary["by_severity"][severity] += count
        
        return summary
    except Exception as e:
        logger.error(f"Error getting anomaly summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get anomaly summary: {str(e)}")
