#!/usr/bin/env python3
"""Backfill org_id and created_by on user resources for organization members."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database.mongo_client import get_database

DB = get_database()


def backfill_collection(col: str, user_field: str, owner_field: str | None = None) -> int:
    updated = 0
    members = list(DB["organization_members"].find({}))
    for m in members:
        org_id = m["org_id"]
        username = m["username"]
        filt = {user_field: username, "$or": [{"org_id": {"$exists": False}}, {"org_id": None}]}
        if owner_field:
            filt = {
                "$or": [
                    {user_field: username, "$or": [{"org_id": {"$exists": False}}, {"org_id": None}]},
                    {owner_field: username, "$or": [{"org_id": {"$exists": False}}, {"org_id": None}]},
                ]
            }
        result = DB[col].update_many(
            filt,
            {
                "$set": {
                    "org_id": org_id,
                    "created_by": username,
                }
            },
        )
        updated += result.modified_count
    return updated


def main() -> None:
    total = 0
    total += backfill_collection("vm_assignments", "user_id")
    total += backfill_collection("provision_deployments", "user_id")
    total += backfill_collection("files", "owner_username", owner_field="owner_username")
    print(f"Backfill complete. Updated {total} documents.")


if __name__ == "__main__":
    main()
