"""Build GCP / Azure SDK clients from Terraform-style BYOC env dicts."""

from __future__ import annotations

import json
from typing import Any, Tuple

from google.cloud import storage as gcp_storage
from google.oauth2 import service_account


def gcp_storage_client(cloud_env: dict[str, str]) -> Tuple[gcp_storage.Client, str]:
    raw = cloud_env.get("GOOGLE_CREDENTIALS") or ""
    if not raw:
        raise ValueError("GOOGLE_CREDENTIALS missing from provision environment.")
    info = json.loads(raw) if isinstance(raw, str) else raw
    project = cloud_env.get("GOOGLE_PROJECT") or info.get("project_id") or ""
    credentials = service_account.Credentials.from_service_account_info(info)
    return gcp_storage.Client(project=project, credentials=credentials), project


def azure_credential_and_subscription(cloud_env: dict[str, str]) -> Tuple[Any, str]:
    from azure.identity import ClientSecretCredential

    tenant = cloud_env.get("ARM_TENANT_ID", "")
    client_id = cloud_env.get("ARM_CLIENT_ID", "")
    secret = cloud_env.get("ARM_CLIENT_SECRET", "")
    subscription = cloud_env.get("ARM_SUBSCRIPTION_ID", "")
    if not all([tenant, client_id, secret, subscription]):
        raise ValueError("Azure ARM credentials incomplete in provision environment.")
    credential = ClientSecretCredential(
        tenant_id=tenant,
        client_id=client_id,
        client_secret=secret,
    )
    return credential, subscription
