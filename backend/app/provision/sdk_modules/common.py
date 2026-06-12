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


# x64-only fallbacks — Ubuntu/Debian marketplace images are amd64 (not Arm64 *pts* SKUs).
AZURE_VM_SIZE_FALLBACKS: dict[str, list[str]] = {
    "Standard_B1s": [
        "Standard_B1ms",
        "Standard_B2s",
        "Standard_B2ms",
        "Standard_A1_v2",
        "Standard_A2_v2",
        "Standard_DS1_v2",
        "Standard_D2s_v3",
        "Standard_D2as_v5",
        "Standard_F2s_v2",
    ],
    "Standard_B1ms": ["Standard_B1s", "Standard_B2s", "Standard_A1_v2"],
    "Standard_B2s": ["Standard_B1s", "Standard_B1ms", "Standard_B2ms"],
    "Standard_B2ms": ["Standard_B2s", "Standard_B1ms", "Standard_B1s"],
}


def is_azure_vm_architecture_error(exc: BaseException) -> bool:
    """VM size requires Arm64 but our Linux images are x64 (or the reverse)."""
    msg = str(exc)
    return "CPU Architecture" in msg and ("Arm64" in msg or "x64" in msg)


def is_azure_sku_capacity_error(exc: BaseException) -> bool:
    try:
        from azure.core.exceptions import HttpResponseError

        if isinstance(exc, HttpResponseError):
            code = getattr(getattr(exc, "error", None), "code", "") or ""
            if code == "SkuNotAvailable":
                return True
    except Exception:
        pass
    msg = str(exc)
    return "SkuNotAvailable" in msg or "Capacity Restrictions" in msg


def azure_vm_sizes_to_try(primary: str) -> list[str]:
    """Preferred VM size first, then regional capacity fallbacks."""
    ordered = [primary or "Standard_B1s"]
    ordered.extend(AZURE_VM_SIZE_FALLBACKS.get(ordered[0], []))
    seen: set[str] = set()
    out: list[str] = []
    for size in ordered:
        if size not in seen:
            seen.add(size)
            out.append(size)
    return out
