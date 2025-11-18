# backend/app/vm/manager.py

import os
from google.cloud import compute_v1
from google.oauth2 import service_account
from app.utils.config import settings
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from app.database.mongo_client import get_database
from app.vm.models import (
    ClusterType, VMStatus, AssignmentStatus,
    VMAssignmentDB, VMMetricsDB, UserAssignmentResponse
)
from app.vm.workload_analyzer import WorkloadAnalyzer
from app.vm.metrics_collector import VMMetricsCollector
import uuid

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
    print("WARNING: No GCP service account key path configured (settings missing). GCP operations will be disabled.")
    credentials = None
else:
    try:
        credentials = service_account.Credentials.from_service_account_file(GCP_SA_KEY_FULL_PATH)
        print(f"GCP Credentials loaded from: {GCP_SA_KEY_FULL_PATH}")
    except Exception as e:
        print(f"ERROR: Could not load GCP Service Account Key from {GCP_SA_KEY_FULL_PATH}: {e}")
        credentials = None # Set to None if credentials fail to load

# Initialize Compute Engine client
instance_client = compute_v1.InstancesClient(credentials=credentials)
image_client = compute_v1.ImagesClient(credentials=credentials)
machine_type_client = compute_v1.MachineTypesClient(credentials=credentials)


# --- Helper to get default image (Debian 11) ---
def get_default_image_uri(project_id: str = "debian-cloud") -> str:
    """Returns the URI for the latest Debian 11 image."""
    try:
        image_name = "debian-11" # Using an older, stable Debian image
        # Construct the request to get the image
        image_request = compute_v1.GetImageRequest(
            project=project_id,
            image=image_name
        )
        image = image_client.get(request=image_request)
        return image.self_link
    except Exception as e:
        print(f"Error getting default image URI: {e}. Falling back to hardcoded path.")
        # Fallback to a common public image URI if API call fails
        return f"projects/{project_id}/global/images/family/debian-11"


# --- VM Management Functions ---

def _generate_instance_name(cluster_type: str) -> str:
    """Generates a unique instance name."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{cluster_type}-{timestamp}"

def list_vms() -> List[Dict[str, Any]]:
    """Lists all VM instances in the configured zone."""
    request = compute_v1.ListInstancesRequest(
        project=settings.GCP_PROJECT_ID,
        zone=settings.GCP_ZONE,
    )
    instances = instance_client.list(request=request)

def create_vm(
    name: str,
    machine_type: str,
    source_image: str,
    disk_size_gb: int,
    labels: Optional[Dict[str, str]] = None,
    ssh_public_key: Optional[str] = None,
    ssh_username: str = "vmuser"
) -> Dict[str, Any]:
    """Provisions a new VM instance with optional SSH key."""
    if credentials is None:
        raise Exception("GCP credentials not loaded. Cannot create VM.")

    image_uri = get_default_image_uri() # Using a default Debian 11 image

    # Prepare metadata for SSH keys if provided
    metadata_items = []
    if ssh_public_key:
        from app.vm.ssh_manager import format_ssh_metadata
        ssh_keys_value = format_ssh_metadata(ssh_username, ssh_public_key)
        metadata_items.append(
            compute_v1.Items(key="ssh-keys", value=ssh_keys_value)
        )

    config = compute_v1.Instance(
        name=name,
        machine_type=f"zones/{settings.GCP_ZONE}/machineTypes/{machine_type}",
        disks=[
            compute_v1.AttachedDisk(
                auto_delete=True,
                boot=True,
                type_=compute_v1.AttachedDisk.Type.PERSISTENT,
                initialize_params=compute_v1.AttachedDiskInitializeParams(
                    source_image=image_uri,
                    disk_size_gb=disk_size_gb
                ),
            )
        ],
        network_interfaces=[
            compute_v1.NetworkInterface(
                name="global/networks/default", # Use the default network
                access_configs=[
                    compute_v1.AccessConfig(name="External NAT", type_=compute_v1.AccessConfig.Type.ONE_TO_ONE_NAT)
                ],
            )
        ],
        labels=labels if labels else {},
        metadata=compute_v1.Metadata(items=metadata_items) if metadata_items else None
    )

    request = compute_v1.InsertInstanceRequest(
        project=settings.GCP_PROJECT_ID,
        zone=settings.GCP_ZONE,
        instance_resource=config,
    )

    print(f"Creating VM '{name}' with machine type '{machine_type}' and disk size '{disk_size_gb}GB' in zone '{settings.GCP_ZONE}'...")
    operation = instance_client.insert(request=request)
    operation.result() # Wait for the operation to complete

    # Fetch details of the created VM to get its IP
    vm_details = get_vm_details(name, settings.GCP_ZONE)
    return {"name": name, "status": "RUNNING", "details": vm_details}

def start_vm(name: str) -> Dict[str, Any]:
    """Starts a VM instance."""
    request = compute_v1.StartInstanceRequest(
        project=settings.GCP_PROJECT_ID,
        zone=settings.GCP_ZONE,
        instance=name,
    )
    operation = instance_client.start(request=request)
    operation.result()
    vm_details = get_vm_details(name, settings.GCP_ZONE)
    return {"name": name, "status": "RUNNING", "details": vm_details}

def stop_vm(name: str) -> Dict[str, Any]:
    """Stops a VM instance."""
    try:
        request = compute_v1.StopInstanceRequest(
            project=settings.GCP_PROJECT_ID,
            zone=settings.GCP_ZONE,
            instance=name,
        )
        operation = instance_client.stop(request=request)
        operation.result(timeout=30)  # Add timeout to prevent hanging
        vm_details = get_vm_details(name, settings.GCP_ZONE)
        return {"name": name, "status": "TERMINATED", "details": vm_details}
    except Exception as e:
        logger.warning(f"Failed to stop VM {name} via GCP API: {e}. Marking as stopped locally.")
        # Return success anyway to allow local cleanup
        return {"name": name, "status": "TERMINATED", "details": {"error": str(e)}}

def delete_vm(name: str) -> Dict[str, Any]:
    """Deletes a VM instance."""
    request = compute_v1.DeleteInstanceRequest(
        project=settings.GCP_PROJECT_ID,
        zone=settings.GCP_ZONE,
        instance=name,
    )
    operation = instance_client.delete(request=request)
    operation.result()
    return {"name": name, "status": "DELETED"}

def get_vm_details(name: str, zone: str) -> Dict[str, Any]:
    """Retrieves details for a specific VM instance."""
    request = compute_v1.GetInstanceRequest(
        project=settings.GCP_PROJECT_ID,
        zone=zone,
        instance=name,
    )
    instance = instance_client.get(request=request)

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

# Cluster Configuration
CLUSTER_VMS = {
    ClusterType.GENERAL: ["general-vm-1", "general-vm-2"],
    ClusterType.STORAGE: ["storage-vm-1", "storage-vm-2"]
}

def assign_vm_to_user(
    user_id: str,
    workload_description: str,
    cluster_preference: Optional[ClusterType] = None,
    priority_level: int = 1
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
            print(f"Warning: User preference ({cluster_preference}) differs from recommendation ({recommended_cluster})")
            final_cluster = cluster_preference  # Respect user choice
        else:
            final_cluster = cluster_preference
    else:
        final_cluster = recommended_cluster
    
    # Step 3: Find least loaded VM in cluster using least-connections algorithm
    cluster_vms = CLUSTER_VMS[final_cluster]
    vm_loads = []
    
    for vm_name in cluster_vms:
        # Count active assignments for this VM
        active_count = vm_assignments_collection.count_documents({
            "vm_name": vm_name,
            "status": AssignmentStatus.ACTIVE.value
        })
        
        # Get VM status from GCP
        try:
            vm_details = get_vm_details(vm_name, settings.GCP_ZONE)
            vm_status = vm_details["status"]
            vm_ip = vm_details["external_ip"]
        except Exception as e:
            print(f"Error fetching VM {vm_name} details: {e}")
            continue
        
        vm_loads.append({
            "vm_name": vm_name,
            "vm_ip": vm_ip,
            "active_users": active_count,
            "status": vm_status
        })
    
    # Filter running VMs, sort by active users
    running_vms = [vm for vm in vm_loads if vm["status"] == "RUNNING"]
    
    if not running_vms:
        # No running VMs, start the first VM in cluster
        vm_to_start = cluster_vms[0]
        print(f"No running VMs in {final_cluster} cluster. Starting {vm_to_start}...")
        start_result = start_vm(vm_to_start)
        selected_vm = {
            "vm_name": vm_to_start,
            "vm_ip": start_result["details"]["external_ip"],
            "active_users": 0
        }
    else:
        # Select VM with fewest active users (least-connections)
        running_vms.sort(key=lambda x: x["active_users"])
        selected_vm = running_vms[0]
    
    # Step 4: Generate SSH keypair for this assignment
    from app.vm.ssh_manager import generate_ssh_keypair, encrypt_private_key
    from app.utils.config import settings as app_settings
    
    private_key, public_key = generate_ssh_keypair()
    encrypted_private_key = encrypt_private_key(private_key, app_settings.SECRET_KEY)
    
    # Step 5: Create assignment record in MongoDB with SSH keys
    assignment_id = f"assign_{uuid.uuid4().hex[:12]}"
    assigned_at = datetime.utcnow()
    expires_at = assigned_at + timedelta(hours=24)  # 24-hour session
    
    assignment_doc = {
        "assignment_id": assignment_id,
        "user_id": user_id,
        "vm_name": selected_vm["vm_name"],
        "vm_ip": selected_vm["vm_ip"],
        "cluster_type": final_cluster.value,
        "workload_description": workload_description,
        "priority_level": priority_level,
        "assigned_at": assigned_at,
        "expires_at": expires_at,
        "last_active": assigned_at,
        "status": AssignmentStatus.ACTIVE.value,
        "recommendation_confidence": confidence,
        "ssh_username": "vmuser",
        "ssh_public_key": public_key,
        "ssh_private_key_encrypted": encrypted_private_key
    }
    vm_assignments_collection.insert_one(assignment_doc)
    
    # Step 6: Inject SSH key into VM metadata
    try:
        from app.vm.ssh_manager import format_ssh_metadata
        ssh_keys_value = format_ssh_metadata("vmuser", public_key)
        
        # Update VM metadata with SSH key
        metadata_request = compute_v1.GetInstanceRequest(
            project=settings.GCP_PROJECT_ID,
            zone=settings.GCP_ZONE,
            instance=selected_vm["vm_name"]
        )
        instance = instance_client.get(request=metadata_request)
        
        # Add or update SSH keys in metadata
        metadata_items = list(instance.metadata.items) if instance.metadata and instance.metadata.items else []
        
        # Check if ssh-keys already exists
        ssh_keys_found = False
        for i, item in enumerate(metadata_items):
            if item.key == "ssh-keys":
                # Append to existing keys
                metadata_items[i].value = f"{item.value}\n{ssh_keys_value}"
                ssh_keys_found = True
                break
        
        if not ssh_keys_found:
            metadata_items.append(compute_v1.Items(key="ssh-keys", value=ssh_keys_value))
        
        # Update instance metadata
        update_request = compute_v1.SetMetadataInstanceRequest(
            project=settings.GCP_PROJECT_ID,
            zone=settings.GCP_ZONE,
            instance=selected_vm["vm_name"],
            metadata_resource=compute_v1.Metadata(
                items=metadata_items,
                fingerprint=instance.metadata.fingerprint if instance.metadata else None
            )
        )
        operation = instance_client.set_metadata(request=update_request)
        operation.result()  # Wait for operation to complete
        print(f"✓ SSH key injected into {selected_vm['vm_name']}")
    except Exception as e:
        print(f"⚠ Warning: Could not inject SSH key into VM metadata: {e}")
    
    # Step 7: Generate SSH command
    ssh_command = f"ssh -i ~/.ssh/vm_{assignment_id}.pem vmuser@{selected_vm['vm_ip']}"
    
    print(f"Assigned {user_id} to {selected_vm['vm_name']} (IP: {selected_vm['vm_ip']})")
    return selected_vm["vm_name"], selected_vm["vm_ip"], ssh_command, final_cluster, assigned_at, expires_at


def migrate_user(
    user_id: str,
    target_cluster: Optional[ClusterType] = None,
    target_vm_name: Optional[str] = None
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
    
    # Step 2: Determine target VM
    if target_vm_name:
        # Manual selection
        final_target_vm = target_vm_name
    elif target_cluster:
        # Auto-select least loaded VM in target cluster
        cluster_vms = CLUSTER_VMS[target_cluster]
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
    target_vm_details = get_vm_details(final_target_vm, settings.GCP_ZONE)
    if target_vm_details["status"] != "RUNNING":
        print(f"Starting target VM {final_target_vm}...")
        start_vm(final_target_vm)
        target_vm_details = get_vm_details(final_target_vm, settings.GCP_ZONE)
    
    target_vm_ip = target_vm_details["external_ip"]
    
    # Step 4: Update assignment to new VM
    vm_assignments_collection.update_one(
        {"assignment_id": current_assignment["assignment_id"]},
        {
            "$set": {
                "vm_name": final_target_vm,
                "vm_ip": target_vm_ip,
                "cluster_type": target_cluster.value if target_cluster else current_assignment["cluster_type"],
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
    
    if remaining_users == 0:
        print(f"No remaining users on {source_vm_name}. Stopping VM to save costs...")
        stop_vm(source_vm_name)
        source_vm_stopped = True
    else:
        print(f"{remaining_users} users still active on {source_vm_name}. Keeping VM running.")
        source_vm_stopped = False
    
    return {
        "success": True,
        "source_vm": source_vm_name,
        "target_vm": final_target_vm,
        "target_ip": target_vm_ip,
        "source_vm_stopped": source_vm_stopped,
        "ssh_command": f"ssh user@{target_vm_ip}"
    }


def release_vm_assignment(user_id: str, assignment_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Release user's VM assignment and stop VM if no other users remain.
    If assignment_id is provided, releases that specific assignment.
    Otherwise, releases the first active assignment.
    """
    # Find assignment
    if assignment_id:
        assignment = vm_assignments_collection.find_one({
            "assignment_id": assignment_id,
            "user_id": user_id,
            "status": AssignmentStatus.ACTIVE.value
        })
    else:
        assignment = vm_assignments_collection.find_one({
            "user_id": user_id,
            "status": AssignmentStatus.ACTIVE.value
        })
    
    if not assignment:
        return {"success": False, "message": "No active assignment found"}
    
    vm_name = assignment["vm_name"]
    
    # Mark assignment as released
    vm_assignments_collection.update_one(
        {"assignment_id": assignment["assignment_id"]},
        {
            "$set": {
                "status": AssignmentStatus.RELEASED.value,
                "released_at": datetime.utcnow()
            }
        }
    )
    
    # Check if VM has other active users
    remaining_users = vm_assignments_collection.count_documents({
        "vm_name": vm_name,
        "status": AssignmentStatus.ACTIVE.value
    })
    
    vm_stopped = False
    if remaining_users == 0:
        print(f"No remaining users on {vm_name}. Stopping VM...")
        try:
            stop_vm(vm_name)
            vm_stopped = True
        except Exception as e:
            logger.error(f"Failed to stop VM {vm_name}: {e}")
            # Continue anyway - assignment is released locally
            vm_stopped = False
    
    return {
        "success": True,
        "vm_name": vm_name,
        "vm_stopped": vm_stopped,
        "remaining_users": remaining_users
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
    Get all active VM assignments for a user.
    """
    print(f"🔍 Searching for assignments with user_id='{user_id}', status='active'")
    
    # Debug: Check what's actually in the database
    all_assignments = list(vm_assignments_collection.find({}).limit(5))
    print(f"📊 Sample assignments in DB: {[(a.get('user_id'), a.get('status'), a.get('vm_name')) for a in all_assignments]}")
    
    assignments = vm_assignments_collection.find({
        "user_id": user_id,
        "status": AssignmentStatus.ACTIVE.value
    }).sort("assigned_at", -1)  # Most recent first
    
    result = []
    for assignment in assignments:
        assignment.pop("_id", None)
        result.append(assignment)
    
    print(f"✅ Found {len(result)} assignments for user '{user_id}'")
    return result


def get_cluster_health(cluster_type: ClusterType) -> Dict[str, Any]:
    """
    Get aggregated health metrics for a cluster.
    Optimized with batch GCP status check to reduce API calls.
    """
    cluster_vms = CLUSTER_VMS[cluster_type]
    vm_health_data = []
    
    # Batch fetch all VM statuses at once (single API call)
    vm_statuses = {}
    try:
        print(f"Attempting batch fetch for cluster: {cluster_type.value}")
        response = instance_client.list(
            request=compute_v1.ListInstancesRequest(
                project=settings.GCP_PROJECT_ID,
                zone=settings.GCP_ZONE
            )
        )
        
        # Convert iterator to list
        instances_list = list(response)
        for instance in instances_list:
            vm_statuses[instance.name] = instance.status
        print(f"✓ Batch fetched {len(vm_statuses)} VM statuses: {vm_statuses}")
    except Exception as e:
        print(f"✗ Error in batch VM fetch: {type(e).__name__}: {e}")
        print(f"Falling back to individual VM status checks")
    
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
        
        # Get status from batch result, fallback to individual check
        if vm_name in vm_statuses:
            status = vm_statuses[vm_name]
        else:
            # Fallback: individual VM status check
            try:
                vm_details = get_vm_details(vm_name, settings.GCP_ZONE)
                status = vm_details.get("status", "UNKNOWN")
                print(f"Individual fetch for {vm_name}: {status}")
            except Exception as e:
                print(f"Failed to get status for {vm_name}: {e}")
                status = "UNKNOWN"
        
        vm_health = {
            "vm_name": vm_name,
            "status": status,
            "active_users": active_users,
            "cpu_usage": latest_metrics.get("cpu_usage", 0) if latest_metrics else 0,
            "memory_usage": latest_metrics.get("memory_usage", 0) if latest_metrics else 0,
            "last_updated": latest_metrics.get("collected_at") if latest_metrics else None
        }
        vm_health_data.append(vm_health)
    
    # Calculate cluster-wide stats
    total_users = sum(vm["active_users"] for vm in vm_health_data)
    avg_cpu = sum(vm["cpu_usage"] for vm in vm_health_data) / len(vm_health_data) if vm_health_data else 0
    running_vms = sum(1 for vm in vm_health_data if vm["status"] == "RUNNING")
    
    return {
        "cluster_type": cluster_type.value,
        "total_vms": len(cluster_vms),
        "running_vms": running_vms,
        "total_active_users": total_users,
        "average_cpu_usage": round(avg_cpu, 2),
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
