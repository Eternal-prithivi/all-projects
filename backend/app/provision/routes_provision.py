# =============================================================================
# MODULE: provision/routes_provision.py  (~600 lines)
# PURPOSE: REST API for AWS infrastructure provisioning via Terraform
#   - /templates          → list deployment templates
#   - /modules            → list available AWS modules
#   - /plan               → run terraform plan (policy check + cost estimate)
#   - /apply              → run terraform apply (creates real AWS resources)
#   - /destroy            → run terraform destroy
#   - /deployments        → list user's deployments
#   - /deployments/{id}   → get deployment detail
#   - /deployments/{id}/drift → trigger drift check
#   - /deployments/{id}/remediate → fix drift (terraform apply)
#   - /policy-check       → run policy engine only (no deploy)
#   - /estimate           → cost estimation only
#   - /audit-log          → query provision audit trail
# READS FROM: provision_deployments, provision_audit_log
# WRITES TO: provision_deployments, provision_audit_log
# MOUNTED AT: /api/provision
# DEPENDS ON: BYOC credentials for AWS auth, Terraform CLI on server
# DO NOT:
#   - Allow apply without a prior successful plan
#   - Allow apply when policy check has blocks
#   - Run terraform commands without BYOC credential injection
#   - Skip audit logging on any plan/apply/destroy/remediate action
# =============================================================================
from __future__ import annotations

import asyncio
import logging
import threading
import time
from datetime import datetime, timedelta

from app.debug_agent_log import agent_log
from typing import Any, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.database.mongo_client import get_database
from app.users.routes_users import get_current_user
from app.provision.models import (
    DeploymentRecord,
    DeploymentStatus,
    DriftStatus,
    ProvisionConfig,
    ProvisionTemplate,
)
from app.provision.terraform_runner import (
    TerraformRunner,
    check_terraform_installed,
    create_workspace,
    write_tfvars,
    get_terraform_version,
)
from app.provision.config_normalize import normalize_provision_config
from app.provision.policy_checker import full_policy_check, get_yaml_rules
from app.provision.cost_estimator import estimate_cost
from app.provision.drift_detector import RemediationResult, detect_drift, remediate_drift
from app.provision.boto3_drift import detect_drift_boto3, remediate_drift_boto3
from app.provision.engine_resolver import (
    deployment_engine,
    get_user_provision_engine,
    resolve_provision_engine,
)
from app.provision.boto3_composer import BOTO3_IMPLEMENTED, boto3_can_handle
from app.provision.audit_logger import (
    log_provision_action,
    get_deployment_audit_log,
    get_user_audit_log,
)
from app.provision.boto3_deployer import (
    plan_fast,
    apply_fast,
    destroy_fast,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Provisioning"])

RECENT_DEPLOYMENTS_LIMIT = 5
_DEPLOYMENT_LIST_PROJECTION = {"plan_output": 0, "apply_output": 0}


# ── Helper: resolve BYOC credentials for the current user ──

def _resolve_byoc_credentials(user: Any, region: str = "ap-south-1") -> dict:
    """
    Resolve AWS credentials from the user's BYOC configuration.
    Returns dict with AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, etc.
    Returns empty dict if BYOC is not configured.
    """
    from app.provision.byoc_credentials import resolve_byoc_terraform_env

    return resolve_byoc_terraform_env(user.username, region)


def _get_deployments_collection():
    """Get the provision_deployments MongoDB collection."""
    DB = get_database()
    return DB["provision_deployments"]


# ── Templates & Modules ──


TEMPLATES = [
    {
        "key": "static-site",
        "name": "Static Website (S3 Only)",
        "description": "Host a static HTML/CSS/JS website on S3. Free tier eligible.",
        "services": {"enable_s3": True},
        "estimated_cost": "$0.00/month",
        "icon": "globe",
    },
    {
        "key": "backend-app",
        "name": "Backend Application (VPC + EC2 + IAM)",
        "description": "EC2 instance with VPC networking and IAM role. Free tier eligible.",
        "services": {"enable_vpc": True, "enable_ec2": True, "enable_iam": True, "enable_cloudwatch": True},
        "estimated_cost": "$0.00/month",
        "icon": "server",
    },
    {
        "key": "serverless-db",
        "name": "Serverless Database (DynamoDB)",
        "description": "Always-free DynamoDB table with provisioned capacity within free limits.",
        "services": {"enable_dynamodb": True},
        "estimated_cost": "$0.00/month",
        "icon": "database",
    },
]

MODULES = [
    {"key": "vpc", "name": "VPC", "description": "Virtual Private Cloud with public/private subnets", "flag": "enable_vpc", "free_tier": True},
    {"key": "ec2", "name": "EC2", "description": "Elastic Compute Cloud instance (t2.micro free)", "flag": "enable_ec2", "free_tier": True, "requires": ["vpc"]},
    {"key": "s3", "name": "S3", "description": "Simple Storage Service bucket (5GB free)", "flag": "enable_s3", "free_tier": True},
    {"key": "iam", "name": "IAM", "description": "Identity & Access Management role", "flag": "enable_iam", "free_tier": True},
    {"key": "cloudwatch", "name": "CloudWatch", "description": "Monitoring & alerting (basic free)", "flag": "enable_cloudwatch", "free_tier": True, "requires": ["ec2"]},
    {"key": "billing", "name": "Billing", "description": "AWS Budget alert ($1/month default)", "flag": "always_on", "free_tier": True},
    {"key": "dynamodb", "name": "DynamoDB", "description": "NoSQL database (25 RCU/WCU free)", "flag": "enable_dynamodb", "free_tier": True},
]


@router.get("/templates")
async def list_templates(user: dict = Depends(get_current_user)):
    """List available deployment templates."""
    return {"templates": TEMPLATES}


@router.get("/modules")
async def list_modules(user: dict = Depends(get_current_user)):
    """List all available AWS modules with their config schemas."""
    return {"modules": MODULES}


@router.get("/status")
async def provisioning_status(user: dict = Depends(get_current_user)):
    """Terraform CLI status, user engine preference, and boto3 module support."""
    import os

    tf_installed = check_terraform_installed()
    tf_version = get_terraform_version() if tf_installed else None
    user_engine = get_user_provision_engine(user.username)
    environment = os.getenv("ENVIRONMENT", "development")
    return {
        "terraform_installed": tf_installed,
        "terraform_version": tf_version,
        "policy_rules_count": len(get_yaml_rules()),
        "user_provision_engine": user_engine,
        "boto3_supported_modules": sorted(BOTO3_IMPLEMENTED),
        "environment": environment,
        "hosting_hint": (
            "Boto3 is recommended on Render free tier (fast, low memory). "
            "Terraform works on localhost and Render Docker when the CLI is installed."
            if environment == "production"
            else "Both engines work on localhost; use Boto3 for quick tests without Terraform installed."
        ),
    }


@router.get("/policy-rules")
async def list_policy_rules(user: dict = Depends(get_current_user)):
    """Return YAML policy rules for read-only display in the UI."""
    rules = get_yaml_rules()
    return {"rules": rules, "count": len(rules)}


# ── Policy Check & Cost Estimate (standalone) ──


@router.post("/policy-check")
async def run_policy_check(
    config: ProvisionConfig,
    user: dict = Depends(get_current_user),
):
    """Run policy engine against a config WITHOUT deploying."""
    config_dict = config.model_dump()
    _prepare_provision_config(config_dict)
    result = full_policy_check(config_dict, include_opa=False)
    return result.model_dump()


@router.post("/estimate")
async def run_cost_estimate(
    config: ProvisionConfig,
    user: dict = Depends(get_current_user),
):
    """Get cost estimation for a given config (instant lookup table)."""
    config_dict = config.model_dump()
    _prepare_provision_config(config_dict)
    result = estimate_cost(config_dict, use_infracost=False)
    return result.model_dump()


# ── Plan / Apply / Destroy / Remediate ──


@router.post("/plan")
async def run_plan(
    config: ProvisionConfig,
    user: dict = Depends(get_current_user),
):
    """
    Plan deployment — boto3 (instant) or Terraform (background poll) per Settings.
    Works on localhost and Render; engine from users.settings.preferences.provision_engine.
    """
    config_dict = config.model_dump()
    _prepare_provision_config(config_dict)

    engine = resolve_provision_engine(user.username, config_dict)

    policy_result = full_policy_check(config_dict, include_opa=False)
    cost_result = estimate_cost(config_dict, use_infracost=False)

    deployment_id = f"{user.username}-{int(time.time())}"
    plan_t0 = time.monotonic()

    # #region agent log
    agent_log(
        "H5",
        "routes_provision.run_plan:entry",
        "plan request started",
        {"deployment_id": deployment_id, "user": user.username},
        run_id="post-fix",
    )
    # #endregion

    config_dict["tags"]["Owner"] = user.username
    config_dict["tags"]["ManagedBy"] = "zenith-provision"

    aws_creds = _resolve_byoc_credentials(user, config_dict.get("aws_region", "ap-south-1"))
    if not aws_creds.get("AWS_ACCESS_KEY_ID"):
        msg = (
            "No AWS credentials available for Terraform. "
            "Connect AWS under Settings (BYOC), then try again."
        )
        return {
            "success": False,
            "stage": "credentials",
            "error": msg,
            "policy_check": policy_result.model_dump(),
            "cost_estimate": cost_result.model_dump(),
        }

    if engine == "boto3":
        fast_result = plan_fast(config_dict, aws_creds)
        status = DeploymentStatus.AWAITING_APPLY if fast_result["success"] else DeploymentStatus.PLAN_FAILED
        _save_deployment(
            user.username, deployment_id, config_dict, "boto3",
            status, policy_result, cost_result,
            plan_output=fast_result["output"] or fast_result.get("error", ""),
        )
        _get_deployments_collection().update_one(
            {"deployment_name": deployment_id},
            {"$set": {
                "plan_error": fast_result.get("error") or "",
                "plan_stage": "plan",
                "has_plan_changes": fast_result.get("has_changes", False),
                "provision_engine": "boto3",
                "fast_path": True,
            }},
        )
        log_provision_action(
            action="plan", actor=user.username, deployment_id=deployment_id,
            status="success" if fast_result["success"] else "failed",
            details={"provision_engine": "boto3", "template": config_dict.get("template")},
            error=fast_result.get("error"),
        )
        return {
            "success": fast_result["success"],
            "status": "done",
            "deployment_id": deployment_id,
            "stage": "plan",
            "provision_engine": "boto3",
            "fast_path": True,
            "plan_output": fast_result["output"],
            "error": fast_result.get("error"),
            "policy_check": policy_result.model_dump(),
            "cost_estimate": cost_result.model_dump(),
        }

    _save_deployment(
        user.username, deployment_id, config_dict, "",
        DeploymentStatus.PLANNING, policy_result, cost_result,
        plan_output="Preparing terraform workspace on the server…\n",
    )
    _get_deployments_collection().update_one(
        {"deployment_name": deployment_id},
        {"$set": {"provision_engine": "terraform", "fast_path": False}},
    )

    thread = threading.Thread(
        target=_run_plan_background,
        args=(user.username, deployment_id, config_dict, "", aws_creds, policy_result, cost_result),
        daemon=True,
    )
    thread.start()

    # #region agent log
    agent_log(
        "H1",
        "routes_provision.run_plan:accepted",
        "plan accepted; background thread started",
        {"deployment_id": deployment_id, "elapsed_s": round(time.monotonic() - plan_t0, 2)},
        run_id="post-fix",
    )
    # #endregion

    return {
        "success": True,
        "status": "running",
        "deployment_id": deployment_id,
        "stage": "background",
        "provision_engine": "terraform",
        "message": "Terraform plan is running. Poll /api/provision/plan/status/{deployment_id}.",
        "policy_check": policy_result.model_dump(),
        "cost_estimate": cost_result.model_dump(),
    }


@router.get("/plan/status/{deployment_id}")
async def get_plan_status(
    deployment_id: str,
    user: dict = Depends(get_current_user),
):
    """Poll background terraform plan result."""
    doc = await asyncio.to_thread(_get_deployment_for_user, deployment_id, user.username)
    if not doc:
        raise HTTPException(status_code=404, detail="Deployment not found.")

    status = doc.get("status")
    if isinstance(status, DeploymentStatus):
        status_value = status.value
    else:
        status_value = str(status)

    done = status_value in (
        DeploymentStatus.AWAITING_APPLY.value,
        DeploymentStatus.PLAN_FAILED.value,
    )
    success = status_value == DeploymentStatus.AWAITING_APPLY.value
    plan_output = doc.get("plan_output") or ""
    plan_error = doc.get("plan_error") or ""
    plan_stage = doc.get("plan_stage") or ("plan" if done else "background")

    # Stale planning row (server died mid-plan, thread lost)
    updated_at = doc.get("updated_at")
    if (
        not done
        and status_value == DeploymentStatus.PLANNING.value
        and updated_at
        and isinstance(updated_at, datetime)
        and updated_at < datetime.utcnow() - timedelta(minutes=12)
    ):
        done = True
        success = False
        plan_error = plan_error or (
            "Plan timed out or the server restarted during terraform. "
            "Check Render is Live, open /health, then run a new plan."
        )
        plan_stage = "interrupted"

    return {
        "deployment_id": deployment_id,
        "status": status_value,
        "done": done,
        "success": success if done else None,
        "plan_output": plan_output,
        "error": plan_error if done and not success else (None if success else plan_error),
        "has_changes": doc.get("has_plan_changes", False),
        "stage": plan_stage,
        "message": (
            f"Terraform {plan_stage} in progress…"
            if not done and status_value == DeploymentStatus.PLANNING.value
            else None
        ),
    }


@router.post("/apply/{deployment_id}")
async def run_apply(
    deployment_id: str,
    user: dict = Depends(get_current_user),
):
    """Run terraform apply on a previously planned deployment."""
    collection = _get_deployments_collection()
    deployment = collection.find_one({"deployment_name": deployment_id, "user_id": user.username})

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    if deployment.get("status") not in [DeploymentStatus.AWAITING_APPLY, DeploymentStatus.APPLY_FAILED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot apply — deployment status is '{deployment.get('status')}'. Run /plan first.",
        )

    # Check policy blocks
    policy_check = deployment.get("policy_check", {})
    if policy_check.get("blocks"):
        raise HTTPException(status_code=400, detail="Cannot apply — policy check has blocking violations.")

    config_dict = deployment.get("config", {}) or {}
    aws_creds = _resolve_byoc_credentials(
        user, config_dict.get("aws_region", "ap-south-1")
    )

    collection.update_one(
        {"deployment_name": deployment_id},
        {"$set": {"status": DeploymentStatus.APPLYING, "updated_at": datetime.utcnow()}},
    )

    engine = deployment_engine(deployment)

    if engine == "boto3":
        boto3_ctx = deployment.get("boto3_context")
        apply_result = apply_fast(config_dict, aws_creds, boto3_ctx)
        ctx_out = apply_result.get("boto3_context") or {}
        resources_count = len(ctx_out) if apply_result["success"] else 0
        new_status = DeploymentStatus.DEPLOYED if apply_result["success"] else DeploymentStatus.APPLY_FAILED
        collection.update_one(
            {"deployment_name": deployment_id},
            {"$set": {
                "status": new_status,
                "apply_output": apply_result.get("output", ""),
                "resources_count": resources_count,
                "provision_engine": "boto3",
                "fast_path": True,
                "boto3_context": ctx_out,
                "updated_at": datetime.utcnow(),
            }},
        )
        log_provision_action(
            action="apply", actor=user.username, deployment_id=deployment_id,
            status="success" if apply_result["success"] else "failed",
            details={"resources_count": resources_count, "provision_engine": "boto3"},
            error=apply_result.get("error"),
        )
        return {
            "success": apply_result["success"],
            "status": new_status,
            "resources_count": resources_count,
            "output": apply_result.get("output", ""),
            "error": apply_result.get("error"),
            "provision_engine": "boto3",
        }

    workspace = deployment.get("terraform_workspace", "")
    if not workspace:
        raise HTTPException(status_code=500, detail="Workspace path missing from deployment record.")

    runner = TerraformRunner(workspace, aws_creds)

    apply_result = runner.apply()

    new_status = DeploymentStatus.DEPLOYED if apply_result["success"] else DeploymentStatus.APPLY_FAILED
    resources = runner.get_state_resources() if apply_result["success"] else []

    collection.update_one(
        {"deployment_name": deployment_id},
        {"$set": {
            "status": new_status,
            "apply_output": apply_result.get("output", ""),
            "resources_count": len(resources),
            "updated_at": datetime.utcnow(),
        }},
    )

    log_provision_action(
        action="apply", actor=user.username, deployment_id=deployment_id,
        status="success" if apply_result["success"] else "failed",
        details={"resources_count": len(resources)},
        error=apply_result.get("error"),
    )

    return {
        "success": apply_result["success"],
        "status": new_status,
        "resources_count": len(resources),
        "output": apply_result.get("output", ""),
        "error": apply_result.get("error"),
    }


@router.post("/destroy/{deployment_id}")
async def run_destroy(
    deployment_id: str,
    user: dict = Depends(get_current_user),
):
    """Run terraform destroy on a deployed infrastructure."""
    collection = _get_deployments_collection()
    deployment = collection.find_one({"deployment_name": deployment_id, "user_id": user.username})

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    if deployment.get("status") not in [DeploymentStatus.DEPLOYED, DeploymentStatus.DESTROY_FAILED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot destroy — deployment status is '{deployment.get('status')}'.",
        )

    config_dict = deployment.get("config", {}) or {}
    aws_creds = _resolve_byoc_credentials(
        user, config_dict.get("aws_region", "ap-south-1")
    )

    collection.update_one(
        {"deployment_name": deployment_id},
        {"$set": {"status": DeploymentStatus.DESTROYING, "updated_at": datetime.utcnow()}},
    )

    engine = deployment_engine(deployment)

    if engine == "boto3":
        destroy_result = destroy_fast(config_dict, aws_creds, deployment.get("boto3_context"))
    else:
        workspace = deployment.get("terraform_workspace", "")
        if not workspace or workspace in ("fast-path", "boto3"):
            raise HTTPException(
                status_code=400,
                detail="Terraform workspace missing for this deployment. Cannot destroy via Terraform.",
            )
        runner = TerraformRunner(workspace, aws_creds)
        destroy_result = runner.destroy()

    new_status = DeploymentStatus.DESTROYED if destroy_result["success"] else DeploymentStatus.DESTROY_FAILED

    collection.update_one(
        {"deployment_name": deployment_id},
        {"$set": {
            "status": new_status,
            "resources_count": 0 if destroy_result["success"] else deployment.get("resources_count", 0),
            "destroyed_at": datetime.utcnow() if destroy_result["success"] else None,
            "updated_at": datetime.utcnow(),
        }},
    )

    log_provision_action(
        action="destroy", actor=user.username, deployment_id=deployment_id,
        status="success" if destroy_result["success"] else "failed",
        error=destroy_result.get("error"),
    )

    return {
        "success": destroy_result["success"],
        "status": new_status,
        "output": destroy_result.get("output", ""),
        "error": destroy_result.get("error"),
    }


# ── Deployments ──


def _serialize_deployment_docs(docs: list) -> list:
    for doc in docs:
        doc["_id"] = str(doc["_id"])
    return docs


@router.get("/deployments")
async def list_deployments(user: dict = Depends(get_current_user)):
    """
    List deployments split into recent (active) and history (archived + older active).

    The UI shows only ``recent`` by default; ``history`` holds archived rows and active
    stacks beyond RECENT_DEPLOYMENTS_LIMIT.
    """
    collection = _get_deployments_collection()
    user_filter = {"user_id": user.username}
    active_filter = {**user_filter, "archived": {"$ne": True}}

    all_active = list(
        collection.find(active_filter, _DEPLOYMENT_LIST_PROJECTION).sort("created_at", -1)
    )
    recent = _serialize_deployment_docs(all_active[:RECENT_DEPLOYMENTS_LIMIT])
    overflow = _serialize_deployment_docs(all_active[RECENT_DEPLOYMENTS_LIMIT:])

    archived = _serialize_deployment_docs(
        list(
            collection.find(
                {**user_filter, "archived": True},
                _DEPLOYMENT_LIST_PROJECTION,
            )
            .sort("archived_at", -1)
            .limit(100)
        )
    )

    history = archived + overflow

    return {
        "recent": recent,
        "history": history,
        "deployments": recent,
        "count": len(recent),
        "counts": {
            "recent": len(recent),
            "history": len(history),
            "active": len(all_active),
        },
    }


@router.delete("/deployments/{deployment_id}")
async def remove_deployment(
    deployment_id: str,
    permanent: bool = Query(
        False,
        description="If true, permanently delete an already-archived record",
    ),
    user: dict = Depends(get_current_user),
):
    """
    Archive a deployment (moves to history) or permanently delete from history.

    Archiving does not run terraform destroy — use POST /destroy/{id} for live AWS stacks.
    """
    collection = _get_deployments_collection()
    deployment = collection.find_one(
        {"deployment_name": deployment_id, "user_id": user.username}
    )
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    if permanent:
        if not deployment.get("archived"):
            raise HTTPException(
                status_code=400,
                detail="Archive the deployment first, then remove it from history.",
            )
        collection.delete_one(
            {"deployment_name": deployment_id, "user_id": user.username}
        )
        log_provision_action(
            action="delete_permanent",
            actor=user.username,
            deployment_id=deployment_id,
            status="success",
        )
        return {"success": True, "permanent": True}

    collection.update_one(
        {"deployment_name": deployment_id},
        {
            "$set": {
                "archived": True,
                "archived_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        },
    )
    log_provision_action(
        action="archive",
        actor=user.username,
        deployment_id=deployment_id,
        status="success",
        details={"previous_status": deployment.get("status")},
    )
    return {"success": True, "archived": True}


@router.get("/deployments/{deployment_id}")
async def get_deployment(
    deployment_id: str,
    user: dict = Depends(get_current_user),
):
    """Get full detail of a specific deployment."""
    collection = _get_deployments_collection()
    deployment = collection.find_one(
        {"deployment_name": deployment_id, "user_id": user.username}
    )
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    deployment["_id"] = str(deployment["_id"])
    return deployment


@router.post("/deployments/{deployment_id}/drift")
async def check_drift(
    deployment_id: str,
    user: dict = Depends(get_current_user),
):
    """Trigger an on-demand drift check for a deployed infrastructure."""
    collection = _get_deployments_collection()
    deployment = collection.find_one(
        {"deployment_name": deployment_id, "user_id": user.username}
    )
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    if deployment.get("status") != DeploymentStatus.DEPLOYED:
        raise HTTPException(status_code=400, detail="Drift check only available for deployed infrastructure.")

    config_dict = deployment.get("config", {}) or {}
    aws_creds = _resolve_byoc_credentials(
        user, config_dict.get("aws_region", "ap-south-1")
    )

    engine = deployment_engine(deployment)
    if engine == "boto3":
        drift_report = detect_drift_boto3(
            config_dict, aws_creds, deployment.get("boto3_context")
        )
    else:
        workspace = deployment.get("terraform_workspace", "")
        if not workspace or workspace in ("fast-path", "boto3"):
            raise HTTPException(
                status_code=400,
                detail=(
                    "This deployment has no Terraform workspace. "
                    "Use Boto3 engine in Settings for new deployments, or redeploy with Terraform."
                ),
            )
        drift_report = detect_drift(workspace, aws_creds)

    # Append to drift history and update latest status
    collection.update_one(
        {"deployment_name": deployment_id},
        {
            "$push": {"drift_history": drift_report.model_dump()},
            "$set": {
                "latest_drift": drift_report.status,
                "updated_at": datetime.utcnow(),
            },
        },
    )

    log_provision_action(
        action="drift_check", actor=user.username, deployment_id=deployment_id,
        status="success",
        details={
            "drift_status": drift_report.status,
            "changes_detected": drift_report.changes_detected,
        },
    )

    return drift_report.model_dump()


class RemediateRequest(BaseModel):
    """Request body for drift remediation."""
    check_only: bool = True


@router.post("/deployments/{deployment_id}/remediate")
async def remediate_deployment_drift(
    deployment_id: str,
    body: Optional[RemediateRequest] = None,
    user: dict = Depends(get_current_user),
):
    """
    Remediate drift by re-applying Terraform configuration.

    By default runs in check-only mode (shows plan without applying).
    Set check_only=false in the request body to actually apply.
    """
    check_only = body.check_only if body else True

    collection = _get_deployments_collection()
    deployment = collection.find_one(
        {"deployment_name": deployment_id, "user_id": user.username}
    )
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    if deployment.get("status") != DeploymentStatus.DEPLOYED:
        raise HTTPException(status_code=400, detail="Remediation only available for deployed infrastructure.")

    config_dict = deployment.get("config", {}) or {}
    aws_creds = _resolve_byoc_credentials(
        user, config_dict.get("aws_region", "ap-south-1")
    )

    engine = deployment_engine(deployment)
    if engine == "boto3":
        raw = remediate_drift_boto3(
            config_dict,
            aws_creds,
            deployment.get("boto3_context"),
            check_only=check_only,
        )
        result = RemediationResult(
            success=raw.get("success", False),
            performed=raw.get("performed", False),
            message=raw.get("message", ""),
            plan_output=raw.get("plan_output", ""),
            apply_output=raw.get("apply_output", ""),
        )
        if raw.get("boto3_context"):
            collection.update_one(
                {"deployment_name": deployment_id},
                {"$set": {"boto3_context": raw["boto3_context"]}},
            )
    else:
        workspace = deployment.get("terraform_workspace", "")
        if not workspace or workspace in ("fast-path", "boto3"):
            raise HTTPException(
                status_code=400,
                detail="Terraform workspace missing — cannot remediate with Terraform.",
            )
        result = remediate_drift(workspace, aws_creds, check_only=check_only)

    # If remediation was actually performed, update deployment record
    if result.performed and result.success:
        collection.update_one(
            {"deployment_name": deployment_id},
            {"$set": {
                "latest_drift": DriftStatus.CLEAN,
                "updated_at": datetime.utcnow(),
            }},
        )

    log_provision_action(
        action="remediate", actor=user.username, deployment_id=deployment_id,
        status="success" if result.success else "failed",
        details={
            "check_only": check_only,
            "performed": result.performed,
            "message": result.message,
        },
        error=None if result.success else result.message,
    )

    return result.model_dump()


# ── Audit Log ──


@router.get("/audit-log")
async def get_audit_log(
    deployment_id: Optional[str] = None,
    limit: int = 50,
    user: dict = Depends(get_current_user),
):
    """Query the provision audit log for the current user (or one deployment)."""
    if deployment_id:
        events = get_deployment_audit_log(deployment_id)
    else:
        events = get_user_audit_log(user.username, limit=limit)

    # Serialize datetime objects
    for event in events:
        if isinstance(event.get("timestamp"), datetime):
            event["timestamp"] = event["timestamp"].isoformat()

    return {"events": events, "count": len(events)}


# ── Internal Helpers ──


def _apply_template_defaults(config: dict) -> None:
    """Apply template preset defaults to a config dict."""
    template = config.get("template")
    if not template or template == "custom":
        return

    for tmpl in TEMPLATES:
        if tmpl["key"] == template:
            for flag, value in tmpl["services"].items():
                config[flag] = value
            break


def _prepare_provision_config(config: dict) -> None:
    """Template defaults + validated resource names for Terraform."""
    _apply_template_defaults(config)
    try:
        normalize_provision_config(config)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


def _save_deployment(
    user_id: str,
    deployment_id: str,
    config: dict,
    workspace: str,
    status: DeploymentStatus,
    policy_result: Any,
    cost_result: Any,
    plan_output: str = "",
) -> None:
    """Save or update a deployment record in MongoDB."""
    collection = _get_deployments_collection()

    enabled = [m for m in ["vpc", "ec2", "s3", "iam", "cloudwatch", "dynamodb"]
               if config.get(f"enable_{m}", False)]

    doc = {
        "user_id": user_id,
        "deployment_name": deployment_id,
        "template": config.get("template"),
        "config": config,
        "enabled_modules": enabled,
        "status": status,
        "terraform_workspace": workspace,
        "plan_output": plan_output,
        "apply_output": "",
        "cost_estimate": cost_result.model_dump() if hasattr(cost_result, "model_dump") else cost_result,
        "policy_check": policy_result.model_dump() if hasattr(policy_result, "model_dump") else policy_result,
        "drift_history": [],
        "latest_drift": DriftStatus.UNKNOWN,
        "resources_count": 0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "destroyed_at": None,
    }

    # Upsert — update if exists, insert if new
    collection.update_one(
        {"deployment_name": deployment_id},
        {"$set": doc, "$setOnInsert": {"archived": False}},
        upsert=True,
    )


def _get_deployment_for_user(deployment_id: str, username: str) -> Optional[dict]:
    return _get_deployments_collection().find_one(
        {"deployment_name": deployment_id, "user_id": username}
    )


def recover_plans_interrupted_by_restart(max_age_minutes: int = 3) -> int:
    """
    Mark in-flight plans as failed after a Render/process restart.

    Background terraform threads do not survive deploys or OOM kills; without this,
    the UI polls forever on status=planning.
    """
    cutoff = datetime.utcnow() - timedelta(minutes=max_age_minutes)
    result = _get_deployments_collection().update_many(
        {
            "status": DeploymentStatus.PLANNING.value,
            "updated_at": {"$lt": cutoff},
        },
        {
            "$set": {
                "status": DeploymentStatus.PLAN_FAILED.value,
                "plan_stage": "interrupted",
                "plan_error": (
                    "Terraform plan was interrupted when the server restarted "
                    "(common on Render free tier during terraform init/plan). "
                    "Wait until the service is Live, then start a new plan."
                ),
                "updated_at": datetime.utcnow(),
            }
        },
    )
    return result.modified_count


def _update_plan_progress(deployment_id: str, stage: str, message: str) -> None:
    """Write in-progress status so the UI poll is not stuck on a static line."""
    _get_deployments_collection().update_one(
        {"deployment_name": deployment_id},
        {
            "$set": {
                "plan_stage": stage,
                "plan_output": message,
                "updated_at": datetime.utcnow(),
            }
        },
    )


def _touch_plan_heartbeat(deployment_id: str) -> None:
    """Keep updated_at fresh while terraform runs (Render status polls stay responsive)."""
    _get_deployments_collection().update_one(
        {"deployment_name": deployment_id},
        {"$set": {"updated_at": datetime.utcnow()}},
    )


def _run_plan_background(
    username: str,
    deployment_id: str,
    config_dict: dict,
    workspace: str,
    aws_creds: dict[str, str],
    policy_result: Any,
    cost_result: Any,
) -> None:
    """Run terraform init/plan off the HTTP thread (avoids Render 502 on long requests)."""
    plan_t0 = time.monotonic()
    logger.info("Background terraform plan started deployment_id=%s user=%s", deployment_id, username)
    stop_heartbeat = threading.Event()

    def _heartbeat_loop() -> None:
        while not stop_heartbeat.wait(20):
            try:
                _touch_plan_heartbeat(deployment_id)
            except Exception:
                pass

    heartbeat_thread = threading.Thread(target=_heartbeat_loop, daemon=True)
    heartbeat_thread.start()
    # #region agent log
    agent_log(
        "H1",
        "routes_provision._run_plan_background:start",
        "background plan started",
        {"deployment_id": deployment_id},
        run_id="post-fix",
    )
    # #endregion
    try:
        if not workspace:
            _update_plan_progress(
                deployment_id,
                "workspace",
                "Copying terraform modules into workspace (first time can take ~30s on Render)…\n",
            )
            workspace = create_workspace(deployment_id)
            write_tfvars(workspace, config_dict)
            _get_deployments_collection().update_one(
                {"deployment_name": deployment_id},
                {"$set": {"terraform_workspace": workspace, "config": config_dict}},
            )

        _update_plan_progress(
            deployment_id,
            "init",
            "Running terraform init on the server (may take 1–3 minutes on Render)…\n",
        )

        runner = TerraformRunner(workspace, aws_creds)

        init_t0 = time.monotonic()
        init_result = runner.init()
        # #region agent log
        agent_log(
            "H1",
            "routes_provision._run_plan_background:init_done",
            "terraform init finished",
            {
                "deployment_id": deployment_id,
                "success": init_result["success"],
                "init_s": round(time.monotonic() - init_t0, 2),
                "total_s": round(time.monotonic() - plan_t0, 2),
            },
            run_id="post-fix",
        )
        # #endregion
        if not init_result["success"]:
            err = init_result.get("error") or "Terraform init failed"
            _save_deployment(
                username, deployment_id, config_dict, workspace,
                DeploymentStatus.PLAN_FAILED, policy_result, cost_result,
                plan_output=err,
            )
            _get_deployments_collection().update_one(
                {"deployment_name": deployment_id},
                {"$set": {"plan_error": err, "plan_stage": "init"}},
            )
            return

        init_snippet = (init_result.get("output") or "").strip()
        if init_snippet:
            init_snippet = init_snippet[-2000:] + "\n"
        _update_plan_progress(
            deployment_id,
            "plan",
            f"{init_snippet}Running terraform plan (talking to AWS)…\n",
        )

        plan_t1 = time.monotonic()
        plan_result = runner.plan()
        # #region agent log
        agent_log(
            "H1",
            "routes_provision._run_plan_background:plan_done",
            "terraform plan finished",
            {
                "deployment_id": deployment_id,
                "success": plan_result["success"],
                "plan_s": round(time.monotonic() - plan_t1, 2),
                "total_s": round(time.monotonic() - plan_t0, 2),
            },
            run_id="post-fix",
        )
        # #endregion

        status = DeploymentStatus.AWAITING_APPLY if plan_result["success"] else DeploymentStatus.PLAN_FAILED
        plan_err = plan_result.get("error")
        _save_deployment(
            username, deployment_id, config_dict, workspace,
            status, policy_result, cost_result,
            plan_output=plan_result.get("output", ""),
        )
        _get_deployments_collection().update_one(
            {"deployment_name": deployment_id},
            {
                "$set": {
                    "plan_error": plan_err or "",
                    "plan_stage": "plan" if plan_result["success"] else "plan",
                    "has_plan_changes": plan_result.get("has_changes", False),
                }
            },
        )
        log_provision_action(
            action="plan", actor=username, deployment_id=deployment_id,
            status="success" if plan_result["success"] else "failed",
            details={"has_changes": plan_result.get("has_changes", False)},
            error=plan_err,
        )
        logger.info(
            "Background terraform plan finished deployment_id=%s success=%s total_s=%.1f",
            deployment_id,
            plan_result["success"],
            time.monotonic() - plan_t0,
        )
    except Exception as exc:
        logger.exception("Background plan failed for %s", deployment_id)
        err = str(exc)
        # #region agent log
        agent_log(
            "H2",
            "routes_provision._run_plan_background:exception",
            "background plan exception",
            {"deployment_id": deployment_id, "exc_type": type(exc).__name__},
            run_id="post-fix",
        )
        # #endregion
        try:
            _save_deployment(
                username, deployment_id, config_dict, workspace,
                DeploymentStatus.PLAN_FAILED, policy_result, cost_result,
                plan_output=err,
            )
            _get_deployments_collection().update_one(
                {"deployment_name": deployment_id},
                {"$set": {"plan_error": err, "plan_stage": "server"}},
            )
        except Exception:
            pass
    finally:
        stop_heartbeat.set()
