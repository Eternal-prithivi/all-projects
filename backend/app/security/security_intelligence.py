"""
Security vault intelligence — health scoring, per-file insights, cost preview.

Mirrors storage_intelligence.py for the secure vault (hot-tier only, no lifecycle tiers).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.cloud.providers import normalize_provider
from app.security.security_policy import DEFAULT_SECURITY_PREFS, get_user_security_preferences
from app.storage.cloud_credentials import _gcp_secure_replica_bucket_name
from app.storage.storage_intelligence import cross_cloud_tier_comparison, monthly_cost_usd
from app.utils.config import settings

REPLICATION_MULTIPLIER = 1.2
VAULT_TIER = "hot"
_REPLICATION_CSPS = ("AWS", "GCP", "Azure")


def _vault_replication_available(csp: str) -> bool:
    if csp == "AWS":
        return bool((settings.REPLICA_S3_BUCKET_NAME or "").strip())
    if csp == "GCP":
        return bool(_gcp_secure_replica_bucket_name())
    if csp == "Azure":
        return bool((settings.AZURE_SECURE_REPLICA_CONTAINER_NAME or "").strip())
    return False

SCAN_REASON_LABELS: Dict[str, str] = {
    "sensitive_filename": "Sensitive file name (.pem, .env, credentials, etc.)",
    "credit_card_pattern": "Possible credit card number",
    "credential_keywords": "Password or API key keywords",
    "aws_access_key_id": "AWS access key ID",
    "azure_storage_secret": "Azure storage connection string",
    "azure_client_secret": "Azure client secret",
    "gcp_service_account": "GCP service account JSON",
    "gcp_api_key": "GCP API key",
    "pem_private_key": "Private key block (PEM)",
    "ssn_pattern": "Social Security number pattern",
    "email_address": "Email address",
    "private_ip_address": "Private IP address",
    "ml_elevated_risk": "ML risk model flagged elevated sensitivity",
}


def _size_gb_from_bytes(size_bytes: int) -> float:
    try:
        return max(float(size_bytes) / (1024 ** 3), 0.001)
    except (TypeError, ValueError):
        return 0.001


def _as_utc(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return None


def inactive_days(file_record: Dict[str, Any], now: Optional[datetime] = None) -> Optional[int]:
    now = now or datetime.now(timezone.utc)
    last = _as_utc(file_record.get("last_accessed_at")) or _as_utc(file_record.get("upload_date"))
    if not last:
        return None
    return max((now - last).days, 0)


def label_scan_reasons(codes: List[str]) -> List[str]:
    return [SCAN_REASON_LABELS.get(c, c.replace("_", " ").title()) for c in (codes or [])]


def vault_monthly_cost(
    file_record: Dict[str, Any],
    *,
    csp: Optional[str] = None,
) -> float:
    size_gb = _size_gb_from_bytes(int(file_record.get("size_bytes") or 0))
    file_csp = csp or file_record.get("csp") or "AWS"
    try:
        file_csp = normalize_provider(file_csp)
    except ValueError:
        file_csp = "AWS"
    base = monthly_cost_usd(file_csp, VAULT_TIER, size_gb)
    if file_record.get("replication_enabled"):
        return round(base * REPLICATION_MULTIPLIER, 4)
    return base


def build_security_cost_preview(
    *,
    file_size_mb: float,
    encryption_method: str = "server-side",
    selected_csp: Optional[str] = None,
    enable_replication: bool = False,
) -> Dict[str, Any]:
    size_gb = max(float(file_size_mb) / 1024.0, 0.001)
    csp = selected_csp or "AWS"
    try:
        csp = normalize_provider(csp)
    except ValueError:
        csp = "AWS"

    base_monthly = monthly_cost_usd(csp, VAULT_TIER, size_gb)
    replication_available = _vault_replication_available(csp)
    replication_monthly = (
        round(base_monthly * (REPLICATION_MULTIPLIER - 1), 4)
        if enable_replication and replication_available
        else None
    )
    total = base_monthly
    if replication_monthly:
        total = round(base_monthly + replication_monthly, 4)

    cross = []
    for row in cross_cloud_tier_comparison(size_gb, VAULT_TIER, "balanced"):
        rep_extra = (
            round(row["monthly_cost_usd"] * (REPLICATION_MULTIPLIER - 1), 4)
            if enable_replication and _vault_replication_available(row["csp"])
            else None
        )
        cross.append(
            {
                **row,
                "replication_monthly_usd": rep_extra,
                "total_monthly_usd": round(
                    row["monthly_cost_usd"] + (rep_extra or 0), 4
                ),
            }
        )

    return {
        "size_gb": round(size_gb, 4),
        "selected_csp": csp,
        "encryption_method": encryption_method,
        "base_monthly_usd": base_monthly,
        "replication_monthly_usd": replication_monthly,
        "total_monthly_usd": total,
        "replication_available": replication_available,
        "cross_cloud": cross,
    }


def build_security_file_insight(
    file_record: Dict[str, Any],
    *,
    stale_threshold_days: int = DEFAULT_SECURITY_PREFS["stale_file_days"],
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    awaiting = bool(file_record.get("awaiting_encryption_choice"))
    is_sensitive = bool(file_record.get("is_sensitive"))
    is_encrypted = bool(file_record.get("is_encrypted"))
    vault_status = file_record.get("vault_status") or "active"
    inactive = inactive_days(file_record, now)
    scan_codes = file_record.get("scan_reasons") or []
    ml_score = file_record.get("ml_scan_score")

    if awaiting:
        enc_method = "awaiting"
    elif file_record.get("client_side_encrypted"):
        enc_method = "client-side"
    elif file_record.get("encryption_method") == "server-side":
        enc_method = "server-side"
    else:
        enc_method = "none"

    risk_level = "low"
    if is_sensitive or ml_score and float(ml_score) >= 0.65:
        risk_level = "high"
    elif scan_codes or (ml_score and float(ml_score) >= 0.4):
        risk_level = "medium"

    reasons: List[str] = []
    steps: List[str] = []

    if awaiting:
        status = "action"
        next_action = "encrypt_now"
        reasons.append("Waiting for your encryption choice")
        steps.append("Click Encrypt this or open the upload wizard")
    elif is_sensitive and not is_encrypted:
        status = "action"
        next_action = "encrypt_now"
        if file_record.get("encryption_skipped_by_user"):
            reasons.append("Sensitive content stored without Zenith encryption (user choice)")
            steps.append("Re-upload with encryption or delete if this was a mistake")
        else:
            reasons.append("Sensitive content is not encrypted yet")
            steps.append("Choose cloud-managed or browser encryption")
    elif vault_status == "archived":
        status = "watch"
        next_action = "archived"
        reasons.append(
            "File is in the replica vault — restore to primary before download or delete"
        )
    elif inactive is not None and inactive >= stale_threshold_days and vault_status == "active":
        status = "watch"
        next_action = "review_stale"
        reasons.append(f"Not opened in {inactive} days")
        steps.append("Archive, delete, or snooze the reminder")
    elif is_encrypted:
        status = "protected"
        next_action = "download_ok"
        reasons.append("File is encrypted and stored in the secure vault")
    else:
        status = "protected"
        next_action = "stable"
        reasons.append("No action needed")

    if scan_codes:
        labeled = label_scan_reasons(scan_codes)
        reasons.extend(labeled[:3])

    return {
        "status": status,
        "encryption_method": enc_method,
        "risk_level": risk_level,
        "scan_reasons": label_scan_reasons(scan_codes),
        "ml_scan_score": ml_score,
        "next_action": next_action,
        "reasons": reasons[:5],
        "recommended_steps": steps,
        "inactive_days": inactive,
        "replication_enabled": bool(file_record.get("replication_enabled")),
        "vault_status": vault_status,
        "monthly_cost_usd": vault_monthly_cost(file_record),
    }


def compute_vault_health(
    files: List[Dict[str, Any]],
    *,
    username: Optional[str] = None,
    stale_threshold_days: Optional[int] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    if username and stale_threshold_days is None:
        prefs = get_user_security_preferences(username)
        stale_threshold_days = int(prefs.get("stale_file_days", 90))
    stale_threshold_days = stale_threshold_days or 90

    if not files:
        return {
            "score": 100,
            "grade": "A",
            "summary": "No secure files yet — upload to begin protecting data.",
            "factors": {
                "total_files": 0,
                "awaiting_encryption": 0,
                "unencrypted_sensitive": 0,
                "protected_sensitive": 0,
                "stale_files": 0,
                "estimated_monthly_cost_usd": 0,
            },
        }

    awaiting = 0
    unencrypted_sensitive = 0
    protected_sensitive = 0
    stale = 0
    monthly_cost = 0.0

    for f in files:
        if f.get("awaiting_encryption_choice"):
            awaiting += 1
        if f.get("is_sensitive") and not f.get("is_encrypted"):
            unencrypted_sensitive += 1
        if f.get("is_sensitive") and f.get("is_encrypted"):
            protected_sensitive += 1
        insight = build_security_file_insight(
            f, stale_threshold_days=stale_threshold_days, now=now
        )
        if insight["next_action"] == "review_stale":
            stale += 1
        monthly_cost += insight.get("monthly_cost_usd", 0)

    n = len(files)
    score = 100.0
    score -= min((awaiting / n) * 40, 30)
    score -= min((unencrypted_sensitive / n) * 50, 40)
    score -= min((stale / n) * 20, 15)
    score = round(max(min(score, 100), 0), 1)

    if score >= 85:
        grade = "A"
    elif score >= 70:
        grade = "B"
    elif score >= 55:
        grade = "C"
    else:
        grade = "D"

    parts = []
    if awaiting:
        parts.append(f"{awaiting} file(s) still need encryption")
    if protected_sensitive:
        parts.append(f"{protected_sensitive} sensitive file(s) protected")
    if stale:
        parts.append(f"{stale} stale file(s) to review")
    summary = "; ".join(parts) if parts else f"All {n} vault file(s) look healthy."

    return {
        "score": score,
        "grade": grade,
        "summary": summary,
        "factors": {
            "total_files": n,
            "awaiting_encryption": awaiting,
            "unencrypted_sensitive": unencrypted_sensitive,
            "protected_sensitive": protected_sensitive,
            "stale_files": stale,
            "estimated_monthly_cost_usd": round(monthly_cost, 4),
        },
    }


def compute_vault_savings_summary(files: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Portfolio metrics for the security intelligence bar."""
    awaiting = sum(1 for f in files if f.get("awaiting_encryption_choice"))
    stale = sum(
        1
        for f in files
        if build_security_file_insight(f).get("next_action") == "review_stale"
    )
    monthly_cost = sum(vault_monthly_cost(f) for f in files)
    return {
        "awaiting_encryption": awaiting,
        "stale_files": stale,
        "estimated_monthly_cost_usd": round(monthly_cost, 4),
        "files_tracked": len(files),
    }
