"""
Per-user cloud provider availability — BYOC vs platform Zenith credentials.

Rules:
- If the user has **any** active BYOC connection → only BYOC-connected providers are available
  (no platform fallback for providers they did not connect).
- If the user has **no** BYOC → all platform-configured providers are available.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from app.byoc.credential_resolver import get_byoc_status
from app.cloud.providers import CloudProvider, normalize_provider, normalize_provider_key
from app.utils.config import settings
from app.utils.gcp_credentials import gcp_credentials_file_present

_ALL: tuple[CloudProvider, ...] = ("AWS", "GCP", "Azure")


class CloudFeature(str, Enum):
    STORAGE = "storage"
    SECURITY = "security"
    VM = "vm"
    PROVISION = "provision"
    COST = "cost"


def _byoc_connected(username: str, provider: CloudProvider) -> bool:
    key = normalize_provider_key(provider)
    return bool((get_byoc_status(username).get(key) or {}).get("connected"))


def user_has_any_byoc(username: str) -> bool:
    return any(_byoc_connected(username, p) for p in _ALL)


def platform_storage_configured(provider: CloudProvider) -> bool:
    if provider == "AWS":
        return bool(
            settings.AWS_ACCESS_KEY_ID
            and settings.AWS_SECRET_ACCESS_KEY
            and settings.S3_BUCKET_NAME
        )
    if provider == "GCP":
        return bool(
            gcp_credentials_file_present()
            and settings.GCP_BUCKET_NAME
            and settings.GCP_PROJECT_ID
        )
    return bool(
        settings.AZURE_STORAGE_ACCOUNT_NAME
        and settings.AZURE_STORAGE_ACCOUNT_KEY
        and settings.AZURE_CONTAINER_NAME
    )


def platform_vm_configured(provider: CloudProvider) -> bool:
    if provider == "Azure":
        return False
    if provider == "AWS":
        from app.vm.aws_manager import aws_configured

        return aws_configured()
    from app.vm import manager as gcp_manager

    return gcp_manager.credentials is not None


def platform_provision_configured(provider: CloudProvider) -> bool:
    return platform_storage_configured(provider)


def platform_cost_configured(provider: CloudProvider) -> bool:
    if provider == "AWS":
        return platform_storage_configured("AWS")
    if provider == "GCP":
        return platform_storage_configured("GCP")
    return bool(
        settings.AZURE_SUBSCRIPTION_ID
        and settings.AZURE_TENANT_ID
        and settings.AZURE_CLIENT_ID
        and settings.AZURE_CLIENT_SECRET
    ) or platform_storage_configured("Azure")


def _platform_configured(provider: CloudProvider, feature: CloudFeature) -> bool:
    if feature in (CloudFeature.STORAGE, CloudFeature.SECURITY):
        return platform_storage_configured(provider)
    if feature == CloudFeature.VM:
        return platform_vm_configured(provider)
    if feature == CloudFeature.PROVISION:
        return platform_provision_configured(provider)
    if feature == CloudFeature.COST:
        return platform_cost_configured(provider)
    return False


def _feature_filter(providers: List[CloudProvider], feature: CloudFeature) -> List[CloudProvider]:
    if feature == CloudFeature.VM:
        return [p for p in providers if p != "Azure"]
    return list(providers)


def available_providers(username: str, feature: CloudFeature) -> List[CloudProvider]:
    """Providers the user may use for this feature right now."""
    if user_has_any_byoc(username):
        base = [p for p in _ALL if _byoc_connected(username, p)]
    else:
        base = [p for p in _ALL if _platform_configured(p, feature)]
    return _feature_filter(base, feature)


def default_provider(username: str, feature: CloudFeature) -> Optional[CloudProvider]:
    providers = available_providers(username, feature)
    return providers[0] if providers else None


def provider_not_available_exception(
    username: str,
    provider: CloudProvider,
    feature: CloudFeature,
) -> HTTPException:
    mode = "byoc" if user_has_any_byoc(username) else "platform"
    allowed = available_providers(username, feature)
    return HTTPException(
        status_code=403,
        detail={
            "code": "provider_not_available",
            "message": (
                f"{provider} is not available for {feature.value}. "
                f"{'Connect this cloud in Settings (BYOC)' if mode == 'byoc' else 'Platform credentials for this cloud are not configured'}."
            ),
            "provider": provider,
            "feature": feature.value,
            "credential_mode": mode,
            "available_providers": allowed,
        },
    )


def assert_provider_available(
    username: str,
    csp: str,
    feature: CloudFeature,
) -> CloudProvider:
    """Raise 403 if this provider is not in the user's allowed set."""
    provider = normalize_provider(csp)
    if provider not in available_providers(username, feature):
        raise provider_not_available_exception(username, provider, feature)
    return provider


def build_availability_payload(username: str) -> Dict[str, Any]:
    """API response for GET /api/cloud/availability."""
    byoc_mode = user_has_any_byoc(username)
    connected = [p for p in _ALL if _byoc_connected(username, p)]

    features: Dict[str, Any] = {}
    for feat in CloudFeature:
        providers = available_providers(username, feat)
        features[feat.value] = {
            "providers": providers,
            "default": providers[0] if providers else None,
            "multi_provider": len(providers) > 1,
        }

    return {
        "credential_mode": "byoc" if byoc_mode else "platform",
        "byoc_connected": connected,
        "features": features,
        "summary": {
            "any_provider": any(
                features[f.value]["providers"] for f in CloudFeature
            ),
            "storage_count": len(features["storage"]["providers"]),
        },
    }
