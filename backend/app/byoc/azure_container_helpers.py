"""Azure Blob container helpers for BYOC connect (suggest, validate, create)."""

from __future__ import annotations

import re
import uuid
from typing import Dict, List, Optional, Tuple

from azure.storage.blob import BlobServiceClient

from app.byoc.aws_bucket_helpers import sanitize_username_for_bucket

CONTAINER_NAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])?$")


def suggest_azure_container_names(username: str) -> Dict[str, str]:
    suffix = uuid.uuid4().hex[:6]
    base = sanitize_username_for_bucket(username)
    storage = f"zenith-{base}-{suffix}-storage"
    secure = f"zenith-{base}-{suffix}-secure"
    replica = f"zenith-{base}-{suffix}-replica"
    return {
        "storage_container_name": storage,
        "container_name": storage,
        "secure_container_name": secure,
        "replica_container_name": replica,
    }


def validate_azure_container_name(name: str) -> Optional[str]:
    if not name or len(name) < 3 or len(name) > 63:
        return "Container name must be 3–63 characters."
    if not CONTAINER_NAME_RE.match(name):
        return "Use lowercase letters, numbers, and hyphens only."
    if "--" in name:
        return "Container name cannot contain consecutive hyphens."
    return None


def _blob_service(account_name: str, account_key: str) -> BlobServiceClient:
    conn = (
        "DefaultEndpointsProtocol=https;"
        f"AccountName={account_name};"
        f"AccountKey={account_key};"
        "EndpointSuffix=core.windows.net"
    )
    return BlobServiceClient.from_connection_string(conn)


def create_azure_container(
    account_name: str,
    account_key: str,
    container_name: str,
) -> Tuple[bool, str]:
    try:
        client = _blob_service(account_name, account_key)
        container = client.get_container_client(container_name)
        if container.exists():
            return True, f"Container '{container_name}' already exists."
        container.create_container()
        return True, f"Created container '{container_name}'."
    except Exception as exc:
        return False, f"Could not create container '{container_name}': {str(exc)[:160]}"


def ensure_azure_containers_exist(
    account_name: str,
    account_key: str,
    containers: List[str],
) -> Tuple[bool, str]:
    created: List[str] = []
    for name in containers:
        if not name:
            continue
        fmt = validate_azure_container_name(name)
        if fmt:
            return False, fmt
        ok, message = create_azure_container(account_name, account_key, name)
        if not ok:
            return False, message
        if message.startswith("Created"):
            created.append(name)
    if created:
        return True, f"Created container(s): {', '.join(created)}."
    return True, "All containers already exist."
