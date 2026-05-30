# =============================================================================
# MODULE: provision/models.py
# PURPOSE: Pydantic models for infrastructure provisioning requests and records
# USED BY: routes_provision.py, terraform_runner.py, policy_checker.py
# DO NOT:
#   - Add fields without updating the tfvars generation in terraform_runner.py
#   - Remove free-tier defaults — they protect users from accidental charges
# =============================================================================
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from app.provision.config_normalize import sanitize_s3_bucket_name


class ProvisionTemplate(str, Enum):
    """Pre-built deployment templates."""
    STATIC_SITE = "static-site"
    BACKEND_APP = "backend-app"
    SERVERLESS_DB = "serverless-db"
    CUSTOM = "custom"


class DeploymentStatus(str, Enum):
    """Lifecycle status of a provisioned deployment."""
    PLANNING = "planning"
    PLAN_FAILED = "plan_failed"
    AWAITING_APPLY = "awaiting_apply"
    APPLYING = "applying"
    DEPLOYED = "deployed"
    APPLY_FAILED = "apply_failed"
    DESTROYING = "destroying"
    DESTROYED = "destroyed"
    DESTROY_FAILED = "destroy_failed"


class DriftStatus(str, Enum):
    """Result of a drift detection check."""
    UNKNOWN = "unknown"
    CLEAN = "clean"
    DRIFT_DETECTED = "drift_detected"
    CHECK_FAILED = "check_failed"


# ── Request Models ──


class ProvisionConfig(BaseModel):
    """Infrastructure configuration submitted from the provisioning wizard."""
    # Template selection (optional — if set, overrides module flags)
    template: Optional[ProvisionTemplate] = None

    # AWS region
    aws_region: str = "ap-south-1"

    # Feature flags — which modules to deploy
    enable_vpc: bool = False
    enable_ec2: bool = False
    enable_s3: bool = False
    enable_iam: bool = False
    enable_cloudwatch: bool = False
    enable_dynamodb: bool = False
    # Billing requires budgets:* IAM permission — off by default to avoid plan hangs
    enable_billing: bool = False

    # VPC config
    vpc_cidr: str = "10.0.0.0/16"

    # EC2 config
    instance_type: str = "t2.micro"
    instance_name: str = "main-instance"
    ami_id: str = ""

    # S3 config
    bucket_name: str = ""

    @field_validator("bucket_name", mode="before")
    @classmethod
    def _sanitize_bucket_name(cls, value: object) -> str:
        if value is None:
            return ""
        return sanitize_s3_bucket_name(str(value))

    # IAM config
    role_name: str = "app-role"

    # CloudWatch config
    alarm_email: str = ""

    # Billing / Budget
    budget_limit: str = "1"
    budget_email: str = ""

    # DynamoDB config
    dynamodb_table_name: str = ""
    dynamodb_hash_key: str = "id"
    dynamodb_hash_key_type: str = "S"
    dynamodb_read_capacity: int = 5
    dynamodb_write_capacity: int = 5
    dynamodb_enable_pitr: bool = False

    # Tags
    tags: dict[str, str] = Field(default_factory=dict)
    environment: str = "free-tier"


# ── Response Models ──


class PolicyViolation(BaseModel):
    """A single policy rule violation."""
    rule_name: str
    description: str
    severity: str  # "block" or "warning"


class PolicyCheckResult(BaseModel):
    """Result of evaluating config against policy engines."""
    blocks: list[PolicyViolation] = Field(default_factory=list)
    warnings: list[PolicyViolation] = Field(default_factory=list)
    can_deploy: bool = True


class CostEstimate(BaseModel):
    """Pre-deployment cost estimation."""
    available: bool = True
    total_monthly_cost: str = "0.00"
    currency: str = "USD"
    resources: list[dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None


class DriftReport(BaseModel):
    """Result of a drift detection check."""
    status: DriftStatus = DriftStatus.UNKNOWN
    changes_detected: int = 0
    details: list[str] = Field(default_factory=list)
    checked_at: Optional[datetime] = None


class DeploymentRecord(BaseModel):
    """MongoDB document schema for a provisioned deployment."""
    user_id: str
    deployment_name: str
    template: Optional[str] = None
    config: dict[str, Any] = Field(default_factory=dict)
    enabled_modules: list[str] = Field(default_factory=list)
    status: DeploymentStatus = DeploymentStatus.PLANNING
    terraform_workspace: str = ""
    plan_output: str = ""
    apply_output: str = ""
    cost_estimate: Optional[CostEstimate] = None
    policy_check: Optional[PolicyCheckResult] = None
    drift_history: list[DriftReport] = Field(default_factory=list)
    latest_drift: DriftStatus = DriftStatus.UNKNOWN
    resources_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    destroyed_at: Optional[datetime] = None
