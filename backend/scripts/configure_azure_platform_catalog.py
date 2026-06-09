#!/usr/bin/env python3
"""
Wire multi-region Azure storage accounts into platform_storage_catalog.json.

Uses storage account access keys (portal → Storage account → Access keys).
Does not require Azure service-principal auth.

Usage (from backend/):
  1. Copy config/azure_platform_keys.example.json → config/azure_platform_keys.json
  2. Paste Key1 for zenithpriasia, zenithprieu, zenithpriafrica
  3. python scripts/configure_azure_platform_catalog.py
  4. python scripts/configure_azure_platform_catalog.py --verify-only
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

# Zenith slug → Azure account (from your portal setup)
AZURE_BY_SLUG = {
    "asia": {
        "account_name": "zenithpriasia",
        "region": "centralindia",
        "container": "zenith-storage",
    },
    "us": {
        "account_name": "zenithprithivi",
        "region": "eastus",
        "container": "zenith-main-bucket",
        "key_from_env": True,
    },
    "europe": {
        "account_name": "zenithprieu",
        "region": "northeurope",
        "container": "zenith-storage",
    },
    "africa": {
        "account_name": "zenithpriafrica",
        "region": "southafricanorth",
        "container": "zenith-storage",
    },
}


def load_keys(keys_path: Path) -> dict[str, str]:
    if not keys_path.is_file():
        return {}
    data = json.loads(keys_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{keys_path} must be a JSON object of account_name → key")
    return {k.strip(): v.strip() for k, v in data.items() if v and str(v).strip()}


def resolve_key(account_name: str, keys: dict[str, str], env_key: str | None) -> str:
    if env_key:
        return env_key
    key = keys.get(account_name, "").strip()
    if not key or key.startswith("PASTE_"):
        raise ValueError(
            f"Missing access key for {account_name}. "
            f"Add it to config/azure_platform_keys.json (see example file)."
        )
    return key


def ensure_container(account_name: str, account_key: str, container: str, dry_run: bool) -> None:
    from azure.storage.blob import BlobServiceClient

    conn = (
        f"DefaultEndpointsProtocol=https;AccountName={account_name};"
        f"AccountKey={account_key};EndpointSuffix=core.windows.net"
    )
    blob_service = BlobServiceClient.from_connection_string(conn)
    cc = blob_service.get_container_client(container)
    if cc.exists():
        print(f"  OK container: {account_name}/{container}")
        return
    if dry_run:
        print(f"  WOULD CREATE container: {account_name}/{container}")
        return
    cc.create_container()
    print(f"  CREATED container: {account_name}/{container}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify-only", action="store_true", help="Check containers; do not write catalog")
    parser.add_argument(
        "--keys-file",
        default=str(BACKEND_ROOT / "config" / "azure_platform_keys.json"),
    )
    parser.add_argument(
        "--catalog",
        default=str(BACKEND_ROOT / "config" / "platform_storage_catalog.json"),
    )
    args = parser.parse_args()

    load_dotenv(BACKEND_ROOT / ".env")
    import os

    keys = load_keys(Path(args.keys_file))
    env_us_key = (os.environ.get("AZURE_STORAGE_ACCOUNT_KEY") or "").strip()

    catalog_path = Path(args.catalog)
    if not catalog_path.is_file():
        print(f"Catalog not found: {catalog_path}", file=sys.stderr)
        return 1

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    slug_index = {entry["slug"]: entry for entry in catalog}

    print("=== Azure platform storage ===")
    errors: list[str] = []

    for slug, az_meta in AZURE_BY_SLUG.items():
        account = az_meta["account_name"]
        container = az_meta["container"]
        region = az_meta["region"]
        try:
            key = resolve_key(
                account,
                keys,
                env_us_key if az_meta.get("key_from_env") else None,
            )
            ensure_container(account, key, container, args.dry_run or args.verify_only)
            if not args.verify_only and slug in slug_index:
                slug_index[slug]["azure"] = {
                    "account_name": account,
                    "account_key": key,
                    "container": container,
                    "region": region,
                }
        except Exception as exc:
            msg = f"{slug} ({account}): {exc}"
            errors.append(msg)
            print(f"  ERROR: {msg}", file=sys.stderr)

    if args.verify_only:
        return 1 if errors else 0

    if args.dry_run:
        print("\nDry run — catalog not written.")
        return 1 if errors else 0

    if errors:
        print("\nFix errors above before writing catalog.", file=sys.stderr)
        return 1

    catalog_path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
    print(f"\nUpdated catalog: {catalog_path}")

    from app.cloud.platform_storage_catalog import invalidate_platform_catalog_cache

    invalidate_platform_catalog_cache()
    print("Invalidated in-process catalog cache (restart uvicorn if already running).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
