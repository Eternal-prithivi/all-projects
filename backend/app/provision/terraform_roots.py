"""Resolve Terraform root directory per cloud provider."""

from __future__ import annotations

import os
from pathlib import Path

from app.cloud.providers import CloudProvider, normalize_provider


def _base_terraform_dir() -> Path:
    if custom := os.getenv("TERRAFORM_ROOT"):
        return Path(custom).parent if Path(custom).name in ("aws", "gcp", "azure") else Path(custom)
    here = Path(__file__).resolve()
    for base in (here.parent.parent.parent, here.parent.parent.parent.parent):
        candidate = base / "terraform"
        if candidate.is_dir():
            return candidate
    return here.parent.parent.parent / "terraform"


def get_terraform_root(csp: str = "AWS") -> Path:
    """AWS uses backend/terraform; GCP and Azure use dedicated subdirectories."""
    provider: CloudProvider = normalize_provider(csp)
    base = _base_terraform_dir()
    if provider == "GCP":
        root = base / "gcp"
    elif provider == "Azure":
        root = base / "azure"
    else:
        return base
    if not root.is_dir():
        raise FileNotFoundError(f"Terraform root not found for {provider}: {root}")
    return root
