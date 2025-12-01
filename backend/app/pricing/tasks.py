# backend/app/pricing/tasks.py

from celery import shared_task
from datetime import datetime, timedelta
from app.pricing.pricing_fetcher import fetch_all_pricing
from app.database.mongo_client import get_database
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

@shared_task(name="update_pricing_cache")
def update_pricing_cache():
    """
    Celery task to update pricing cache weekly.
    Scheduled in celery_worker.py
    """
    try:
        logger.info(f"Starting weekly pricing update")
        
        # Fetch fresh pricing from all providers
        pricing_data = fetch_all_pricing()
        
        # Store in MongoDB
        db = get_database()
        pricing_collection = db["pricing_cache"]
        pricing_collection.insert_one(pricing_data)
        
        # Clean up old pricing (keep last 12 weeks)
        old_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        pricing_collection.delete_many({
            "last_updated": {"$lt": (old_date - timedelta(weeks=12)).isoformat()}
        })
        
        logger.info(f"Pricing updated successfully")
        
        return {
            "status": "success",
            "last_updated": pricing_data['last_updated']
        }
        
    except Exception as e:
        logger.error(f"Error updating pricing: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
