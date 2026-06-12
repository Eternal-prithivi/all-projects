# =============================================================================
# MODULE: provision/engine_resolver.py
# PURPOSE: Resolve Boto3 / SDK / Terraform from user Settings + deployment config.
# Works on localhost and Render — Boto3/SDK need no CLI; Terraform checks PATH.
# =============================================================================
from __future__ import annotations

from typing import Literal

from fastapi import HTTPException

from app.database.mongo_client import get_database
from app.provision.boto3_composer import boto3_can_handle, enabled_modules
from app.provision.sdk_composer import sdk_can_handle
from app.provision.terraform_runner import check_terraform_installed

ProvisionEngine = Literal["boto3", "terraform", "sdk"]

DEFAULT_ENGINE: ProvisionEngine = "boto3"
VALID_ENGINES = frozenset({"boto3", "terraform", "sdk"})


def get_user_provision_engine(username: str) -> ProvisionEngine:
    """Read users.settings.preferences.provision_engine (default boto3)."""
    user = get_database()["users"].find_one(
        {"username": username},
        {"settings.preferences.provision_engine": 1},
    )
    raw = (
        (user or {}).get("settings", {}).get("preferences", {}).get("provision_engine")
        or DEFAULT_ENGINE
    )
    raw = str(raw).lower().strip()
    if raw not in VALID_ENGINES:
        return DEFAULT_ENGINE
    return raw  # type: ignore[return-value]


def resolve_provision_engine(
    username: str, config: dict, csp: str = "AWS"
) -> ProvisionEngine:
    """
    Pick engine for this plan/apply.

    - AWS + boto3 preference: Boto3 when modules supported.
    - GCP/Azure + boto3 preference: cloud SDK fast path when modules supported.
    - terraform: always Terraform when CLI is available.
    """
    from app.cloud.providers import normalize_provider

    provider = normalize_provider(csp or config.get("csp") or "AWS")
    pref = get_user_provision_engine(username)

    if provider != "AWS":
        if pref == "terraform":
            if not check_terraform_installed():
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "Terraform CLI is required for GCP and Azure provisioning. "
                        "Install Terraform on the server or use the Docker image."
                    ),
                )
            return "terraform"

        ok, unsupported = sdk_can_handle(config)
        if ok:
            return "sdk"

        if pref == "boto3" and unsupported:
            names = ", ".join(sorted(unsupported)) or "unknown"
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Cloud SDK fast path cannot provision: {names}. "
                    "Switch to Terraform in Settings or use a supported template (GCS / Blob)."
                ),
            )

        if check_terraform_installed():
            return "terraform"

        raise HTTPException(
            status_code=503,
            detail=(
                "Terraform CLI is required for this GCP/Azure configuration. "
                "Install Terraform or use storage-only templates with Fast path (Cloud SDK) in Settings."
            ),
        )

    if pref == "terraform":
        if not check_terraform_installed():
            raise HTTPException(
                status_code=503,
                detail=(
                    "Terraform CLI is not installed on this server. "
                    "Use Fast path (Cloud SDK) in Settings (recommended on Render free tier) or deploy the Docker image."
                ),
            )
        return "terraform"

    ok, unsupported = boto3_can_handle(config)
    if not ok:
        names = ", ".join(sorted(unsupported)) or "unknown"
        raise HTTPException(
            status_code=400,
            detail=(
                f"AWS fast path cannot provision: {names}. "
                "Switch to Terraform in Settings or disable those modules."
            ),
        )

    if not enabled_modules(config):
        raise HTTPException(
            status_code=400,
            detail="Enable at least one infrastructure module before deploying.",
        )

    return "boto3"


def deployment_engine(deployment: dict) -> ProvisionEngine:
    """Engine used for an existing deployment (plan time), with legacy fallback."""
    raw = deployment.get("provision_engine")
    if raw in VALID_ENGINES:
        return raw  # type: ignore[return-value]
    if deployment.get("fast_path"):
        csp = (deployment.get("config") or {}).get("csp") or "AWS"
        from app.cloud.providers import normalize_provider

        if normalize_provider(csp) == "AWS":
            return "boto3"
        return "sdk"
    return "terraform"
