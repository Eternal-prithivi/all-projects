"""
Lightweight reinforcement-learning policy for storage tier selection (report §3.4 Step 5).

Uses a contextual bandit (Q-table over discretized workload states) updated from
evaluated user feedback rewards. Complements the supervised ensemble rather than
replacing it.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from pymongo.database import Database

from app.ml.storage_ensemble import TIERS

COLLECTION = "ml_rl_policy"
DEFAULT_EPSILON = 0.08
RL_BLEND_WEIGHT = 0.25  # How much RL can shift tier when experienced


def _size_bucket(file_size_mb: float) -> str:
    if file_size_mb > 1024:
        return "xlarge"
    if file_size_mb > 100:
        return "large"
    if file_size_mb > 10:
        return "medium"
    return "small"


def state_key_from_features(features: Dict[str, float]) -> str:
    priority = "cost" if features.get("priority_cost") else (
        "performance" if features.get("priority_performance") else "balanced"
    )
    intent = "archival" if features.get("intent_archival") else (
        "infrequent" if features.get("intent_infrequent") else "frequent"
    )
    file_type = int(features.get("file_type_code", 3))
    size_bucket = _size_bucket(float(features.get("file_size_mb", 0.0)))
    return f"{priority}|{intent}|ft{file_type}|{size_bucket}"


def _empty_q() -> Dict[str, float]:
    return {tier: 0.0 for tier in TIERS}


def get_policy_entry(db: Database, state_key: str) -> Dict[str, Any]:
    doc = db[COLLECTION].find_one({"_id": state_key})
    if not doc:
        return {
            "_id": state_key,
            "q_values": _empty_q(),
            "visit_count": 0,
            "updated_at": None,
        }
    q_values = doc.get("q_values") or _empty_q()
    for tier in TIERS:
        q_values.setdefault(tier, 0.0)
    return doc


def select_tier(
    db: Database,
    *,
    state_key: str,
    ensemble_tier: str,
    epsilon: float = DEFAULT_EPSILON,
) -> Dict[str, Any]:
    """Epsilon-greedy tier selection blended with ensemble recommendation."""
    import random

    entry = get_policy_entry(db, state_key)
    q_values: Dict[str, float] = entry.get("q_values") or _empty_q()
    visits = int(entry.get("visit_count", 0) or 0)

    explore = random.random() < epsilon and visits > 0
    if explore:
        rl_tier = random.choice(list(TIERS))
        source = "explore"
    else:
        rl_tier = max(TIERS, key=lambda tier: (q_values.get(tier, 0.0), -TIERS.index(tier)))
        source = "exploit"

    if visits < 5:
        final_tier = ensemble_tier
        blend_mode = "ensemble_only"
    elif rl_tier == ensemble_tier:
        final_tier = ensemble_tier
        blend_mode = "agreement"
    else:
        # Conservative blend: prefer ensemble unless RL is clearly better
        rl_best = q_values.get(rl_tier, 0.0)
        ens_score = q_values.get(ensemble_tier, 0.0)
        if rl_best - ens_score >= 0.15:
            final_tier = rl_tier
            blend_mode = "rl_override"
        else:
            final_tier = ensemble_tier
            blend_mode = "ensemble_guarded"

    return {
        "state_key": state_key,
        "ensemble_tier": ensemble_tier,
        "rl_tier": rl_tier,
        "final_tier": final_tier,
        "blend_mode": blend_mode,
        "selection_source": source,
        "visit_count": visits,
        "q_values": {tier: round(q_values.get(tier, 0.0), 4) for tier in TIERS},
    }


def update_q_value(
    db: Database,
    *,
    state_key: str,
    action_tier: str,
    reward: float,
    learning_rate: float = 0.12,
) -> Dict[str, Any]:
    """Q-learning style update: Q(s,a) <- Q(s,a) + alpha * (reward - Q(s,a))."""
    if action_tier not in TIERS:
        return {"updated": False, "reason": "invalid_tier"}

    entry = get_policy_entry(db, state_key)
    q_values = dict(entry.get("q_values") or _empty_q())
    old = float(q_values.get(action_tier, 0.0))
    clipped_reward = max(0.0, min(float(reward), 1.0))
    q_values[action_tier] = old + learning_rate * (clipped_reward - old)

    db[COLLECTION].update_one(
        {"_id": state_key},
        {
            "$set": {
                "q_values": q_values,
                "updated_at": datetime.utcnow(),
            },
            "$inc": {"visit_count": 1},
        },
        upsert=True,
    )
    return {
        "updated": True,
        "state_key": state_key,
        "action_tier": action_tier,
        "reward": clipped_reward,
        "new_q": round(q_values[action_tier], 4),
    }


def update_policy_from_feedback(db: Database, limit: int = 500) -> Dict[str, Any]:
    """Update Q-table from evaluated storage predictions with feedback scores."""
    cursor = db["ml_predictions"].find(
        {
            "evaluation_status": "evaluated",
            "feedback_score": {"$exists": True, "$ne": None},
            "input_features": {"$exists": True},
            "final_tier": {"$exists": True},
        }
    ).sort("evaluated_at", -1).limit(limit)

    updated = 0
    skipped = 0
    for doc in cursor:
        features = doc.get("input_features")
        tier = doc.get("final_tier")
        score = doc.get("feedback_score")
        if not isinstance(features, dict) or tier not in TIERS or score is None:
            skipped += 1
            continue
        state_key = state_key_from_features(features)
        update_q_value(db, state_key=state_key, action_tier=tier, reward=float(score))
        updated += 1

    return {"states_updated": updated, "skipped": skipped}


def get_policy_summary(db: Database, limit: int = 20) -> Dict[str, Any]:
    total = db[COLLECTION].count_documents({})
    top = list(
        db[COLLECTION].find().sort("visit_count", -1).limit(limit)
    )
    for row in top:
        row["_id"] = str(row["_id"])
        if isinstance(row.get("updated_at"), datetime):
            row["updated_at"] = row["updated_at"].isoformat()
    return {"total_states": total, "top_states": top}
