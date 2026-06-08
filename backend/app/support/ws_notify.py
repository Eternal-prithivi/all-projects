"""WebSocket notifications for support ticket events."""

from __future__ import annotations

import json
from typing import Any, Dict

from app.database.mongo_client import get_users_collection
from app.websockets.connection_manager import manager


def _ticket_id(ticket: Dict[str, Any]) -> str:
    oid = ticket.get("_id")
    return str(oid) if oid is not None else ""


async def notify_ticket_agent_reply(ticket: Dict[str, Any]) -> None:
    """Notify logged-in customer that support replied."""
    user_id = ticket.get("user_id")
    if not user_id:
        return
    payload = json.dumps(
        {
            "event": "support_reply",
            "reference_code": ticket.get("reference_code") or "",
            "ticket_id": _ticket_id(ticket),
        }
    )
    try:
        await manager.send_personal_message(payload, user_id)
    except Exception:
        pass


async def notify_ticket_customer_reply(ticket: Dict[str, Any]) -> None:
    """Notify connected admins that a customer replied on a ticket."""
    payload = json.dumps(
        {
            "event": "support_customer_reply",
            "reference_code": ticket.get("reference_code") or "",
            "ticket_id": _ticket_id(ticket),
        }
    )
    try:
        admins = get_users_collection().find({"role": "admin"}, {"username": 1})
        for admin in admins:
            username = admin.get("username")
            if username:
                await manager.send_personal_message(payload, username)
    except Exception:
        pass
