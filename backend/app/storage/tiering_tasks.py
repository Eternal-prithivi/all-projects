from celery import shared_task
from pymongo import MongoClient
from datetime import datetime, timedelta, timezone

from app.utils.config import settings
from app.storage.manager import change_tier_on_aws, change_tier_on_gcp, change_tier_on_azure

# This map is now used for both demotions and promotions across all tiers.
TIER_MAP = {
    "AWS": {"hot": "STANDARD", "warm": "STANDARD_IA", "cold": "GLACIER"},
    "GCP": {"hot": "STANDARD", "warm": "NEARLINE", "cold": "ARCHIVE"},
    "Azure": {"hot": "Hot", "warm": "Cool", "cold": "Archive"}
}

# Helper lists for easier querying
HOT_TIER_NAMES = ["Standard", "S3 Standard", "Standard Storage", "Hot Blob Storage"]
WARM_TIER_NAMES = ["STANDARD_IA", "NEARLINE", "Cool"]
COLD_TIER_NAMES = ["GLACIER", "ARCHIVE", "Archive"]

@shared_task(name="app.storage.tiering_tasks.run_storage_optimization")
def run_storage_optimization():
    """
    The main scheduled task for the complete long-term storage optimization model.
    Handles multi-level demotions and intelligent, one-level-up promotions.
    """
    print(f"\n--- [{datetime.now(timezone.utc)}] Running Scheduled Storage Optimization Task ---")
    
    mongo_client = MongoClient(settings.MONGO_CONNECTION_STRING)
    db = mongo_client['CloudResourceOptimizationDB']
    files_db = db["files"]

    now = datetime.now(timezone.utc)
    
    tier_change_functions = {
        "AWS": change_tier_on_aws,
        "GCP": change_tier_on_gcp,
        "Azure": change_tier_on_azure
    }

    # --- PART 1: TIERING DOWN (DEMOTION LOGIC) ---
    
    # --- Demotion 1: Hot -> Warm ---
    print("\n[INFO] --- Starting Demotion Analysis (Hot -> Warm) ---")
    cooldown_period = now - timedelta(days=30)
    thirty_days_ago = now - timedelta(days=30)
    
    candidates_to_warm = list(files_db.find({
        "storage_class": {"$in": HOT_TIER_NAMES},
        "upload_date": {"$lt": cooldown_period},
        "$or": [{"last_accessed_at": None}, {"last_accessed_at": {"$lt": thirty_days_ago}}]
    }))

    print(f"Found {len(candidates_to_warm)} candidates to move to WARM storage.")
    for file_record in candidates_to_warm:
        # This is a helper function to perform the actual move
        _perform_tier_change(file_record, "warm", tier_change_functions, files_db)

    # --- Demotion 2: Warm -> Cold (Archival) ---
    print("\n[INFO] --- Starting Demotion Analysis (Warm -> Cold) ---")
    # A longer inactivity period is required to move to deep archive.
    ninety_days_ago = now - timedelta(days=90)

    candidates_to_cold = list(files_db.find({
        "storage_class": {"$in": WARM_TIER_NAMES},
        # We check that the file hasn't been touched in a long time (90 days)
        "last_accessed_at": {"$lt": ninety_days_ago}
    }))
    
    print(f"Found {len(candidates_to_cold)} candidates to move to COLD (Archive) storage.")
    for file_record in candidates_to_cold:
        _perform_tier_change(file_record, "cold", tier_change_functions, files_db)


    # --- PART 2: TIERING UP (PROMOTION LOGIC) ---
    print("\n[INFO] --- Starting Promotion Analysis (Warm/Cold -> Hot) ---")
    # --- NEW RULE: Stricter time window of 5 days ---
    five_days_ago = now - timedelta(days=5)
    
    # This query implements the new, stricter "Promotion Threshold".
    candidates_to_promote = list(files_db.find({
        "storage_class": {"$in": WARM_TIER_NAMES + COLD_TIER_NAMES},
        "last_accessed_at": {"$gt": five_days_ago},
        # --- NEW RULE: Stricter frequency of more than 2 accesses ---
        "access_frequency_score": {"$gt": 2} 
    }))

    print(f"Found {len(candidates_to_promote)} candidates for promotion.")
    for file_record in candidates_to_promote:
        current_tier = file_record.get("storage_class")
        
        # --- NEW RULE: Determine the target tier (only one level up) ---
        target_tier_name = ""
        if current_tier in COLD_TIER_NAMES:
            target_tier_name = "warm" # If it's Cold, the next level up is Warm
        elif current_tier in WARM_TIER_NAMES:
            target_tier_name = "hot" # If it's Warm, the next level up is Hot
            
        if target_tier_name:
             _perform_tier_change(file_record, target_tier_name, tier_change_functions, files_db, is_promotion=True)


    print("\n--- Storage Optimization Task Finished ---\n")
    
    mongo_client.close()
    return f"Task complete."

def _perform_tier_change(file_record, target_tier, tier_change_functions, files_db, is_promotion=False):
    """A helper function to perform and log the tier change for a single file."""
    filename = file_record.get("filename")
    csp = file_record.get("csp", "AWS")
    object_key = file_record.get("s3_key")
    
    change_function = tier_change_functions.get(csp)
    new_tier_api_name = TIER_MAP.get(csp, {}).get(target_tier)

    if change_function and new_tier_api_name:
        try:
            action = "Promoting" if is_promotion else "Demoting"
            print(f"[ACTION] {action} '{filename}' on {csp} to {target_tier.upper()} tier ({new_tier_api_name})...")
            
            change_function(object_key, new_tier_api_name)
            
            update_operation = {"$set": {"storage_class": new_tier_api_name, "csp": csp}}
            # If it's a promotion, we also reset the frequency score to re-evaluate its "hotness"
            if is_promotion:
                update_operation["$set"]["access_frequency_score"] = 0

            files_db.update_one({"_id": file_record["_id"]}, update_operation)
            print(f"Successfully moved '{filename}'.")
        except Exception as e:
            print(f"!!! ERROR moving '{filename}': {e}")
    else:
        print(f"[WARNING] No tiering action configured for CSP '{csp}' or tier '{target_tier}'.")

