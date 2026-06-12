"""Single-org-per-user team management with cloud health rollups."""

import secrets
from datetime import datetime, timedelta
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from app.auth.auth_utils import get_current_user
from app.contact.email_service import email_service
from app.database.mongo_client import get_database
from app.organizations import approvals, billing as org_billing, recommendations, resource_acl, service
from app.organizations import routes_billing
from app.users.user_model import UserInDB
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter(prefix="/organizations", tags=["Organizations"])
router.include_router(routes_billing.router)

DB = get_database()
ORGS = "organizations"
MEMBERS = "organization_members"
INVITES = "organization_invites"

VALID_ROLES = {"owner", "admin", "member"}


class CreateOrgBody(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)


class InviteBody(BaseModel):
    email: EmailStr
    role: str = Field(default="member")


class UpdateMemberRoleBody(BaseModel):
    role: str


class TransferOwnershipBody(BaseModel):
    new_owner_username: str


class OrgSettingsBody(BaseModel):
    monthly_budget_usd: Optional[float] = Field(default=None, ge=0)
    budget_alert_threshold: Optional[float] = Field(default=None, ge=1, le=100)
    approval_threshold_usd: Optional[float] = Field(default=None, ge=0)


class ApprovalReviewBody(BaseModel):
    status: str = Field(..., pattern="^(approved|denied)$")


class AssignActionBody(BaseModel):
    assigned_to: str


def _slugify(name: str) -> str:
    base = "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-")
    return base[:48] or "org"


@router.post("")
def create_organization(
    body: CreateOrgBody,
    current_user: UserInDB = Depends(get_current_user),
):
    if service.get_membership(current_user.username):
        raise HTTPException(status_code=400, detail="Leave your current organization first")

    slug = _slugify(body.name)
    if DB[ORGS].find_one({"slug": slug}):
        slug = f"{slug}-{secrets.token_hex(3)}"

    org = {
        "name": body.name.strip(),
        "slug": slug,
        "owner_username": current_user.username,
        "created_at": datetime.utcnow(),
        **org_billing._default_billing_fields(current_user.username, 1),
    }
    result = DB[ORGS].insert_one(org)
    org_id = str(result.inserted_id)

    DB[MEMBERS].insert_one(
        {
            "org_id": org_id,
            "username": current_user.username,
            "role": "owner",
            "joined_at": datetime.utcnow(),
        }
    )
    return {"org_id": org_id, "name": org["name"], "slug": slug, "role": "owner"}


@router.get("/me")
def get_my_organization(current_user: UserInDB = Depends(get_current_user)):
    m = service.get_membership(current_user.username)
    if not m:
        return {"organization": None, "members": [], "pending_invites": []}

    org = service.get_org_doc(m["org_id"])
    if not org:
        return {"organization": None, "members": [], "pending_invites": []}

    members = service.list_org_members(m["org_id"])
    invites = []
    if m.get("role") in ("owner", "admin"):
        invites = list(
            DB[INVITES].find(
                {
                    "org_id": m["org_id"],
                    "accepted_at": None,
                    "expires_at": {"$gt": datetime.utcnow()},
                }
            )
        )

    return {
        "organization": {
            "id": m["org_id"],
            "name": org.get("name"),
            "slug": org.get("slug"),
            "owner_username": org.get("owner_username"),
        },
        "my_role": m.get("role"),
        "members": [
            {
                "username": x["username"],
                "role": x.get("role"),
                "joined_at": x.get("joined_at").isoformat() + "Z" if x.get("joined_at") else None,
            }
            for x in members
        ],
        "pending_invites": [
            {
                "email": i.get("email"),
                "role": i.get("role"),
                "expires_at": i.get("expires_at").isoformat() + "Z" if i.get("expires_at") else None,
            }
            for i in invites
        ],
    }


@router.get("/summary")
def get_organization_summary(current_user: UserInDB = Depends(get_current_user)):
    return service.get_org_summary(current_user.username)


@router.get("/recommendations")
def get_organization_recommendations(current_user: UserInDB = Depends(get_current_user)):
    return recommendations.get_recommendations_safe(current_user.username)


@router.post("/recommendations/{item_id}/assign")
def assign_recommendation(
    item_id: str,
    body: AssignActionBody,
    current_user: UserInDB = Depends(get_current_user),
):
    m = service.require_membership(current_user.username, min_role="admin")
    try:
        return recommendations.assign_action_item(
            m["org_id"],
            item_id,
            body.assigned_to,
            actor=current_user.username,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/approvals")
def list_organization_approvals(
    status: Optional[str] = None,
    current_user: UserInDB = Depends(get_current_user),
):
    return approvals.list_approvals(current_user.username, status=status)


@router.patch("/approvals/{approval_id}")
def review_organization_approval(
    approval_id: str,
    body: ApprovalReviewBody,
    current_user: UserInDB = Depends(get_current_user),
):
    return approvals.review_approval(
        current_user.username,
        approval_id,
        status=body.status,
    )


@router.patch("/settings")
def update_organization_settings(
    body: OrgSettingsBody,
    current_user: UserInDB = Depends(get_current_user),
):
    m = service.require_membership(current_user.username, min_role="admin")
    updates = body.model_dump(exclude_unset=True)
    service.update_org_settings(m["org_id"], updates)
    org = service.get_org_doc(m["org_id"]) or {}
    return {
        "success": True,
        "monthly_budget_usd": org.get("monthly_budget_usd"),
        "budget_alert_threshold": org.get("budget_alert_threshold", 80),
        "approval_threshold_usd": org.get("approval_threshold_usd"),
    }


@router.post("/invites")
def invite_member(
    body: InviteBody,
    current_user: UserInDB = Depends(get_current_user),
):
    m = service.require_membership(current_user.username, min_role="admin")
    if body.role not in VALID_ROLES or body.role == "owner":
        raise HTTPException(status_code=400, detail="Invalid invite role")

    # v1: pending invites do not reserve seats; accept is guarded in assert_seats_available.
    token = secrets.token_urlsafe(32)
    DB[INVITES].insert_one(
        {
            "org_id": m["org_id"],
            "email": body.email.lower(),
            "role": body.role,
            "token": token,
            "created_by": current_user.username,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=7),
            "accepted_at": None,
        }
    )

    org = service.get_org_doc(m["org_id"]) or {}
    try:
        email_service.send_org_invite(
            to_email=str(body.email),
            org_name=org.get("name", "Organization"),
            invite_token=token,
            role=body.role,
            invited_by=current_user.username,
        )
    except Exception as email_err:
        logger.warning("Org invite email failed (non-critical): %s", email_err)

    return {
        "success": True,
        "invite_link": f"/invite/{token}",
        "message": f"Invite created for {body.email}",
        "email_sent": bool(email_service.sender_email),
    }


@router.get("/invites/{token}")
def preview_invite(token: str):
    invite = DB[INVITES].find_one({"token": token, "accepted_at": None})
    if not invite or invite.get("expires_at") < datetime.utcnow():
        raise HTTPException(status_code=404, detail="Invite not found or expired")
    org = service.get_org_doc(invite["org_id"])
    return {
        "org_name": org.get("name") if org else "Organization",
        "email": invite.get("email"),
        "role": invite.get("role"),
    }


@router.post("/invites/{token}/accept")
def accept_invite(token: str, current_user: UserInDB = Depends(get_current_user)):
    invite = DB[INVITES].find_one({"token": token, "accepted_at": None})
    if not invite or invite.get("expires_at") < datetime.utcnow():
        raise HTTPException(status_code=404, detail="Invite not found or expired")

    if current_user.email.lower() != invite.get("email", "").lower():
        raise HTTPException(
            status_code=403,
            detail="This invite was sent to a different email address",
        )
    if service.get_membership(current_user.username):
        raise HTTPException(status_code=400, detail="You are already in an organization")

    org_billing.assert_seats_available(invite["org_id"])

    DB[MEMBERS].insert_one(
        {
            "org_id": invite["org_id"],
            "username": current_user.username,
            "role": invite.get("role", "member"),
            "joined_at": datetime.utcnow(),
        }
    )
    DB[INVITES].update_one(
        {"_id": invite["_id"]},
        {"$set": {"accepted_at": datetime.utcnow(), "accepted_by": current_user.username}},
    )
    DB["users"].update_one(
        {"username": current_user.username},
        {"$set": {"onboarding_team": True, "onboarding_team_at": datetime.utcnow()}},
    )
    service.invalidate_org_cache(invite["org_id"])
    return {"success": True, "org_id": invite["org_id"]}


@router.delete("/invites/{email}")
def revoke_invite(
    email: str,
    current_user: UserInDB = Depends(get_current_user),
):
    m = service.require_membership(current_user.username, min_role="admin")
    normalized = email.strip().lower()
    result = DB[INVITES].delete_one(
        {
            "org_id": m["org_id"],
            "email": normalized,
            "accepted_at": None,
        }
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Pending invite not found")
    return {"success": True, "email": normalized}


@router.patch("/members/{username}/role")
def update_member_role(
    username: str,
    body: UpdateMemberRoleBody,
    current_user: UserInDB = Depends(get_current_user),
):
    m = service.require_membership(current_user.username, min_role="owner")
    if body.role not in ("admin", "member"):
        raise HTTPException(status_code=400, detail="Role must be admin or member")

    target = DB[MEMBERS].find_one({"org_id": m["org_id"], "username": username})
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")
    if target.get("role") == "owner":
        raise HTTPException(status_code=400, detail="Cannot change owner role here — use transfer ownership")

    DB[MEMBERS].update_one(
        {"org_id": m["org_id"], "username": username},
        {"$set": {"role": body.role, "updated_at": datetime.utcnow()}},
    )
    service.invalidate_org_cache(m["org_id"])
    return {"success": True, "username": username, "role": body.role}


@router.post("/transfer-ownership")
def transfer_ownership(
    body: TransferOwnershipBody,
    current_user: UserInDB = Depends(get_current_user),
):
    m = service.require_membership(current_user.username, min_role="owner")
    new_owner = body.new_owner_username.strip()
    if new_owner == current_user.username:
        raise HTTPException(status_code=400, detail="Already the owner")

    target = DB[MEMBERS].find_one({"org_id": m["org_id"], "username": new_owner})
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")

    DB[MEMBERS].update_one(
        {"org_id": m["org_id"], "username": current_user.username},
        {"$set": {"role": "admin", "updated_at": datetime.utcnow()}},
    )
    DB[MEMBERS].update_one(
        {"org_id": m["org_id"], "username": new_owner},
        {"$set": {"role": "owner", "updated_at": datetime.utcnow()}},
    )
    DB[ORGS].update_one(
        {"_id": ObjectId(m["org_id"])},
        {"$set": {"owner_username": new_owner, "updated_at": datetime.utcnow()}},
    )
    service.invalidate_org_cache(m["org_id"])
    return {"success": True, "owner_username": new_owner}


@router.get("/members/cloud-status", summary="Per-member BYOC readiness (admin/owner)")
def get_members_cloud_status(current_user: UserInDB = Depends(get_current_user)):
    from app.organizations.cloud_health import org_members_cloud_status

    m = service.require_membership(current_user.username, min_role="admin")
    members = service.list_org_members(m["org_id"])
    usernames = [x["username"] for x in members]
    return {
        "org_id": m["org_id"],
        "members": org_members_cloud_status(usernames),
    }


@router.get("/resources/summary")
def get_resources_summary(current_user: UserInDB = Depends(get_current_user)):
    m = service.require_membership(current_user.username)
    from app.organizations.limits import count_org_storage_bytes, count_org_vms

    org_id = m["org_id"]
    org = service.get_org_doc(org_id) or {}
    return {
        "org_id": org_id,
        "org_name": org.get("name"),
        "total_vms": count_org_vms(org_id),
        "total_storage_gb": round(count_org_storage_bytes(org_id) / (1024**3), 2),
        "my_role": m.get("role"),
    }


class ReassignResourceBody(BaseModel):
    resource_type: str = Field(..., pattern="^(vm_assignment|provision|file)$")
    resource_id: str
    new_owner: str


@router.patch("/resources/reassign")
def reassign_resource(
    body: ReassignResourceBody,
    current_user: UserInDB = Depends(get_current_user),
):
    m = service.require_membership(current_user.username, min_role="admin")
    org_id = m["org_id"]
    members = {x["username"] for x in service.list_org_members(org_id)}
    if body.new_owner not in members:
        raise HTTPException(status_code=400, detail="new_owner must be an org member")

    col_map = {
        "vm_assignment": ("vm_assignments", "assignment_id"),
        "provision": ("provision_deployments", "deployment_name"),
        "file": ("files", "filename"),
    }
    col_name, id_field = col_map[body.resource_type]
    result = DB[col_name].update_one(
        {"org_id": org_id, id_field: body.resource_id},
        {"$set": {"created_by": body.new_owner, "reassigned_at": datetime.utcnow()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Resource not found")
    DB["activity_log"].insert_one(
        {
            "username": current_user.username,
            "action": "Org resource reassigned",
            "description": f"{body.resource_type}:{body.resource_id} -> {body.new_owner}",
            "timestamp": datetime.utcnow(),
        }
    )
    return {"success": True}


@router.delete("/members/{username}")
def remove_member(
    username: str,
    current_user: UserInDB = Depends(get_current_user),
):
    m = service.require_membership(current_user.username, min_role="admin")
    target = DB[MEMBERS].find_one({"org_id": m["org_id"], "username": username})
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")
    if target.get("role") == "owner":
        raise HTTPException(status_code=400, detail="Cannot remove organization owner")

    counts = resource_acl.count_member_resources(m["org_id"], username)
    if counts["vms"] > 0 or counts["files"] > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Member still has {counts['vms']} VM(s) and {counts['files']} file(s). Reassign or delete first.",
        )

    DB[MEMBERS].delete_one({"org_id": m["org_id"], "username": username})
    service.invalidate_org_cache(m["org_id"])
    return {"success": True}


@router.post("/leave")
def leave_organization(current_user: UserInDB = Depends(get_current_user)):
    m = service.get_membership(current_user.username)
    if not m:
        raise HTTPException(status_code=404, detail="Not in an organization")
    if m.get("role") == "owner":
        count = DB[MEMBERS].count_documents({"org_id": m["org_id"]})
        if count > 1:
            raise HTTPException(
                status_code=400,
                detail="Transfer ownership or remove members before leaving",
            )
        DB[ORGS].delete_one({"_id": ObjectId(m["org_id"])})
        DB[INVITES].delete_many({"org_id": m["org_id"]})
    org_id = m["org_id"]
    DB[MEMBERS].delete_one({"username": current_user.username})
    service.invalidate_org_cache(org_id)
    return {"success": True}
