"""Per-user BYOC feature readiness — what instant connect actually unlocks."""

from __future__ import annotations

from typing import Any

from app.byoc.credential_resolver import (
    get_byoc_status,
    resolve_aws_credentials,
    resolve_azure_credentials,
    resolve_gcp_credentials,
)
from app.cloud.providers import normalize_provider, normalize_provider_key
from app.cost.billing_config import azure_billing_configured, gcp_billing_configured

_FEATURE_KEYS = ("storage", "security", "vm", "provision", "cost")

_GAP_ACTIONS = {
    "azure_sp_missing": "settings_byoc_azure_compute",
    "gcp_billing_export_missing": "settings_byoc_gcp_billing",
    "aws_credentials_missing": "settings_byoc_aws",
    "gcp_sa_missing": "settings_byoc_gcp",
    "azure_storage_missing": "settings_byoc_azure",
}


def _aws_storage_ready(creds: dict[str, Any]) -> bool:
    if not creds.get("is_byoc"):
        return False
    if creds.get("connection_method") == "iam_role":
        return bool(creds.get("access_key_id") and creds.get("secret_access_key"))
    return bool(creds.get("access_key_id") and creds.get("secret_access_key"))


def _gcp_sa_ready(creds: dict[str, Any]) -> bool:
    if not creds.get("is_byoc"):
        return False
    return bool((creds.get("service_account_json") or "").strip())


def _azure_storage_ready(creds: dict[str, Any]) -> bool:
    if not creds.get("is_byoc"):
        return False
    return bool(creds.get("account_name") and creds.get("account_key"))


def _azure_sp_ready(creds: dict[str, Any]) -> bool:
    if not creds.get("is_byoc"):
        return False
    return all(
        (creds.get(k) or "").strip()
        for k in ("subscription_id", "tenant_id", "client_id", "client_secret")
    )


def byoc_features_ready(username: str, csp: str) -> dict[str, bool]:
    """Feature flags for an active BYOC connection (all false if not connected)."""
    provider = normalize_provider(csp)
    key = normalize_provider_key(provider)
    if not (get_byoc_status(username).get(key) or {}).get("connected"):
        return {f: False for f in _FEATURE_KEYS}

    if provider == "AWS":
        creds = resolve_aws_credentials(username)
        base = _aws_storage_ready(creds)
        return {
            "storage": base,
            "security": base,
            "vm": base,
            "provision": base,
            "cost": base,
        }

    if provider == "GCP":
        creds = resolve_gcp_credentials(username)
        base = _gcp_sa_ready(creds)
        cost = base and gcp_billing_configured(username)
        return {
            "storage": base,
            "security": base,
            "vm": base,
            "provision": base,
            "cost": cost,
        }

    creds = resolve_azure_credentials(username)
    storage = _azure_storage_ready(creds)
    compute = _azure_sp_ready(creds)
    cost = azure_billing_configured(username) if creds.get("is_byoc") else False
    return {
        "storage": storage,
        "security": storage,
        "vm": compute,
        "provision": compute,
        "cost": cost,
    }


def byoc_setup_gaps(username: str, csp: str) -> list[dict[str, str]]:
    """Human-readable gaps blocking full BYOC unlock for a CSP."""
    provider = normalize_provider(csp)
    key = normalize_provider_key(provider)
    if not (get_byoc_status(username).get(key) or {}).get("connected"):
        return []

    ready = byoc_features_ready(username, provider)
    gaps: list[dict[str, str]] = []

    if provider == "AWS":
        if not ready["storage"]:
            gaps.append({
                "code": "aws_credentials_missing",
                "message": "AWS access keys or IAM role credentials are incomplete.",
                "action": _GAP_ACTIONS["aws_credentials_missing"],
            })
        return gaps

    if provider == "GCP":
        if not ready["storage"]:
            gaps.append({
                "code": "gcp_sa_missing",
                "message": "GCP service account JSON is missing or invalid.",
                "action": _GAP_ACTIONS["gcp_sa_missing"],
            })
        elif not ready["cost"]:
            gaps.append({
                "code": "gcp_billing_export_missing",
                "message": "Add BigQuery billing export dataset and table IDs to unlock Cost.",
                "action": _GAP_ACTIONS["gcp_billing_export_missing"],
            })
        return gaps

    if not ready["storage"]:
        gaps.append({
            "code": "azure_storage_missing",
            "message": "Azure storage account name and key are required.",
            "action": _GAP_ACTIONS["azure_storage_missing"],
        })
    elif not ready["provision"]:
        gaps.append({
            "code": "azure_sp_missing",
            "message": "Add subscription and service principal fields to unlock VMs, Provision, and Cost.",
            "action": _GAP_ACTIONS["azure_sp_missing"],
        })
    elif not ready["cost"]:
        gaps.append({
            "code": "azure_sp_missing",
            "message": "Service principal must be valid for Azure Cost Management.",
            "action": _GAP_ACTIONS["azure_sp_missing"],
        })
    return gaps


def build_byoc_capabilities_payload(username: str) -> dict[str, Any]:
    """Summary for /byoc/status and /cloud/availability."""
    out: dict[str, Any] = {}
    for provider in ("AWS", "GCP", "Azure"):
        key = normalize_provider_key(provider)
        connected = bool((get_byoc_status(username).get(key) or {}).get("connected"))
        if not connected:
            out[key] = {
                "connected": False,
                "features": {f: False for f in _FEATURE_KEYS},
                "gaps": [],
                "unlocked_features": [],
            }
            continue
        features = byoc_features_ready(username, provider)
        gaps = byoc_setup_gaps(username, provider)
        out[key] = {
            "connected": True,
            "features": features,
            "gaps": gaps,
            "unlocked_features": [f for f, ok in features.items() if ok],
        }
    return out


def assert_byoc_feature_ready(username: str, csp: str, feature: Any) -> None:
    """Raise HTTPException when BYOC is connected but feature credentials are incomplete."""
    from fastapi import HTTPException

    provider = normalize_provider(csp)
    key = normalize_provider_key(provider)
    if not (get_byoc_status(username).get(key) or {}).get("connected"):
        return
    feat_key = feature.value if hasattr(feature, "value") else str(feature)
    if byoc_features_ready(username, provider).get(feat_key, False):
        return
    gaps = byoc_setup_gaps(username, provider)
    relevant = gaps
    if feat_key == "cost":
        relevant = [g for g in gaps if g["code"] in ("gcp_billing_export_missing", "azure_sp_missing")]
    elif feat_key in ("vm", "provision"):
        relevant = [g for g in gaps if g["code"] == "azure_sp_missing"]
    code = relevant[0]["code"] if relevant else "byoc_setup_incomplete"
    message = relevant[0]["message"] if relevant else "Complete BYOC setup in Settings."
    action = relevant[0].get("action") if relevant else "settings_byoc"
    raise HTTPException(
        status_code=400,
        detail={
            "code": code,
            "message": message,
            "action": action,
            "provider": provider,
            "feature": feat_key,
            "setup_gaps": gaps,
        },
    )
