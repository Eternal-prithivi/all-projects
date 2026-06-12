"""Celery tasks for organization-level monitoring."""

from __future__ import annotations

import logging
from datetime import datetime

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="check_org_budget_alerts")
def check_org_budget_alerts():
    """Daily check: email org admins when team spend exceeds budget threshold."""
    from app.contact.email_service import email_service
    from app.database.mongo_client import get_database
    from app.organizations.service import build_org_summary, list_org_members

    DB = get_database()
    orgs = list(DB["organizations"].find({"monthly_budget_usd": {"$gt": 0}}))
    alerts_sent = 0

    for org in orgs:
        org_id = str(org["_id"])
        members = list_org_members(org_id)
        if not members:
            continue
        summary = build_org_summary(org_id, org, members)
        status = summary.get("budget_status")
        if status not in ("warning", "exceeded"):
            continue

        spend = summary["org_totals"]["monthly_spend_usd"]
        budget = summary.get("monthly_budget_usd")
        org_name = org.get("name", "Organization")

        admin_emails = []
        for m in members:
            if m.get("role") in ("owner", "admin"):
                user = DB["users"].find_one({"username": m["username"]}, {"email": 1})
                if user and user.get("email"):
                    admin_emails.append((m["username"], user["email"]))

        for _username, email in admin_emails:
            try:
                email_service.send_org_budget_alert(
                    to_email=email,
                    org_name=org_name,
                    spend_usd=spend,
                    budget_usd=float(budget),
                    status=status,
                )
                alerts_sent += 1
            except Exception as exc:
                logger.warning("Org budget alert failed for %s: %s", email, exc)

    return {"orgs_checked": len(orgs), "alerts_sent": alerts_sent, "at": datetime.utcnow().isoformat()}
