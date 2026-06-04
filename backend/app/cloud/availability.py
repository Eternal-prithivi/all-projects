"""
Per-user cloud provider availability — hybrid BYOC + platform.

Rules:
- **Hybrid:** Union of BYOC-connected CSPs and platform-configured CSPs (per feature).
  Example: AWS BYOC only → user still gets GCP/Azure via Zenith platform keys for storage/cost.
- **Credential routing** (upload, billing): BYOC when connected for that CSP, else platform
  (`credential_resolver.py` — unchanged).
- **UI availability:** Same union — selectors show every CSP the user can actually use.
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


def credential_source(username: str, provider: CloudProvider) -> str:
    """Which credential bucket applies for this CSP: byoc | platform."""
    return "byoc" if _byoc_connected(username, provider) else "platform"


def platform_storage_configured(provider: CloudProvider) -> bool:
    if provider == "AWS":
        return bool(
            settings.AWS_ACCESS_KEY_ID
            and settings.AWS_SECRET_ACCESS_KEY
            and settings.S3_BUCKET_NAME
        )
    if provider == "GCP":
        # Same pattern as Azure: list when bucket + project are configured;
        # service account JSON path is required at upload time (see build_gcp_storage_client).
        return bool(settings.GCP_BUCKET_NAME and settings.GCP_PROJECT_ID)
    return bool(
        settings.AZURE_STORAGE_ACCOUNT_NAME
        and settings.AZURE_STORAGE_ACCOUNT_KEY
        and settings.AZURE_CONTAINER_NAME
    )


def platform_vm_configured(provider: CloudProvider) -> bool:
    if provider == "Azure":
        from app.vm.azure_manager import azure_configured

        if azure_configured():
            return True
        # List when storage + SP are set (like GCP project/zone); subscription required at provision time.
        return bool(
            settings.AZURE_TENANT_ID
            and settings.AZURE_CLIENT_ID
            and settings.AZURE_CLIENT_SECRET
            and platform_storage_configured("Azure")
        )
    if provider == "AWS":
        from app.vm.aws_manager import aws_configured

        return aws_configured()
    if provider == "GCP":
        from app.vm import manager as gcp_manager

        if gcp_credentials_file_present() and gcp_manager.credentials is not None:
            return True
        return bool(settings.GCP_PROJECT_ID and settings.GCP_ZONE)
    return False


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


def _provider_available(username: str, provider: CloudProvider, feature: CloudFeature) -> bool:
    return _byoc_connected(username, provider) or _platform_configured(provider, feature)


def available_providers(username: str, feature: CloudFeature) -> List[CloudProvider]:
    """Hybrid union of BYOC-connected and platform-configured providers (all features)."""
    return [p for p in _ALL if _provider_available(username, p, feature)]


def default_provider(username: str, feature: CloudFeature) -> Optional[CloudProvider]:
    providers = available_providers(username, feature)
    return providers[0] if providers else None


def provider_not_available_exception(
    username: str,
    provider: CloudProvider,
    feature: CloudFeature,
) -> HTTPException:
    allowed = available_providers(username, feature)
    return HTTPException(
        status_code=403,
        detail={
            "code": "provider_not_available",
            "message": (
                f"{provider} is not available for {feature.value}. "
                "Connect BYOC in Settings or ensure the platform has credentials for this cloud."
            ),
            "provider": provider,
            "feature": feature.value,
            "credential_mode": resolve_credential_mode(username),
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


def resolve_credential_mode(username: str) -> str:
    """platform | byoc | hybrid — for UI copy."""
    has_byoc = user_has_any_byoc(username)
    has_platform_any = any(
        _platform_configured(p, CloudFeature.STORAGE) for p in _ALL
    )
    if has_byoc and has_platform_any:
        return "hybrid"
    if has_byoc:
        return "byoc"
    return "platform"


def build_availability_payload(username: str) -> Dict[str, Any]:
    """API response for GET /api/cloud/availability."""
    connected = [p for p in _ALL if _byoc_connected(username, p)]
    mode = resolve_credential_mode(username)
    sources = {p: credential_source(username, p) for p in _ALL}

    features: Dict[str, Any] = {}
    for feat in CloudFeature:
        providers = available_providers(username, feat)
        features[feat.value] = {
            "providers": providers,
            "default": providers[0] if providers else None,
            "multi_provider": len(providers) > 1,
            "credential_sources": {
                p: sources[p] for p in providers if p in sources
            },
        }

    return {
        "credential_mode": mode,
        "byoc_connected": connected,
        "credential_sources": sources,
        "features": features,
        "summary": {
            "any_provider": any(
                features[f.value]["providers"] for f in CloudFeature
            ),
            "storage_count": len(features["storage"]["providers"]),
        },
    }
