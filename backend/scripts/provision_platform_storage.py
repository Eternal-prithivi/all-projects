#!/usr/bin/env python3
"""
Provision platform multi-region storage (AWS S3, GCS, Azure) and write catalog JSON.

Usage (from backend/):
  python scripts/provision_platform_storage.py
  python scripts/provision_platform_storage.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

# Reuse existing asia bucket; create named buckets for other regions.
CATALOG_SPEC = [
    {
        "slug": "asia",
        "label": "Asia",
        "aws": {"bucket": "zeneith-storage-bucket", "region": "ap-south-1"},
        "gcp": {"bucket": "zeneith-main-asia", "location": "ASIA-SOUTH1"},
        "azure": {
            "account_name": "zenithpriasia",
            "container": "zenith-storage",
            "region": "centralindia",
        },
    },
    {
        "slug": "us",
        "label": "United States",
        "aws": {"bucket": "zeneith-storage-us", "region": "us-east-1"},
        "gcp": {"bucket": "zenith-main-bucket", "location": "US-CENTRAL1"},
        "azure": {
            "account_name": "zenithprius",
            "container": "zenith-storage",
            "region": "eastus",
        },
    },
    {
        "slug": "europe",
        "label": "Europe",
        "aws": {"bucket": "zeneith-storage-europe", "region": "eu-west-1"},
        "gcp": {"bucket": "zeneith-main-europe", "location": "EUROPE-WEST1"},
        "azure": {
            "account_name": "zenithprieu",
            "container": "zenith-storage",
            "region": "northeurope",
        },
    },
    {
        "slug": "africa",
        "label": "Africa",
        "aws": {"bucket": "zeneith-storage-africa", "region": "af-south-1"},
        "gcp": {"bucket": "zeneith-main-africa", "location": "AFRICA-SOUTH1"},
        "azure": {
            "account_name": "zenithpriafrica",
            "container": "zenith-storage",
            "region": "southafricanorth",
        },
    },
]

# Dedicated secure vault (separate from multi-region storage catalog).
SECURE_VAULT_SPEC = {
    "gcp": {
        "secure_bucket": "zenith-secure-gcp",
        "secure_location": "ASIA-SOUTH1",
        "replica_bucket": "zenith-secure-gcp-replica",
        "replica_location": "US-EAST1",
    },
    "azure": {
        "secure_container": "zenith-secure",
        "replica_container": "zenith-secure-replica",
    },
}


def ensure_aws_bucket(s3, name: str, region: str, dry_run: bool) -> str:
    from botocore.exceptions import ClientError

    try:
        s3.head_bucket(Bucket=name)
        print(f"  AWS OK (exists): s3://{name} [{region}]")
        return "exists"
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code not in ("404", "NoSuchBucket", "NotFound"):
            if code == "403":
                print(f"  AWS SKIP: {name} [{region}] — access denied (enable {region}?)", file=sys.stderr)
                return "skip"
            raise

    if dry_run:
        print(f"  AWS WOULD CREATE: s3://{name} [{region}]")
        return "would_create"

    if region == "us-east-1":
        s3.create_bucket(Bucket=name)
    else:
        s3.create_bucket(
            Bucket=name,
            CreateBucketConfiguration={"LocationConstraint": region},
        )
    print(f"  AWS CREATED: s3://{name} [{region}]")
    return "created"


def ensure_gcp_bucket(client, name: str, location: str, dry_run: bool) -> str:
    bucket = client.bucket(name)
    if bucket.exists():
        bucket.reload()
        print(f"  GCP OK (exists): gs://{name} [{bucket.location}]")
        return "exists"

    if dry_run:
        print(f"  GCP WOULD CREATE: gs://{name} [{location}]")
        return "would_create"

    client.create_bucket(name, location=location)
    print(f"  GCP CREATED: gs://{name} [{location}]")
    return "created"


def ensure_azure_account(
    storage_client,
    resource_group: str,
    account_name: str,
    region: str,
    container: str,
    dry_run: bool,
) -> tuple[str, str | None]:
    """Return (status, account_key or None)."""
    from azure.core.exceptions import ResourceNotFoundError
    from azure.mgmt.storage.models import Kind, Sku, SkuName, StorageAccountCreateParameters
    from azure.storage.blob import BlobServiceClient

    key: str | None = None
    try:
        storage_client.storage_accounts.get_properties(resource_group, account_name)
        print(f"  Azure OK (exists): {account_name} [{region}]")
        status = "exists"
    except ResourceNotFoundError:
        if dry_run:
            print(f"  Azure WOULD CREATE: {account_name} [{region}]")
            return "would_create", None
        params = StorageAccountCreateParameters(
            sku=Sku(name=SkuName.standard_lrs),
            kind=Kind.storage_v2,
            location=region,
            enable_https_traffic_only=True,
            minimum_tls_version="TLS1_2",
        )
        poller = storage_client.storage_accounts.begin_create(
            resource_group, account_name, params
        )
        poller.result()
        print(f"  Azure CREATED account: {account_name} [{region}]")
        status = "created"

    key_result = storage_client.storage_accounts.list_keys(resource_group, account_name)
    key_list = getattr(key_result, "keys_property", None) or key_result.keys
    if callable(key_list):
        key_list = key_list()
    key = key_list[0].value

    conn = (
        f"DefaultEndpointsProtocol=https;AccountName={account_name};"
        f"AccountKey={key};EndpointSuffix=core.windows.net"
    )
    blob_service = BlobServiceClient.from_connection_string(conn)
    container_client = blob_service.get_container_client(container)
    if not container_client.exists():
        if dry_run:
            print(f"  Azure WOULD CREATE container: {account_name}/{container}")
        else:
            container_client.create_container()
            print(f"  Azure CREATED container: {account_name}/{container}")
    else:
        print(f"  Azure OK (container exists): {account_name}/{container}")

    return status, key


def ensure_azure_container_on_account(
    account_name: str,
    account_key: str,
    container: str,
    dry_run: bool,
) -> str:
    from azure.storage.blob import BlobServiceClient

    if not account_name or not account_key:
        print(f"  Azure SKIP container {container}: missing account credentials", file=sys.stderr)
        return "skip"

    conn = (
        f"DefaultEndpointsProtocol=https;AccountName={account_name};"
        f"AccountKey={account_key};EndpointSuffix=core.windows.net"
    )
    blob_service = BlobServiceClient.from_connection_string(conn)
    cc = blob_service.get_container_client(container)
    if cc.exists():
        print(f"  Azure OK (container exists): {account_name}/{container}")
        return "exists"
    if dry_run:
        print(f"  Azure WOULD CREATE container: {account_name}/{container}")
        return "would_create"
    cc.create_container()
    print(f"  Azure CREATED container: {account_name}/{container}")
    return "created"


def provision_secure_vault(
    *,
    gcp_client,
    azure_account: str,
    azure_key: str,
    dry_run: bool,
) -> None:
    print("\n=== Secure vault (GCP + Azure) ===")
    gcp = SECURE_VAULT_SPEC["gcp"]
    try:
        ensure_gcp_bucket(gcp_client, gcp["secure_bucket"], gcp["secure_location"], dry_run)
        ensure_gcp_bucket(gcp_client, gcp["replica_bucket"], gcp["replica_location"], dry_run)
    except Exception as exc:
        print(f"  GCP secure vault ERROR: {exc}", file=sys.stderr)

    az = SECURE_VAULT_SPEC["azure"]
    for container in (az["secure_container"], az["replica_container"]):
        try:
            ensure_azure_container_on_account(azure_account, azure_key, container, dry_run)
        except Exception as exc:
            print(f"  Azure secure vault ERROR ({container}): {exc}", file=sys.stderr)


def _append_env_secure_vault_keys(env_path: Path) -> None:
    """Ensure .env has dedicated secure vault keys (does not overwrite existing values)."""
    gcp = SECURE_VAULT_SPEC["gcp"]
    az = SECURE_VAULT_SPEC["azure"]
    desired = {
        "GCP_SECURE_BUCKET_NAME": gcp["secure_bucket"],
        "GCP_SECURE_REPLICA_BUCKET_NAME": gcp["replica_bucket"],
        "AZURE_SECURE_CONTAINER_NAME": az["secure_container"],
        "AZURE_SECURE_REPLICA_CONTAINER_NAME": az["replica_container"],
    }
    if not env_path.is_file():
        return
    lines = env_path.read_text(encoding="utf-8").splitlines()
    present = {line.split("=", 1)[0] for line in lines if "=" in line and not line.strip().startswith("#")}
    appended = []
    for key, value in desired.items():
        if key not in present:
            lines.append(f"{key}={value}")
            appended.append(key)
    if appended:
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Added to {env_path}: {', '.join(appended)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--catalog-out",
        default=str(BACKEND_ROOT / "config" / "platform_storage_catalog.json"),
    )
    args = parser.parse_args()

    load_dotenv(BACKEND_ROOT / ".env")

    import boto3
    from azure.identity import ClientSecretCredential
    from azure.mgmt.storage import StorageManagementClient
    from google.cloud import storage as gcs

    aws_key = os.environ["AWS_ACCESS_KEY_ID"]
    aws_secret = os.environ["AWS_SECRET_ACCESS_KEY"]
    gcp_path = os.environ["GCP_SERVICE_ACCOUNT_JSON_PATH"]
    gcp_project = os.environ["GCP_PROJECT_ID"]
    az_sub = os.environ["AZURE_SUBSCRIPTION_ID"]
    az_tenant = os.environ["AZURE_TENANT_ID"]
    az_client = os.environ["AZURE_CLIENT_ID"]
    az_secret = os.environ["AZURE_CLIENT_SECRET"]
    az_rg = os.environ.get("AZURE_RESOURCE_GROUP", "zenith-rg")

    # Map existing US Azure account if names match
    existing_az_account = os.environ.get("AZURE_STORAGE_ACCOUNT_NAME", "").strip()
    existing_az_key = os.environ.get("AZURE_STORAGE_ACCOUNT_KEY", "").strip()
    existing_az_container = os.environ.get("AZURE_CONTAINER_NAME", "zenith-main-bucket").strip()

    catalog_out: list[dict] = []
    errors: list[str] = []

    print("\n=== AWS S3 ===")
    for entry in CATALOG_SPEC:
        aws = entry["aws"]
        region = aws["region"]
        name = aws["bucket"]
        s3 = boto3.client(
            "s3",
            region_name=region,
            aws_access_key_id=aws_key,
            aws_secret_access_key=aws_secret,
        )
        try:
            ensure_aws_bucket(s3, name, region, args.dry_run)
        except Exception as exc:
            msg = f"AWS {name}: {exc}"
            errors.append(msg)
            print(f"  AWS ERROR: {msg}", file=sys.stderr)

    print("\n=== GCP GCS ===")
    gcp_client = gcs.Client.from_service_account_json(gcp_path, project=gcp_project)
    for entry in CATALOG_SPEC:
        gcp = entry["gcp"]
        try:
            ensure_gcp_bucket(gcp_client, gcp["bucket"], gcp["location"], args.dry_run)
        except Exception as exc:
            msg = f"GCP {gcp['bucket']}: {exc}"
            errors.append(msg)
            print(f"  GCP ERROR: {msg}", file=sys.stderr)

    print("\n=== Azure Storage ===")
    credential = ClientSecretCredential(az_tenant, az_client, az_secret)
    az_storage = StorageManagementClient(credential, az_sub)

    for entry in CATALOG_SPEC:
        az = entry["azure"]
        account = az["account_name"]
        # Reuse existing eastus account for US slug when configured
        if entry["slug"] == "us" and existing_az_account and existing_az_key:
            account = existing_az_account
            az = {**az, "account_name": account, "container": existing_az_container}
            print(f"  Azure US: reusing existing account {account}")
            if not args.dry_run:
                from azure.storage.blob import BlobServiceClient

                conn = (
                    f"DefaultEndpointsProtocol=https;AccountName={account};"
                    f"AccountKey={existing_az_key};EndpointSuffix=core.windows.net"
                )
                blob_service = BlobServiceClient.from_connection_string(conn)
                cc = blob_service.get_container_client(az["container"])
                if not cc.exists():
                    cc.create_container()
                    print(f"  Azure CREATED container: {account}/{az['container']}")
                else:
                    print(f"  Azure OK (container exists): {account}/{az['container']}")
            key = existing_az_key
        else:
            try:
                _, key = ensure_azure_account(
                    az_storage,
                    az_rg,
                    account,
                    az["region"],
                    az["container"],
                    args.dry_run,
                )
            except Exception as exc:
                msg = f"Azure {account}: {exc}"
                errors.append(msg)
                print(f"  Azure ERROR: {msg}", file=sys.stderr)
                key = None

        catalog_out.append(
            {
                "slug": entry["slug"],
                "label": entry["label"],
                "aws": entry["aws"],
                "gcp": entry["gcp"],
                "azure": {
                    **az,
                    "account_key": key or "REPLACE_ME",
                },
            }
        )

    provision_secure_vault(
        gcp_client=gcp_client,
        azure_account=existing_az_account,
        azure_key=existing_az_key,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print("\nDry run complete — no catalog written.")
        _append_env_secure_vault_keys(BACKEND_ROOT / ".env")
        return 1 if errors else 0

    out_path = Path(args.catalog_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(catalog_out, fh, indent=2)
        fh.write("\n")
    print(f"\nWrote catalog: {out_path}")

    env_path = BACKEND_ROOT / ".env"
    env_text = env_path.read_text(encoding="utf-8")
    lines = []
    seen_catalog = False
    seen_default = False
    for line in env_text.splitlines():
        if line.startswith("PLATFORM_STORAGE_CATALOG_JSON="):
            lines.append("PLATFORM_STORAGE_CATALOG_JSON=config/platform_storage_catalog.json")
            seen_catalog = True
        elif line.startswith("PLATFORM_STORAGE_DEFAULT_SLUG="):
            lines.append("PLATFORM_STORAGE_DEFAULT_SLUG=asia")
            seen_default = True
        else:
            lines.append(line)
    if not seen_catalog:
        lines.append("PLATFORM_STORAGE_CATALOG_JSON=config/platform_storage_catalog.json")
    if not seen_default:
        lines.append("PLATFORM_STORAGE_DEFAULT_SLUG=asia")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Updated backend/.env with PLATFORM_STORAGE_CATALOG_JSON")
    _append_env_secure_vault_keys(env_path)

    if errors:
        print("\nCompleted with errors:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
