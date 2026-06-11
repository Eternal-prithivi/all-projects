"""GCP service account SDK module."""

from __future__ import annotations

from typing import Any

from google.api_core import exceptions as gcp_exc
from google.cloud import iam_admin_v1

from app.provision.sdk_clients import gcp_iam_client
from app.provision.sdk_modules.context import SdkDeployContext


def plan_gcp_service_account(config: dict, cloud_env: dict[str, str]) -> dict[str, Any]:
    sa_id = config.get("service_account_id") or "zenith-app-sa"
    lines = [f"  + google_service_account.{sa_id}"]
    if config.get("enable_gcs"):
        lines.append("  + google_project_iam_member.storage_viewer (optional)")
    return {"lines": lines, "error": None, "resources": lines}


def apply_gcp_service_account(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> dict[str, Any]:
    client, project = gcp_iam_client(cloud_env)
    sa_id = (config.get("service_account_id") or "zenith-app-sa").strip()[:30]
    steps: list[str] = []
    try:
        email = f"{sa_id}@{project}.iam.gserviceaccount.com"
        name = f"projects/{project}/serviceAccounts/{email}"
        try:
            client.get_service_account(name=name)
            steps.append(f"✓ Service account '{sa_id}' exists")
        except gcp_exc.NotFound:
            client.create_service_account(
                name=f"projects/{project}",
                account_id=sa_id,
                service_account=iam_admin_v1.ServiceAccount(
                    display_name="Zenith provisioned app service account",
                ),
            )
            steps.append(f"✓ Service account '{sa_id}'")
        ctx.service_account_email = email
        ctx.gcp_project = project
        return {"success": True, "steps": steps, "error": None}
    except Exception as exc:
        return {"success": False, "steps": steps, "error": str(exc)}


def destroy_gcp_service_account(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> dict[str, Any]:
    client, project = gcp_iam_client(cloud_env)
    email = ctx.service_account_email
    if not email:
        sa_id = config.get("service_account_id") or "zenith-app-sa"
        email = f"{sa_id}@{project}.iam.gserviceaccount.com"
    steps: list[str] = []
    try:
        name = f"projects/{project}/serviceAccounts/{email}"
        try:
            client.delete_service_account(name=name)
            steps.append(f"✓ Deleted service account '{email}'")
        except gcp_exc.NotFound:
            pass
        return {"success": True, "steps": steps or ["Service account: nothing to delete"], "error": None}
    except Exception as exc:
        return {"success": False, "steps": steps, "error": str(exc)}


def check_gcp_service_account_drift(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> tuple[int, list[str]]:
    client, project = gcp_iam_client(cloud_env)
    email = ctx.service_account_email
    if not email:
        sa_id = config.get("service_account_id") or "zenith-app-sa"
        email = f"{sa_id}@{project}.iam.gserviceaccount.com"
    try:
        client.get_service_account(name=f"projects/{project}/serviceAccounts/{email}")
        return 0, []
    except gcp_exc.NotFound:
        return 1, [f"~ Service account '{email}' missing"]
    except Exception as exc:
        return 1, [f"~ Service account check failed: {exc}"]
