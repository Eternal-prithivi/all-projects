"""Shared storage tier names and lifecycle normalization (AWS/GCP/Azure)."""

from __future__ import annotations

from typing import Optional

# Provider API class names used when changing tiers (Celery lifecycle).
TIER_MAP = {
    "AWS": {"hot": "STANDARD", "warm": "STANDARD_IA", "cold": "GLACIER"},
    "GCP": {"hot": "STANDARD", "warm": "NEARLINE", "cold": "ARCHIVE"},
    "Azure": {"hot": "Hot", "warm": "Cool", "cold": "Archive"},
}

# UI / ML / upload labels and provider-native names (lowercase matching in normalize_lifecycle_tier).
HOT_TIER_NAMES = [
    "Standard",
    "STANDARD",
    "S3 Standard",
    "Standard Storage",
    "Hot",
    "Hot Blob Storage",
]
WARM_TIER_NAMES = [
    "STANDARD_IA",
    "S3 Standard-IA",
    "NEARLINE",
    "Nearline",
    "Nearline Storage",
    "Cool",
    "Cool Blob Storage",
]
COLD_TIER_NAMES = [
    "GLACIER",
    "DEEP_ARCHIVE",
    "S3 Glacier Flexible",
    "ARCHIVE",
    "Archive",
    "Archive Storage",
]

ALL_TIER_NAMES = HOT_TIER_NAMES + WARM_TIER_NAMES + COLD_TIER_NAMES

_HOT_LOWER = {name.strip().lower() for name in HOT_TIER_NAMES}
_WARM_LOWER = {name.strip().lower() for name in WARM_TIER_NAMES}
_COLD_LOWER = {name.strip().lower() for name in COLD_TIER_NAMES}


def normalize_lifecycle_tier(storage_class: Optional[str]) -> Optional[str]:
    """Map provider-specific storage classes into hot/warm/cold lifecycle tiers."""
    if not storage_class:
        return None

    normalized = storage_class.strip().lower()
    if normalized in _HOT_LOWER or normalized == "hot":
        return "hot"
    if normalized in _WARM_LOWER or normalized == "warm":
        return "warm"
    if normalized in _COLD_LOWER or normalized == "cold":
        return "cold"
    return None
