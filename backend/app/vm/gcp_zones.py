"""Resolve a usable GCP zone from catalog location or region name."""

from __future__ import annotations

from typing import Dict, Optional

from app.utils.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

_ZONE_SUFFIXES = ("a", "b", "c", "d", "f")
_zone_cache: Dict[str, frozenset[str]] = {}


def _region_from_location(location: str) -> str:
    lower = location.lower().replace("_", "-")
    parts = lower.split("-")
    if len(parts) >= 3 and len(parts[-1]) == 1 and parts[-1].isalpha():
        return "-".join(parts[:-1])
    return lower


def gcp_zone_from_location(
    location: str,
    *,
    explicit_zone: Optional[str] = None,
    available_zones: Optional[frozenset[str]] = None,
) -> str:
    """
    Map a catalog GCP location (e.g. EUROPE-WEST1) to a zone that exists in the project.

    Some regions omit zone suffix ``-a`` (e.g. europe-west1 only has b/c/d); when project
    zones are known we pick the first available zone in that region.
    """
    if explicit_zone and str(explicit_zone).strip():
        return str(explicit_zone).strip().lower()

    raw = (location or "").strip()
    if not raw:
        return getattr(settings, "GCP_ZONE", "us-central1-a")

    lower = raw.lower().replace("_", "-")
    parts = lower.split("-")
    if len(parts) >= 3 and len(parts[-1]) == 1 and parts[-1].isalpha():
        return lower

    region = lower
    zones = available_zones if available_zones is not None else _project_zones()
    if zones:
        matches = sorted(z for z in zones if z.startswith(f"{region}-"))
        if matches:
            return matches[0]

    for suffix in _ZONE_SUFFIXES:
        candidate = f"{region}-{suffix}"
        if not zones or candidate in zones:
            return candidate
    return f"{region}-b"


def _project_zones() -> frozenset[str]:
    try:
        from app.vm.gcp_runtime import gcp_project_id
        from app.vm.manager import credentials

        if credentials is None:
            return frozenset()

        project_id = gcp_project_id()
        cached = _zone_cache.get(project_id)
        if cached is not None:
            return cached

        from google.cloud import compute_v1

        client = compute_v1.ZonesClient(credentials=credentials)
        req = compute_v1.ListZonesRequest(project=project_id)
        zones = frozenset(z.name for z in client.list(request=req))
        _zone_cache[project_id] = zones
        return zones
    except Exception as exc:
        logger.debug("Could not list GCP zones for resolution: %s", exc)
        return frozenset()


def invalidate_gcp_zone_cache() -> None:
    _zone_cache.clear()
