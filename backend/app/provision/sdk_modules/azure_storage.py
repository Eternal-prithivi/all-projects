from __future__ import annotations

from typing import Any

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import BlobServiceClient

from app.provision.sdk_clients import azure_credential_and_subscription, azure_storage_mgmt_client
from app.provision.sdk_modules.azure_resource_group import azure_effective_location, ensure_resource_group
from app.provision.sdk_modules.context import SdkDeployContext


def _storage_mgmt(cloud_env: dict[str, str]):
    return azure_storage_mgmt_client(cloud_env)


def plan_azure_storage(config: dict, cloud_env: dict[str, str]) -> dict[str, Any]:
    sa_name = (config.get("storage_account_name") or "").strip()
    if not sa_name:
        return {"lines": [], "error": "Storage account name is required.", "resources": []}
    rg = config.get("resource_group_name") or "zenith-rg"
    container = config.get("container_name") or "zenith-static"
    location = config.get("azure_location") or "eastus"
    lines = [  # plan uses requested region; apply resolves via ensure_resource_group
        f"  + azurerm_resource_group.main ({rg}, {location})",
        f"  + azurerm_storage_account.main ({sa_name})",
        f"  + azurerm_storage_container.static ({container})",
    ]
    return {"lines": lines, "error": None, "resources": lines}


def apply_azure_storage(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> dict[str, Any]:
    from azure.mgmt.storage.models import Kind, Sku, SkuName, StorageAccountCreateParameters

    sa_name = (config.get("storage_account_name") or "").strip()
    rg = config.get("resource_group_name") or "zenith-rg"
    container = config.get("container_name") or "zenith-static"
    steps: list[str] = []
    try:
        ok, rg_steps, err = ensure_resource_group(config, cloud_env, ctx)
        steps.extend(rg_steps)
        if not ok:
            return {"success": False, "steps": steps, "error": err}
        rg = ctx.azure_resource_group
        location = azure_effective_location(config, ctx)

        storage_client, credential = _storage_mgmt(cloud_env)
        existing = [
            a.name
            for a in storage_client.storage_accounts.list_by_resource_group(rg)
        ]
        if sa_name not in existing:
            poller = storage_client.storage_accounts.begin_create(
                rg,
                sa_name,
                StorageAccountCreateParameters(
                    sku=Sku(name=SkuName.STANDARD_LRS),
                    kind=Kind.STORAGE_V2,
                    location=location,
                    minimum_tls_version="TLS1_2",
                ),
            )
            poller.result()
        steps.append(f"✓ Storage account '{sa_name}'")

        blob_service = BlobServiceClient(
            account_url=f"https://{sa_name}.blob.core.windows.net",
            credential=credential,
        )
        try:
            blob_service.create_container(container)
        except ResourceExistsError:
            pass
        steps.append(f"✓ Container '{container}'")

        ctx.azure_resource_group = rg
        ctx.azure_storage_account = sa_name
        ctx.azure_container = container
        return {"success": True, "steps": steps, "error": None}
    except Exception as exc:
        return {"success": False, "steps": steps, "error": str(exc)}


def destroy_azure_storage(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> dict[str, Any]:
    sa_name = (config.get("storage_account_name") or ctx.azure_storage_account or "").strip()
    rg = config.get("resource_group_name") or ctx.azure_resource_group or "zenith-rg"
    container = config.get("container_name") or ctx.azure_container or "zenith-static"
    if not sa_name:
        return {"success": True, "steps": ["Azure storage: nothing to delete"], "error": None}
    steps: list[str] = []
    try:
        credential, subscription = azure_credential_and_subscription(cloud_env)
        blob_service = BlobServiceClient(
            account_url=f"https://{sa_name}.blob.core.windows.net",
            credential=credential,
        )
        try:
            blob_service.delete_container(container)
            steps.append(f"✓ Deleted container '{container}'")
        except ResourceNotFoundError:
            pass

        storage_client, _ = _storage_mgmt(cloud_env)
        storage_client.storage_accounts.delete(rg, sa_name)
        steps.append(f"✓ Deleted storage account '{sa_name}'")
        return {"success": True, "steps": steps, "error": None}
    except Exception as exc:
        return {"success": False, "steps": steps, "error": str(exc)}


def check_azure_storage_drift(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> tuple[int, list[str]]:
    sa_name = (config.get("storage_account_name") or ctx.azure_storage_account or "").strip()
    rg = config.get("resource_group_name") or ctx.azure_resource_group or "zenith-rg"
    container = config.get("container_name") or ctx.azure_container or "zenith-static"
    if not sa_name:
        return 0, []
    details: list[str] = []
    changes = 0
    try:
        from app.provision.sdk_clients import azure_resource_client

        resource_client, credential, _ = azure_resource_client(cloud_env)
        resource_client.resource_groups.get(rg)

        storage_client, _ = _storage_mgmt(cloud_env)
        account = storage_client.storage_accounts.get_properties(rg, sa_name)
        if (account.minimum_tls_version or "").upper() != "TLS1_2":
            changes += 1
            details.append("~ Storage account minimum_tls_version is not TLS1_2")

        blob_service = BlobServiceClient(
            account_url=f"https://{sa_name}.blob.core.windows.net",
            credential=credential,
        )
        blob_service.get_container_client(container).get_container_properties()
    except ResourceNotFoundError as exc:
        return 1, [f"~ Azure resource missing: {exc}"]
    except Exception as exc:
        return 1, [f"~ Azure storage check failed: {exc}"]
    return changes, details
