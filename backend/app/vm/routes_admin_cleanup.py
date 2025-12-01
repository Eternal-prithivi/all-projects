# Admin cleanup endpoint - temporary for demo
from fastapi import APIRouter, HTTPException
from app.database.mongo_client import get_database
from app.vm.manager import stop_vm
from app.utils.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])
DB = get_database()

@router.post("/cleanup-assignments")
async def cleanup_all_assignments():
    """
    Release all active VM assignments AND stop all VMs for demo reset.
    ⚠️ ADMIN ONLY - Remove this in production!
    """
    try:
        # Get current state
        active_count = DB["vm_assignments"].count_documents({"status": "active"})
        
        # Release all active assignments
        result = DB["vm_assignments"].update_many(
            {"status": "active"},
            {"$set": {"status": "released"}}
        )
        
        # Stop all VMs in both clusters
        vms_to_stop = ["general-vm-1", "general-vm-2", "storage-vm-1", "storage-vm-2"]
        stopped_vms = []
        
        for vm_name in vms_to_stop:
            try:
                stop_vm(vm_name, settings.GCP_ZONE)
                stopped_vms.append(vm_name)
            except Exception as e:
                logger.error(f"Failed to stop {vm_name}: {e}")
        
        return {
            "success": True,
            "message": "All assignments released and VMs stopped for demo reset",
            "previously_active": active_count,
            "released_count": result.modified_count,
            "remaining_active": DB["vm_assignments"].count_documents({"status": "active"}),
            "vms_stopped": stopped_vms
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
