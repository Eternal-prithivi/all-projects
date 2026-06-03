"""Persist billing-only fields on active BYOC records."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from fastapi import HTTPException

from app.byoc.encryption import decrypt_credentials_dict, encrypt_credentials_dict
from app.database.mongo_client import get_database
from app.byoc.credential_resolver import get_user_cloud_credentials

DB = get_database()
BYOC = DB["byoc_credentials"]


def _merge_byoc_credentials(username: str, csp: str, updates: Dict[str, str]) -> None:
    record = BYOC.find_one({"username": username, "csp": csp, "is_active": True})
    if not record:
        raise HTTPException(
            status_code=400,
            detail={
                "status": "missing_byoc",
                "message": f"Connect {csp} under BYOC before saving billing settings in Zenith.",
                "setup_steps": [
                    "Open Settings → BYOC and connect your cloud account",
                    "Or set platform .env variables on the deployment",
                ],
            },
        )
    existing = decrypt_credentials_dict(record.get("credentials") or {})
    for key, value in updates.items():
        if value is not None and str(value).strip():
            existing[key] = str(value).strip()
    encrypted = encrypt_credentials_dict(existing)
    BYOC.update_one(
        {"_id": record["_id"]},
        {"$set": {"credentials": encrypted, "updated_at": datetime.utcnow()}},
    )


def save_gcp_billing_setup(
    username: str,
    *,
    billing_dataset_id: str,
    billing_table_id: str,
) -> Dict[str, Any]:
    if not billing_dataset_id.strip() or not billing_table_id.strip():
        raise HTTPException(status_code=400, detail="dataset_id and table_id are required.")
    _merge_byoc_credentials(
        username,
        "GCP",
        {
            "billing_dataset_id": billing_dataset_id,
            "billing_table_id": billing_table_id,
        },
    )
    from app.cost.billing_config import gcp_setup_status

    return {"success": True, "message": "GCP billing export settings saved.", **gcp_setup_status(username)}


def save_azure_billing_setup(
    username: str,
    *,
    subscription_id: str,
    tenant_id: str,
    client_id: str,
    client_secret: str | None = None,
) -> Dict[str, Any]:
    if not all([subscription_id.strip(), tenant_id.strip(), client_id.strip()]):
        raise HTTPException(
            status_code=400,
            detail="subscription_id, tenant_id, and client_id are required.",
        )
    updates: Dict[str, str] = {
        "subscription_id": subscription_id,
        "tenant_id": tenant_id,
        "client_id": client_id,
    }
    if client_secret and client_secret.strip():
        updates["client_secret"] = client_secret
    elif not (get_user_cloud_credentials(username, "Azure") or {}).get("credentials", {}).get(
        "client_secret"
    ):
        raise HTTPException(
            status_code=400,
            detail="client_secret is required on first save.",
        )
    _merge_byoc_credentials(username, "Azure", updates)
    from app.cost.billing_config import azure_setup_status

    return {
        "success": True,
        "message": "Azure Cost Management settings saved.",
        **azure_setup_status(username),
    }
