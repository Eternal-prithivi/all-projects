import re

# This data structure remains the same
STORAGE_TIERS_DATA = {
    "hot": [
        {"csp": "AWS", "service_name": "S3 Standard", "price_per_gb": 0.023, "retrieval_penalty": 0, "min_duration_penalty": 0},
        {"csp": "GCP", "service_name": "Standard Storage", "price_per_gb": 0.020, "retrieval_penalty": 0, "min_duration_penalty": 0},
        {"csp": "Azure", "service_name": "Hot Blob Storage", "price_per_gb": 0.018, "retrieval_penalty": 0, "min_duration_penalty": 0}
    ],
    "warm": [
        {"csp": "AWS", "service_name": "S3 Standard-IA", "price_per_gb": 0.0125, "retrieval_penalty": 1, "min_duration_penalty": 1},
        {"csp": "GCP", "service_name": "Nearline Storage", "price_per_gb": 0.010, "retrieval_penalty": 1, "min_duration_penalty": 1},
        {"csp": "Azure", "service_name": "Cool Blob Storage", "price_per_gb": 0.010, "retrieval_penalty": 1, "min_duration_penalty": 1}
    ],
    "cold": [
        {"csp": "AWS", "service_name": "S3 Glacier Flexible", "price_per_gb": 0.004, "retrieval_penalty": 5, "min_duration_penalty": 5},
        {"csp": "GCP", "service_name": "Archive Storage", "price_per_gb": 0.0012, "retrieval_penalty": 10, "min_duration_penalty": 10},
        {"csp": "Azure", "service_name": "Archive Storage", "price_per_gb": 0.00099, "retrieval_penalty": 8, "min_duration_penalty": 8}
    ]
}

def get_file_type(filename: str) -> str:
    filename = filename.lower()
    if filename.endswith(('.zip', '.tar', '.gz', '.bak')):
        return "archive"
    if filename.endswith(('.log', '.csv', '.sql', '.json')):
        return "data"
    if filename.endswith(('.jpg', '.jpeg', '.png', '.mp4', '.mov')):
        return "media"
    return "document"

def calculate_initial_placement_score(user_priority: str, user_intent: str, filename: str, file_size_mb: float) -> int:
    score = 0
    file_type = get_file_type(filename)
    filename_lower = filename.lower()
    if user_priority == 'cost': score += 5
    elif user_priority == 'performance': score -= 5
    if user_intent == 'archival': score += 15
    elif user_intent == 'infrequent': score += 10
    if any(keyword in filename_lower for keyword in ['backup', 'archive', 'export', 'log']): score += 5
    if re.search(r'\d{4}[-_]\d{2}[-_]\d{2}', filename_lower): score += 3
    type_scores = {"archive": 5, "data": 3, "media": -5, "document": 0}
    score += type_scores.get(file_type, 0)
    if file_size_mb > 1024: score += 5
    elif file_size_mb > 100: score += 3
    return score

def classify_storage_tier(score: int) -> str:
    if score > 12: return "cold"
    if score > 5: return "warm"
    return "hot"

def select_best_csp_for_tier(tier: str, user_priority: str) -> dict:
    options = STORAGE_TIERS_DATA.get(tier, [])
    if not options: return None
    best_option = None
    lowest_effective_cost = float('inf')
    for option in options:
        effective_cost = option['price_per_gb']
        if user_priority == 'performance':
            effective_cost += option['retrieval_penalty'] * 2
        else:
            effective_cost += option['retrieval_penalty']
        effective_cost += option['min_duration_penalty']
        if effective_cost < lowest_effective_cost:
            lowest_effective_cost = effective_cost
            best_option = option
    return best_option

# --- CHANGE: This is the upgraded main function for Model 1 ---
def get_initial_placement_recommendation(
    user_priority: str, user_intent: str, filename: str, file_size_mb: float
) -> dict:
    """
    Runs the full analysis and returns the best recommendation, plus a full list
    of options for the determined tier across all CSPs.
    """
    score = calculate_initial_placement_score(user_priority, user_intent, filename, file_size_mb)
    tier = classify_storage_tier(score)
    
    # Find the single best recommendation as before
    best_recommendation = select_best_csp_for_tier(tier, user_priority)
    
    # Also get all available options for that tier
    all_options_for_tier = STORAGE_TIERS_DATA.get(tier, [])
    
    return {
        "analysis_score": score,
        "determined_tier": tier,
        "recommendation": best_recommendation,
        # --- NEW: Provide all options so the frontend can make smart overrides ---
        "options_by_csp": {opt['csp']: opt for opt in all_options_for_tier}
    }

