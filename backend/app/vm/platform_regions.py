"""Map platform catalog slugs (asia, us, …) to VM compute locations per CSP."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.cloud.platform_storage_catalog import (
    default_platform_slug,
    get_platform_regions,
    get_region_by_slug,
)
from app.cloud.providers import normalize_provider
from app.utils.config import settings
from app.vm.gcp_zones import gcp_zone_from_location


def resolve_vm_compute(csp: str, platform_region_slug: Optional[str] = None) -> Dict[str, str]:
    """
    Resolve AWS region, GCP zone, and Azure location for a platform region pill.
    Falls back to .env defaults when slug is missing or unknown.
    """
    provider = normalize_provider(csp or "GCP")
    slug = (platform_region_slug or default_platform_slug()).strip().lower()
    entry = get_region_by_slug(slug) or (get_platform_regions()[0] if get_platform_regions() else None)

    aws_region = settings.PRIMARY_S3_REGION
    gcp_zone = getattr(settings, "GCP_ZONE", "us-central1-a")
    azure_location = getattr(settings, "AZURE_LOCATION", "eastus")
    label = slug

    if entry:
        label = str(entry.get("label") or slug)
        aws = entry.get("aws") or {}
        gcp = entry.get("gcp") or {}
        az = entry.get("azure") or {}
        if aws.get("region"):
            aws_region = str(aws["region"])
        if gcp.get("location"):
            gcp_zone = gcp_zone_from_location(
                str(gcp["location"]),
                explicit_zone=str(gcp["zone"]) if gcp.get("zone") else None,
            )
        if az.get("region"):
            azure_location = str(az["region"])

    if provider == "AWS":
        return {
            "platform_region_slug": slug,
            "label": label,
            "aws_region": aws_region,
            "gcp_zone": gcp_zone,
            "azure_location": azure_location,
            "compute_target": aws_region,
        }
    if provider == "Azure":
        return {
            "platform_region_slug": slug,
            "label": label,
            "aws_region": aws_region,
            "gcp_zone": gcp_zone,
            "azure_location": azure_location,
            "compute_target": azure_location,
        }
    return {
        "platform_region_slug": slug,
        "label": label,
        "aws_region": aws_region,
        "gcp_zone": gcp_zone,
        "azure_location": azure_location,
        "compute_target": gcp_zone,
    }


def list_vm_platform_regions() -> List[Dict[str, Any]]:
    """Region pills for the VM UI (same slugs as storage/security)."""
    regions = get_platform_regions()
    if not regions:
        return []
    out: List[Dict[str, Any]] = []
    for entry in regions:
        slug = entry.get("slug")
        if not slug:
            continue
        aws = entry.get("aws") or {}
        gcp = entry.get("gcp") or {}
        az = entry.get("azure") or {}
        out.append(
            {
                "slug": slug,
                "label": entry.get("label") or slug,
                "aws_region": aws.get("region"),
                "gcp_zone": gcp_zone_from_location(
                    str(gcp.get("location") or ""),
                    explicit_zone=str(gcp["zone"]) if gcp.get("zone") else None,
                )
                if gcp.get("location")
                else None,
                "azure_location": az.get("region"),
            }
        )
    return out
