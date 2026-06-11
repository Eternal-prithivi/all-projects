"""User and guest support ticket routes."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.auth.auth_utils import get_current_user
from app.support import service
from app.support.guest_auth import get_guest_ticket_access
from app.users.user_model import UserInDB
from app.contact.email_service import email_service

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/api/support", tags=["Support"])


class GuestOtpRequest(BaseModel):
    reference_code: str = Field(..., min_length=4, max_length=32)
    email: EmailStr


class GuestOtpVerify(BaseModel):
    reference_code: str = Field(..., min_length=4, max_length=32)
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)


class MessageCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=8000)


class TicketCreate(BaseModel):
    subject: str = Field(default="general", max_length=64)
    category: str = Field(default="general", max_length=64)
    body: str = Field(..., min_length=1, max_length=8000)


@router.post("/tickets")
async def create_my_ticket(
    payload: TicketCreate,
    current_user: UserInDB = Depends(get_current_user),
):
    category = payload.category or payload.subject or "general"
    ticket = service.create_ticket_from_contact(
        name=current_user.username,
        email=current_user.email or f"{current_user.username}@users.local",
        subject=category,
        message=payload.body,
        user_id=current_user.username,
    )
    try:
        email_payload = service.ticket_to_email_submission(ticket, payload.body)
        email_service.send_contact_notification(email_payload)
    except Exception:
        pass
    return service.get_ticket_detail_for_user(
        ticket["reference_code"], current_user
    )


@router.get("/tickets")
def list_my_tickets(current_user: UserInDB = Depends(get_current_user)):
    tickets = service.list_user_tickets(current_user)
    return {"tickets": tickets, "total": len(tickets)}


@router.get("/tickets/{reference_code}")
def get_my_ticket(
    reference_code: str,
    current_user: UserInDB = Depends(get_current_user),
):
    return service.get_ticket_detail_for_user(reference_code, current_user)


@router.post("/tickets/{reference_code}/messages")
async def post_my_ticket_message(
    reference_code: str,
    payload: MessageCreate,
    current_user: UserInDB = Depends(get_current_user),
):
    service.get_ticket_detail_for_user(reference_code, current_user)
    from app.support import repository as repo

    raw_ticket = repo.find_ticket_by_reference(reference_code)
    service.add_customer_message(
        reference_code,
        body=payload.body,
        author_name=current_user.username,
        author_id=current_user.username,
        ticket=raw_ticket,
    )
    try:
        if raw_ticket:
            email_service.send_admin_customer_reply_notification(
                raw_ticket, payload.body
            )
    except Exception:
        pass
    if raw_ticket:
        from app.support.ws_notify import notify_ticket_customer_reply

        await notify_ticket_customer_reply(raw_ticket)
    return service.get_ticket_detail_for_user(reference_code, current_user)


@router.post("/guest/request-otp")
@limiter.limit("5/minute")
def guest_request_otp(request: Request, payload: GuestOtpRequest):
    otp = service.request_guest_otp(payload.reference_code, str(payload.email))
    try:
        email_service.send_ticket_otp_email(
            str(payload.email),
            payload.reference_code.upper().strip(),
            otp,
        )
    except Exception:
        pass
    return {
        "success": True,
        "message": "If the reference and email match our records, a verification code was sent.",
    }


@router.post("/guest/verify-otp")
@limiter.limit("10/minute")
def guest_verify_otp(request: Request, payload: GuestOtpVerify):
    return service.verify_guest_otp(
        payload.reference_code,
        str(payload.email),
        payload.code,
    )


@router.get("/guest/tickets/{reference_code}")
def guest_get_ticket(
    reference_code: str,
    guest: dict = Depends(get_guest_ticket_access),
):
    from app.support import repository as repo

    ticket = repo.find_ticket_by_reference(reference_code)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.get("requester_email") != guest.get("email"):
        raise HTTPException(status_code=403, detail="Access denied")
    return service.get_ticket_detail_guest(ticket)


@router.post("/guest/tickets/{reference_code}/messages")
async def guest_post_message(
    reference_code: str,
    payload: MessageCreate,
    guest: dict = Depends(get_guest_ticket_access),
):
    from app.support import repository as repo

    ticket = repo.find_ticket_by_reference(reference_code)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.get("requester_email") != guest.get("email"):
        raise HTTPException(status_code=403, detail="Access denied")

    name = ticket.get("requester_name") or "Guest"
    service.add_customer_message(
        reference_code,
        body=payload.body,
        author_name=name,
        author_id="guest",
        ticket=ticket,
    )
    try:
        email_service.send_admin_customer_reply_notification(ticket, payload.body)
    except Exception:
        pass
    from app.support.ws_notify import notify_ticket_customer_reply

    await notify_ticket_customer_reply(ticket)
    return service.get_ticket_detail_guest(
        repo.find_ticket_by_reference(reference_code)  # type: ignore[arg-type]
    )
