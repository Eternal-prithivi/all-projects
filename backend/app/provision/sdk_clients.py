"""Build GCP / Azure SDK clients from Terraform-style BYOC env dicts."""

from __future__ import annotations

import json
from typing import Any, Tuple

from google.cloud import storage as gcp_storage
from google.oauth2 import service_account


def _gcp_credentials(cloud_env: dict[str, str]):
    raw = cloud_env.get("GOOGLE_CREDENTIALS") or ""
    if not raw:
        raise ValueError("GOOGLE_CREDENTIALS missing from provision environment.")
    info = json.loads(raw) if isinstance(raw, str) else raw
    project = cloud_env.get("GOOGLE_PROJECT") or info.get("project_id") or ""
    credentials = service_account.Credentials.from_service_account_info(info)
    return credentials, project


def gcp_storage_client(cloud_env: dict[str, str]) -> Tuple[gcp_storage.Client, str]:
    credentials, project = _gcp_credentials(cloud_env)
    return gcp_storage.Client(project=project, credentials=credentials), project


def gcp_compute_clients(cloud_env: dict[str, str]):
    from google.cloud import compute_v1

    credentials, project = _gcp_credentials(cloud_env)
    return (
        compute_v1.NetworksClient(credentials=credentials),
        compute_v1.SubnetworksClient(credentials=credentials),
        compute_v1.InstancesClient(credentials=credentials),
        project,
    )


def gcp_iam_client(cloud_env: dict[str, str]):
    from google.cloud import iam_admin_v1

    credentials, project = _gcp_credentials(cloud_env)
    return iam_admin_v1.IAMClient(credentials=credentials), project


def gcp_monitoring_client(cloud_env: dict[str, str]):
    from google.cloud import monitoring_v3

    credentials, project = _gcp_credentials(cloud_env)
    return monitoring_v3.NotificationChannelServiceClient(credentials=credentials), monitoring_v3.AlertPolicyServiceClient(credentials=credentials), project


def gcp_firestore_admin_client(cloud_env: dict[str, str]):
    from google.cloud.firestore_admin_v1 import FirestoreAdminClient

    credentials, project = _gcp_credentials(cloud_env)
    return FirestoreAdminClient(credentials=credentials), project


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


def azure_resource_client(cloud_env: dict[str, str]):
    from azure.mgmt.resource import ResourceManagementClient

    credential, subscription = azure_credential_and_subscription(cloud_env)
    return ResourceManagementClient(credential, subscription), credential, subscription


def azure_network_client(cloud_env: dict[str, str]):
    from azure.mgmt.network import NetworkManagementClient

    credential, subscription = azure_credential_and_subscription(cloud_env)
    return NetworkManagementClient(credential, subscription), credential, subscription


def azure_compute_client(cloud_env: dict[str, str]):
    from azure.mgmt.compute import ComputeManagementClient

    credential, subscription = azure_credential_and_subscription(cloud_env)
    return ComputeManagementClient(credential, subscription), credential, subscription


def azure_monitor_client(cloud_env: dict[str, str]):
    from azure.mgmt.monitor import MonitorManagementClient

    credential, subscription = azure_credential_and_subscription(cloud_env)
    return MonitorManagementClient(credential, subscription), credential, subscription


def azure_cosmos_client(cloud_env: dict[str, str]):
    from azure.mgmt.cosmosdb import CosmosDBManagementClient

    credential, subscription = azure_credential_and_subscription(cloud_env)
    return CosmosDBManagementClient(credential, subscription), credential, subscription


def azure_storage_mgmt_client(cloud_env: dict[str, str]):
    from azure.mgmt.storage import StorageManagementClient

    credential, subscription = azure_credential_and_subscription(cloud_env)
    return StorageManagementClient(credential, subscription), credential, subscription
