from celery import Celery
from celery.schedules import crontab # --- NEW: Import crontab for scheduling ---
from app.utils.config import settings

celery_app = Celery(
    "tasks",
    broker=settings.CELERY_BROKER_URL,
    backend="rpc://", # Using RPC as we don't need to store results for these tasks
    # Include all task modules
    include=[
        "app.storage.tasks",
        "app.storage.tiering_tasks",
        "app.vm.tasks"  # NEW: VM management tasks
    ] 
)

# --- NEW: This is the Celery Beat schedule ---
# This dictionary tells the Celery Beat scheduler what tasks to run and when.
celery_app.conf.beat_schedule = {
    # Storage optimization (existing)
    'run-storage-optimization-nightly': {
        'task': 'app.storage.tiering_tasks.run_storage_optimization',
        'schedule': crontab(hour=0, minute=0),
    },
    
    # VM Management tasks (NEW)
    'collect-vm-metrics-every-5-minutes': {
        'task': 'collect_vm_metrics',
        'schedule': 300.0,  # 5 minutes in seconds
    },
    'auto-release-inactive-vms-every-10-minutes': {
        'task': 'auto_release_inactive_vms',
        'schedule': 600.0,  # 10 minutes
    },
    'cluster-health-check-every-15-minutes': {
        'task': 'cluster_health_check',
        'schedule': 900.0,  # 15 minutes
    },
    'cleanup-old-metrics-daily': {
        'task': 'cleanup_old_metrics',
        'schedule': crontab(hour=0, minute=30),  # 12:30 AM UTC
    },
}

# Optional but recommended: Set the timezone to ensure the schedule runs predictably.
celery_app.conf.timezone = 'UTC'
