"""
Per-request GCP Compute context for BYOC users.

When a user has GCP BYOC connected, VM operations use their service account
(project from SA JSON, zone from BYOC gcp_primary_location when set).
"""

from __future__ import annotations

import contextvars
import json
from contextlib import contextmanager
from typing import Any, Iterator, Optional

from google.oauth2 import service_account

from app.byoc.credential_resolver import (
    get_user_cloud_credentials,
    normalize_gcp_byoc_layout,
    resolve_gcp_credentials,
)
from app.utils.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

_gcp_username: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "gcp_username", default=None
)


def set_gcp_username(username: Optional[str]) -> contextvars.Token:
    return _gcp_username.set(username)


def reset_gcp_username(token: contextvars.Token) -> None:
    _gcp_username.reset(token)


@contextmanager
def gcp_user_context(username: str) -> Iterator[None]:
    token = set_gcp_username(username)
    try:
        yield
    finally:
        reset_gcp_username(token)


def _platform_credentials():
    """Lazy import to avoid circular dependency at module load."""
    from app.vm import manager as gcp_manager

    return gcp_manager.credentials


def gcp_compute_ready() -> bool:
    """True when platform GCP key or active BYOC compute context is available."""
    username = _gcp_username.get()
    if username and _resolve_byoc_compute(username):
        return True
    return _platform_credentials() is not None


def gcp_active_credentials():
    """Credentials for GCP Compute API calls (BYOC first, then platform)."""
    username = _gcp_username.get()
    if username:
        ctx = _resolve_byoc_compute(username)
        if ctx:
            return ctx["credentials"]
    return _platform_credentials()


def _byoc_compute_zone(username: str) -> str:
    from app.vm.gcp_zones import gcp_zone_from_location

    record = get_user_cloud_credentials(username, "GCP") or {}
    layout = normalize_gcp_byoc_layout(record)
    explicit_zone = (record.get("gcp_compute_zone") or "").strip() or None
    return gcp_zone_from_location(
        layout.get("primary_location") or "",
        explicit_zone=explicit_zone,
    )


def _resolve_byoc_compute(username: str) -> Optional[dict[str, Any]]:
    gcp = resolve_gcp_credentials(username)
    if not gcp.get("is_byoc"):
        return None
    raw = gcp.get("service_account_json") or ""
    if not raw:
        return None
    sa_info = json.loads(raw) if isinstance(raw, str) else raw
    project_id = sa_info.get("project_id")
    if not project_id:
        logger.warning("BYOC GCP SA missing project_id for user %s", username)
        return None
    credentials = service_account.Credentials.from_service_account_info(sa_info)
    zone = _byoc_compute_zone(username)
    return {
        "project_id": project_id,
        "zone": zone,
        "credentials": credentials,
        "is_byoc": True,
    }


def gcp_project_id() -> str:
    username = _gcp_username.get()
    if username:
        ctx = _resolve_byoc_compute(username)
        if ctx:
            return ctx["project_id"]
    return settings.GCP_PROJECT_ID


def gcp_zone() -> str:
    from app.vm.platform_region_context import get_platform_region_slug
    from app.vm.platform_regions import resolve_vm_compute

    slug = get_platform_region_slug()
    if slug:
        return resolve_vm_compute("GCP", slug)["gcp_zone"]

    username = _gcp_username.get()
    if username:
        ctx = _resolve_byoc_compute(username)
        if ctx:
            return ctx["zone"]
    return getattr(settings, "GCP_ZONE", "us-central1-a")
