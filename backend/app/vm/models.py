# backend/app/vm/models.py
"""
Pydantic models for VM management, assignments, and recommendations.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# --- Enums ---

class ClusterType(str, Enum):
    GENERAL = "general"
    STORAGE = "storage"
    MEMORY = "memory"
    PERFORMANCE = "performance"
    AI_ML = "ai_ml"
    DATABASE = "database"
    NETWORK = "network"
    
    @classmethod
    def _missing_(cls, value):
        """Handle case-insensitive enum values"""
        if isinstance(value, str):
            value = value.lower().replace("-", "_").replace("/", "_").replace(" ", "_")
            for member in cls:
                if member.value == value:
                    return member
        return None


class AssignmentStatus(str, Enum):
    ACTIVE = "active"
    MIGRATING = "migrating"
    EXPIRED = "expired"
    RELEASED = "released"


class VMStatus(str, Enum):
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    TERMINATED = "TERMINATED"
    PROVISIONING = "PROVISIONING"
    STAGING = "STAGING"


class RecommendationStatus(str, Enum):
    PENDING = "pending"
    APPLIED = "applied"
    DISMISSED = "dismissed"


# --- Request Models ---

class VMRequestModel(BaseModel):
    """User request for VM assignment"""
    csp: Optional[str] = Field(
        "GCP",
        description="Cloud provider for VM pool: AWS, GCP, or Azure (Azure planned).",
    )
    workload_description: Optional[str] = Field(
        None,
        description="Description of workload (e.g., 'web app with database'). System will recommend cluster."
    )
    follow_up_answers: Optional[Dict[str, str]] = Field(
        default=None,
        description="Guided answers merged into workload description before NLP analysis",
    )
    cluster_preference: Optional[ClusterType] = Field(
        None,
        description="Explicit cluster choice. Overrides workload analysis."
    )
    priority_level: Optional[int] = Field(
        1,
        ge=1,
        le=5,
        description="User priority (1=normal, 5=premium). Affects assignment order."
    )
    vm_preference: Optional[str] = Field(
        None,
        description="Optional pool slot name (e.g. general-vm-2, storage-aws-vm-1).",
    )
    platform_region_slug: Optional[str] = Field(
        None,
        description="Platform region pill: asia, us, europe, or africa (from platform catalog).",
    )


class VMTransferRequest(BaseModel):
    """User-initiated migration request"""
    csp: Optional[str] = Field(
        None,
        description="Cloud provider; defaults to the active assignment's csp.",
    )
    target_cluster: Optional[ClusterType] = Field(None, description="Target cluster for auto-selection")
    target_vm_name: Optional[str] = Field(None, description="Specific target VM name (e.g., 'general-vm-2')")
    reason: Optional[str] = Field(None, description="Optional reason for transfer")


class AdminMigrateUserRequest(BaseModel):
    """Admin-forced user migration"""
    user_id: str = Field(..., description="User email/ID to migrate")
    target_vm: str = Field(..., description="Target VM name")
    reason: str = Field(..., description="Admin reason for migration")


class ApplyRecommendationRequest(BaseModel):
    """Apply a migration recommendation"""
    recommendation_id: str = Field(..., description="ID of recommendation to apply")


# --- Response Models ---

class VMAssignmentResponse(BaseModel):
    """Response after VM assignment"""
    vm_name: str
    vm_ip: str
    csp: str = "GCP"
    cluster_type: ClusterType
    ssh_command: str
    status: str
    assigned_at: datetime
    expires_at: datetime
    message: str = "VM assigned successfully"


class VMInfoResponse(BaseModel):
    """VM information"""
    name: str
    status: VMStatus
    machine_type: str
    zone: str
    external_ip: Optional[str]
    cluster_type: ClusterType
    active_users: int = 0
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None


class UserAssignmentResponse(BaseModel):
    """Current user's VM assignment"""
    vm_name: Optional[str]
    vm_ip: Optional[str]
    cluster_type: Optional[ClusterType]
    assigned_at: Optional[datetime]
    expires_at: Optional[datetime]
    last_active: Optional[datetime]
    status: AssignmentStatus
    vm_health: Optional[Dict[str, Any]] = None
    message: Optional[str] = None


class MigrationHistoryItem(BaseModel):
    """Single migration record"""
    from_vm: str
    to_vm: str
    migrated_at: datetime
    reason: Optional[str] = None


class VMMetricsResponse(BaseModel):
    """VM performance metrics"""
    vm_name: str
    cluster_type: ClusterType
    cpu_usage: float
    memory_usage: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    active_users: int
    uptime_hours: float
    estimated_cost_usd: float
    status: VMStatus
    recorded_at: datetime


class ClusterMetricsResponse(BaseModel):
    """Cluster-wide metrics"""
    cluster_type: ClusterType
    total_vms: int
    running_vms: int
    total_active_users: int
    average_cpu_usage: float
    average_memory_usage: float
    total_uptime_hours: float
    total_cost_usd: float
    vms: List[VMMetricsResponse]


class MigrationRecommendation(BaseModel):
    """AI-generated migration recommendation"""
    recommendation_id: str
    action: str  # "migrate_user", "consolidate", "rebalance"
    user_id: Optional[str] = None
    source_vm: str
    target_vm: str
    score: int = Field(..., ge=0, le=100, description="Recommendation score (0-100)")
    reasons: List[str]
    expected_improvements: Dict[str, str]
    estimated_downtime_seconds: int = 20
    cost_impact_usd: float = 0.0
    confidence: int = Field(..., ge=0, le=100, description="Confidence % (0-100)")
    generated_at: datetime
    status: RecommendationStatus = RecommendationStatus.PENDING


class RecommendationsListResponse(BaseModel):
    """List of recommendations"""
    recommendations: List[MigrationRecommendation]
    total_count: int
    high_priority_count: int  # Score > 70


class AvailableVMsResponse(BaseModel):
    """VMs available for transfer"""
    available_vms: List[VMInfoResponse]
    current_vm: str
    cluster_type: ClusterType


class MigrationStatusResponse(BaseModel):
    """Migration operation status"""
    success: bool
    message: str
    new_vm_name: Optional[str] = None
    new_vm_ip: Optional[str] = None
    migration_time_seconds: Optional[float] = None


class ClusterCapacityResponse(BaseModel):
    """Cluster capacity info"""
    cluster_type: ClusterType
    max_vms: int
    running_vms: int
    available_capacity: int
    total_users: int
    max_users_per_vm: int
    can_accept_new_users: bool


class VmCostUsageExample(BaseModel):
    id: str
    label: str
    hours: int
    estimated_usd: float


class VmCostLineItem(BaseModel):
    name: str
    monthly_usd: float
    note: Optional[str] = None


class VmCostEstimateResponse(BaseModel):
    """Approximate pre-provision cost overview for a VM slot."""
    csp: str
    vm_name: Optional[str] = None
    cluster_type: str
    tier_label: Optional[str] = None
    machine_type: str
    disk_gb: int
    disk_type: Optional[str] = None
    currency: str = "USD"
    is_approximate: bool = True
    disclaimer: str
    ephemeral_note: str
    compute_monthly_usd: float
    disk_monthly_usd: float
    total_monthly_usd: float
    hourly_usd: float
    line_items: List[VmCostLineItem] = []
    usage_examples: List[VmCostUsageExample] = []


class VmCostRangeResponse(BaseModel):
    """Cost range across all slots in a cluster."""
    csp: str
    cluster_type: str
    currency: str = "USD"
    is_approximate: bool = True
    disclaimer: str
    ephemeral_note: str
    min_monthly_usd: float
    max_monthly_usd: float
    min_hourly_usd: float
    max_hourly_usd: float
    slots: List[VmCostEstimateResponse] = []


# --- Database Models (for MongoDB) ---

class VMAssignmentDB(BaseModel):
    """VM assignment document for MongoDB"""
    user_id: str
    username: str
    vm_name: str
    vm_ip: str
    cluster_type: ClusterType
    assigned_at: datetime
    last_active: datetime
    expires_at: datetime
    status: AssignmentStatus
    priority_level: int = 1
    session_duration_minutes: float = 0.0
    migration_history: List[MigrationHistoryItem] = []
    workload_description: Optional[str] = None


class VMMetricsDB(BaseModel):
    """VM metrics document for MongoDB"""
    vm_name: str
    cluster_type: ClusterType
    cpu_usage: float
    memory_usage: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_in_mb: float
    network_out_mb: float
    active_users: int
    uptime_hours: float
    estimated_cost_usd: float
    last_started: Optional[datetime]
    last_stopped: Optional[datetime]
    recorded_at: datetime


class MigrationRecommendationDB(BaseModel):
    """Migration recommendation document for MongoDB"""
    recommendation_id: str
    cluster_type: ClusterType
    action: str
    user_id: Optional[str]
    source_vm: str
    target_vm: str
    score: int
    reasons: List[str]
    expected_improvements: Dict[str, str]
    estimated_downtime_seconds: int
    cost_impact_usd: float
    confidence: int
    generated_at: datetime
    status: RecommendationStatus
    applied_at: Optional[datetime] = None
    applied_by: Optional[str] = None
