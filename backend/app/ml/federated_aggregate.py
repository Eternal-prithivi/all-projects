"""
Privacy-oriented federated statistics round (report §3 layer 6).

Does not move raw files or credentials across tenants. Aggregates anonymized
feature-bucket statistics from evaluated feedback into a shared round document
for improved global priors (demo-safe, no paid FL infrastructure).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from pymongo.database import Database

ROUNDS_COLLECTION = "ml_federated_rounds"


def _bucket_key(features: Dict[str, float]) -> str:
    priority = "cost" if features.get("priority_cost") else (
        "performance" if features.get("priority_performance") else "balanced"
    )
    intent = "archival" if features.get("intent_archival") else (
        "infrequent" if features.get("intent_infrequent") else "frequent"
    )
    size = float(features.get("file_size_mb", 0.0))
    size_band = "large" if size > 100 else "small"
    return f"{priority}|{intent}|{size_band}"


def run_federated_statistics_round(db: Database, limit: int = 2000) -> Dict[str, Any]:
    """
    Aggregate mean feedback scores per anonymized feature bucket across users.
    """
    cursor = db["ml_predictions"].find(
        {
            "evaluation_status": "evaluated",
            "feedback_score": {"$exists": True},
            "input_features": {"$exists": True},
            "final_tier": {"$exists": True},
        }
    ).limit(limit)

    buckets: Dict[str, Dict[str, Any]] = {}
    for doc in cursor:
        features = doc.get("input_features") or {}
        if not isinstance(features, dict):
            continue
        key = _bucket_key(features)
        bucket = buckets.setdefault(
            key,
            {"count": 0, "score_sum": 0.0, "tier_counts": {"hot": 0, "warm": 0, "cold": 0}},
        )
        bucket["count"] += 1
        bucket["score_sum"] += float(doc.get("feedback_score", 0.0) or 0.0)
        tier = doc.get("final_tier")
        if tier in bucket["tier_counts"]:
            bucket["tier_counts"][tier] += 1

    aggregated: List[Dict[str, Any]] = []
    for key, stats in buckets.items():
        count = stats["count"]
        if count < 2:
            continue
        aggregated.append(
            {
                "bucket": key,
                "sample_count": count,
                "mean_feedback_score": round(stats["score_sum"] / count, 4),
                "tier_distribution": stats["tier_counts"],
            }
        )

    round_doc = {
        "completed_at": datetime.utcnow(),
        "participant_samples": sum(b["count"] for b in buckets.values()),
        "bucket_count": len(aggregated),
        "aggregates": sorted(aggregated, key=lambda row: -row["sample_count"])[:50],
        "method": "federated_statistics_v1",
    }
    db[ROUNDS_COLLECTION].insert_one(round_doc)
    round_doc.pop("_id", None)
    if "completed_at" in round_doc and hasattr(round_doc["completed_at"], "isoformat"):
        round_doc["completed_at"] = round_doc["completed_at"].isoformat()
    return round_doc


def latest_federated_round(db: Database) -> Dict[str, Any]:
    doc = db[ROUNDS_COLLECTION].find_one(sort=[("completed_at", -1)])
    if not doc:
        return {"available": False}
    doc["_id"] = str(doc["_id"])
    if isinstance(doc.get("completed_at"), datetime):
        doc["completed_at"] = doc["completed_at"].isoformat()
    doc["available"] = True
    return doc
