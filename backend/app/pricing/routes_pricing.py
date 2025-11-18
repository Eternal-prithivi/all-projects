# backend/app/pricing/routes_pricing.py

from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
from app.database.mongo_client import get_database

router = APIRouter()

@router.get("/pricing")
async def get_pricing():
    """
    Get cached pricing data for all cloud providers.
    Updates weekly via Celery task.
    """
    try:
        db = get_database()
        pricing_collection = db["pricing_cache"]
        
        # Get latest pricing from cache
        cached_pricing = pricing_collection.find_one(
            {},
            sort=[("last_updated", -1)]
        )
        
        if not cached_pricing:
            # No cache exists, return default pricing
            from app.pricing.pricing_fetcher import fetch_all_pricing
            pricing_data = fetch_all_pricing()
            
            # Store in cache
            pricing_collection.insert_one(pricing_data)
            
            # Remove _id for JSON response
            pricing_data.pop('_id', None)
            return pricing_data
        
        # Check if cache is older than 7 days
        last_updated = datetime.fromisoformat(cached_pricing['last_updated'])
        if datetime.utcnow() - last_updated > timedelta(days=7):
            # Cache expired, fetch new pricing
            from app.pricing.pricing_fetcher import fetch_all_pricing
            pricing_data = fetch_all_pricing()
            pricing_collection.insert_one(pricing_data)
            cached_pricing = pricing_data
        
        # Remove MongoDB _id field
        cached_pricing.pop('_id', None)
        
        return cached_pricing
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching pricing: {str(e)}")

@router.post("/pricing/refresh")
async def refresh_pricing():
    """
    Manually trigger pricing refresh (admin only).
    """
    try:
        from app.pricing.pricing_fetcher import fetch_all_pricing
        
        db = get_database()
        pricing_collection = db["pricing_cache"]
        
        # Fetch fresh pricing
        pricing_data = fetch_all_pricing()
        
        # Insert new pricing
        result = pricing_collection.insert_one(pricing_data)
        
        return {
            "message": "Pricing refreshed successfully",
            "last_updated": pricing_data['last_updated']
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error refreshing pricing: {str(e)}")
