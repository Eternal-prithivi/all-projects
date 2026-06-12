"""Azure Cosmos DB SQL API SDK module."""

from __future__ import annotations

from typing import Any

from azure.core.exceptions import ResourceNotFoundError
from azure.mgmt.cosmosdb.models import (
    ConsistencyPolicy,
    CreateUpdateOptions,
    DatabaseAccountCreateUpdateParameters,
    DatabaseAccountKind,
    Location,
    SqlDatabaseCreateUpdateParameters,
    SqlDatabaseResource,
)

from app.provision.provision_config_options import AZURE_IDENTITY_PRESETS, normalize_azure_identity_preset
from app.provision.sdk_clients import azure_cosmos_client, azure_credential_and_subscription
from app.provision.sdk_modules.azure_rbac import assign_cosmos_role
from app.provision.sdk_modules.azure_resource_group import azure_effective_location, ensure_resource_group
from app.provision.sdk_modules.common import azure_tags
from app.provision.sdk_modules.context import SdkDeployContext


def plan_cosmos(config: dict, cloud_env: dict[str, str]) -> dict[str, Any]:
    account = config.get("cosmos_account_name") or "zenithcosmos"
    db = config.get("cosmos_database_name") or "zenith-db"
    lines = [
        f"  + azurerm_cosmosdb_account.{account}",
        f"  + azurerm_cosmosdb_sql_database.{db}",
    ]
    return {"lines": lines, "error": None, "resources": lines}


def apply_cosmos(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> dict[str, Any]:
    account = (config.get("cosmos_account_name") or "").strip()
    if not account:
        return {"success": False, "steps": [], "error": "Cosmos account name is required."}
    ok, steps, err = ensure_resource_group(config, cloud_env, ctx)
    if not ok:
        return {"success": False, "steps": steps, "error": err}
    rg = ctx.azure_resource_group
    location = azure_effective_location(config, ctx)
    db_name = config.get("cosmos_database_name") or "zenith-db"
    client, _, _ = azure_cosmos_client(cloud_env)
    try:
        try:
            client.database_accounts.get(rg, account)
            steps.append(f"✓ Cosmos account '{account}' exists")
        except ResourceNotFoundError:
            params = DatabaseAccountCreateUpdateParameters(
                location=location,
                locations=[Location(location_name=location, failover_priority=0)],
                kind=DatabaseAccountKind.GLOBAL_DOCUMENT_DB,
                consistency_policy=ConsistencyPolicy(default_consistency_level="Session"),
                tags=azure_tags(config.get("tags")),
            )
            client.database_accounts.begin_create_or_update(rg, account, params).result()
            steps.append(f"✓ Cosmos account '{account}'")

        try:
            client.sql_resources.get_sql_database(rg, account, db_name)
            steps.append(f"✓ Cosmos database '{db_name}' exists")
        except ResourceNotFoundError:
            client.sql_resources.begin_create_update_sql_database(
                rg,
                account,
                db_name,
                SqlDatabaseCreateUpdateParameters(
                    resource=SqlDatabaseResource(id=db_name),
                    options=CreateUpdateOptions(),
                ),
            ).result()
            steps.append(f"✓ Cosmos database '{db_name}'")

        ctx.cosmos_account_name = account
        ctx.cosmos_database_name = db_name

        identity_preset = normalize_azure_identity_preset(config.get("azure_identity_preset"))
        if identity_preset == "cosmos_data_contributor":
            principal_id = (ctx.azure_vm_principal_id or "").strip()
            preset_meta = AZURE_IDENTITY_PRESETS[identity_preset]
            if principal_id:
                credential, subscription_id = azure_credential_and_subscription(cloud_env)
                assign_cosmos_role(
                    credential,
                    subscription_id,
                    rg,
                    account,
                    preset_meta["role_id"],
                    principal_id,
                    steps,
                    preset_meta["role_name"],
                )
            else:
                steps.append("⚠ Cosmos RBAC skipped — enable Azure VM with managed identity first.")

        return {"success": True, "steps": steps, "error": None}
    except Exception as exc:
        return {"success": False, "steps": steps, "error": str(exc)}


def destroy_cosmos(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> dict[str, Any]:
    account = ctx.cosmos_account_name or config.get("cosmos_account_name") or ""
    rg = ctx.azure_resource_group or config.get("resource_group_name") or "zenith-rg"
    if not account:
        return {"success": True, "steps": ["Cosmos: nothing to delete"], "error": None}
    client, _, _ = azure_cosmos_client(cloud_env)
    steps: list[str] = []
    try:
        try:
            client.database_accounts.begin_delete(rg, account).result()
            steps.append(f"✓ Deleted Cosmos account '{account}'")
        except ResourceNotFoundError:
            pass
        return {"success": True, "steps": steps, "error": None}
    except Exception as exc:
        return {"success": False, "steps": steps, "error": str(exc)}


def check_cosmos_drift(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> tuple[int, list[str]]:
    account = ctx.cosmos_account_name or config.get("cosmos_account_name") or ""
    if not account:
        return 0, []
    rg = ctx.azure_resource_group or config.get("resource_group_name") or "zenith-rg"
    client, _, _ = azure_cosmos_client(cloud_env)
    try:
        client.database_accounts.get(rg, account)
        return 0, []
    except ResourceNotFoundError:
        return 1, [f"~ Cosmos account '{account}' missing"]
    except Exception as exc:
        return 1, [f"~ Cosmos check failed: {exc}"]
