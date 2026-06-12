"""Azure RBAC role assignments for VM managed identities."""

from __future__ import annotations

import uuid
from typing import Any

import requests
from azure.core.exceptions import HttpResponseError


def _role_definition_path(subscription_id: str, role_id: str) -> str:
    return (
        f"/subscriptions/{subscription_id}/providers/Microsoft.Authorization/"
        f"roleDefinitions/{role_id}"
    )


def assign_azure_role(
    credential: Any,
    subscription_id: str,
    scope: str,
    role_id: str,
    principal_id: str,
    steps: list[str],
    label: str,
) -> None:
    if not principal_id or not role_id:
        return
    assignment_id = str(uuid.uuid4())
    url = (
        f"https://management.azure.com{scope}/providers/Microsoft.Authorization/"
        f"roleAssignments/{assignment_id}?api-version=2022-04-01"
    )
    token = credential.get_token("https://management.azure.com/.default")
    body = {
        "properties": {
            "roleDefinitionId": _role_definition_path(subscription_id, role_id),
            "principalId": principal_id,
            "principalType": "ServicePrincipal",
        }
    }
    response = requests.put(
        url,
        headers={
            "Authorization": f"Bearer {token.token}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=60,
    )
    if response.status_code in (200, 201):
        steps.append(f"✓ RBAC: {label} on scope")
        return
    if response.status_code == 409:
        steps.append(f"✓ RBAC: {label} already assigned")
        return
    try:
        response.raise_for_status()
    except Exception as exc:
        raise RuntimeError(f"RBAC assignment failed ({label}): {exc}") from exc


def assign_storage_blob_role(
    credential: Any,
    subscription_id: str,
    resource_group: str,
    storage_account: str,
    role_id: str,
    principal_id: str,
    steps: list[str],
    role_label: str,
) -> None:
    scope = (
        f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/"
        f"providers/Microsoft.Storage/storageAccounts/{storage_account}"
    )
    try:
        assign_azure_role(
            credential,
            subscription_id,
            scope,
            role_id,
            principal_id,
            steps,
            role_label,
        )
    except HttpResponseError as exc:
        raise RuntimeError(str(exc)) from exc


def assign_cosmos_role(
    credential: Any,
    subscription_id: str,
    resource_group: str,
    cosmos_account: str,
    role_id: str,
    principal_id: str,
    steps: list[str],
    role_label: str,
) -> None:
    scope = (
        f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/"
        f"providers/Microsoft.DocumentDB/databaseAccounts/{cosmos_account}"
    )
    assign_azure_role(
        credential,
        subscription_id,
        scope,
        role_id,
        principal_id,
        steps,
        role_label,
    )
