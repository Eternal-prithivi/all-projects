"""Single-org-per-user team management (enterprise MVP)."""

import secrets
from datetime import datetime, timedelta
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from app.auth.auth_utils import get_current_user
from app.database.mongo_client import get_database
from app.users.user_model import UserInDB

router = APIRouter(prefix="/organizations", tags=["Organizations"])

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


def _slugify(name: str) -> str:
    base = "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-")
    return base[:48] or "org"


def _member_org(username: str):
    return DB[MEMBERS].find_one({"username": username})


def _require_membership(username: str, min_role: Optional[str] = None):
    m = _member_org(username)
    if not m:
        raise HTTPException(status_code=404, detail="You are not in an organization")
    if min_role == "admin" and m.get("role") not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    if min_role == "owner" and m.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Owner access required")
    return m


@router.post("")
def create_organization(
    body: CreateOrgBody,
    current_user: UserInDB = Depends(get_current_user),
):
    if _member_org(current_user.username):
        raise HTTPException(status_code=400, detail="Leave your current organization first")

    slug = _slugify(body.name)
    if DB[ORGS].find_one({"slug": slug}):
        slug = f"{slug}-{secrets.token_hex(3)}"

    org = {
        "name": body.name.strip(),
        "slug": slug,
        "owner_username": current_user.username,
        "created_at": datetime.utcnow(),
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
    m = _member_org(current_user.username)
    if not m:
        return {"organization": None, "members": [], "pending_invites": []}

    org = DB[ORGS].find_one({"_id": ObjectId(m["org_id"])})
    if not org:
        return {"organization": None, "members": [], "pending_invites": []}

    members = list(DB[MEMBERS].find({"org_id": m["org_id"]}))
    invites = []
    if m.get("role") in ("owner", "admin"):
        invites = list(
            DB[INVITES].find(
                {"org_id": m["org_id"], "accepted_at": None, "expires_at": {"$gt": datetime.utcnow()}}
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


@router.post("/invites")
def invite_member(
    body: InviteBody,
    current_user: UserInDB = Depends(get_current_user),
):
    m = _require_membership(current_user.username, min_role="admin")
    if body.role not in VALID_ROLES or body.role == "owner":
        raise HTTPException(status_code=400, detail="Invalid invite role")

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
    return {
        "success": True,
        "invite_link": f"/invite/{token}",
        "message": f"Invite created for {body.email}",
    }


@router.get("/invites/{token}")
def preview_invite(token: str):
    invite = DB[INVITES].find_one({"token": token, "accepted_at": None})
    if not invite or invite.get("expires_at") < datetime.utcnow():
        raise HTTPException(status_code=404, detail="Invite not found or expired")
    org = DB[ORGS].find_one({"_id": ObjectId(invite["org_id"])})
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
    if _member_org(current_user.username):
        raise HTTPException(status_code=400, detail="You are already in an organization")

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
    return {"success": True, "org_id": invite["org_id"]}


@router.delete("/members/{username}")
def remove_member(
    username: str,
    current_user: UserInDB = Depends(get_current_user),
):
    m = _require_membership(current_user.username, min_role="admin")
    target = DB[MEMBERS].find_one({"org_id": m["org_id"], "username": username})
    if not target:
        raise HTTPException(status_code=404, detail="Member not found")
    if target.get("role") == "owner":
        raise HTTPException(status_code=400, detail="Cannot remove organization owner")
    if username == current_user.username and m.get("role") != "owner":
        pass  # allow self-leave via separate endpoint
    elif m.get("role") not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="Not allowed")

    DB[MEMBERS].delete_one({"org_id": m["org_id"], "username": username})
    return {"success": True}


@router.post("/leave")
def leave_organization(current_user: UserInDB = Depends(get_current_user)):
    m = _member_org(current_user.username)
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
    DB[MEMBERS].delete_one({"username": current_user.username})
    return {"success": True}
