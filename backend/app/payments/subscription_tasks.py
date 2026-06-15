"""Celery tasks for subscription lifecycle enforcement."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.celery_worker import celery_app
from app.database.mongo_client import get_database
from app.payments.subscription_service import set_user_subscription
from app.utils.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)
DB = get_database()


@celery_app.task(name="enforce_subscription_expiry")
def enforce_subscription_expiry_task():
    """Downgrade expired paid subscriptions to free tier."""
    now = datetime.utcnow()
    grace_days = int(getattr(settings, "SUBSCRIPTION_GRACE_DAYS", 3) or 3)
    cutoff = now - timedelta(days=grace_days)

    cursor = DB["subscriptions"].find(
        {
            "plan_id": {"$ne": "free"},
            "current_period_end": {"$lt": cutoff},
            "status": {"$in": ["active", "canceled", "past_due"]},
        }
    )
    downgraded = 0
    for sub in cursor:
        username = sub.get("user_id") or sub.get("username")
        if not username:
            continue
        set_user_subscription(username, "free", status="expired")
        downgraded += 1
        logger.info("Downgraded expired subscription for %s", username)

    return {"downgraded": downgraded, "checked_at": now.isoformat()}


@celery_app.task(name="teardown_inactive_free_provisions")
def teardown_inactive_free_provisions_task():
    """Archive free-tier platform deployments inactive for 7+ days."""
    from app.payments.subscription_service import get_effective_plan_id

    threshold = datetime.utcnow() - timedelta(days=7)
    archived = 0
    for dep in DB["provision_deployments"].find(
        {
            "status": {"$in": ["deployed", "awaiting_apply"]},
            "updated_at": {"$lt": threshold},
        }
    ):
        user_id = dep.get("user_id")
        if not user_id or get_effective_plan_id(user_id) != "free":
            continue
        DB["provision_deployments"].update_one(
            {"_id": dep["_id"]},
            {"$set": {"status": "archived", "archived_at": datetime.utcnow(), "archive_reason": "free_inactivity"}},
        )
        archived += 1
    return {"archived": archived}
