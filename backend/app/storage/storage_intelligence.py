"""
Storage intelligence layer — cost previews, file insights, portfolio health.

Powers the Storage page differentiation: transparent signals, what-if costs,
tri-cloud comparison, savings proof, and health scoring.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.cloud.providers import normalize_provider
from app.storage.lifecycle_policy import demotion_thresholds, normalize_lifecycle_policy
from app.storage.lifecycle_signals import (
    compute_access_metrics,
    estimate_monthly_savings,
    evaluate_demotion_eligibility,
    evaluate_promotion_eligibility,
)
from app.storage.optimizer import STORAGE_TIERS_DATA, select_best_csp_for_tier
from app.storage.storage_tiers import normalize_lifecycle_tier

TIER_LABELS = {"hot": "Hot", "warm": "Warm", "cold": "Cold / Archive"}


def _size_gb_from_mb(file_size_mb: float) -> float:
    return max(float(file_size_mb) / 1024.0, 0.001)


def _size_gb_from_record(file_record: Dict[str, Any]) -> float:
    size_bytes = file_record.get("size_bytes") or 0
    try:
        return max(float(size_bytes) / (1024 ** 3), 0.001)
    except (TypeError, ValueError):
        return 0.001


def monthly_cost_usd(csp: str, tier: str, size_gb: float) -> float:
    for option in STORAGE_TIERS_DATA.get(tier, []):
        if option.get("csp") == csp:
            return round(float(option["price_per_gb"]) * size_gb, 4)
    return 0.0


def cross_cloud_tier_comparison(
    size_gb: float,
    tier: str,
    user_priority: str = "balanced",
) -> List[Dict[str, Any]]:
    """$/month for the same workload tier on AWS, GCP, and Azure."""
    rows: List[Dict[str, Any]] = []
    for option in STORAGE_TIERS_DATA.get(tier, []):
        csp = option["csp"]
        monthly = monthly_cost_usd(csp, tier, size_gb)
        effective = float(option["price_per_gb"])
        if user_priority == "performance":
            effective += option.get("retrieval_penalty", 0) * 2
        else:
            effective += option.get("retrieval_penalty", 0)
        effective += option.get("min_duration_penalty", 0)
        rows.append(
            {
                "csp": csp,
                "service_name": option["service_name"],
                "price_per_gb": option["price_per_gb"],
                "monthly_cost_usd": monthly,
                "effective_score": round(effective, 4),
                "is_recommended": False,
            }
        )
    if rows:
        best = min(rows, key=lambda r: r["effective_score"])
        best["is_recommended"] = True
    return sorted(rows, key=lambda r: r["monthly_cost_usd"])


def _lifecycle_monthly_blend(
    size_gb: float,
    csp: str,
    user_intent: str,
    lifecycle_policy: str,
    start_tier: str = "hot",
) -> float:
    """
    Simplified 12-month average $/month for what-if scenarios.
    Models gradual demotion for auto/aggressive vs flat for keep_hot.
    """
    policy = normalize_lifecycle_policy(lifecycle_policy)
    if policy == "keep_hot":
        return monthly_cost_usd(csp, start_tier, size_gb)

    hot_m = monthly_cost_usd(csp, "hot", size_gb)
    warm_m = monthly_cost_usd(csp, "warm", size_gb)
    cold_m = monthly_cost_usd(csp, "cold", size_gb)

    if policy == "manual":
        return hot_m

    intent = (user_intent or "active").lower()
    if policy == "aggressive" or intent == "archival":
        # ~2mo hot, 3mo warm, 7mo cold
        return round((2 * hot_m + 3 * warm_m + 7 * cold_m) / 12, 4)
    if intent == "infrequent":
        return round((4 * hot_m + 4 * warm_m + 4 * cold_m) / 12, 4)
    # balanced auto / active
    return round((6 * hot_m + 3 * warm_m + 3 * cold_m) / 12, 4)


def build_cost_preview(
    *,
    file_size_mb: float,
    determined_tier: str,
    user_priority: str = "balanced",
    user_intent: str = "active",
    lifecycle_policy: str = "auto",
    selected_csp: Optional[str] = None,
) -> Dict[str, Any]:
    """12-month what-if and tri-cloud comparison for upload wizard."""
    size_gb = _size_gb_from_mb(file_size_mb)
    tier = determined_tier if determined_tier in ("hot", "warm", "cold") else "warm"
    policy = normalize_lifecycle_policy(lifecycle_policy)
    best = select_best_csp_for_tier(tier, user_priority) or {}
    csp = selected_csp or best.get("csp") or "AWS"
    try:
        csp = normalize_provider(csp)
    except ValueError:
        csp = "AWS"

    placement_monthly = monthly_cost_usd(csp, tier, size_gb)
    keep_hot_monthly = monthly_cost_usd(csp, "hot", size_gb)
    policy_monthly = _lifecycle_monthly_blend(size_gb, csp, user_intent, policy, start_tier=tier)

    scenarios = [
        {
            "id": "keep_hot",
            "label": "Keep fast access (no auto-demote)",
            "monthly_usd": keep_hot_monthly,
            "twelve_month_usd": round(keep_hot_monthly * 12, 2),
        },
        {
            "id": policy,
            "label": f"Your lifecycle policy ({policy.replace('_', ' ')})",
            "monthly_usd": policy_monthly,
            "twelve_month_usd": round(policy_monthly * 12, 2),
        },
    ]
    savings_12m = round(scenarios[0]["twelve_month_usd"] - scenarios[1]["twelve_month_usd"], 2)

    return {
        "size_gb": round(size_gb, 4),
        "determined_tier": tier,
        "selected_csp": csp,
        "placement_monthly_usd": placement_monthly,
        "scenarios": scenarios,
        "estimated_12_month_savings_usd": max(savings_12m, 0),
        "cross_cloud": cross_cloud_tier_comparison(size_gb, tier, user_priority),
        "cross_cloud_by_tier": {
            t: cross_cloud_tier_comparison(size_gb, t, user_priority)
            for t in ("hot", "warm", "cold")
        },
    }


def build_file_insight(file_record: Dict[str, Any], now: Optional[datetime] = None) -> Dict[str, Any]:
    """Per-file transparency: tier alignment, blockers, next action, savings."""
    now = now or datetime.now(timezone.utc)
    current_tier = normalize_lifecycle_tier(file_record.get("storage_class")) or "hot"
    planned = (file_record.get("initial_planned_tier") or current_tier).lower()
    policy = normalize_lifecycle_policy(file_record.get("lifecycle_policy", "auto"))
    metrics = compute_access_metrics(file_record, now)

    next_tier = ""
    if current_tier == "hot":
        next_tier = "warm"
    elif current_tier == "warm":
        next_tier = "cold"

    demotion_eligible = False
    demotion_signals: Dict[str, Any] = {}
    if next_tier:
        demotion_eligible, demotion_signals = evaluate_demotion_eligibility(
            file_record, next_tier, now
        )

    promo_eligible, promo_signals = evaluate_promotion_eligibility(file_record, now)
    pending = file_record.get("lifecycle_pending_demotion")
    lifetime_savings = float(file_record.get("lifecycle_savings_total_usd", 0) or 0)

    if pending:
        next_action = "pending_demotion"
        status = "action"
    elif promo_eligible and current_tier in ("warm", "cold"):
        next_action = "eligible_promotion"
        status = "watch"
    elif demotion_eligible:
        next_action = "eligible_demotion"
        status = "watch"
    elif planned != current_tier and policy != "keep_hot":
        next_action = "tier_drift"
        status = "watch"
    else:
        next_action = "stable"
        status = "aligned"

    blockers = demotion_signals.get("blockers") or []
    boosts = demotion_signals.get("boosts") or []
    monthly_if_moved = (
        demotion_signals.get("monthly_savings_usd", 0) if next_tier else 0
    )

    reasons: List[str] = []
    if blockers:
        reasons.append(f"Blocked: {', '.join(b.replace('_', ' ') for b in blockers[:3])}")
    elif pending:
        execute = pending.get("execute_after")
        reasons.append(f"Move to {TIER_LABELS.get(pending.get('target_tier', ''), 'cheaper tier')} scheduled")
        if execute:
            reasons.append(f"After {str(execute)[:10]}")
    elif demotion_eligible:
        reasons.append(f"Ready to demote → {TIER_LABELS.get(next_tier, next_tier)}")
    elif promo_eligible:
        reasons.append("Recent activity — may promote to faster tier")
    elif planned != current_tier:
        reasons.append(f"ML planned {planned}, currently {current_tier}")
    else:
        reasons.append("Tier matches usage signals")

    return {
        "current_tier": current_tier,
        "planned_tier": planned,
        "lifecycle_policy": policy,
        "status": status,
        "next_action": next_action,
        "blockers": blockers,
        "boosts": boosts,
        "reasons": reasons,
        "monthly_savings_if_moved_usd": monthly_if_moved,
        "lifetime_savings_usd": round(lifetime_savings, 4),
        "access_velocity_ratio": metrics.get("access_velocity_ratio"),
        "accesses_last_30d": metrics.get("accesses_last_30d"),
        "inactive_days": metrics.get("inactive_days"),
    }


def compute_portfolio_health(files: List[Dict[str, Any]], now: Optional[datetime] = None) -> Dict[str, Any]:
    """0–100 score: how well storage aligns with usage and ML intent."""
    now = now or datetime.now(timezone.utc)
    if not files:
        return {
            "score": 100,
            "grade": "A",
            "summary": "No files yet — upload to begin optimization.",
            "factors": {},
        }

    misaligned = 0
    idle_hot = 0
    pending_moves = 0
    protected_sensitive = 0
    total_savings = 0.0

    for f in files:
        insight = build_file_insight(f, now)
        if insight["status"] in ("watch", "action"):
            misaligned += 1
        if insight["next_action"] == "pending_demotion":
            pending_moves += 1
        if f.get("is_sensitive"):
            protected_sensitive += 1
        current = insight["current_tier"]
        if current == "hot" and (insight.get("inactive_days") or 0) >= 30:
            idle_hot += 1
        total_savings += float(f.get("lifecycle_savings_total_usd", 0) or 0)

    n = len(files)
    misaligned_pct = misaligned / n
    idle_hot_pct = idle_hot / n

    score = 100.0
    score -= min(misaligned_pct * 40, 35)
    score -= min(idle_hot_pct * 30, 25)
    score -= min(pending_moves / max(n, 1) * 10, 10)
    score = round(max(min(score, 100), 0), 1)

    if score >= 85:
        grade = "A"
    elif score >= 70:
        grade = "B"
    elif score >= 55:
        grade = "C"
    else:
        grade = "D"

    return {
        "score": score,
        "grade": grade,
        "summary": (
            f"{misaligned} of {n} files could optimize further; "
            f"{idle_hot} hot files idle 30+ days."
            if misaligned or idle_hot
            else f"All {n} files align with current usage signals."
        ),
        "factors": {
            "total_files": n,
            "needs_attention": misaligned,
            "idle_hot_files": idle_hot,
            "pending_tier_moves": pending_moves,
            "sensitive_protected": protected_sensitive,
            "lifetime_savings_usd": round(total_savings, 2),
        },
    }


def compute_savings_summary(
    files: List[Dict[str, Any]],
    lifecycle_reports: Optional[List[Dict[str, Any]]] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Outcome proof widget: savings and recent lifecycle activity."""
    now = now or datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    lifetime = sum(float(f.get("lifecycle_savings_total_usd", 0) or 0) for f in files)
    pending_count = sum(1 for f in files if f.get("lifecycle_pending_demotion"))
    demotions_month = 0
    promotions_month = 0

    if lifecycle_reports:
        for report in lifecycle_reports:
            ran = report.get("ran_at")
            if not ran:
                continue
            ran_dt = ran if isinstance(ran, datetime) else None
            if ran_dt and ran_dt.tzinfo is None:
                ran_dt = ran_dt.replace(tzinfo=timezone.utc)
            if ran_dt and ran_dt >= month_start:
                demotions_month += int(report.get("demotions_completed", 0) or 0)
                promotions_month += int(report.get("promotions_completed", 0) or 0)

    # Estimate monthly run-rate from idle hot files
    estimated_monthly_opportunity = 0.0
    for f in files:
        insight = build_file_insight(f, now)
        if insight["next_action"] in ("eligible_demotion", "pending_demotion"):
            estimated_monthly_opportunity += float(
                insight.get("monthly_savings_if_moved_usd", 0) or 0
            )

    return {
        "lifetime_savings_usd": round(lifetime, 2),
        "estimated_monthly_opportunity_usd": round(estimated_monthly_opportunity, 2),
        "pending_tier_moves": pending_count,
        "demotions_this_month": demotions_month,
        "promotions_this_month": promotions_month,
        "files_tracked": len(files),
    }
