"""Shared helpers for GCP/Azure SDK provision modules."""

from __future__ import annotations

import re
from typing import Any


def gcp_labels(tags: dict[str, Any] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in (tags or {}).items():
        label_key = re.sub(r"[^a-z0-9_-]", "_", str(key).lower())[:63]
        if label_key:
            out[label_key] = str(value)[:63]
    return out


def azure_tags(tags: dict[str, Any] | None) -> dict[str, str]:
    return {str(k): str(v) for k, v in (tags or {}).items()}


def gcp_zone(region: str) -> str:
    return f"{region}-a"


def disk_gb(config: dict[str, Any]) -> int:
    return max(8, min(int(config.get("disk_size_gb") or 30), 2000))
