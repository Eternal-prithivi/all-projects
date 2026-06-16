"""Sync Terraform apply/destroy runners (Celery worker or background thread)."""

from __future__ import annotations

import logging
import os
import threading
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


def should_offload_terraform() -> bool:
    role = os.getenv("ZENITH_SERVICE_ROLE", "monolith").lower()
    if role in ("api", "web"):
        return True
    return os.getenv("PROVISION_OFFLOAD_TERRAFORM", "").lower() in ("1", "true", "yes")


def _deployments():
    from app.database.mongo_client import get_database

    return get_database()["provision_deployments"]


def run_terraform_apply_sync(deployment_id: str, username: str) -> dict[str, Any]:
    from app.cloud.providers import normalize_provider
    from app.provision.byoc_credentials import resolve_provision_terraform_env
    from app.provision.models import DeploymentStatus
    from app.provision.terraform_runner import TerraformRunner
    from app.provision.audit_logger import log_provision_action
    from app.provision.created_resources import resources_from_terraform_state

    collection = _deployments()
    deployment = collection.find_one({"deployment_name": deployment_id, "user_id": username})
    if not deployment:
        return {"success": False, "error": "not_found"}

    config_dict = deployment.get("config", {}) or {}
    csp = normalize_provider(config_dict.get("csp") or "AWS")
    region = config_dict.get("aws_region", "ap-south-1")
    cloud_env, cred_err = resolve_provision_terraform_env(username, csp, region)
    if cred_err:
        collection.update_one(
            {"deployment_name": deployment_id},
            {"$set": {"status": DeploymentStatus.APPLY_FAILED, "plan_error": cred_err}},
        )
        return {"success": False, "error": cred_err}

    workspace = deployment.get("terraform_workspace", "")
    runner = TerraformRunner(workspace, cloud_env=cloud_env)
    apply_result = runner.apply()
    new_status = DeploymentStatus.DEPLOYED if apply_result["success"] else DeploymentStatus.APPLY_FAILED
    resources = runner.get_state_resources() if apply_result["success"] else []
    created = (
        resources_from_terraform_state(config_dict, resources) if apply_result["success"] else []
    )
    collection.update_one(
        {"deployment_name": deployment_id},
        {
            "$set": {
                "status": new_status,
                "apply_output": apply_result.get("output", ""),
                "resources_count": len(resources),
                "created_resources": created,
                "updated_at": datetime.utcnow(),
            }
        },
    )
    log_provision_action(
        action="apply",
        actor=username,
        deployment_id=deployment_id,
        status="success" if apply_result["success"] else "failed",
        details={"resources_count": len(resources)},
        error=apply_result.get("error"),
    )
    return {"success": apply_result["success"], "status": new_status.value}


def run_terraform_destroy_sync(deployment_id: str, username: str) -> dict[str, Any]:
    from app.cloud.providers import normalize_provider
    from app.provision.byoc_credentials import resolve_provision_terraform_env
    from app.provision.models import DeploymentStatus
    from app.provision.terraform_runner import TerraformRunner
    from app.provision.audit_logger import log_provision_action

    collection = _deployments()
    deployment = collection.find_one({"deployment_name": deployment_id, "user_id": username})
    if not deployment:
        return {"success": False, "error": "not_found"}

    config_dict = deployment.get("config", {}) or {}
    csp = normalize_provider(config_dict.get("csp") or "AWS")
    region = config_dict.get("aws_region", "ap-south-1")
    cloud_env, cred_err = resolve_provision_terraform_env(username, csp, region)
    if cred_err:
        return {"success": False, "error": cred_err}

    workspace = deployment.get("terraform_workspace", "")
    runner = TerraformRunner(workspace, cloud_env=cloud_env)
    destroy_result = runner.destroy()
    new_status = DeploymentStatus.DESTROYED if destroy_result["success"] else DeploymentStatus.DESTROY_FAILED
    collection.update_one(
        {"deployment_name": deployment_id},
        {
            "$set": {
                "status": new_status,
                "resources_count": 0 if destroy_result["success"] else deployment.get("resources_count", 0),
                "destroyed_at": datetime.utcnow() if destroy_result["success"] else None,
                "updated_at": datetime.utcnow(),
            }
        },
    )
    log_provision_action(
        action="destroy",
        actor=username,
        deployment_id=deployment_id,
        status="success" if destroy_result["success"] else "failed",
        error=destroy_result.get("error"),
    )
    return {"success": destroy_result["success"], "status": new_status.value}


def dispatch_terraform_apply(deployment_id: str, username: str) -> str:
    """Queue apply on Celery provision queue or background thread. Returns mode."""
    try:
        from app.provision.terraform_tasks import terraform_apply_task

        terraform_apply_task.apply_async(
            args=[deployment_id, username],
            queue=os.getenv("PROVISION_CELERY_QUEUE", "provision"),
        )
        return "celery"
    except Exception as exc:
        logger.warning("Celery apply dispatch failed, using thread: %s", exc)
        threading.Thread(
            target=run_terraform_apply_sync,
            args=(deployment_id, username),
            daemon=True,
        ).start()
        return "thread"


def dispatch_terraform_destroy(deployment_id: str, username: str) -> str:
    try:
        from app.provision.terraform_tasks import terraform_destroy_task

        terraform_destroy_task.apply_async(
            args=[deployment_id, username],
            queue=os.getenv("PROVISION_CELERY_QUEUE", "provision"),
        )
        return "celery"
    except Exception as exc:
        logger.warning("Celery destroy dispatch failed, using thread: %s", exc)
        threading.Thread(
            target=run_terraform_destroy_sync,
            args=(deployment_id, username),
            daemon=True,
        ).start()
        return "thread"
