#!/usr/bin/env python3
"""Seed a fixed admin user for Playwright E2E (zenith_test or MONGO_DB_NAME)."""

from __future__ import annotations

import os
import sys

# Allow `python scripts/seed_e2e_admin.py` from backend/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymongo import MongoClient

from app.auth.auth_utils import get_password_hash


def main() -> None:
    username = os.environ.get("E2E_ADMIN_USERNAME", "e2e_admin")
    password = os.environ.get("E2E_ADMIN_PASSWORD", "SecurePass1!")
    email = os.environ.get("E2E_ADMIN_EMAIL", f"{username}@example.com")
    uri = os.environ.get("MONGO_CONNECTION_STRING", "mongodb://localhost:27017")
    db_name = os.environ.get("MONGO_DB_NAME", "zenith_test")

    client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    client.admin.command("ping")
    db = client[db_name]
    db["users"].update_one(
        {"username": username},
        {
            "$set": {
                "username": username,
                "email": email,
                "hashed_password": get_password_hash(password),
                "role": "admin",
                "email_verified": True,
                "two_fa_enabled": False,
                "two_fa_verified": False,
            },
            "$unset": {"email_verify_token": ""},
        },
        upsert=True,
    )
    print(f"Seeded E2E admin user '{username}' in database '{db_name}'")


if __name__ == "__main__":
    main()
