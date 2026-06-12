# =============================================================================
# MODULE: vm/manager.py  (726 lines)
# PURPOSE: GCP Compute Engine VM lifecycle — create/delete/start/stop VMs,
#          five-cluster seed provisioning, SSH key injection, IP assignment
# CLUSTERS: GENERAL, STORAGE, MEMORY, PERFORMANCE, AI_ML (3 VMs each = 15 total)
# DEPENDS ON: google-cloud-compute library, GCP credentials (settings.GCP_*)
#             Called exclusively by routes_vm.py
# DO NOT:
#   - Hardcode the five cluster names — they're constants used by routes_vm.py & NLP
#   - Change SSH key injection format — vm/tasks.py depends on the stored key path
#   - Call GCP APIs directly from routes — always go through manager.py functions
# =============================================================================
# backend/app/vm/manager.py

import os
from google.api_core.exceptions import BadRequest, NotFound
from google.cloud import compute_v1
from google.oauth2 import service_account
from app.utils.config import settings
from app.utils.logger import setup_logger
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from app.database.mongo_client import get_database
from app.vm.models import (
    ClusterType, VMStatus, AssignmentStatus,
    VMAssignmentDB, VMMetricsDB, UserAssignmentResponse
)
from app.vm.workload_analyzer import WorkloadAnalyzer
from app.ml.repository import (
    build_workload_log_from_analysis,
    log_workload_classification,
)
from app.vm.metrics_collector import VMMetricsCollector
from app.vm import vm_provider
from app.vm.gcp_runtime import gcp_project_id, gcp_zone, _gcp_username, _resolve_byoc_compute
import uuid

# Set up logger
logger = setup_logger(__name__)

# Determine the absolute path to the service account key
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # This gets to backend/app
PROJECT_ROOT = os.path.dirname(BASE_DIR) # This gets to CloudResourceOptimizationPlatform/

# Resolve GCP service account key path from settings. Support both the new
# `GCP_SERVICE_ACCOUNT_JSON_PATH` name and the older `GCP_SA_KEY_PATH` for
# backwards compatibility. Accept absolute paths or paths relative to the
# repository `backend` directory.
gcp_key_setting = getattr(settings, 'GCP_SERVICE_ACCOUNT_JSON_PATH', None) or getattr(settings, 'GCP_SA_KEY_PATH', None)
if not gcp_key_setting:
    GCP_SA_KEY_FULL_PATH = None
else:
    if os.path.isabs(gcp_key_setting):
        GCP_SA_KEY_FULL_PATH = gcp_key_setting
    else:
        GCP_SA_KEY_FULL_PATH = os.path.join(PROJECT_ROOT, 'backend', gcp_key_setting)

# Initialize credentials
if not GCP_SA_KEY_FULL_PATH:
    logger.warning("No GCP service account key path configured. GCP operations will be disabled.")
    credentials = None
else:
    try:
        credentials = service_account.Credentials.from_service_account_file(GCP_SA_KEY_FULL_PATH)
        logger.info(f"GCP Credentials loaded successfully from: {GCP_SA_KEY_FULL_PATH}")
    except Exception as e:
        logger.error(f"Failed to load GCP Service Account Key from {GCP_SA_KEY_FULL_PATH}: {str(e)}")
        credentials = None # Set to None if credentials fail to load

# Initialize Compute Engine clients lazily to avoid crashes when GCP credentials are missing
_instance_client = None
_image_client = None
_machine_type_client = None

def _get_instance_client():
    username = _gcp_username.get()
    if username:
        ctx = _resolve_byoc_compute(username)
        if ctx:
            return compute_v1.InstancesClient(credentials=ctx["credentials"])
    global _instance_client
    if _instance_client is None:
        _instance_client = compute_v1.InstancesClient(credentials=credentials)
    return _instance_client


def _get_image_client():
    username = _gcp_username.get()
    if username:
        ctx = _resolve_byoc_compute(username)
        if ctx:
            return compute_v1.ImagesClient(credentials=ctx["credentials"])
    global _image_client
    if _image_client is None:
        _image_client = compute_v1.ImagesClient(credentials=credentials)
    return _image_client


def _get_machine_type_client():
    username = _gcp_username.get()
    if username:
        ctx = _resolve_byoc_compute(username)
        if ctx:
            return compute_v1.MachineTypesClient(credentials=ctx["credentials"])
    global _machine_type_client
    if _machine_type_client is None:
        _machine_type_client = compute_v1.MachineTypesClient(credentials=credentials)
    return _machine_type_client


# --- Helper to get default boot image (Debian family) ---
def get_default_image_uri(project_id: str = "debian-cloud", family: str = "") -> str:
    """
    Resolve a current Debian boot image for new VMs.

    GCP no longer publishes a static image named ``debian-11``; images are
    versioned (e.g. ``debian-12-bookworm-v20260609``). Use image *families*
    so provisioning keeps working as Google rotates releases.
    """
    preferred_families = (family,) if family else ("debian-12", "debian-11")
    client = _get_image_client()
    for image_family in preferred_families:
        try:
            image = client.get_from_family(
                project=project_id,
                family=image_family,
            )
            logger.info(
                "Using GCP image family %s (%s)",
                image_family,
                getattr(image, "name", image_family),
            )
            # self_link is accepted by InsertInstance; family path works too
            return image.self_link or (
                f"projects/{project_id}/global/images/family/{image_family}"
            )
        except Exception as exc:
            logger.debug("GCP image family %s unavailable: %s", image_family, exc)

    logger.warning(
        "Could not resolve Debian image via API; using family fallback debian-12"
    )
    return f"projects/{project_id}/global/images/family/debian-12"


def _resolve_gcp_boot_image(source_image: str) -> str:
    """Resolve catalog image path (project/family) to a GCP image URI."""
    src = (source_image or "").strip()
    if not src:
        return get_default_image_uri()
    if src.startswith("projects/"):
        return src
    if "/" in src:
        project_id, family = src.split("/", 1)
        return get_default_image_uri(project_id=project_id or "debian-cloud", family=family)
    return get_default_image_uri(family=src)


# --- VM Management Functions ---

def _generate_instance_name(cluster_type: str) -> str:
    """Generates a unique instance name."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{cluster_type}-{timestamp}"

def list_vms() -> List[Dict[str, Any]]:
    """Lists all VM instances in the configured zone."""
    if credentials is None:
        logger.debug("GCP not configured, returning empty VM list from DB fallback")
        # Fallback: return VMs from MongoDB assignments
        DB = get_database()
        db_vms = []
        for doc in DB["vm_assignments"].find({"status": {"$in": ["assigned", "active"]}}):
            db_vms.append({
                "name": doc.get("vm_name", "unknown"),
                "status": doc.get("vm_status", "UNKNOWN"),
                "labels": {"cluster_type": doc.get("cluster_type", "performance")},
                "machine_type": doc.get("machine_type", "unknown"),
                "zone": gcp_zone() if hasattr(settings, 'GCP_ZONE') else "us-central1-a",
            })
        return db_vms
    
    try:
        request = compute_v1.ListInstancesRequest(
            project=gcp_project_id(),
            zone=gcp_zone(),
        )
        instances = _get_instance_client().list(request=request)
        
        vm_list = []
        for instance in instances:
            vm_list.append({
                "name": instance.name,
                "status": instance.status,
                "machine_type": instance.machine_type.split("/")[-1] if instance.machine_type else "unknown",
                "zone": instance.zone.split("/")[-1] if instance.zone else "unknown",
                "labels": dict(instance.labels) if instance.labels else {},
                "creation_timestamp": instance.creation_timestamp,
                "network_interfaces": [
                    {
                        "network_ip": ni.network_i_p,
                        "external_ip": ni.access_configs[0].nat_i_p if ni.access_configs else None
                    }
                    for ni in (instance.network_interfaces or [])
                ],
            })
        return vm_list
    except Exception as e:
        logger.error(f"Error listing VMs from GCP: {e}")
        return []
def create_vm(
    name: str,
    machine_type: str,
    source_image: str,
    disk_size_gb: int,
    labels: Optional[Dict[str, str]] = None,
    *,
    disk_type: str = "",
) -> Dict[str, Any]:
    """Provisions a new VM instance."""
    if credentials is None:
        raise Exception("GCP credentials not loaded. Cannot create VM.")

    image_uri = _resolve_gcp_boot_image(source_image)
    if image_uri.startswith("https://") and "/compute/v1/" in image_uri:
        image_uri = image_uri.split("/compute/v1/", 1)[1]

    disk_params: dict[str, Any] = {
        "source_image": image_uri,
        "disk_size_gb": disk_size_gb,
    }
    if disk_type:
        disk_params["disk_type"] = disk_type

    config = compute_v1.Instance(
        name=name,
        machine_type=f"zones/{gcp_zone()}/machineTypes/{machine_type}",
        disks=[
            compute_v1.AttachedDisk(
                auto_delete=True,
                boot=True,
                # Use string enum values — proto + Python 3.14 rejects Type.* enum members here
                type="PERSISTENT",
                initialize_params=compute_v1.AttachedDiskInitializeParams(**disk_params),
            )
        ],
        network_interfaces=[
            compute_v1.NetworkInterface(
                name="global/networks/default",
                access_configs=[
                    compute_v1.AccessConfig(
                        name="External NAT",
                        type="ONE_TO_ONE_NAT",
                    )
                ],
            )
        ],
        labels=labels if labels else {},
    )

    request = compute_v1.InsertInstanceRequest(
        project=gcp_project_id(),
        zone=gcp_zone(),
        instance_resource=config,
    )

    logger.info(f"Creating VM '{name}' with machine type '{machine_type}' and disk size '{disk_size_gb}GB' in zone '{gcp_zone()}'")
    operation = _get_instance_client().insert(request=request)
    operation.result() # Wait for the operation to complete

    # Fetch details of the created VM to get its IP
    vm_details = get_vm_details(name, gcp_zone())
    return {"name": name, "status": "RUNNING", "details": vm_details}

def start_vm(name: str) -> Dict[str, Any]:
    """Starts a VM instance."""
    request = compute_v1.StartInstanceRequest(
        project=gcp_project_id(),
        zone=gcp_zone(),
        instance=name,
    )
    operation = _get_instance_client().start(request=request)
    operation.result()
    vm_details = get_vm_details(name, gcp_zone())
    return {"name": name, "status": "RUNNING", "details": vm_details}

def find_gcp_instance_zone(name: str) -> Optional[str]:
    """Locate a VM by name across all zones in the project."""
    if credentials is None:
        return None
    request = compute_v1.AggregatedListInstancesRequest(
        project=gcp_project_id(),
        filter=f'(name = "{name}")',
    )
    for zone_path, scoped in _get_instance_client().aggregated_list(request=request):
        if scoped.instances:
            return zone_path.rsplit("/", 1)[-1] if zone_path else None
    return None


def _resolve_gcp_zone(name: str, zone: Optional[str] = None) -> str:
    target = zone or gcp_zone()
    details = get_vm_details(name, target)
    if details.get("status") != "NOT_PROVISIONED":
        return target
    found = find_gcp_instance_zone(name)
    return found or target


def stop_vm(name: str, zone: Optional[str] = None) -> Dict[str, Any]:
    """Stops a VM instance."""
    target_zone = _resolve_gcp_zone(name, zone)
    request = compute_v1.StopInstanceRequest(
        project=gcp_project_id(),
        zone=target_zone,
        instance=name,
    )
    try:
        operation = _get_instance_client().stop(request=request)
        operation.result()
    except NotFound:
        logger.info("GCP VM '%s' not found in zone %s during stop", name, target_zone)
    vm_details = get_vm_details(name, target_zone)
    return {"name": name, "status": "TERMINATED", "details": vm_details}


def delete_vm(name: str, zone: Optional[str] = None) -> Dict[str, Any]:
    """Deletes a VM instance and its boot disk."""
    target_zone = _resolve_gcp_zone(name, zone)

    def _do_delete(z: str) -> None:
        request = compute_v1.DeleteInstanceRequest(
            project=gcp_project_id(),
            zone=z,
            instance=name,
        )
        operation = _get_instance_client().delete(request=request)
        operation.result()

    try:
        _do_delete(target_zone)
    except NotFound:
        found = find_gcp_instance_zone(name)
        if found and found != target_zone:
            try:
                _do_delete(found)
            except NotFound:
                logger.info("GCP VM '%s' already deleted", name)
        else:
            logger.info("GCP VM '%s' not found; treating as deleted", name)
    return {"name": name, "status": "DELETED"}

def get_vm_details(name: str, zone: str) -> Dict[str, Any]:
    """Retrieves details for a specific VM instance."""
    if credentials is None:
        return {
            "name": name,
            "status": "UNKNOWN",
            "machine_type": "unknown",
            "zone": zone,
            "external_ip": "N/A",
            "creation_timestamp": None,
            "labels": {}
        }

    request = compute_v1.GetInstanceRequest(
        project=gcp_project_id(),
        zone=zone,
        instance=name,
    )
    try:
        instance = _get_instance_client().get(request=request)
    except NotFound:
        logger.debug("GCP VM '%s' not found in zone %s", name, zone)
        return {
            "name": name,
            "status": "NOT_PROVISIONED",
            "machine_type": "unknown",
            "zone": zone,
            "external_ip": "N/A",
            "creation_timestamp": None,
            "labels": {},
        }
    except BadRequest as exc:
        message = str(exc).lower()
        if "zone" in message:
            logger.warning("GCP zone '%s' invalid or unavailable for VM '%s': %s", zone, name, exc)
            return {
                "name": name,
                "status": "NOT_PROVISIONED",
                "machine_type": "unknown",
                "zone": zone,
                "external_ip": "N/A",
                "creation_timestamp": None,
                "labels": {},
            }
        raise

    external_ip = "N/A"
    if instance.network_interfaces and instance.network_interfaces[0].access_configs:
        # The field is accessed as natIP (not nat_ip or nat_I_P)
        access_config = instance.network_interfaces[0].access_configs[0]
        external_ip = getattr(access_config, 'natIP', getattr(access_config, 'nat_i_p', 'N/A'))

    return {
        "name": instance.name,
        "status": instance.status,
        "machine_type": instance.machine_type.split('/')[-1],
        "zone": zone,
        "external_ip": external_ip,
        "creation_timestamp": instance.creation_timestamp,
        "labels": dict(instance.labels) # Convert RepeatedComposite to dict
    }


# --- Advanced VM Management with User Assignment ---

# MongoDB Collections
DB = get_database()
vm_assignments_collection = DB["vm_assignments"]
vm_metrics_collection = DB["vm_metrics"]

# Cluster Configuration — sourced from cluster_catalog (7 clusters × 4 slots)
from app.vm.cluster_catalog import cluster_types, legacy_cluster_vms_dict

CLUSTER_VMS = legacy_cluster_vms_dict()


def calculate_efficiency_score(metrics: Optional[Dict[str, Any]], active_users: int = 0) -> float:
    """
    Multi-factor VM resource score from the report's S_eff idea.
    Combines CPU, memory, disk I/O, network I/O, and user density into a 0-100 score.
    """
    if not metrics:
        return 0.0

    cpu = float(metrics.get("cpu_usage", 0) or 0)
    memory = float(metrics.get("memory_usage", 0) or 0)
    disk_io = float(metrics.get("disk_io_read_mb", 0) or 0) + float(metrics.get("disk_io_write_mb", 0) or 0)
    network_io = float(metrics.get("network_in_mb", 0) or 0) + float(metrics.get("network_out_mb", 0) or 0)
    user_density = min(100.0, (active_users / 5) * 100)

    disk_score = min(100.0, disk_io / 2.0)
    network_score = min(100.0, network_io / 1.5)

    score = (
        cpu * 0.35
        + memory * 0.25
        + disk_score * 0.15
        + network_score * 0.15
        + user_density * 0.10
    )
    return round(max(0.0, min(100.0, score)), 2)

def assign_vm_to_user(
    user_id: str,
    workload_description: str,
    cluster_preference: Optional[ClusterType] = None,
    priority_level: int = 1,
    csp: str = "GCP",
    vm_preference: Optional[str] = None,
    platform_region_slug: Optional[str] = None,
) -> Tuple[str, str, str, ClusterType, datetime, datetime]:
    """
    Assign a VM to user using least-connections load balancing.
    Returns (vm_name, vm_ip, ssh_command, cluster_type, assigned_at, expires_at).
    """
    # Step 1: Analyze workload to recommend cluster
    analyzer = WorkloadAnalyzer()
    recommended_cluster, confidence, analysis = analyzer.analyze(workload_description)
    
    # Step 2: Validate user preference
    if cluster_preference:
        if cluster_preference != recommended_cluster:
            logger.warning(f"User preference ({cluster_preference}) differs from recommendation ({recommended_cluster})")
            final_cluster = cluster_preference  # Respect user choice
        else:
            final_cluster = cluster_preference
    else:
        final_cluster = recommended_cluster

    user_overrode = bool(
        cluster_preference and cluster_preference != recommended_cluster
    )
    log_workload_classification(
        build_workload_log_from_analysis(
            username=user_id,
            workload_description=workload_description or "",
            recommended_cluster=recommended_cluster.value,
            final_cluster=final_cluster.value,
            confidence=confidence,
            analysis_details=analysis,
            user_overrode=user_overrode,
        )
    )

    # Step 3: Find least loaded VM in cluster using least-connections algorithm
    cluster_vms = vm_provider.cluster_vms(csp, final_cluster)
    zone = vm_provider.vm_zone(csp)
    vm_loads = []
    
    for vm_name in cluster_vms:
        # Count active assignments for this VM
        active_count = vm_assignments_collection.count_documents({
            "vm_name": vm_name,
            "status": AssignmentStatus.ACTIVE.value
        })
        
        try:
            vm_details = vm_provider.get_vm_details(csp, vm_name, zone)
            vm_status = vm_details["status"]
            vm_ip = vm_details["external_ip"]
        except Exception as e:
            logger.error(f"Error fetching VM {vm_name} details: {e}")
            continue
        
        vm_loads.append({
            "vm_name": vm_name,
            "vm_ip": vm_ip,
            "active_users": active_count,
            "status": vm_status
        })
    
    if not vm_provider.cloud_configured(csp):
        vm_to_start = cluster_vms[0]
        logger.info(
            f"{csp} not configured. Assigning {user_id} to simulated {final_cluster.value} VM {vm_to_start}"
        )
        selected_vm = {
            "vm_name": vm_to_start,
            "vm_ip": "N/A",
            "active_users": 0,
        }
    else:
        # Start stopped pool VMs or provision missing ones when the cluster is idle
        selected_vm = vm_provider.ensure_cluster_vm_for_assignment(
            csp, final_cluster, vm_loads, vm_preference=vm_preference
        )
    
    # Step 4: Create assignment record in MongoDB
    assignment_id = f"assign_{uuid.uuid4().hex[:12]}"
    assigned_at = datetime.utcnow()
    expires_at = assigned_at + timedelta(hours=24)  # 24-hour session
    
    from app.organizations.limits import maybe_assert_org_quotas
    from app.organizations.resource_acl import org_tags_for_create

    maybe_assert_org_quotas(user_id)

    from app.vm.cluster_catalog import find_slot_by_vm_name, resolve_vm_alias

    canonical_vm = resolve_vm_alias(selected_vm["vm_name"], csp)
    slot_meta = find_slot_by_vm_name(canonical_vm, csp)

    assignment_doc = {
        "assignment_id": assignment_id,
        "user_id": user_id,
        "vm_name": canonical_vm,
        "vm_ip": selected_vm["vm_ip"],
        "cluster_type": final_cluster.value,
        "workload_description": workload_description,
        "priority_level": priority_level,
        "assigned_at": assigned_at,
        "expires_at": expires_at,
        "last_active": assigned_at,
        "status": AssignmentStatus.ACTIVE.value,
        "recommendation_confidence": confidence,
        "csp": csp,
        "platform_region_slug": platform_region_slug,
        "compute_zone": zone,
        "slot_id": canonical_vm,
        "tier": slot_meta.tier if slot_meta else None,
        "tier_label": slot_meta.tier_label if slot_meta else None,
        "slot_index": slot_meta.slot_index if slot_meta else None,
        **org_tags_for_create(user_id),
    }
    vm_assignments_collection.insert_one(assignment_doc)
    
    # Step 5: Generate SSH command
    ssh_command = f"ssh user@{selected_vm['vm_ip']}"
    
    logger.info(f"Assigned {user_id} to {selected_vm['vm_name']} (IP: {selected_vm['vm_ip']})")
    return selected_vm["vm_name"], selected_vm["vm_ip"], ssh_command, final_cluster, assigned_at, expires_at


def migrate_user(
    user_id: str,
    target_cluster: Optional[ClusterType] = None,
    target_vm_name: Optional[str] = None,
    csp: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Migrate user from current VM to another VM (workload transfer).
    Either specify target_cluster for auto-selection or target_vm_name for manual.
    """
    # Step 1: Find current assignment
    current_assignment = vm_assignments_collection.find_one({
        "user_id": user_id,
        "status": AssignmentStatus.ACTIVE.value
    })
    
    if not current_assignment:
        raise ValueError(f"No active assignment found for user {user_id}")
    
    source_vm_name = current_assignment["vm_name"]
    source_cluster = ClusterType(current_assignment["cluster_type"])
    effective_csp = csp or current_assignment.get("csp") or "GCP"
    zone = vm_provider.vm_zone(effective_csp)
    
    # Step 2: Determine target VM
    if target_vm_name:
        # Manual selection
        final_target_vm = target_vm_name
    elif target_cluster:
        # Auto-select least loaded VM in target cluster
        cluster_vms = vm_provider.cluster_vms(effective_csp, target_cluster)
        vm_loads = []
        
        for vm_name in cluster_vms:
            if vm_name == source_vm_name:
                continue  # Skip source VM

            active_count = vm_assignments_collection.count_documents({
                "vm_name": vm_name,
                "status": AssignmentStatus.ACTIVE.value
            })
            vm_loads.append({"vm_name": vm_name, "active_users": active_count})
        
        if not vm_loads:
            raise ValueError(f"No available VMs in {target_cluster} cluster")
        
        vm_loads.sort(key=lambda x: x["active_users"])
        final_target_vm = vm_loads[0]["vm_name"]
    else:
        raise ValueError("Must specify either target_cluster or target_vm_name")
    
    # Step 3: Start target VM if stopped
    target_vm_details = vm_provider.get_vm_details(effective_csp, final_target_vm, zone)
    if not vm_provider.cloud_configured(effective_csp):
        logger.info("%s not configured. Performing simulated VM migration.", effective_csp)
        target_vm_details = {
            "name": final_target_vm,
            "status": "UNKNOWN",
            "external_ip": "N/A",
        }
    elif target_vm_details["status"] != "RUNNING":
        logger.info(f"Ensuring target VM {final_target_vm} is running")
        effective_cluster = target_cluster or source_cluster
        ensured = vm_provider.ensure_vm_running(
            effective_csp, effective_cluster, final_target_vm
        )
        target_vm_details = {
            "name": ensured["vm_name"],
            "external_ip": ensured["vm_ip"],
            "status": "RUNNING",
        }

    target_vm_ip = target_vm_details["external_ip"]
    
    # Step 4: Update assignment to new VM
    vm_assignments_collection.update_one(
        {"assignment_id": current_assignment["assignment_id"]},
        {
            "$set": {
                "vm_name": final_target_vm,
                "vm_ip": target_vm_ip,
                "cluster_type": target_cluster.value if target_cluster else current_assignment["cluster_type"],
                "csp": effective_csp,
                "migrated_at": datetime.utcnow(),
                "last_active": datetime.utcnow()
            }
        }
    )
    
    # Step 5: Check if source VM can be stopped (no other active users)
    remaining_users = vm_assignments_collection.count_documents({
        "vm_name": source_vm_name,
        "status": AssignmentStatus.ACTIVE.value
    })
    
    if remaining_users == 0 and vm_provider.cloud_configured(effective_csp):
        logger.info(f"No remaining users on {source_vm_name}. Stopping VM to save costs")
        vm_provider.stop_vm(effective_csp, source_vm_name)
        source_vm_stopped = True
    else:
        logger.info(f"{remaining_users} users still active on {source_vm_name}. Keeping VM running")
        source_vm_stopped = False
    
    return {
        "success": True,
        "source_vm": source_vm_name,
        "target_vm": final_target_vm,
        "target_ip": target_vm_ip,
        "source_vm_stopped": source_vm_stopped,
        "ssh_command": f"ssh user@{target_vm_ip}"
    }


def _terminate_vm_if_idle(assignment: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Terminate or stop a VM when no active assignments remain on that slot."""
    from app.utils.config import settings
    from app.vm.vm_provider import vm_runtime_context

    vm_name = assignment["vm_name"]
    effective_csp = assignment.get("csp") or "GCP"
    platform_region = assignment.get("platform_region_slug")
    compute_zone = assignment.get("compute_zone")

    active_on_vm = vm_assignments_collection.count_documents({
        "vm_name": vm_name,
        "status": AssignmentStatus.ACTIVE.value,
    })
    # Still active while releasing the last assignment — only skip when others remain.
    if active_on_vm > 1:
        return {
            "vm_stopped": False,
            "vm_deleted": False,
            "skipped": True,
            "reason": "other_active_users",
        }

    if not vm_provider.cloud_configured(effective_csp):
        return {"vm_stopped": False, "vm_deleted": False, "skipped": True, "reason": "csp_not_configured"}

    vm_stopped = False
    vm_deleted = False
    with vm_runtime_context(user_id, effective_csp, platform_region):
        zone = compute_zone or vm_provider.vm_zone(effective_csp)
        if getattr(settings, "VM_DELETE_ON_IDLE", True):
            logger.info(
                "Terminating idle VM %s in %s (region=%s)",
                vm_name,
                zone,
                platform_region or "default",
            )
            vm_provider.delete_vm(effective_csp, vm_name, zone=zone)
            vm_deleted = True
        else:
            logger.info("Stopping idle VM %s in %s", vm_name, zone)
            vm_provider.stop_vm(effective_csp, vm_name, zone=zone)
            vm_stopped = True

    return {"vm_stopped": vm_stopped, "vm_deleted": vm_deleted, "skipped": False}


def release_vm_assignment(user_id: str, assignment_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Release user's VM assignment and stop VM if no other users remain.
    If assignment_id is provided, releases that specific assignment.
    Otherwise, releases the first active assignment.

    When an assignment was already marked released but the cloud VM was left running
    (legacy bug), release by assignment_id still terminates the orphaned instance.
    """
    from app.organizations.resource_acl import can_access_resource

    assignment = None
    already_released = False

    if assignment_id:
        assignment = vm_assignments_collection.find_one({
            "assignment_id": assignment_id,
            "status": AssignmentStatus.ACTIVE.value,
        })
        if not assignment:
            stale = vm_assignments_collection.find_one({"assignment_id": assignment_id})
            if stale and stale.get("status") == AssignmentStatus.RELEASED.value:
                if not can_access_resource(user_id, stale, "delete", user_field="user_id"):
                    return {"success": False, "message": "Not authorized to release this assignment"}
                cleanup = _terminate_vm_if_idle(stale, user_id)
                if cleanup.get("skipped") and cleanup.get("reason") == "other_active_users":
                    return {
                        "success": False,
                        "message": "VM still has other active users",
                    }
                return {
                    "success": True,
                    "vm_name": stale["vm_name"],
                    "vm_stopped": cleanup.get("vm_stopped", False),
                    "vm_deleted": cleanup.get("vm_deleted", False),
                    "remaining_users": vm_assignments_collection.count_documents({
                        "vm_name": stale["vm_name"],
                        "status": AssignmentStatus.ACTIVE.value,
                    }),
                    "already_released": True,
                    "message": "Assignment was already released; cloud VM cleaned up",
                }
    else:
        assignment = vm_assignments_collection.find_one({
            "user_id": user_id,
            "status": AssignmentStatus.ACTIVE.value,
        })

    if not assignment:
        return {"success": False, "message": "No active assignment found"}

    if not can_access_resource(user_id, assignment, "delete", user_field="user_id"):
        return {"success": False, "message": "Not authorized to release this assignment"}

    vm_name = assignment["vm_name"]
    cleanup = _terminate_vm_if_idle(assignment, user_id)
    vm_stopped = cleanup.get("vm_stopped", False)
    vm_deleted = cleanup.get("vm_deleted", False)

    vm_assignments_collection.update_one(
        {"assignment_id": assignment["assignment_id"]},
        {
            "$set": {
                "status": AssignmentStatus.RELEASED.value,
                "released_at": datetime.utcnow(),
            }
        },
    )

    remaining_users = vm_assignments_collection.count_documents({
        "vm_name": vm_name,
        "status": AssignmentStatus.ACTIVE.value,
    })

    return {
        "success": True,
        "vm_name": vm_name,
        "vm_stopped": vm_stopped,
        "vm_deleted": vm_deleted,
        "remaining_users": remaining_users,
        "already_released": already_released,
    }


def get_user_assignment(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get current active VM assignment for a user.
    Returns the first assignment for backward compatibility.
    """
    assignment = vm_assignments_collection.find_one({
        "user_id": user_id,
        "status": AssignmentStatus.ACTIVE.value
    })
    
    if not assignment:
        return None
    
    # Remove MongoDB _id field for JSON serialization
    assignment.pop("_id", None)
    return assignment


def get_all_user_assignments(user_id: str) -> List[Dict[str, Any]]:
    """
    Get all active VM assignments visible to a user (org-aware).
    """
    from app.organizations.resource_acl import list_filter_for_user

    filt = list_filter_for_user(user_id, user_field="user_id")
    assignments = vm_assignments_collection.find(
        {"$and": [filt, {"status": AssignmentStatus.ACTIVE.value}]}
    ).sort("assigned_at", -1)
    
    result = []
    for assignment in assignments:
        assignment.pop("_id", None)
        result.append(assignment)
    
    return result


def get_cluster_health(cluster_type: ClusterType, csp: str = "GCP") -> Dict[str, Any]:
    """Aggregated health metrics for a cluster (GCP or AWS)."""
    cluster_vms = vm_provider.cluster_vms(csp, cluster_type)
    vm_health_data = []
    vm_statuses = {v["name"]: v["status"] for v in vm_provider.list_vms(csp)}
    zone = vm_provider.vm_zone(csp)
    
    for vm_name in cluster_vms:
        # Get latest metrics from MongoDB (fast, local)
        latest_metrics = vm_metrics_collection.find_one(
            {"vm_name": vm_name},
            sort=[("collected_at", -1)]
        )
        
        # Get active user count (fast, local)
        active_users = vm_assignments_collection.count_documents({
            "vm_name": vm_name,
            "status": AssignmentStatus.ACTIVE.value
        })
        
        # Use cloud inventory from list_vms — avoid per-VM API calls that 404 when not seeded.
        if vm_name in vm_statuses:
            status = vm_statuses[vm_name]
        elif not vm_provider.cloud_configured(csp):
            status = "UNKNOWN"
        else:
            status = "NOT_PROVISIONED"
        
        vm_health = {
            "vm_name": vm_name,
            "status": status,
            "active_users": active_users,
            "cpu_usage": latest_metrics.get("cpu_usage", 0) if latest_metrics else 0,
            "memory_usage": latest_metrics.get("memory_usage", 0) if latest_metrics else 0,
            "efficiency_score": calculate_efficiency_score(latest_metrics, active_users),
            "last_updated": latest_metrics.get("collected_at") if latest_metrics else None
        }
        vm_health_data.append(vm_health)
    
    # Calculate cluster-wide stats
    total_users = sum(vm["active_users"] for vm in vm_health_data)
    avg_cpu = sum(vm["cpu_usage"] for vm in vm_health_data) / len(vm_health_data) if vm_health_data else 0
    avg_efficiency = sum(vm["efficiency_score"] for vm in vm_health_data) / len(vm_health_data) if vm_health_data else 0
    running_vms = sum(1 for vm in vm_health_data if vm["status"] == "RUNNING")
    
    return {
        "cluster_type": cluster_type.value,
        "csp": csp,
        "total_vms": len(cluster_vms),
        "running_vms": running_vms,
        "total_active_users": total_users,
        "average_cpu_usage": round(avg_cpu, 2),
        "average_efficiency_score": round(avg_efficiency, 2),
        "scoring_model": "S_eff_v1",
        "vms": vm_health_data
    }


def update_user_activity(user_id: str) -> None:
    """
    Update last_active timestamp for user's assignment.
    Call this periodically (e.g., every API request from user).
    """
    vm_assignments_collection.update_one(
        {"user_id": user_id, "status": AssignmentStatus.ACTIVE.value},
        {"$set": {"last_active": datetime.utcnow()}}
    )
