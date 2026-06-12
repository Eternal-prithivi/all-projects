"""Resolve per-user GCP/Azure billing configuration (BYOC + platform .env)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.byoc.credential_resolver import get_byoc_status, resolve_gcp_credentials
from app.utils.config import settings


GCP_SETUP_STEPS = [
    "Enable BigQuery billing export: https://console.cloud.google.com/billing/export",
    "Create or note the dataset ID and table ID (e.g. gcp_billing_export_v1_XXXXX)",
    "Grant the service account BigQuery Data Viewer on the billing export dataset",
    "Set GCP_BILLING_DATASET_ID and GCP_BILLING_TABLE_ID in backend .env, or save below when GCP BYOC is connected",
]

AZURE_SETUP_STEPS = [
    "Create an Azure AD app registration (service principal) for Cost Management Reader",
    "Assign Cost Management Reader on the subscription",
    "Set AZURE_SUBSCRIPTION_ID, AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET in .env",
    "Or save Cost Management fields on your Azure BYOC connection (storage keys alone are not enough)",
]

BYOC_SETUP_GUIDE_PAYLOAD = {
    "gcp_billing": {
        "csp": "GCP",
        "title": "GCP BigQuery billing export (recommended)",
        "works_without": ["Storage", "Security", "VMs", "Provision"],
        "blocked_without": ["Cost"],
        "steps": GCP_SETUP_STEPS,
    },
    "azure_compute": {
        "csp": "Azure",
        "title": "Azure service principal (recommended)",
        "works_without": ["Storage", "Security"],
        "blocked_without": ["VMs", "Provision", "Cost"],
        "steps": AZURE_SETUP_STEPS,
    },
}


def resolve_gcp_billing_ids(username: str) -> Dict[str, str]:
    gcp = resolve_gcp_credentials(username)
    return {
        "dataset_id": (
            (gcp.get("billing_dataset_id") or "").strip()
            or (settings.GCP_BILLING_DATASET_ID or "").strip()
        ),
        "table_id": (
            (gcp.get("billing_table_id") or "").strip()
            or (settings.GCP_BILLING_TABLE_ID or "").strip()
        ),
        "is_byoc": bool(gcp.get("is_byoc")),
    }


def resolve_azure_billing_creds(username: str) -> Dict[str, str]:
    from app.byoc.credential_resolver import resolve_azure_credentials

    azure = resolve_azure_credentials(username)
    return {
        "subscription_id": (azure.get("subscription_id") or "").strip(),
        "tenant_id": (azure.get("tenant_id") or "").strip(),
        "client_id": (azure.get("client_id") or "").strip(),
        "client_secret": (azure.get("client_secret") or "").strip(),
        "is_byoc": bool(azure.get("is_byoc")),
    }


def gcp_billing_configured(username: str) -> bool:
    ids = resolve_gcp_billing_ids(username)
    return bool(ids["dataset_id"] and ids["table_id"])


def azure_billing_configured(username: str) -> bool:
    creds = resolve_azure_billing_creds(username)
    return all(
        creds.get(k) for k in ("subscription_id", "tenant_id", "client_id", "client_secret")
    )


def gcp_setup_status(username: str) -> Dict[str, Any]:
    ids = resolve_gcp_billing_ids(username)
    byoc = get_byoc_status(username).get("gcp") or {}
    configured = bool(ids["dataset_id"] and ids["table_id"])
    return {
        "provider": "gcp",
        "configured": configured,
        "source": "byoc" if ids["is_byoc"] else "platform",
        "byoc_connected": bool(byoc.get("connected")),
        "billing_dataset_id": ids["dataset_id"] or None,
        "billing_table_id": ids["table_id"] or None,
        "setup_steps": GCP_SETUP_STEPS,
        "can_update_via_api": bool(byoc.get("connected")),
    }


def azure_setup_status(username: str) -> Dict[str, Any]:
    creds = resolve_azure_billing_creds(username)
    byoc = get_byoc_status(username).get("azure") or {}
    configured = azure_billing_configured(username)
    return {
        "provider": "azure",
        "configured": configured,
        "source": "byoc" if creds["is_byoc"] else "platform",
        "byoc_connected": bool(byoc.get("connected")),
        "subscription_id": creds["subscription_id"] or None,
        "tenant_id": creds["tenant_id"] or None,
        "client_id": creds["client_id"] or None,
        "has_client_secret": bool(creds["client_secret"]),
        "setup_steps": AZURE_SETUP_STEPS,
        "can_update_via_api": bool(byoc.get("connected")),
    }


def build_byoc_setup_guides_payload() -> Dict[str, Any]:
    return {"guides": BYOC_SETUP_GUIDE_PAYLOAD}


def missing_gcp_config_payload() -> Dict[str, Any]:
    return {
        "message": "GCP billing not configured",
        "status": "missing_config",
        "error": "Set GCP_BILLING_DATASET_ID and GCP_BILLING_TABLE_ID",
        "implementation_steps": GCP_SETUP_STEPS,
        "estimated_cost": 0.0,
        "currency": "USD",
    }


def missing_azure_config_payload(byoc_connected: bool = False) -> Dict[str, Any]:
    steps = list(AZURE_SETUP_STEPS)
    return {
        "message": "Azure billing not configured",
        "status": "missing_config",
        "error": "Set Azure Cost Management credentials in .env or BYOC record",
        "implementation_steps": steps,
        "estimated_cost": 0.0,
        "currency": "USD",
    }
