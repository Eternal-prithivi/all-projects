"""
Enterprise VM adaptive control (report §3.4 Step 4).

Uses latest metrics + MigrationRecommender. Persists alerts/actions and
optionally auto-migrates users when VM_AUTO_MIGRATE_ENABLED=true.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.database.mongo_client import get_database
from app.notifications import service as notification_service
from app.utils.config import settings
from app.utils.logger import setup_logger
from app.vm import vm_provider
from app.vm.cluster_catalog import cluster_types
from app.vm.migration_recommender import MigrationRecommender
from app.vm.models import ClusterType, VMMetricsResponse, VMStatus

logger = setup_logger(__name__)

ACTIONS_COLLECTION = "vm_agent_actions"
ALERTS_COLLECTION = "vm_cluster_alerts"
METRICS_COLLECTION = "vm_metrics"
ASSIGNMENTS_COLLECTION = "vm_assignments"


def _latest_metrics_by_vm(db) -> Dict[str, Dict[str, Any]]:
    """Most recent metrics document per VM name."""
    pipeline = [
        {"$sort": {"collected_at": -1}},
        {
            "$group": {
                "_id": "$vm_name",
                "doc": {"$first": "$$ROOT"},
            }
        },
    ]
    out: Dict[str, Dict[str, Any]] = {}
    for row in db[METRICS_COLLECTION].aggregate(pipeline):
        doc = row.get("doc") or {}
        name = doc.get("vm_name") or row.get("_id")
        if name:
            out[str(name)] = doc
    return out


def _doc_to_metrics_response(
    vm_name: str,
    cluster_type: ClusterType,
    doc: Dict[str, Any],
    active_users: int,
) -> VMMetricsResponse:
    status_raw = (doc.get("status") or "RUNNING").upper()
    try:
        status = VMStatus(status_raw)
    except ValueError:
        status = VMStatus.RUNNING

    recorded = doc.get("collected_at") or doc.get("recorded_at") or datetime.utcnow()
    return VMMetricsResponse(
        vm_name=vm_name,
        cluster_type=cluster_type,
        cpu_usage=float(doc.get("cpu_usage", 0) or 0),
        memory_usage=float(doc.get("memory_usage", 0) or 0),
        disk_io_read_mb=float(doc.get("disk_io_read_mb", 0) or 0),
        disk_io_write_mb=float(doc.get("disk_io_write_mb", 0) or 0),
        active_users=active_users,
        uptime_hours=float(doc.get("uptime_hours", 0) or 0),
        estimated_cost_usd=float(doc.get("estimated_cost_usd", 0) or 0),
        status=status,
        recorded_at=recorded if isinstance(recorded, datetime) else datetime.utcnow(),
    )


def _active_assignments(db, cluster_type: ClusterType) -> List[Dict[str, Any]]:
    return list(
        db[ASSIGNMENTS_COLLECTION].find(
            {
                "cluster_type": cluster_type.value,
                "status": {"$in": ["active", "ACTIVE"]},
            }
        )
    )


def run_adaptive_control_cycle() -> Dict[str, Any]:
    """
    Analyze clusters, persist alerts, notify users, optionally auto-migrate.
    """
    db = get_database()
    if not settings.GCP_SERVICE_ACCOUNT_JSON_PATH and not settings.DEMO_MODE:
        return {
            "skipped": True,
            "reason": "gcp_not_configured",
            "alerts": [],
            "migrations_attempted": 0,
        }

    auto_migrate = bool(getattr(settings, "VM_AUTO_MIGRATE_ENABLED", False))
    min_score = int(getattr(settings, "VM_AUTO_MIGRATE_MIN_SCORE", 85))
    latest = _latest_metrics_by_vm(db)
    now = datetime.utcnow()

    all_alerts: List[Dict[str, Any]] = []
    migrations_attempted = 0
    migrations_applied = 0
    recommendations_total = 0

    clusters = list(cluster_types())
    for cluster_type in clusters:
        vm_names = vm_provider.cluster_vms("GCP", cluster_type)
        vm_metrics: List[VMMetricsResponse] = []
        assignments = _active_assignments(db, cluster_type)

        for vm_name in vm_names:
            doc = latest.get(vm_name)
            if not doc:
                continue
            active_users = sum(1 for a in assignments if a.get("vm_name") == vm_name)
            vm_metrics.append(
                _doc_to_metrics_response(vm_name, cluster_type, doc, active_users)
            )

        if len(vm_metrics) < 2:
            continue

        avg_cpu = sum(m.cpu_usage for m in vm_metrics) / len(vm_metrics)
        if avg_cpu > 80:
            alert = {
                "severity": "HIGH",
                "cluster": cluster_type.value,
                "message": f"Cluster average CPU {avg_cpu:.1f}%",
                "recommendation": "Review migration recommendations or start another VM",
                "detected_at": now,
            }
            all_alerts.append(alert)
            db[ALERTS_COLLECTION].insert_one(alert)

        recs = MigrationRecommender.generate_recommendations(
            cluster_type, vm_metrics, assignments
        )
        recommendations_total += len(recs)

        for rec in sorted(recs, key=lambda r: r.score, reverse=True)[:10]:
            action_doc = {
                "recommendation_id": rec.recommendation_id,
                "action": rec.action,
                "user_id": rec.user_id,
                "source_vm": rec.source_vm,
                "target_vm": rec.target_vm,
                "score": rec.score,
                "confidence": rec.confidence,
                "status": "pending",
                "auto_eligible": rec.score >= min_score and rec.action == "migrate_user",
                "created_at": now,
            }
            db[ACTIONS_COLLECTION].insert_one(action_doc)

            if (
                auto_migrate
                and rec.action == "migrate_user"
                and rec.user_id
                and rec.score >= min_score
            ):
                migrations_attempted += 1
                try:
                    result = migrate_user(
                        rec.user_id,
                        target_vm_name=rec.target_vm,
                    )
                    if result.get("success", True):
                        migrations_applied += 1
                        db[ACTIONS_COLLECTION].update_one(
                            {"recommendation_id": rec.recommendation_id},
                            {"$set": {"status": "applied", "applied_at": now, "result": result}},
                        )
                        notification_service.create_notification(
                            rec.user_id,
                            title="Workload moved for performance",
                            message=(
                                f"Zenith moved your session from {rec.source_vm} to "
                                f"{rec.target_vm} due to high load (score {rec.score})."
                            ),
                            type="vm_agent",
                            link="/dashboard/vm",
                        )
                except Exception as exc:
                    logger.warning(
                        "Auto-migrate failed for %s: %s", rec.user_id, exc
                    )
                    db[ACTIONS_COLLECTION].update_one(
                        {"recommendation_id": rec.recommendation_id},
                        {"$set": {"status": "failed", "error": str(exc)[:200]}},
                    )
            elif rec.user_id and rec.score >= 50:
                notification_service.create_notification(
                    rec.user_id,
                    title="VM optimization suggestion",
                    message=(
                        f"Consider moving from {rec.source_vm} to {rec.target_vm} "
                        f"(confidence {rec.confidence}%)."
                    ),
                    type="vm_recommendation",
                    link="/dashboard/vm",
                )

    return {
        "skipped": False,
        "auto_migrate_enabled": auto_migrate,
        "alerts": all_alerts,
        "recommendations_generated": recommendations_total,
        "migrations_attempted": migrations_attempted,
        "migrations_applied": migrations_applied,
        "timestamp": now.isoformat(),
    }
