#!/usr/bin/env python3
"""Set a user's Zenith subscription plan in MongoDB (local or production URI)."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Allow: python scripts/set_subscription_plan.py --username "Tanjore developer" --plan enterprise
BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv

load_dotenv(BACKEND_ROOT / ".env")

from app.payments.subscription_service import set_user_subscription, get_effective_plan_id


def main() -> None:
    parser = argparse.ArgumentParser(description="Set Zenith subscription plan for a user")
    parser.add_argument("--username", required=True, help="Zenith username (exact match)")
    parser.add_argument(
        "--plan",
        default="enterprise",
        choices=["free", "basic", "pro", "enterprise"],
    )
    args = parser.parse_args()

    set_user_subscription(args.username, args.plan)
    effective = get_effective_plan_id(args.username)
    print(f"OK: {args.username} -> plan_id={effective}")


if __name__ == "__main__":
    main()
