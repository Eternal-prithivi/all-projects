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
        "app.vm.tasks",  # VM management tasks
        "app.pricing.tasks",  # Pricing update tasks
        "app.cost.tasks_anomaly",  # Cost anomaly detection
        "app.budgets.tasks",  # Budget monitoring and alerts
        "app.security.tasks_alerts",  # Security alert pipeline (email + SMS)
        "app.security.security_stale_tasks",  # Stale secure-file awareness
        "app.ml.tasks_feedback",  # Phase 8 feedback evaluation/retraining readiness
        "app.provision.tasks",  # Phase 11 Terraform drift detection
    ] 
)

# --- NEW: This is the Celery Beat schedule ---
# This dictionary tells the Celery Beat scheduler what tasks to run and when.
celery_app.conf.beat_schedule = {
    # Storage optimization (existing)
    'run-storage-optimization-nightly': {
        'task': 'app.storage.tiering_tasks.run_storage_optimization',
        'schedule': crontab(hour=2, minute=0),  # Report §4.3 example: 02:00 UTC
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
    
    # Pricing updates (NEW)
    'update-pricing-weekly': {
        'task': 'update_pricing_cache',
        'schedule': crontab(day_of_week=1, hour=2, minute=0),  # Every Monday at 2 AM UTC
    },
    
    # Cost anomaly detection
    'check-cost-anomalies-daily': {
        'task': 'check_cost_anomalies',
        'schedule': crontab(hour=1, minute=0),  # Every day at 1 AM UTC
    },
    
    # Budget monitoring and SMS alerts (NEW)
    'check-budget-alerts-daily': {
        'task': 'check_budget_alerts',
        'schedule': crontab(hour=9, minute=0),  # Every day at 9 AM UTC
    },

    # Security alerts (email + SMS)
    'check-security-alerts-daily': {
        'task': 'check_security_alerts',
        'schedule': crontab(hour=8, minute=0),  # Every day at 8 AM UTC
    },

    # Secure vault stale-file awareness
    'run-security-stale-check-daily': {
        'task': 'run_security_stale_check',
        'schedule': crontab(hour=3, minute=0),  # Every day at 3 AM UTC
    },

    # Phase 8 ML feedback/retraining readiness
    'evaluate-ml-feedback-daily': {
        'task': 'evaluate_ml_feedback',
        'schedule': crontab(hour=3, minute=0),  # Every day at 3 AM UTC
    },

    # Guarded self-retraining from evaluated user feedback
    'retrain-ml-models-from-feedback-weekly': {
        'task': 'retrain_ml_models_from_feedback',
        'schedule': crontab(day_of_week=0, hour=3, minute=30),  # Sunday 3:30 AM UTC
    },

    # Phase 11: Terraform drift detection
    'check-provision-drift-daily': {
        'task': 'app.provision.tasks.scheduled_drift_check',
        'schedule': crontab(hour=6, minute=0),  # Every day at 6 AM UTC
    },

    'update-rl-policy-daily': {
        'task': 'update_rl_policy_from_feedback',
        'schedule': crontab(hour=3, minute=15),  # After feedback evaluation
    },

    'federated-statistics-weekly': {
        'task': 'federated_statistics_round',
        'schedule': crontab(day_of_week=0, hour=4, minute=0),  # Sunday 04:00 UTC
    },
}

# Optional but recommended: Set the timezone to ensure the schedule runs predictably.
celery_app.conf.timezone = 'UTC'

