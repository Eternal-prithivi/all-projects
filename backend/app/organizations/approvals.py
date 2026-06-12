"""Organization approval requests for high-cost provisions."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from bson import ObjectId
from fastapi import HTTPException

from app.database.mongo_client import get_database
from app.notifications import service as notification_service
from app.organizations import service as org_service

DB = get_database()
APPROVALS = "organization_approval_requests"


def _parse_estimated_cost(cost_estimate: Any) -> float:
    if hasattr(cost_estimate, "total_monthly_cost"):
        raw = cost_estimate.total_monthly_cost
    elif isinstance(cost_estimate, dict):
        raw = cost_estimate.get("total_monthly_cost") or cost_estimate.get("total_monthly")
    else:
        raw = 0
    try:
        return float(raw or 0)
    except (TypeError, ValueError):
        return 0.0


def get_approval_threshold(org: Dict[str, Any]) -> Optional[float]:
    raw = org.get("approval_threshold_usd")
    if raw is None:
        return None
    try:
        val = float(raw)
        return val if val > 0 else None
    except (TypeError, ValueError):
        return None


def maybe_gate_provision(username: str, cost_estimate: Any, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    If user's org requires approval for estimated cost, create a pending request.
    Returns dict with approval_id when gated; None to proceed.
    """
    m = org_service.get_membership(username)
    if not m:
        return None
    if m.get("role") in ("owner", "admin"):
        return None

    org = org_service.get_org_doc(m["org_id"])
    if not org:
        return None

    threshold = get_approval_threshold(org)
    if threshold is None:
        return None

    estimated = _parse_estimated_cost(cost_estimate)
    if estimated < threshold:
        return None

    doc = {
        "org_id": m["org_id"],
        "requester": username,
        "type": "vm_provision",
        "payload": payload,
        "estimated_monthly_usd": estimated,
        "status": "pending",
        "reviewed_by": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    result = DB[APPROVALS].insert_one(doc)
    approval_id = str(result.inserted_id)

    for admin in org_service.list_org_members(m["org_id"]):
        if admin.get("role") in ("owner", "admin"):
            notification_service.create_notification(
                admin["username"],
                title="Provision approval needed",
                message=f"{username} requested provisioning estimated at ${estimated:.2f}/mo",
                type="warning",
                link="/dashboard/team",
                metadata={"approval_id": approval_id},
            )

    return {
        "approval_required": True,
        "approval_id": approval_id,
        "estimated_monthly_usd": estimated,
        "threshold_usd": threshold,
        "message": (
            f"This deployment is estimated at ${estimated:.2f}/mo, above your org "
            f"approval threshold of ${threshold:.2f}/mo. An admin must approve it."
        ),
    }


def list_approvals(username: str, *, status: Optional[str] = None) -> Dict[str, Any]:
    m = org_service.require_membership(username)
    org_id = m["org_id"]
    role = m.get("role")

    query: Dict[str, Any] = {"org_id": org_id}
    if status:
        query["status"] = status
    if role not in ("owner", "admin"):
        query["requester"] = username

    rows = list(DB[APPROVALS].find(query).sort("created_at", -1).limit(100))
    items = []
    for doc in rows:
        items.append(
            {
                "id": str(doc["_id"]),
                "requester": doc.get("requester"),
                "type": doc.get("type"),
                "estimated_monthly_usd": doc.get("estimated_monthly_usd"),
                "status": doc.get("status"),
                "reviewed_by": doc.get("reviewed_by"),
                "created_at": doc.get("created_at").isoformat() + "Z"
                if doc.get("created_at")
                else None,
                "payload_summary": (doc.get("payload") or {}).get("template")
                or (doc.get("payload") or {}).get("csp"),
            }
        )
    return {"approvals": items, "total": len(items)}


def review_approval(
    username: str,
    approval_id: str,
    *,
    status: str,
) -> Dict[str, Any]:
    org_service.require_membership(username, min_role="admin")
    if status not in ("approved", "denied"):
        raise HTTPException(status_code=400, detail="status must be approved or denied")

    try:
        oid = ObjectId(approval_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid approval id") from exc

    doc = DB[APPROVALS].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if doc.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Approval already reviewed")

    DB[APPROVALS].update_one(
        {"_id": oid},
        {
            "$set": {
                "status": status,
                "reviewed_by": username,
                "reviewed_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        },
    )

    requester = doc.get("requester")
    if requester:
        notification_service.create_notification(
            requester,
            title=f"Provision request {status}",
            message=f"Your provisioning request was {status} by {username}.",
            type="success" if status == "approved" else "warning",
            link="/dashboard/team",
            metadata={"approval_id": approval_id, "status": status},
        )

    return {"id": approval_id, "status": status}
