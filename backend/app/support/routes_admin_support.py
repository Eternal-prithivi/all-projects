"""Admin support inbox routes."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.admin.routes_admin import verify_admin
from app.support import repository as repo
from app.support import service
from app.contact.email_service import email_service

router = APIRouter(prefix="/api/admin/support", tags=["Admin Support"])


class AdminMessageCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=8000)


class TicketStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(open|waiting_on_customer|resolved|closed)$")


@router.get("/tickets")
async def admin_list_tickets(
    status: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    admin_user=Depends(verify_admin),
):
    items, total = repo.list_tickets_admin(
        status=status,
        search=search,
        skip=skip,
        limit=min(limit, 100),
    )
    return {
        "tickets": [repo.serialize_ticket(t) for t in items],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/tickets/{ticket_id}")
async def admin_get_ticket(
    ticket_id: str,
    admin_user=Depends(verify_admin),
):
    ticket = repo.find_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    messages = repo.get_messages(ticket["_id"])
    return {
        "ticket": repo.serialize_ticket(ticket),
        "messages": [repo.serialize_message(m) for m in messages],
    }


@router.post("/tickets/{ticket_id}/messages")
async def admin_reply(
    ticket_id: str,
    payload: AdminMessageCreate,
    admin_user=Depends(verify_admin),
):
    agent_username = getattr(admin_user, "username", None) or (
        admin_user.get("username") if isinstance(admin_user, dict) else "admin"
    )
    agent_name = agent_username
    ticket = service.add_agent_message(
        ticket_id,
        body=payload.body,
        agent_username=agent_username,
        agent_name=agent_name,
    )
    try:
        email_service.send_agent_reply_email(ticket, payload.body)
    except Exception:
        pass

    try:
        from app.support.ws_notify import notify_ticket_agent_reply

        await notify_ticket_agent_reply(ticket)
    except Exception:
        pass

    messages = repo.get_messages(ticket["_id"])
    return {
        "ticket": repo.serialize_ticket(ticket),
        "messages": [repo.serialize_message(m) for m in messages],
    }


@router.patch("/tickets/{ticket_id}")
async def admin_update_status(
    ticket_id: str,
    payload: TicketStatusUpdate,
    admin_user=Depends(verify_admin),
):
    agent_username = getattr(admin_user, "username", None) or (
        admin_user.get("username") if isinstance(admin_user, dict) else "admin"
    )
    ticket = service.update_ticket_status(
        ticket_id,
        payload.status,
        agent_username=agent_username,
    )
    if payload.status in ("resolved", "closed"):
        try:
            email_service.send_ticket_resolved_email(ticket)
        except Exception:
            pass
    return {"ticket": repo.serialize_ticket(ticket)}
