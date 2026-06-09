"""
Multi-signal lifecycle intelligence for storage tier decisions.

Beyond simple last-accessed dates, evaluates access velocity, economic viability,
tier-change cooldowns, upload intent, and archive retrieval risk — similar to
enterprise lifecycle policies (S3 Intelligent-Tiering / GCS Autoclass heuristics)
but transparent and user-policy-aware.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.cloud.providers import normalize_provider
from app.storage.lifecycle_policy import demotion_thresholds
from app.storage.optimizer import STORAGE_TIERS_DATA
from app.storage.storage_tiers import normalize_lifecycle_tier

# Economic & stability guards
MIN_MONTHLY_SAVINGS_USD = 0.08
MIN_TIER_COOLDOWN_DAYS = 14
THRASHING_TRANSITION_COUNT = 5
THRASHING_MIN_SAVINGS_USD = 0.75

# Access pattern windows
BURST_WINDOW_DAYS = 7
RECENCY_GUARD_DAYS = 10
VELOCITY_HEATING_RATIO = 0.35

# Archive retrieval estimate (USD per GB) for breakeven on cold demotion
ESTIMATED_COLD_RETRIEVAL_PER_GB = 0.02

TIER_MONTHLY_FALLBACK = {"hot": 0.023, "warm": 0.0125, "cold": 0.004}


def _as_utc(value: Any) -> Optional[datetime]:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _days_since(value: Any, now: datetime, fallback: int = 0) -> int:
    dt = _as_utc(value)
    if not dt:
        return fallback
    return max((now - dt).days, 0)


def _tier_monthly_cost_per_gb(csp: str, tier: str) -> float:
    for option in STORAGE_TIERS_DATA.get(tier, []):
        if option.get("csp") == csp:
            return float(option.get("price_per_gb", TIER_MONTHLY_FALLBACK.get(tier, 0.023)))
    return TIER_MONTHLY_FALLBACK.get(tier, 0.023)


def _parse_access_history(file_record: Dict[str, Any]) -> List[datetime]:
    raw = file_record.get("access_history") or []
    parsed: List[datetime] = []
    for item in raw:
        dt = _as_utc(item)
        if dt:
            parsed.append(dt)
    last = _as_utc(file_record.get("last_accessed_at"))
    if last and (not parsed or parsed[-1] != last):
        parsed.append(last)
    return sorted(parsed)


def compute_access_metrics(file_record: Dict[str, Any], now: Optional[datetime] = None) -> Dict[str, Any]:
    """Derive access velocity and pattern metrics from download history."""
    now = now or datetime.now(timezone.utc)
    history = _parse_access_history(file_record)
    total_lifetime = max(int(file_record.get("access_frequency_score", 0) or 0), len(history))

    def count_in_window(days: int) -> int:
        cutoff = now - timedelta(days=days)
        return sum(1 for dt in history if dt >= cutoff)

    last_7d = count_in_window(7)
    last_14d = count_in_window(14)
    last_30d = count_in_window(30)
    prior_30d = sum(
        1 for dt in history
        if now - timedelta(days=60) <= dt < now - timedelta(days=30)
    )
    velocity_ratio = last_7d / max(last_30d, 1)
    is_heating = last_7d >= 1 and velocity_ratio >= VELOCITY_HEATING_RATIO
    is_burst = last_7d >= 2 or (last_14d >= 3 and last_30d >= 4)

    avg_gap_days = None
    if len(history) >= 2:
        gaps = [(history[i] - history[i - 1]).days for i in range(1, len(history))]
        avg_gap_days = round(sum(gaps) / len(gaps), 1)

    upload_age = _days_since(
        file_record.get("upload_date") or file_record.get("created_at"),
        now,
    )
    inactive_days = _days_since(
        file_record.get("last_accessed_at"),
        now,
        fallback=upload_age,
    )

    return {
        "accesses_last_7d": last_7d,
        "accesses_last_14d": last_14d,
        "accesses_last_30d": last_30d,
        "accesses_prior_30d": prior_30d,
        "access_velocity_ratio": round(velocity_ratio, 3),
        "is_access_heating": is_heating,
        "is_burst_pattern": is_burst,
        "avg_days_between_accesses": avg_gap_days,
        "inactive_days": inactive_days,
        "upload_age_days": upload_age,
        "lifetime_access_count": total_lifetime,
    }


def _file_size_gb(file_record: Dict[str, Any]) -> float:
    size_bytes = file_record.get("size_bytes") or file_record.get("file_size") or 0
    try:
        return max(float(size_bytes) / (1024 ** 3), 0.001)
    except (TypeError, ValueError):
        return 0.001


def estimate_monthly_savings(file_record: Dict[str, Any], target_tier: str) -> float:
    current_tier = normalize_lifecycle_tier(file_record.get("storage_class")) or "hot"
    try:
        csp = normalize_provider(file_record.get("csp", "AWS"))
    except ValueError:
        csp = "AWS"
    size_gb = _file_size_gb(file_record)
    current_cost = _tier_monthly_cost_per_gb(csp, current_tier)
    target_cost = _tier_monthly_cost_per_gb(csp, target_tier)
    return max((current_cost - target_cost) * size_gb, 0.0)


def evaluate_demotion_eligibility(
    file_record: Dict[str, Any],
    target_tier: str,
    now: Optional[datetime] = None,
    *,
    policy: Optional[str] = None,
) -> Tuple[bool, Dict[str, Any]]:
    """
    Returns (eligible, signals) where signals explains scores, blockers, and boosts.
    """
    now = now or datetime.now(timezone.utc)
    resolved_policy = policy or file_record.get("lifecycle_policy", "auto")
    hot_days, cold_days = demotion_thresholds(resolved_policy)
    metrics = compute_access_metrics(file_record, now)
    upload_age = metrics["upload_age_days"]
    inactive = metrics["inactive_days"]

    blockers: List[str] = []
    boosts: List[str] = []

    # Base inactivity thresholds (policy-specific)
    if target_tier == "warm":
        if upload_age < hot_days or inactive < hot_days:
            blockers.append(f"inactive_under_{hot_days}d")
    elif target_tier == "cold":
        if inactive < cold_days:
            blockers.append(f"inactive_under_{cold_days}d")

    # Recency & velocity guards
    if metrics["accesses_last_14d"] >= 1 and target_tier in ("warm", "cold"):
        blockers.append("accessed_within_14d")
    if metrics["is_access_heating"]:
        blockers.append("access_velocity_heating")
    if metrics["is_burst_pattern"] and target_tier == "cold":
        blockers.append("burst_access_pattern")

    # Upload intent respect
    upload_intent = (file_record.get("upload_user_intent") or "").lower()
    upload_priority = (file_record.get("upload_user_priority") or "").lower()
    if upload_intent == "frequent" and inactive < max(hot_days, 45):
        blockers.append("upload_intent_frequent")
    if upload_priority == "performance" and inactive < max(hot_days, 45):
        blockers.append("upload_priority_performance")

    # Tier change cooldown & thrashing
    days_since_tier_change = _days_since(file_record.get("last_tier_change"), now, fallback=9999)
    transition_count = int(file_record.get("tier_transition_count", 0) or 0)
    if days_since_tier_change < MIN_TIER_COOLDOWN_DAYS:
        blockers.append("tier_cooldown")
    if transition_count >= THRASHING_TRANSITION_COUNT:
        monthly_savings = estimate_monthly_savings(file_record, target_tier)
        if monthly_savings < THRASHING_MIN_SAVINGS_USD:
            blockers.append("thrashing_guard")

    # Economic viability
    monthly_savings = estimate_monthly_savings(file_record, target_tier)
    if monthly_savings < MIN_MONTHLY_SAVINGS_USD:
        blockers.append("savings_below_minimum")

    # Cold tier: retrieval breakeven (avoid archive for tiny savings)
    if target_tier == "cold":
        size_gb = _file_size_gb(file_record)
        est_retrieval = size_gb * ESTIMATED_COLD_RETRIEVAL_PER_GB
        annual_savings = monthly_savings * 12
        if est_retrieval > annual_savings * 0.5 and annual_savings < 2.0:
            blockers.append("cold_retrieval_breakeven")

    # Boost signals (used in priority scoring, not eligibility)
    if upload_intent == "archival":
        boosts.append("upload_intent_archival")
    planned = (file_record.get("initial_planned_tier") or "").lower()
    current = normalize_lifecycle_tier(file_record.get("storage_class")) or "hot"
    if planned in ("cold", "warm") and current == "hot" and target_tier == planned:
        boosts.append("matches_initial_ml_tier")
    if metrics["lifetime_access_count"] == 0 and inactive >= hot_days:
        boosts.append("never_accessed")

    eligible = len(blockers) == 0
    return eligible, {
        "metrics": metrics,
        "blockers": blockers,
        "boosts": boosts,
        "monthly_savings_usd": round(monthly_savings, 4),
        "days_since_tier_change": days_since_tier_change,
        "transition_count": transition_count,
        "target_tier": target_tier,
        "policy": resolved_policy,
    }


def evaluate_promotion_eligibility(
    file_record: Dict[str, Any],
    now: Optional[datetime] = None,
) -> Tuple[bool, Dict[str, Any]]:
    """Smarter promotion: recency + velocity, not only lifetime counter."""
    now = now or datetime.now(timezone.utc)
    metrics = compute_access_metrics(file_record, now)
    lifetime = metrics["lifetime_access_count"]
    reasons: List[str] = []

    if metrics["accesses_last_7d"] >= 1:
        reasons.append("recent_access_7d")
    if metrics["is_access_heating"]:
        reasons.append("velocity_heating")
    if lifetime > 2:
        reasons.append("lifetime_access_gt_2")
    if metrics["accesses_last_30d"] >= 3:
        reasons.append("active_last_30d")

    # Promote if: (recent activity + heating) OR (strong 30d activity) OR (legacy rule)
    eligible = (
        (metrics["accesses_last_7d"] >= 1 and metrics["access_velocity_ratio"] >= 0.2)
        or metrics["accesses_last_30d"] >= 3
        or (lifetime > 2 and metrics["accesses_last_14d"] >= 1)
    )
    return eligible, {"metrics": metrics, "reasons": reasons}


def enhanced_priority_score(
    file_record: Dict[str, Any],
    target_tier: str,
    base_priority: Dict[str, Any],
    signals: Dict[str, Any],
) -> Dict[str, Any]:
    """Blend base five-factor score with signal boosts/penalties."""
    score = float(base_priority.get("score", 0))
    factors = dict(base_priority.get("factors") or {})
    boosts = signals.get("boosts") or []
    boost_points = 0.0
    if "upload_intent_archival" in boosts:
        boost_points += 8
    if "matches_initial_ml_tier" in boosts:
        boost_points += 12
    if "never_accessed" in boosts:
        boost_points += 6
    if signals.get("monthly_savings_usd", 0) >= 1.0:
        boost_points += 5
    metrics = signals.get("metrics") or {}
    if metrics.get("inactive_days", 0) >= 120:
        boost_points += 4

    adjusted = round(min(score + boost_points, 100), 2)
    factors["signal_boost"] = round(boost_points, 2)
    factors["access_velocity_ratio"] = metrics.get("access_velocity_ratio")
    factors["accesses_last_30d"] = metrics.get("accesses_last_30d")
    factors["lifecycle_signals"] = {
        "boosts": boosts,
        "blockers": signals.get("blockers"),
    }
    return {
        **base_priority,
        "score": adjusted,
        "factors": factors,
        "signals": signals,
    }


def build_download_access_update(now: Optional[datetime] = None) -> Dict[str, Any]:
    """MongoDB update fragment for rich access tracking on download."""
    now = now or datetime.utcnow()
    return {
        "$set": {"last_accessed_at": now},
        "$inc": {"access_frequency_score": 1},
        "$push": {
            "access_history": {
                "$each": [now],
                "$slice": -20,
            }
        },
    }
