#!/usr/bin/env python3
"""
Create or reset a Zenith user (e.g. after accidental DB wipe).

Usage (from backend/):
  python scripts/restore_user.py --username tanjiro --email tanjiro@example.com --plan enterprise
  python scripts/restore_user.py --username tanjiro --password 'YourNewPass123!'
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv

load_dotenv(BACKEND_ROOT / ".env")

from app.auth.auth_utils import get_password_hash
from app.database.mongo_client import get_database
from app.payments.subscription_service import set_user_subscription


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore a Zenith user account")
    parser.add_argument("--username", required=True)
    parser.add_argument("--email", default=None)
    parser.add_argument("--password", default=os.environ.get("RESTORE_USER_PASSWORD", "Zenith@Restore1"))
    parser.add_argument(
        "--plan",
        default="enterprise",
        choices=["free", "basic", "pro", "enterprise"],
    )
    parser.add_argument("--role", default="admin", choices=["user", "admin"])
    args = parser.parse_args()

    db = get_database()
    email = args.email or f"{args.username}@example.com"
    now = datetime.utcnow()

    db["users"].update_one(
        {"username": args.username},
        {
            "$set": {
                "username": args.username,
                "email": email,
                "hashed_password": get_password_hash(args.password),
                "role": args.role,
                "email_verified": True,
                "two_fa_enabled": False,
                "two_fa_verified": False,
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
            "$unset": {"deleted": "", "email_verify_token": ""},
        },
        upsert=True,
    )

    set_user_subscription(args.username, args.plan, status="active")

    print(f"OK: user {args.username!r} restored with plan={args.plan}")
    print(f"    email: {email}")
    print(f"    temporary password: {args.password}")
    print("    Change password after login via Profile → Change password.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
