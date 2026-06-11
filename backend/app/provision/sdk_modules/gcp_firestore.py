"""GCP Firestore Native database SDK module."""

from __future__ import annotations

from typing import Any

from google.api_core import exceptions as gcp_exc
from google.cloud.firestore_admin_v1.types import Database

from app.provision.sdk_clients import gcp_firestore_admin_client
from app.provision.sdk_modules.context import SdkDeployContext


def plan_firestore(config: dict, cloud_env: dict[str, str]) -> dict[str, Any]:
    db_id = config.get("firestore_database_id") or "(default)"
    region = config.get("gcp_region") or "us-central1"
    lines = [f"  + google_firestore_database.{db_id} ({region})"]
    return {"lines": lines, "error": None, "resources": [f"firestore:{db_id}"]}


def apply_firestore(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> dict[str, Any]:
    client, project = gcp_firestore_admin_client(cloud_env)
    db_id = (config.get("firestore_database_id") or "(default)").strip()
    region = config.get("gcp_region") or "us-central1"
    steps: list[str] = []
    try:
        parent = f"projects/{project}"
        name = f"{parent}/databases/{db_id}"
        try:
            client.get_database(name=name)
            steps.append(f"✓ Firestore database '{db_id}' exists")
        except gcp_exc.NotFound:
            client.create_database(
                parent=parent,
                database_id=db_id,
                database=Database(
                    location_id=region,
                    type_=Database.DatabaseType.FIRESTORE_NATIVE,
                ),
            )
            steps.append(f"✓ Firestore database '{db_id}'")
        ctx.firestore_database_id = db_id
        ctx.gcp_project = project
        return {"success": True, "steps": steps, "error": None}
    except Exception as exc:
        return {"success": False, "steps": steps, "error": str(exc)}


def destroy_firestore(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> dict[str, Any]:
    client, project = gcp_firestore_admin_client(cloud_env)
    db_id = ctx.firestore_database_id or config.get("firestore_database_id") or "(default)"
    steps: list[str] = []
    try:
        name = f"projects/{project}/databases/{db_id}"
        try:
            client.delete_database(name=name)
            steps.append(f"✓ Deleted Firestore database '{db_id}'")
        except gcp_exc.NotFound:
            pass
        return {"success": True, "steps": steps or ["Firestore: nothing to delete"], "error": None}
    except Exception as exc:
        return {"success": False, "steps": steps, "error": str(exc)}


def check_firestore_drift(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> tuple[int, list[str]]:
    client, project = gcp_firestore_admin_client(cloud_env)
    db_id = ctx.firestore_database_id or config.get("firestore_database_id") or "(default)"
    try:
        client.get_database(name=f"projects/{project}/databases/{db_id}")
        return 0, []
    except gcp_exc.NotFound:
        return 1, [f"~ Firestore database '{db_id}' missing"]
    except Exception as exc:
        return 1, [f"~ Firestore check failed: {exc}"]
