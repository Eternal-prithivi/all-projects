#!/usr/bin/env python3
"""Migrate legacy contact_submissions into support_tickets + support_messages."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime

from bson import ObjectId

from app.database.mongo_client import get_database
from app.support import repository as repo
from app.support import service as support_service


def migrate() -> None:
    db = get_database()
    repo.ensure_support_indexes()
    coll = db["contact_submissions"]
    migrated = 0
    skipped = 0

    for doc in coll.find({}):
        legacy_id = doc["_id"]
        if db["support_tickets"].find_one({"legacy_submission_id": legacy_id}):
            skipped += 1
            continue

        ref = doc.get("reference_code")
        if ref and db["support_tickets"].find_one({"reference_code": ref}):
            skipped += 1
            continue

        ts = doc.get("timestamp") or datetime.utcnow()
        status = "open"
        if doc.get("replied"):
            status = "waiting_on_customer"
        if doc.get("status") == "read":
            status = "waiting_on_customer"

        ticket_doc = {
            "status": status,
            "category": doc.get("subject", "general"),
            "subject": doc.get("subject", "general"),
            "requester_name": doc.get("name", "Unknown"),
            "requester_email": (doc.get("email") or "").strip().lower(),
            "user_id": None,
            "assigned_to": None,
            "created_at": ts,
            "updated_at": ts,
            "last_message_at": ts,
            "resolved_at": None,
            "legacy_submission_id": legacy_id,
        }
        if ref:
            ticket_doc["reference_code"] = ref.upper()

        ticket_id = db["support_tickets"].insert_one(ticket_doc).inserted_id
        if not ref:
            ref = repo.make_reference_code(ticket_id)
            db["support_tickets"].update_one(
                {"_id": ticket_id}, {"$set": {"reference_code": ref}}
            )

        db["support_messages"].insert_one(
            {
                "ticket_id": ticket_id,
                "author_type": "customer",
                "author_id": "guest",
                "author_name": doc.get("name", "Unknown"),
                "body": doc.get("message", ""),
                "created_at": ts,
                "email_sent": False,
            }
        )
        coll.update_one(
            {"_id": legacy_id},
            {"$set": {"reference_code": ref, "ticket_id": str(ticket_id)}},
        )
        migrated += 1

    print(f"Migration complete: {migrated} migrated, {skipped} skipped")


if __name__ == "__main__":
    migrate()
