"""Team-level recommendations and action items."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from bson import ObjectId

from app.database.mongo_client import get_database
from app.organizations import service as org_service

DB = get_database()
ACTION_ITEMS = "organization_action_items"
INVITES = "organization_invites"
SNAPSHOTS = "dashboard_cost_snapshots"
ANOMALIES = "cost_anomalies"


def _is_admin(role: str) -> bool:
    return role in ("owner", "admin")


def _stale_cost_members(usernames: List[str], days: int = 7) -> List[str]:
    cutoff = (datetime.utcnow() - timedelta(days=days)).date().isoformat()
    stale = []
    for username in usernames:
        recent = DB[SNAPSHOTS].find_one(
            {"username": username, "date": {"$gte": cutoff}},
            {"_id": 1},
        )
        if not recent:
            stale.append(username)
    return stale


def _expiring_invites(org_id: str) -> List[Dict[str, Any]]:
    soon = datetime.utcnow() + timedelta(hours=48)
    return list(
        DB[INVITES].find(
            {
                "org_id": org_id,
                "accepted_at": None,
                "expires_at": {"$lte": soon, "$gt": datetime.utcnow()},
            }
        )
    )


def _anomaly_items(usernames: List[str]) -> List[Dict[str, Any]]:
    items = []
    cursor = DB[ANOMALIES].find(
        {"acknowledged": False, "username": {"$in": usernames}},
        limit=50,
    ).sort("detected_at", -1)
    for doc in cursor:
        items.append(
            {
                "id": f"anomaly-{doc.get('_id')}",
                "type": "cost_anomaly",
                "severity": doc.get("severity", "warning"),
                "message": (
                    f"Unacknowledged {doc.get('severity', 'cost')} anomaly on "
                    f"{doc.get('provider', 'cloud')} (${float(doc.get('cost', 0)):.2f})"
                ),
                "username": doc.get("username"),
                "action_path": "/dashboard/costs",
            }
        )
    return items


def get_recommendations(username: str) -> Dict[str, Any]:
    from fastapi import HTTPException

    m = org_service.get_membership(username)
    if not m:
        raise HTTPException(status_code=404, detail="You are not in an organization")

    org_id = m["org_id"]
    role = m.get("role")
    members = org_service.list_org_members(org_id)
    usernames = [x["username"] for x in members]

    items: List[Dict[str, Any]] = []

    for u in _stale_cost_members(usernames):
        if not _is_admin(role) and u != username:
            continue
        items.append(
            {
                "id": f"stale-cost-{u}",
                "type": "stale_cost_data",
                "severity": "warning",
                "message": f"No recent cost refresh for {u} — open Overview and click Refresh.",
                "username": u,
                "action_path": "/dashboard",
            }
        )

    if _is_admin(role):
        for inv in _expiring_invites(org_id):
            items.append(
                {
                    "id": f"invite-exp-{inv.get('email')}",
                    "type": "invite_expiring",
                    "severity": "normal",
                    "message": f"Invite for {inv.get('email')} expires soon.",
                    "username": None,
                    "action_path": "/dashboard/team",
                }
            )

    items.extend(_anomaly_items(usernames if _is_admin(role) else [username]))

    stored = list(
        DB[ACTION_ITEMS].find({"org_id": org_id, "status": {"$ne": "done"}}).sort("created_at", -1)
    )
    for doc in stored:
        if not _is_admin(role) and doc.get("username") != username and doc.get("assigned_to") != username:
            continue
        items.append(
            {
                "id": str(doc["_id"]),
                "type": doc.get("type", "action_item"),
                "severity": doc.get("severity", "normal"),
                "message": doc.get("message", ""),
                "username": doc.get("username"),
                "assigned_to": doc.get("assigned_to"),
                "action_path": doc.get("action_path", "/dashboard/team"),
            }
        )

    return {"items": items, "total": len(items)}


def get_recommendations_safe(username: str) -> Dict[str, Any]:
    return get_recommendations(username)


def assign_action_item(
    org_id: str,
    item_id: str,
    assigned_to: str,
    *,
    actor: str,
) -> Dict[str, Any]:
    org_service.require_membership(actor, min_role="admin")
    member_usernames = {m["username"] for m in org_service.list_org_members(org_id)}
    if assigned_to not in member_usernames:
        raise ValueError("assignee must be an org member")

    if item_id.startswith("anomaly-") or item_id.startswith("stale-cost-") or item_id.startswith("invite-exp-"):
        doc = {
            "org_id": org_id,
            "type": "assigned_recommendation",
            "source_id": item_id,
            "message": f"Assigned recommendation {item_id} to {assigned_to}",
            "username": None,
            "assigned_to": assigned_to,
            "assigned_by": actor,
            "status": "open",
            "action_path": "/dashboard/team",
            "severity": "normal",
            "created_at": datetime.utcnow(),
        }
        result = DB[ACTION_ITEMS].insert_one(doc)
        return {"id": str(result.inserted_id), "assigned_to": assigned_to}

    try:
        oid = ObjectId(item_id)
    except Exception as exc:
        raise ValueError("Invalid action item id") from exc

    result = DB[ACTION_ITEMS].update_one(
        {"_id": oid, "org_id": org_id},
        {"$set": {"assigned_to": assigned_to, "assigned_by": actor, "updated_at": datetime.utcnow()}},
    )
    if result.matched_count == 0:
        raise ValueError("Action item not found")
    return {"id": item_id, "assigned_to": assigned_to}
