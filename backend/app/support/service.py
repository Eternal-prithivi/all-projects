"""Support ticket business logic."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import HTTPException, status

from app.contact.email_templates import subject_label
from app.support import repository as repo
from app.support.constants import (
    MESSAGE_MAX_LENGTH,
    OTP_EXPIRE_MINUTES,
    OTP_MAX_ATTEMPTS,
)
from app.users.user_model import UserInDB

OTP_COLLECTION = repo.OTP_COLLECTION  # noqa: F401 — re-export for tests


def _hash_otp(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _now() -> datetime:
    return datetime.utcnow()


def user_owns_ticket(ticket: Dict[str, Any], user: UserInDB) -> bool:
    email = _normalize_email(user.email or "")
    return ticket.get("user_id") == user.username or ticket.get(
        "requester_email"
    ) == email


def create_ticket_from_contact(
    *,
    name: str,
    email: str,
    subject: str,
    message: str,
    user_id: Optional[str] = None,
    legacy_submission_id: Optional[ObjectId] = None,
) -> Dict[str, Any]:
    if len(message) > MESSAGE_MAX_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Message must be at most {MESSAGE_MAX_LENGTH} characters",
        )
    now = _now()
    category = subject
    ticket_doc = {
        "status": "open",
        "category": category,
        "subject": subject_label(category),
        "requester_name": name.strip(),
        "requester_email": _normalize_email(email),
        "user_id": user_id,
        "assigned_to": None,
        "created_at": now,
        "updated_at": now,
        "last_message_at": now,
        "resolved_at": None,
    }
    if legacy_submission_id:
        ticket_doc["legacy_submission_id"] = legacy_submission_id

    ticket_id = repo.insert_ticket(ticket_doc)
    ticket = repo.find_ticket_by_id(ticket_id)
    assert ticket is not None

    repo.insert_message(
        {
            "ticket_id": ticket_id,
            "author_type": "customer",
            "author_id": user_id or "guest",
            "author_name": name.strip(),
            "body": message.strip(),
            "created_at": now,
            "email_sent": False,
        }
    )
    return ticket


def get_ticket_detail_for_user(
    reference_code: str, user: UserInDB
) -> Dict[str, Any]:
    ticket = repo.find_ticket_by_reference(reference_code)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if not user_owns_ticket(ticket, user):
        raise HTTPException(status_code=403, detail="Access denied")
    messages = repo.get_messages(ticket["_id"])
    return {
        "ticket": repo.serialize_ticket(ticket),
        "messages": [repo.serialize_message(m) for m in messages],
    }


def add_customer_message(
    reference_code: str,
    *,
    body: str,
    author_name: str,
    author_id: str,
    ticket: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if len(body) > MESSAGE_MAX_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Message must be at most {MESSAGE_MAX_LENGTH} characters",
        )
    if ticket is None:
        ticket = repo.find_ticket_by_reference(reference_code)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.get("status") in ("closed",):
        raise HTTPException(status_code=400, detail="Ticket is closed")

    now = _now()
    repo.insert_message(
        {
            "ticket_id": ticket["_id"],
            "author_type": "customer",
            "author_id": author_id,
            "author_name": author_name,
            "body": body.strip(),
            "created_at": now,
            "email_sent": False,
        }
    )
    repo.update_ticket(
        ticket["_id"],
        {
            "status": "open",
            "updated_at": now,
            "last_message_at": now,
        },
    )
    return repo.find_ticket_by_id(ticket["_id"])  # type: ignore[return-value]


def request_guest_otp(reference_code: str, email: str) -> str:
    ref = reference_code.upper().strip()
    email_norm = _normalize_email(email)
    ticket = repo.find_ticket_by_reference(ref)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if ticket.get("requester_email") != email_norm:
        raise HTTPException(
            status_code=404,
            detail="No ticket found for this email and reference",
        )

    otp = f"{secrets.randbelow(1_000_000):06d}"
    now = _now()
    repo.upsert_otp(
        {
            "reference_code": ref,
            "email": email_norm,
            "otp_hash": _hash_otp(otp),
            "expires_at": now + timedelta(minutes=OTP_EXPIRE_MINUTES),
            "attempts": 0,
            "created_at": now,
        }
    )
    return otp


def verify_guest_otp(reference_code: str, email: str, code: str) -> Dict[str, Any]:
    ref = reference_code.upper().strip()
    email_norm = _normalize_email(email)
    record = repo.find_otp(ref, email_norm)
    if not record:
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    if record.get("expires_at") and record["expires_at"] < _now():
        repo.delete_otp(ref, email_norm)
        raise HTTPException(status_code=400, detail="Code expired")

    attempts = int(record.get("attempts", 0))
    if attempts >= OTP_MAX_ATTEMPTS:
        repo.delete_otp(ref, email_norm)
        raise HTTPException(status_code=400, detail="Too many attempts")

    if _hash_otp(code.strip()) != record.get("otp_hash"):
        repo.upsert_otp({**record, "attempts": attempts + 1})
        raise HTTPException(status_code=400, detail="Invalid code")

    repo.delete_otp(ref, email_norm)
    ticket = repo.find_ticket_by_reference(ref)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    from app.support.guest_auth import create_guest_ticket_token

    token = create_guest_ticket_token(reference_code=ref, email=email_norm)
    detail = get_ticket_detail_guest(ticket)
    return {"guest_token": token, **detail}


def get_ticket_detail_guest(ticket: Dict[str, Any]) -> Dict[str, Any]:
    messages = repo.get_messages(ticket["_id"])
    return {
        "ticket": repo.serialize_ticket(ticket),
        "messages": [repo.serialize_message(m) for m in messages],
    }


def add_agent_message(
    ticket_id: str,
    *,
    body: str,
    agent_username: str,
    agent_name: str,
) -> Dict[str, Any]:
    ticket = repo.find_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    if len(body) > MESSAGE_MAX_LENGTH:
        raise HTTPException(status_code=400, detail="Message too long")

    now = _now()
    repo.insert_message(
        {
            "ticket_id": ticket["_id"],
            "author_type": "agent",
            "author_id": agent_username,
            "author_name": agent_name,
            "body": body.strip(),
            "created_at": now,
            "email_sent": True,
        }
    )
    repo.update_ticket(
        ticket["_id"],
        {
            "status": "waiting_on_customer",
            "updated_at": now,
            "last_message_at": now,
            "assigned_to": agent_username,
        },
    )
    updated = repo.find_ticket_by_id(ticket["_id"])
    assert updated is not None
    return updated


def update_ticket_status(
    ticket_id: str, new_status: str, *, agent_username: str
) -> Dict[str, Any]:
    from app.support.constants import TICKET_STATUSES

    if new_status not in TICKET_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")

    ticket = repo.find_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    now = _now()
    fields: Dict[str, Any] = {
        "status": new_status,
        "updated_at": now,
        "assigned_to": agent_username,
    }
    if new_status in ("resolved", "closed"):
        fields["resolved_at"] = now

    repo.update_ticket(ticket["_id"], fields)
    updated = repo.find_ticket_by_id(ticket["_id"])
    assert updated is not None
    return updated


def list_user_tickets(user: UserInDB) -> List[Dict[str, Any]]:
    items = repo.list_tickets_for_user(
        email=user.email or "",
        username=user.username,
    )
    return [repo.serialize_ticket(t) for t in items]


def ticket_to_email_submission(ticket: Dict[str, Any], message_body: str) -> Dict[str, Any]:
    """Shape ticket for existing email template helpers."""
    return {
        "name": ticket.get("requester_name", ""),
        "email": ticket.get("requester_email", ""),
        "subject": ticket.get("category", "general"),
        "message": message_body,
        "timestamp": ticket.get("created_at") or _now(),
        "submission_id": str(ticket["_id"]),
        "reference_code": ticket.get("reference_code"),
    }
