from __future__ import annotations

from typing import Any

from google.api_core.exceptions import Conflict, NotFound

from app.provision.sdk_clients import gcp_storage_client
from app.provision.sdk_modules.context import SdkDeployContext


def plan_gcs(config: dict, cloud_env: dict[str, str]) -> dict[str, Any]:
    bucket_name = (config.get("bucket_name") or "").strip()
    if not bucket_name:
        return {"lines": [], "error": "Bucket name is required for GCS.", "resources": []}
    region = config.get("gcp_region") or "us-central1"
    try:
        client, project = gcp_storage_client(cloud_env)
        if client.bucket(bucket_name).exists():
            return {
                "lines": [],
                "error": f"GCS bucket '{bucket_name}' already exists.",
                "resources": [],
            }
    except Exception as exc:
        return {"lines": [], "error": str(exc), "resources": []}
    lines = [
        f"  + google_storage_bucket.main ({bucket_name}, {region}, project={project})",
        "  + uniform_bucket_level_access",
    ]
    return {
        "lines": lines,
        "error": None,
        "resources": [f"google_storage_bucket.main:{bucket_name}"],
    }


def apply_gcs(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> dict[str, Any]:
    bucket_name = (config.get("bucket_name") or "").strip()
    region = config.get("gcp_region") or "us-central1"
    steps: list[str] = []
    try:
        client, project = gcp_storage_client(cloud_env)
        bucket = client.bucket(bucket_name)
        if bucket.exists():
            return {"success": False, "steps": steps, "error": f"GCS bucket '{bucket_name}' already exists."}
        bucket = client.create_bucket(bucket_name, location=region)
        bucket.reload()
        bucket.iam_configuration.uniform_bucket_level_access_enabled = True
        bucket.patch()
        tags = config.get("tags") or {}
        if tags:
            bucket.labels = {str(k).lower().replace(" ", "_"): str(v) for k, v in tags.items()}
            bucket.patch()
        ctx.gcs_bucket = bucket_name
        ctx.gcp_project = project
        steps.append(f"✓ GCS bucket '{bucket_name}' ({region})")
        return {"success": True, "steps": steps, "error": None}
    except Conflict:
        return {"success": False, "steps": steps, "error": f"GCS bucket '{bucket_name}' already exists."}
    except Exception as exc:
        return {"success": False, "steps": steps, "error": str(exc)}


def destroy_gcs(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> dict[str, Any]:
    bucket_name = (config.get("bucket_name") or ctx.gcs_bucket or "").strip()
    if not bucket_name:
        return {"success": True, "steps": ["GCS: nothing to delete"], "error": None}
    try:
        client, _ = gcp_storage_client(cloud_env)
        bucket = client.bucket(bucket_name)
        if not bucket.exists():
            return {"success": True, "steps": [f"GCS bucket '{bucket_name}' already absent"], "error": None}
        bucket.delete(force=True)
        return {"success": True, "steps": [f"✓ Deleted GCS bucket '{bucket_name}'"], "error": None}
    except NotFound:
        return {"success": True, "steps": [f"GCS bucket '{bucket_name}' already absent"], "error": None}
    except Exception as exc:
        return {"success": False, "steps": [], "error": str(exc)}


def check_gcs_drift(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> tuple[int, list[str]]:
    bucket_name = (config.get("bucket_name") or ctx.gcs_bucket or "").strip()
    if not bucket_name:
        return 0, []
    details: list[str] = []
    changes = 0
    try:
        client, _ = gcp_storage_client(cloud_env)
        bucket = client.get_bucket(bucket_name)
        if bucket.iam_configuration.uniform_bucket_level_access_enabled is not True:
            changes += 1
            details.append("~ GCS uniform bucket-level access not enabled")
        expected_loc = (config.get("gcp_region") or "us-central1").lower()
        if (bucket.location or "").lower() != expected_loc:
            changes += 1
            details.append(f"~ GCS location is {bucket.location}, expected {expected_loc}")
    except NotFound:
        return 1, [f"~ GCS bucket '{bucket_name}' missing"]
    except Exception as exc:
        return 1, [f"~ GCS check failed: {exc}"]
    return changes, details
