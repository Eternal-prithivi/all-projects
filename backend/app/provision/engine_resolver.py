# =============================================================================
# MODULE: provision/engine_resolver.py
# PURPOSE: Resolve Boto3 vs Terraform from user Settings + deployment config.
# Works on localhost and Render — Boto3 needs no CLI; Terraform checks PATH.
# =============================================================================
from __future__ import annotations

from typing import Literal

from fastapi import HTTPException

from app.database.mongo_client import get_database
from app.provision.boto3_composer import boto3_can_handle, enabled_modules
from app.provision.terraform_runner import check_terraform_installed

ProvisionEngine = Literal["boto3", "terraform"]

DEFAULT_ENGINE: ProvisionEngine = "boto3"
VALID_ENGINES = frozenset({"boto3", "terraform"})


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


def resolve_provision_engine(username: str, config: dict) -> ProvisionEngine:
    """
    Pick engine for this plan/apply.

    - terraform: always Terraform when CLI is available (localhost + Render Docker).
    - boto3: modular composer when every enabled module is implemented.
    """
    pref = get_user_provision_engine(username)

    if config.get("enable_billing"):
        raise HTTPException(
            status_code=400,
            detail=(
                "AWS Budgets (billing module) requires Terraform. "
                "Switch to Terraform in Settings or disable billing alerts."
            ),
        )

    if pref == "terraform":
        if not check_terraform_installed():
            raise HTTPException(
                status_code=503,
                detail=(
                    "Terraform CLI is not installed on this server. "
                    "Use Boto3 in Settings (recommended on Render free tier) or deploy the Docker image."
                ),
            )
        return "terraform"

    ok, unsupported = boto3_can_handle(config)
    if not ok:
        names = ", ".join(sorted(unsupported)) or "unknown"
        raise HTTPException(
            status_code=400,
            detail=(
                f"Boto3 cannot provision: {names}. "
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
        return "boto3"
    return "terraform"
