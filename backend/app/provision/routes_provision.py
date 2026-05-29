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
#   - /roles              → manage RBAC role assignments
#   - /audit-log          → query provision audit trail
#   - /my-permissions     → show current user's provision permissions
# READS FROM: provision_deployments, provision_roles, provision_audit_log
# WRITES TO: provision_deployments, provision_roles, provision_audit_log
# MOUNTED AT: /api/provision
# DEPENDS ON: BYOC credentials for AWS auth, Terraform CLI on server
# DO NOT:
#   - Allow apply without a prior successful plan
#   - Allow apply when policy check has blocks
#   - Run terraform commands without BYOC credential injection
#   - Skip RBAC checks on state-changing endpoints
#   - Skip audit logging on any plan/apply/destroy/remediate action
# =============================================================================
from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
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
from app.provision.drift_detector import detect_drift, remediate_drift
from app.provision.rbac import (
    ProvisionAction,
    check_permission,
    get_user_permissions,
    get_user_provision_role,
    assign_provision_role,
    list_role_assignments,
)
from app.provision.audit_logger import (
    log_provision_action,
    get_deployment_audit_log,
    get_user_audit_log,
    get_recent_audit_log,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Provisioning"])


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


def _enforce_permission(user: Any, action: str, deployment_id: str = ""):
    """
    Check RBAC permission and raise HTTPException if denied.
    Also logs the denial to the audit trail.
    """
    allowed, message = check_permission(user, action)
    if not allowed:
        log_provision_action(
            action=action,
            actor=user.username,
            deployment_id=deployment_id or "n/a",
            status="denied",
            details={"reason": message},
        )
        raise HTTPException(status_code=403, detail=message)


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
    """Check if Terraform is installed and return system status."""
    tf_installed = check_terraform_installed()
    tf_version = get_terraform_version() if tf_installed else None
    user_perms = get_user_permissions(user)
    return {
        "terraform_installed": tf_installed,
        "terraform_version": tf_version,
        "policy_rules_count": len(get_yaml_rules()),
        "user_permissions": user_perms,
    }


@router.get("/my-permissions")
async def my_permissions(user: dict = Depends(get_current_user)):
    """Show the current user's provision RBAC permissions."""
    return get_user_permissions(user)


@router.get("/policy-rules")
async def list_policy_rules(user: dict = Depends(get_current_user)):
    """Return YAML policy rules for read-only display in the UI."""
    _enforce_permission(user, ProvisionAction.VIEW)
    rules = get_yaml_rules()
    return {"rules": rules, "count": len(rules)}


# ── Policy Check & Cost Estimate (standalone) ──


@router.post("/policy-check")
async def run_policy_check(
    config: ProvisionConfig,
    user: dict = Depends(get_current_user),
):
    """Run policy engine against a config WITHOUT deploying."""
    _enforce_permission(user, ProvisionAction.PLAN)
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
    _enforce_permission(user, ProvisionAction.PLAN)
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
    Run terraform plan — creates workspace, writes tfvars, runs policy check,
    cost estimate, and terraform plan. Returns full result.
    """
    _enforce_permission(user, ProvisionAction.PLAN)

    if not check_terraform_installed():
        raise HTTPException(status_code=503, detail="Terraform CLI is not installed on this server.")

    config_dict = config.model_dump()
    _prepare_provision_config(config_dict)

    # Step 1–2: Fast review (YAML policies + lookup table; no OPA/Infracost yet)
    policy_result = full_policy_check(config_dict, include_opa=False)
    cost_result = estimate_cost(config_dict, use_infracost=False)

    # Step 3: Create workspace + write tfvars
    deployment_id = f"{user.username}-{int(time.time())}"
    workspace = create_workspace(deployment_id)
    write_tfvars(workspace, config_dict)

    # Fill in user-specific tags
    config_dict["tags"]["Owner"] = user.username
    config_dict["tags"]["ManagedBy"] = "zenith-provision"

    # Step 4: Terraform init + plan
    aws_creds = _resolve_byoc_credentials(user, config_dict.get("aws_region", "ap-south-1"))
    runner = TerraformRunner(workspace, aws_creds)

    init_result = runner.init()
    if not init_result["success"]:
        _save_deployment(user.username, deployment_id, config_dict, workspace,
                         DeploymentStatus.PLAN_FAILED, policy_result, cost_result,
                         plan_output=init_result.get("error", ""))
        log_provision_action(
            action="plan", actor=user.username, deployment_id=deployment_id,
            status="failed", details={"stage": "init"},
            error=init_result.get("error"),
        )
        return {
            "success": False,
            "stage": "init",
            "error": init_result.get("error"),
            "policy_check": policy_result.model_dump(),
            "cost_estimate": cost_result.model_dump(),
        }

    plan_result = runner.plan()

    status = DeploymentStatus.AWAITING_APPLY if plan_result["success"] else DeploymentStatus.PLAN_FAILED
    _save_deployment(user.username, deployment_id, config_dict, workspace,
                     status, policy_result, cost_result,
                     plan_output=plan_result.get("output", ""))

    log_provision_action(
        action="plan", actor=user.username, deployment_id=deployment_id,
        status="success" if plan_result["success"] else "failed",
        details={
            "has_changes": plan_result.get("has_changes", False),
            "policy_blocks": len(policy_result.blocks),
            "cost": cost_result.total_monthly_cost,
        },
        error=plan_result.get("error"),
    )

    return {
        "success": plan_result["success"],
        "stage": "plan",
        "deployment_id": deployment_id,
        "plan_output": plan_result.get("output", ""),
        "has_changes": plan_result.get("has_changes", False),
        "policy_check": policy_result.model_dump(),
        "cost_estimate": cost_result.model_dump(),
        "error": plan_result.get("error"),
    }


@router.post("/apply/{deployment_id}")
async def run_apply(
    deployment_id: str,
    user: dict = Depends(get_current_user),
):
    """Run terraform apply on a previously planned deployment."""
    _enforce_permission(user, ProvisionAction.APPLY, deployment_id)

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

    workspace = deployment.get("terraform_workspace", "")
    if not workspace:
        raise HTTPException(status_code=500, detail="Workspace path missing from deployment record.")

    aws_creds = _resolve_byoc_credentials(
        user, deployment.get("config", {}).get("aws_region", "ap-south-1")
    )
    runner = TerraformRunner(workspace, aws_creds)

    # Update status to APPLYING
    collection.update_one(
        {"deployment_name": deployment_id},
        {"$set": {"status": DeploymentStatus.APPLYING, "updated_at": datetime.utcnow()}},
    )

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
    _enforce_permission(user, ProvisionAction.DESTROY, deployment_id)

    collection = _get_deployments_collection()
    deployment = collection.find_one({"deployment_name": deployment_id, "user_id": user.username})

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    if deployment.get("status") not in [DeploymentStatus.DEPLOYED, DeploymentStatus.DESTROY_FAILED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot destroy — deployment status is '{deployment.get('status')}'.",
        )

    workspace = deployment.get("terraform_workspace", "")
    aws_creds = _resolve_byoc_credentials(
        user, deployment.get("config", {}).get("aws_region", "ap-south-1")
    )
    runner = TerraformRunner(workspace, aws_creds)

    collection.update_one(
        {"deployment_name": deployment_id},
        {"$set": {"status": DeploymentStatus.DESTROYING, "updated_at": datetime.utcnow()}},
    )

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


@router.get("/deployments")
async def list_deployments(user: dict = Depends(get_current_user)):
    """List all deployments for the current user."""
    collection = _get_deployments_collection()
    deployments = list(
        collection.find(
            {"user_id": user.username},
            {"plan_output": 0, "apply_output": 0},  # Exclude large text fields
        ).sort("created_at", -1).limit(50)
    )

    for d in deployments:
        d["_id"] = str(d["_id"])

    return {"deployments": deployments, "count": len(deployments)}


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
    _enforce_permission(user, ProvisionAction.DRIFT_CHECK, deployment_id)

    collection = _get_deployments_collection()
    deployment = collection.find_one(
        {"deployment_name": deployment_id, "user_id": user.username}
    )
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    if deployment.get("status") != DeploymentStatus.DEPLOYED:
        raise HTTPException(status_code=400, detail="Drift check only available for deployed infrastructure.")

    workspace = deployment.get("terraform_workspace", "")
    aws_creds = _resolve_byoc_credentials(
        user, deployment.get("config", {}).get("aws_region", "ap-south-1")
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
    _enforce_permission(user, ProvisionAction.REMEDIATE, deployment_id)

    check_only = body.check_only if body else True

    collection = _get_deployments_collection()
    deployment = collection.find_one(
        {"deployment_name": deployment_id, "user_id": user.username}
    )
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    if deployment.get("status") != DeploymentStatus.DEPLOYED:
        raise HTTPException(status_code=400, detail="Remediation only available for deployed infrastructure.")

    workspace = deployment.get("terraform_workspace", "")
    aws_creds = _resolve_byoc_credentials(
        user, deployment.get("config", {}).get("aws_region", "ap-south-1")
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


# ── RBAC Management ──


class RoleAssignRequest(BaseModel):
    """Request body for assigning a provision role."""
    username: str
    role: str


@router.post("/roles/assign")
async def assign_role(
    body: RoleAssignRequest,
    user: dict = Depends(get_current_user),
):
    """Assign a provision role to a user. Only admins can do this."""
    _enforce_permission(user, ProvisionAction.MANAGE_ROLES)

    try:
        result = assign_provision_role(
            target_username=body.username,
            role=body.role,
            assigned_by=user.username,
        )
        log_provision_action(
            action="role_assign", actor=user.username,
            deployment_id="system",
            status="success",
            details={"target": body.username, "role": body.role},
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/roles")
async def list_roles(user: dict = Depends(get_current_user)):
    """List all provision role assignments. Only admins can see all."""
    _enforce_permission(user, ProvisionAction.MANAGE_ROLES)
    assignments = list_role_assignments()
    return {"assignments": assignments, "count": len(assignments)}


# ── Audit Log ──


@router.get("/audit-log")
async def get_audit_log(
    deployment_id: Optional[str] = None,
    limit: int = 50,
    user: dict = Depends(get_current_user),
):
    """
    Query the provision audit log.

    Admins/devops can see all events. Developers/viewers see only their own.
    """
    role = get_user_provision_role(user)

    if deployment_id:
        events = get_deployment_audit_log(deployment_id)
    elif role in ("admin", "devops"):
        events = get_recent_audit_log(limit=limit)
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
        {"$set": doc},
        upsert=True,
    )
