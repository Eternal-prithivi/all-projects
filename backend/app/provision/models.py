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
    csp: str = Field(
        default="AWS",
        description="Cloud provider: AWS, GCP, or Azure",
    )
    # Template selection (optional — if set, overrides module flags)
    template: Optional[str] = None

    # AWS region
    aws_region: str = "ap-south-1"

    # GCP
    gcp_region: str = "us-central1"
    gcp_project: str = ""
    enable_gcs: bool = False
    enable_gcp_network: bool = False
    enable_gce: bool = False
    enable_gcp_service_account: bool = False
    enable_gcp_monitoring: bool = False
    enable_firestore: bool = False
    machine_type: str = "e2-micro"
    service_account_id: str = "zenith-app-sa"
    gce_os: str = "debian_12"
    gce_startup_script: str = ""
    gcp_sa_preset: str = "gcs_read_only"
    firestore_database_id: str = "(default)"

    # Azure
    azure_location: str = "eastus"
    resource_group_name: str = "zenith-rg"
    storage_account_name: str = ""
    container_name: str = "zenith-static"
    enable_azure_storage: bool = False
    enable_vnet: bool = False
    enable_azure_vm: bool = False
    enable_azure_monitor: bool = False
    enable_cosmos: bool = False
    vm_size: str = "Standard_B1s"
    azure_os: str = "ubuntu_22_04"
    azure_startup_script: str = ""
    azure_identity_preset: str = "storage_blob_read"
    cosmos_account_name: str = ""
    cosmos_database_name: str = "zenith-db"

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
    ec2_os: str = "amazon_linux_2"
    ec2_user_data: str = ""

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
    iam_role_preset: str = "s3_read_only"

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

    # Intent / wizard metadata
    workload_description: Optional[str] = None
    follow_up_answers: Optional[dict[str, str]] = None
    intent_recommendation: Optional[dict[str, Any]] = None
    deployment_display_name: str = ""
    size_profile: str = "micro"
    disk_size_gb: int = Field(default=30, ge=8, le=2000)

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


class IntentAnalyzeBody(BaseModel):
    workload_description: str = Field(..., min_length=1)
    follow_up_answers: Optional[dict[str, str]] = None
    csp: Optional[str] = Field(default="AWS", description="Cloud for module suggestions (AWS/GCP/Azure)")


class CompareCloudsBody(BaseModel):
    template: str
    size_profile: str = "micro"
    environment: str = "free-tier"
    fit_base: int = Field(default=70, ge=0, le=100)
    reasons: Optional[list[str]] = None


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
    csp: str = "AWS"
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
