# =============================================================================
# MODULE: routes_vm.py  (984 lines)
# PURPOSE: VM lifecycle — request/release VMs, NLP workload classification,
#          five-cluster assignment, metrics, migration, transfer
# READS FROM:  vm_assignments, vm_metrics, users collections
# WRITES TO:   vm_assignments, vm_metrics, ml_workload_descriptions collections
# DEPENDS ON:  auth_utils.get_current_user(), nlp_workload.py, manager.py
# MOUNTED AT:  /api/vm → request, release, clusters, assignment, analyze-workload,
#              migrate, transfer, my-assignment
# DO NOT:
#   - Change the five cluster types: General/Storage/Memory/Performance/AI-ML
#   - Bypass the NLP classifier for cluster assignment
#   - Delete vm_assignments without updating vm_metrics records
# =============================================================================

from fastapi import APIRouter, HTTPException, Depends, Body
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from google.cloud import compute_v1
from app.vm.manager import (
    list_vms, create_vm, start_vm, stop_vm, delete_vm, get_vm_details,
    assign_vm_to_user, migrate_user, release_vm_assignment, 
    get_user_assignment, get_cluster_health, _get_instance_client, CLUSTER_VMS
)
from app.vm.models import (
    VMRequestModel, VMAssignmentResponse, VMTransferRequest,
    VMMetricsResponse, ClusterType, MigrationRecommendation, VMStatus
)
from app.vm.migration_recommender import MigrationRecommender
from app.vm.workload_analyzer import WorkloadAnalyzer
from app.vm.metrics_collector import VMMetricsCollector
from app.utils.config import settings
from app.database.mongo_client import get_database
from app.users.routes_users import get_current_user  # Import real auth
from app.users.user_model import User
from app.utils.logger import setup_logger
from datetime import datetime
import asyncio # For asynchronous operations
import time # For cache timing

logger = setup_logger(__name__)
router = APIRouter()
DB = get_database()

# Cache for metrics to reduce GCP API calls
metrics_cache = {}
METRICS_CACHE_TTL = 120  # Cache for 2 minutes (120 seconds) - reduced for better UX

# Cache for cluster health (reduced for real-time updates after VM operations)
cluster_health_cache = {}
CLUSTER_HEALTH_CACHE_TTL = 60  # 1 minute - will auto-invalidate on VM changes anyway

# Cache for recommendations (reduced for fresher data)
recommendations_cache = {}
RECOMMENDATIONS_CACHE_TTL = 180  # 3 minutes

# Helper function to check if caching is enabled
def is_caching_enabled():
    """Check if caching is enabled (disabled in REAL_TIME_MODE)"""
    return not settings.REAL_TIME_MODE

# Helper function to invalidate all caches
def invalidate_all_caches():
    """Clear all caches to force fresh data fetch on next request"""
    global cluster_health_cache, metrics_cache, recommendations_cache
    cluster_health_cache.clear()
    metrics_cache.clear()
    recommendations_cache.clear()
    mode = "REAL-TIME" if settings.REAL_TIME_MODE else "CACHED"
    logger.info(f"All VM caches invalidated (cluster health, metrics, recommendations) - Mode: {mode}")

# Helper function to invalidate cluster health cache (backward compatibility)
def invalidate_cluster_health_cache():
    """Clear cluster health cache to force fresh data fetch on next request"""
    global cluster_health_cache
    cluster_health_cache.clear()
    logger.info("Cluster health cache invalidated")

# --- Pydantic Models for Request/Response ---

class VMCreateRequest(BaseModel):
    cluster_type: str = Field(
        ...,
        description="Cluster to provision from: general, storage, memory, performance, or ai_ml",
    )
    # vm_name: Optional[str] = Field(None, description="Optional: A specific name for the VM. If not provided, one will be generated.")
    # machine_type: Optional[str] = Field(None, description="Optional: Machine type for the VM (e.g., 'e2-micro'). Overrides cluster default if provided.")
    # disk_size_gb: Optional[int] = Field(None, description="Optional: Disk size in GB. Overrides cluster default if provided.")

class VMResponse(BaseModel):
    name: str
    status: str
    machine_type: str
    zone: str
    external_ip: str
    creation_timestamp: Optional[str] = None
    labels: Optional[Dict[str, str]] = None

class VMListResponse(BaseModel):
    vms: List[VMResponse]

class OperationStatusResponse(BaseModel):
    name: str
    status: str
    details: Optional[Dict[str, Any]] = None

# --- Helper to get cluster counts and determine next action ---
async def _get_cluster_vm_counts():
    all_vms = list_vms()
    counts = {}
    active_statuses = {"RUNNING", "PROVISIONING", "STAGING"}

    for cluster_type in CLUSTER_VMS:
        cluster_name = cluster_type.value
        cluster_vms = [
            vm for vm in all_vms
            if vm.get("labels", {}).get("cluster_type") == cluster_name
            or vm.get("name") in CLUSTER_VMS[cluster_type]
        ]
        running_vms = [vm for vm in cluster_vms if vm.get("status") in active_statuses]
        counts[cluster_name] = {
            "current_count": len(running_vms),
            "max_vms": _cluster_max_vms(cluster_type),
            "available_vms": [vm for vm in cluster_vms if vm.get("status") in {"TERMINATED", "STOPPED"}],
        }

    return counts


def _cluster_max_vms(cluster_type: ClusterType) -> int:
    if cluster_type == ClusterType.STORAGE:
        return settings.STORAGE_CLUSTER_MAX_VMS
    return settings.PERFORMANCE_CLUSTER_MAX_VMS


def _cluster_machine_type(cluster_type: ClusterType) -> str:
    if cluster_type == ClusterType.STORAGE:
        return settings.STORAGE_VM_MACHINE_TYPE
    return settings.PERFORMANCE_VM_MACHINE_TYPE


def _cluster_disk_size_gb(cluster_type: ClusterType) -> int:
    if cluster_type == ClusterType.STORAGE:
        return settings.STORAGE_VM_DISK_SIZE_GB
    if cluster_type == ClusterType.MEMORY:
        return max(20, settings.STORAGE_VM_DISK_SIZE_GB)
    return 10


# --- API Endpoints ---

@router.get("/status", summary="Get VM Cluster Status")
async def get_vm_cluster_status() -> Dict[str, Any]:
    """
    Returns the current status of VM clusters including counts and available slots.
    """
    cluster_counts = await _get_cluster_vm_counts()
    clusters = {
        cluster_name: {
            "running_vms": data["current_count"],
            "max_vms": data["max_vms"],
            "available_for_start": len(data["available_vms"]),
            "can_provision_new": data["current_count"] < data["max_vms"],
        }
        for cluster_name, data in cluster_counts.items()
    }
    return {
        "message": "VM Cluster Status",
        "clusters": clusters,
        "performance_cluster": clusters.get("performance", {}),
        "storage_cluster": clusters.get("storage", {}),
        "all_vms_in_zone": list_vms()
    }

@router.post("/provision", response_model=OperationStatusResponse, summary="Provision or Assign VM")
async def provision_or_assign_vm(request: VMCreateRequest) -> OperationStatusResponse:
    """
    Provisions a new VM from a cluster or assigns/starts an existing one.
    """
    cluster_name = request.cluster_type.lower().replace("-", "_")
    try:
        cluster_type = ClusterType(cluster_name)
    except ValueError:
        allowed = ", ".join(cluster.value for cluster in CLUSTER_VMS)
        raise HTTPException(status_code=400, detail=f"Invalid cluster_type. Must be one of: {allowed}.")

    cluster_status = (await _get_cluster_vm_counts())[cluster_type.value]

    # 1. Check for terminated VMs in the cluster that can be started
    if cluster_status['available_for_start'] > 0:
        vm_to_start = cluster_status['available_vms'][0] # Pick the first available
        logger.info(f"Starting existing VM: {vm_to_start['name']} for {cluster_type.value} cluster")
        result = start_vm(vm_to_start['name'])
        return OperationStatusResponse(name=vm_to_start['name'], status="STARTING_EXISTING", details=result['details'])

    # 2. If no terminated VMs, try to provision a new one if limits allow
    if cluster_status['current_count'] < cluster_status['max_vms']:
        machine_type = _cluster_machine_type(cluster_type)
        disk_size = _cluster_disk_size_gb(cluster_type)

        new_vm_name = f"{cluster_type.value}-vm-{cluster_status['current_count'] + 1}"
        labels = {"cluster_type": cluster_type.value}

        logger.info(f"Provisioning new VM: {new_vm_name} for {cluster_type.value} cluster")
        result = create_vm(
            name=new_vm_name,
            machine_type=machine_type,
            source_image="debian-cloud/debian-11", # Using a common free-tier eligible image
            disk_size_gb=disk_size,
            labels=labels
        )
        return OperationStatusResponse(name=new_vm_name, status="PROVISIONING_NEW", details=result['details'])
    else:
        raise HTTPException(
            status_code=409,
            detail=f"No available VMs and cluster '{cluster_type.value}' has reached its maximum capacity of {cluster_status['max_vms']} running instances."
        )

@router.get("/list", response_model=VMListResponse, summary="List all VMs")
async def get_all_vms() -> VMListResponse:
    """
    Lists all VM instances managed by this application.
    """
    vms = list_vms()
    return VMListResponse(vms=[VMResponse(**vm) for vm in vms])

@router.post("/{vm_name}/start", response_model=OperationStatusResponse, summary="Start a VM")
async def start_single_vm(vm_name: str) -> OperationStatusResponse:
    """
    Starts a specific VM instance.
    """
    try:
        result = start_vm(vm_name)
        return OperationStatusResponse(name=vm_name, status="STARTING", details=result['details'])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start VM: {e}")

@router.post("/{vm_name}/stop", response_model=OperationStatusResponse, summary="Stop a VM")
async def stop_single_vm(vm_name: str) -> OperationStatusResponse:
    """
    Stops a specific VM instance.
    """
    try:
        result = stop_vm(vm_name)
        return OperationStatusResponse(name=vm_name, status="STOPPING", details=result['details'])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop VM: {e}")

@router.delete("/{vm_name}", response_model=OperationStatusResponse, summary="Delete a VM")
async def delete_single_vm(vm_name: str) -> OperationStatusResponse:
    """
    Deletes a specific VM instance.
    """
    try:
        result = delete_vm(vm_name)
        return OperationStatusResponse(name=vm_name, status="DELETING", details=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete VM: {e}")

@router.get("/{vm_name}/details", response_model=VMResponse, summary="Get VM Details")
async def get_single_vm_details(vm_name: str) -> VMResponse:
    """
    Retrieves details for a specific VM instance.
    """
    try:
        details = get_vm_details(vm_name, settings.GCP_ZONE)
        return VMResponse(**details)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"VM '{vm_name}' not found or error fetching details: {e}")


# --- New Advanced VM Management Endpoints ---


class WorkloadAnalyzeBody(BaseModel):
    workload_description: str = Field(..., min_length=1, description="Natural language workload description")
    follow_up_answers: Optional[Dict[str, str]] = Field(
        default=None,
        description="Optional guided answers merged into the description before NLP",
    )


@router.post("/analyze-workload", summary="Analyze workload description (NLP)")
async def analyze_workload_description(
    body: WorkloadAnalyzeBody,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Preview NLP workload classification without provisioning a VM.
    Uses report §4.1 pipeline (TextBlob + spaCy + tech dictionaries).
    Includes readiness score, missing signals, and follow-up question prompts.
    """
    from app.vm.workload_guidance import (
        assess_workload_readiness,
        build_follow_up_questions,
        merge_follow_up_answers,
    )

    effective_description = merge_follow_up_answers(
        body.workload_description,
        body.follow_up_answers,
    )
    cluster, confidence, details = WorkloadAnalyzer.analyze(effective_description)
    readiness = assess_workload_readiness(effective_description)
    follow_up_questions = build_follow_up_questions(
        readiness.get("missing_signals", []),
        body.follow_up_answers,
    )
    return {
        "recommended_cluster": cluster.value,
        "confidence": confidence,
        "classifier_version": details.get("classifier_version", "unknown"),
        "report_cluster": details.get("report_cluster"),
        "auto_assign_eligible": details.get("auto_assign_eligible", confidence >= 85),
        "readiness": readiness,
        "follow_up_questions": follow_up_questions,
        "effective_description": effective_description,
        "analysis": details,
    }


@router.post("/request", response_model=VMAssignmentResponse, summary="Request VM Assignment")
async def request_vm_assignment(
    request: VMRequestModel,
    current_user: User = Depends(get_current_user)
) -> VMAssignmentResponse:
    """
    Intelligent VM assignment based on workload analysis.
    Automatically selects optimal VM using least-connections load balancing.
    """
    try:
        from app.vm.workload_guidance import merge_follow_up_answers

        effective_workload = merge_follow_up_answers(
            request.workload_description or "",
            request.follow_up_answers,
        )
        vm_name, vm_ip, ssh_command, cluster_type, assigned_at, expires_at = assign_vm_to_user(
            user_id=current_user.username,
            workload_description=effective_workload,
            cluster_preference=request.cluster_preference,
            priority_level=request.priority_level
        )
        
        # Invalidate ALL caches to immediately reflect changes
        invalidate_all_caches()
        
        return VMAssignmentResponse(
            vm_name=vm_name,
            vm_ip=vm_ip,
            ssh_command=ssh_command,
            cluster_type=cluster_type,
            status="active",
            assigned_at=assigned_at,
            expires_at=expires_at,
            message="VM assigned successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"VM assignment failed: {str(e)}")


@router.post("/migrate", response_model=dict)
async def migrate_vm(
    request: VMTransferRequest,
    current_user: User = Depends(get_current_user)
):
    """
    User-initiated or admin-forced migration to another VM.
    Supports both cluster-based auto-selection and manual VM selection.
    """
    try:
        result = migrate_user(
            user_id=current_user.username,
            target_cluster=request.target_cluster,
            target_vm_name=request.target_vm_name
        )
        
        # Invalidate ALL caches to immediately reflect changes
        invalidate_all_caches()
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")


# Backwards-compatible alias for older frontends that call `/transfer`
@router.post("/transfer", response_model=dict, summary="Transfer VM (alias)")
async def transfer_vm_alias(
    request: VMTransferRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Compatibility wrapper for `/transfer` used by some frontend pages.
    Delegates to the canonical migrate_vm endpoint.
    """
    return await migrate_vm(request, current_user)


@router.get("/my-assignment", summary="Get My VM Assignment")
async def get_my_vm_assignment(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Retrieve current active VM assignment for the authenticated user.
    """
    assignment = get_user_assignment(current_user.username)
    
    if not assignment:
        raise HTTPException(status_code=404, detail="No active VM assignment found")
    
    return assignment


@router.get("/my-assignments", summary="Get All My VM Assignments")
async def get_all_my_vm_assignments(
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Retrieve all active VM assignments for the authenticated user.
    """
    from app.vm.manager import get_all_user_assignments
    assignments = get_all_user_assignments(current_user.username)
    return assignments


@router.post("/release/{assignment_id}", response_model=dict)
async def release_vm(
    assignment_id: str,
    current_user: User = Depends(get_current_user)
):
    if assignment_id:
        result = release_vm_assignment(current_user.username, assignment_id)
    else:
        result = release_vm_assignment(current_user.username)
    
    if not result["success"]:
        raise HTTPException(status_code=404, detail=result["message"])
    
    # Invalidate ALL caches to immediately reflect changes in dashboard
    invalidate_all_caches()
    
    return result


@router.get("/metrics/{vm_name}", response_model=VMMetricsResponse, summary="Get VM Metrics")
async def get_vm_metrics(vm_name: str, use_real: bool = False) -> VMMetricsResponse:
    """
    Fetch real-time performance metrics for a specific VM from GCP Monitoring API.
    Uses cache for expensive GCP metrics (CPU, memory, disk, network) unless REAL_TIME_MODE=true.
    Always fetches fresh user count from MongoDB (free, no cache).
    
    Query parameter:
    - use_real: If true, uses real GCP metrics. If false (default), uses simulated metrics.
    """
    try:
        # Always get fresh user count from MongoDB (no cost, always up-to-date)
        active_users = DB["vm_assignments"].count_documents({
            "vm_name": vm_name,
            "status": "active"
        })
        
        # Check cache for expensive GCP metrics - include use_real in cache key
        # Skip cache if REAL_TIME_MODE is enabled
        cache_key = f"metrics_{vm_name}_{'real' if use_real else 'sim'}"
        now = datetime.utcnow()
        
        if is_caching_enabled() and cache_key in metrics_cache:
            cached_data, cached_time = metrics_cache[cache_key]
            if (now - cached_time).total_seconds() < METRICS_CACHE_TTL:
                # Update with fresh user count
                cached_data["active_users"] = active_users
                return VMMetricsResponse(**cached_data)
        
        # Cache miss or expired or REAL_TIME_MODE - collect fresh metrics
        mode_msg = "REAL-TIME" if settings.REAL_TIME_MODE else "cached"
        logger.debug(f"Collecting metrics for {vm_name} (Mode: {mode_msg})")
        
        # Determine cluster type
        cluster_type = ClusterType.GENERAL if "general" in vm_name else ClusterType.STORAGE
        
        # Get VM details to check if running
        vm_details = get_vm_details(vm_name, settings.GCP_ZONE)
        last_started = None
        if vm_details.get("status") == "RUNNING":
            last_started = now
        
        # Collect metrics
        collector = VMMetricsCollector()
        metrics_db = await collector.collect_all_metrics(
            vm_name=vm_name,
            cluster_type=cluster_type,
            active_users=active_users,
            last_started=last_started
        )
        
        # Convert VMMetricsDB object to dict for caching and response
        # VMMetricsDB returns disk_io_read_mb and disk_io_write_mb separately
        # Calculate total disk usage for the response
        total_disk_gb = (metrics_db.disk_io_read_mb + metrics_db.disk_io_write_mb) / 1024.0
        
        response_data = {
            "vm_name": metrics_db.vm_name,
            "cluster_type": metrics_db.cluster_type,
            "cpu_usage": metrics_db.cpu_usage,
            "memory_usage": metrics_db.memory_usage,
            "disk_usage_gb": total_disk_gb,
            "disk_io_read_mb": metrics_db.disk_io_read_mb,
            "disk_io_write_mb": metrics_db.disk_io_write_mb,
            "network_in_mb": metrics_db.network_in_mb,
            "network_out_mb": metrics_db.network_out_mb,
            "active_users": metrics_db.active_users,
            "uptime_hours": metrics_db.uptime_hours,
            "estimated_cost_usd": metrics_db.estimated_cost_usd,
            "status": vm_details.get("status", "TERMINATED"),
            "recorded_at": metrics_db.recorded_at,
            "recommendation_score": 50,  # Default score, can be enhanced with ML
            "recommendation_reason": ""  # Can be populated based on metrics thresholds
        }
        
        # Store in cache only if caching is enabled
        if is_caching_enabled():
            metrics_cache[cache_key] = (response_data, now)
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to collect metrics: {str(e)}")


@router.get("/config/{vm_name}", summary="Get Detailed VM Configuration")
async def get_vm_configuration(vm_name: str) -> Dict[str, Any]:
    """
    Get comprehensive VM configuration details including:
    - Machine type (CPU cores, memory)
    - Disk configuration (size, type)
    - Network configuration
    - Current metrics
    """
    try:
        # Get VM instance details from GCP
        request = compute_v1.GetInstanceRequest(
            project=settings.GCP_PROJECT_ID,
            zone=settings.GCP_ZONE,
            instance=vm_name,
        )
        instance = _get_instance_client().get(request=request)
        
        # Parse machine type to get CPU and memory info
        machine_type = instance.machine_type.split('/')[-1]
        
        # Common GCP machine types specs
        machine_specs = {
            'e2-micro': {'cpus': 2, 'memory_gb': 1},
            'e2-small': {'cpus': 2, 'memory_gb': 2},
            'e2-medium': {'cpus': 2, 'memory_gb': 4},
            'e2-standard-2': {'cpus': 2, 'memory_gb': 8},
            'e2-standard-4': {'cpus': 4, 'memory_gb': 16},
            'n1-standard-1': {'cpus': 1, 'memory_gb': 3.75},
            'n1-standard-2': {'cpus': 2, 'memory_gb': 7.5},
        }
        
        specs = machine_specs.get(machine_type, {'cpus': 2, 'memory_gb': 1})
        
        # Get disk information
        disks = []
        for disk in instance.disks:
            disk_info = {
                'name': disk.device_name,
                'size_gb': disk.disk_size_gb if hasattr(disk, 'disk_size_gb') else 10,
                'type': disk.type_ if hasattr(disk, 'type_') else 'PERSISTENT',
                'boot': disk.boot if hasattr(disk, 'boot') else False
            }
            disks.append(disk_info)
        
        # Get network information
        networks = []
        for interface in instance.network_interfaces:
            network_info = {
                'network': interface.network.split('/')[-1] if interface.network else 'default',
                'internal_ip': interface.network_i_p if hasattr(interface, 'network_i_p') else 'N/A',
            }
            
            # Get external IP if available
            if interface.access_configs:
                access_config = interface.access_configs[0]
                external_ip = getattr(access_config, 'natIP', getattr(access_config, 'nat_i_p', 'N/A'))
                network_info['external_ip'] = external_ip
            else:
                network_info['external_ip'] = None
            
            networks.append(network_info)
        
        # Get current metrics
        active_users = DB["vm_assignments"].count_documents({
            "vm_name": vm_name,
            "status": "active"
        })
        
        latest_metrics = DB["vm_metrics"].find_one(
            {"vm_name": vm_name},
            sort=[("collected_at", -1)]
        )
        
        # Get cluster type
        cluster_type = "GENERAL" if "general" in vm_name else "STORAGE"
        
        return {
            'vm_name': vm_name,
            'status': instance.status,
            'cluster_type': cluster_type,
            'machine_type': machine_type,
            'cpu_cores': specs['cpus'],
            'memory_gb': specs['memory_gb'],
            'disks': disks,
            'total_disk_gb': sum(d['size_gb'] for d in disks),
            'networks': networks,
            'zone': settings.GCP_ZONE,
            'created': instance.creation_timestamp,
            'active_users': active_users,
            'current_metrics': {
                'cpu_usage': latest_metrics.get('cpu_usage', 0) if latest_metrics else 0,
                'memory_usage': latest_metrics.get('memory_usage', 0) if latest_metrics else 0,
                'disk_usage_gb': latest_metrics.get('disk_usage_gb', 0) if latest_metrics else 0,
                'network_in_mb': latest_metrics.get('network_in_mb', 0) if latest_metrics else 0,
                'network_out_mb': latest_metrics.get('network_out_mb', 0) if latest_metrics else 0,
            } if latest_metrics else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get VM configuration: {str(e)}")


@router.get("/admin/recommendations", response_model=List[MigrationRecommendation], summary="Get AI Migration Recommendations")
async def get_migration_recommendations(
    cluster_type: Optional[ClusterType] = None,
    min_score: int = 50
) -> List[MigrationRecommendation]:
    """
    Admin endpoint: Get AI-powered migration recommendations for load balancing and cost optimization.
    Cached for 3 minutes to reduce expensive metrics collection (unless REAL_TIME_MODE=true).
    """
    try:
        cache_key = f"recommendations_{cluster_type}_{min_score}"
        
        # Check cache only if caching is enabled
        if is_caching_enabled() and cache_key in recommendations_cache:
            cached_data, cached_time = recommendations_cache[cache_key]
            if time.time() - cached_time < RECOMMENDATIONS_CACHE_TTL:
                return cached_data
        
        # Skip recommendations entirely if GCP credentials are not configured
        if not settings.GCP_SERVICE_ACCOUNT_JSON_PATH:
            logger.info("GCP credentials not configured — returning empty recommendations")
            return []
        
        # Fetch current metrics for all VMs
        collector = VMMetricsCollector()
        
        # Determine which clusters to analyze
        clusters_to_analyze = [cluster_type] if cluster_type else [ClusterType.GENERAL, ClusterType.STORAGE]
        
        all_recommendations = []
        for cluster in clusters_to_analyze:
            # Get VM metrics for cluster
            cluster_vms = ["general-vm-1", "general-vm-2"] if cluster == ClusterType.GENERAL else ["storage-vm-1", "storage-vm-2"]
            vm_metrics = []
            
            for vm_name in cluster_vms:
                try:
                    # Get active user count
                    active_users = DB["vm_assignments"].count_documents({
                        "vm_name": vm_name,
                        "status": "active"
                    })
                    
                    # Get VM details (requires GCP)
                    vm_details = get_vm_details(vm_name, settings.GCP_ZONE)
                    last_started = None
                    if vm_details.get("status") == "RUNNING":
                        last_started = datetime.utcnow()  # Simplified for recommendations
                    
                    metrics = await collector.collect_all_metrics(
                        vm_name=vm_name,
                        cluster_type=cluster,
                        active_users=active_users,
                        last_started=last_started
                    )
                    vm_metrics.append(metrics)
                except Exception as e:
                    logger.warning(f"Skipping {vm_name} for recommendations (GCP unavailable): {type(e).__name__}")
                    continue
            
            if len(vm_metrics) < 2:
                # Need at least 2 VMs with metrics for migration recommendations
                continue
            
            # Get user assignments
            user_assignments = list(DB["vm_assignments"].find({"status": "active"}))
            
            # Generate recommendations
            recommendations = MigrationRecommender.generate_recommendations(
                cluster_type=cluster,
                vm_metrics=vm_metrics,
                user_assignments=user_assignments
            )
            
            all_recommendations.extend(recommendations)
        
        # Filter and return top recommendations
        filtered = MigrationRecommender.filter_recommendations(
            all_recommendations,
            min_score=min_score,
            max_count=10
        )
        
        # Cache the results only if caching is enabled
        if is_caching_enabled():
            recommendations_cache[cache_key] = (filtered, time.time())
        
        return filtered
    except Exception as e:
        logger.error(f"Recommendations generation failed: {e}")
        return []  # Return empty list instead of 500


@router.post("/admin/apply-recommendation/{recommendation_id}", summary="Apply Migration Recommendation")
async def apply_recommendation(recommendation_id: str) -> Dict[str, Any]:
    """
    Admin endpoint: Execute a specific migration recommendation.
    """
    # Find recommendation in recent recommendations (stored in MongoDB or cache)
    # For simplicity, this is a placeholder - in production, store recommendations in DB
    
    return {
        "success": True,
        "message": f"Recommendation {recommendation_id} applied",
        "note": "Implementation pending: Store recommendations in DB for tracking"
    }


@router.get("/admin/cluster-metrics/{cluster_type}", summary="Get Cluster Health Dashboard")
async def get_cluster_metrics(cluster_type: ClusterType) -> Dict[str, Any]:
    """
    Admin endpoint: Get aggregated health metrics for entire cluster.
    Used by frontend dashboard for real-time monitoring.
    Cached for 1 minute to reduce GCP API calls (unless REAL_TIME_MODE=true).
    """
    try:
        cache_key = f"cluster_health_{cluster_type.value}"
        
        # Check cache only if caching is enabled
        if is_caching_enabled() and cache_key in cluster_health_cache:
            cached_data, cached_time = cluster_health_cache[cache_key]
            if time.time() - cached_time < CLUSTER_HEALTH_CACHE_TTL:
                return cached_data
        
        # Fetch fresh data
        health_data = get_cluster_health(cluster_type)
        
        # Update cache only if caching is enabled
        if is_caching_enabled():
            cluster_health_cache[cache_key] = (health_data, time.time())
        
        return health_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cluster health: {str(e)}")



@router.get("/admin/predict-load", summary="Predict Cluster Load (1 Hour)")
async def predict_cluster_load(cluster_type: ClusterType) -> Dict[str, Any]:
    """
    Admin endpoint: Predict cluster state in 1 hour using historical trends.
    """
    try:
        collector = VMMetricsCollector()
        
        # Get current metrics
        cluster_vms = ["general-vm-1", "general-vm-2"] if cluster_type == ClusterType.GENERAL else ["storage-vm-1", "storage-vm-2"]
        current_metrics = []
        
        for vm_name in cluster_vms:
            try:
                # Get active user count
                active_users = DB["vm_assignments"].count_documents({
                    "vm_name": vm_name,
                    "status": "active"
                })
                
                # Determine cluster type from VM name
                vm_cluster = ClusterType.GENERAL if "general" in vm_name else ClusterType.STORAGE
                
                # Get VM details
                vm_details = get_vm_details(vm_name, settings.GCP_ZONE)
                last_started = None
                if vm_details.get("status") == "RUNNING":
                    last_started = datetime.utcnow()
                
                metrics = await collector.collect_all_metrics(
                    vm_name=vm_name,
                    cluster_type=vm_cluster,
                    active_users=active_users,
                    last_started=last_started
                )
                current_metrics.append(metrics)
            except Exception as e:
                logger.error(f"Error collecting metrics for {vm_name}: {e}")
                continue
        
        # Predict (simple trend analysis for now)
        prediction = MigrationRecommender.predict_cluster_health_1_hour(
            current_metrics=current_metrics,
            historical_trend="stable"  # TODO: Calculate from MongoDB historical data
        )
        
        return prediction
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.get("/ssh-key/{assignment_id}", summary="Download SSH Private Key")
async def download_ssh_key(
    assignment_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Download the SSH private key for a specific VM assignment.
    Returns the key as a downloadable .pem file.
    """
    from fastapi.responses import Response
    from app.vm.ssh_manager import decrypt_private_key, generate_ssh_keypair, encrypt_private_key, format_ssh_metadata
    from app.utils.config import settings as app_settings
    
    try:
        assignment = DB["vm_assignments"].find_one({
            "assignment_id": assignment_id,
            "user_id": current_user.username,
            "status": "active"
        })
        
        if not assignment:
            raise HTTPException(
                status_code=404,
                detail="Assignment not found or you don't have permission to access it"
            )
        
        # Check if SSH key exists, if not generate one (for backward compatibility)
        encrypted_key = assignment.get("ssh_private_key_encrypted")
        
        if not encrypted_key:
            logger.warning(f"No SSH key found for assignment {assignment_id}, generating new one")
            
            # Generate new keypair
            private_key, public_key = generate_ssh_keypair()
            encrypted_private_key = encrypt_private_key(private_key, app_settings.SECRET_KEY)
            
            # Update assignment with new keys
            DB["vm_assignments"].update_one(
                {"assignment_id": assignment_id, "user_id": current_user.username},
                {"$set": {
                    "ssh_username": "vmuser",
                    "ssh_public_key": public_key,
                    "ssh_private_key_encrypted": encrypted_private_key
                }}
            )
            
            # Inject key into VM metadata
            try:
                vm_name = assignment["vm_name"]
                ssh_keys_value = format_ssh_metadata("vmuser", public_key)
                
                # Get current VM metadata
                metadata_request = compute_v1.GetInstanceRequest(
                    project=settings.GCP_PROJECT_ID,
                    zone=settings.GCP_ZONE,
                    instance=vm_name
                )
                instance = _get_instance_client().get(request=metadata_request)
                
                # Add or update SSH keys
                metadata_items = list(instance.metadata.items) if instance.metadata and instance.metadata.items else []
                
                ssh_keys_found = False
                for i, item in enumerate(metadata_items):
                    if item.key == "ssh-keys":
                        metadata_items[i].value = f"{item.value}\n{ssh_keys_value}"
                        ssh_keys_found = True
                        break
                
                if not ssh_keys_found:
                    metadata_items.append(compute_v1.Items(key="ssh-keys", value=ssh_keys_value))
                
                # Update VM metadata
                update_request = compute_v1.SetMetadataInstanceRequest(
                    project=settings.GCP_PROJECT_ID,
                    zone=settings.GCP_ZONE,
                    instance=vm_name,
                    metadata_resource=compute_v1.Metadata(
                        items=metadata_items,
                        fingerprint=instance.metadata.fingerprint if instance.metadata else None
                    )
                )
                operation = _get_instance_client().set_metadata(request=update_request)
                operation.result()
                logger.info(f"SSH key injected into {vm_name}")
            except Exception as e:
                logger.warning(f"Could not inject SSH key: {e}")
            
            encrypted_key = encrypted_private_key
        
        # Decrypt the private key
        private_key = decrypt_private_key(encrypted_key, app_settings.SECRET_KEY)
        
        # Return as downloadable file
        return Response(
            content=private_key,
            media_type="application/x-pem-file",
            headers={
                "Content-Disposition": f"attachment; filename=vm_{assignment_id}.pem"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve SSH key: {str(e)}")


@router.get("/ssh-instructions/{assignment_id}", summary="Get SSH Connection Instructions")
async def get_ssh_instructions(
    assignment_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed instructions for connecting to the VM via SSH.
    """
    try:
        assignment = DB["vm_assignments"].find_one({
            "assignment_id": assignment_id,
            "user_id": current_user.username,
            "status": "active"
        })
        
        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        vm_ip = assignment.get("vm_ip")
        ssh_username = assignment.get("ssh_username", "vmuser")
        
        instructions = {
            "assignment_id": assignment_id,
            "vm_name": assignment["vm_name"],
            "vm_ip": vm_ip,
            "ssh_username": ssh_username,
            "steps": [
                {
                    "step": 1,
                    "title": "Download your SSH key",
                    "description": f"Click the 'Download SSH Key' button or use: GET /api/vm/ssh-key/{assignment_id}"
                },
                {
                    "step": 2,
                    "title": "Set correct permissions",
                    "command": f"chmod 400 ~/.ssh/vm_{assignment_id}.pem",
                    "description": "Make the key file read-only for security"
                },
                {
                    "step": 3,
                    "title": "Connect to your VM",
                    "command": f"ssh -i ~/.ssh/vm_{assignment_id}.pem {ssh_username}@{vm_ip}",
                    "description": "Use this command to connect to your VM"
                },
                {
                    "step": 4,
                    "title": "Disconnect from VM",
                    "command": "exit",
                    "description": "Type 'exit' or press Ctrl+D to safely disconnect when you're done"
                }
            ],
            "troubleshooting": [
                {
                    "issue": "Permission denied (publickey)",
                    "solution": "Ensure you've downloaded the correct key and set permissions with chmod 400"
                },
                {
                    "issue": "Connection timeout",
                    "solution": "Check if the VM is running and has an external IP. Wait 1-2 minutes after VM starts."
                }
            ]
        }
        
        return instructions
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get instructions: {str(e)}")
