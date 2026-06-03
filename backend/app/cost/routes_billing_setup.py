"""Billing setup wizards — GCP BigQuery export and Azure Cost Management (BYOC updates)."""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.cloud.providers import normalize_provider_key
from app.cost.billing_config import azure_setup_status, gcp_setup_status
from app.cost.billing_setup import save_azure_billing_setup, save_gcp_billing_setup
from app.users.routes_users import get_current_user
from app.users.user_model import User

router = APIRouter(tags=["Cost Billing Setup"])


class GcpBillingSetupRequest(BaseModel):
    billing_dataset_id: str = Field(..., min_length=1)
    billing_table_id: str = Field(..., min_length=1)


class AzureBillingSetupRequest(BaseModel):
    subscription_id: str = Field(..., min_length=1)
    tenant_id: str = Field(..., min_length=1)
    client_id: str = Field(..., min_length=1)
    client_secret: Optional[str] = None


@router.get("/setup/{provider}", summary="Billing setup status for GCP or Azure")
async def get_billing_setup(provider: str, user: User = Depends(get_current_user)):
    key = normalize_provider_key(provider)
    if key == "gcp":
        return gcp_setup_status(user.username)
    if key == "azure":
        return azure_setup_status(user.username)
    return {
        "provider": key,
        "configured": True,
        "message": "AWS uses Cost Explorer with your AWS/BYOC credentials — no extra billing export setup.",
    }


@router.put("/setup/gcp", summary="Save GCP BigQuery billing export IDs on BYOC record")
async def put_gcp_billing_setup(
    body: GcpBillingSetupRequest,
    user: User = Depends(get_current_user),
):
    return save_gcp_billing_setup(
        user.username,
        billing_dataset_id=body.billing_dataset_id,
        billing_table_id=body.billing_table_id,
    )


@router.put("/setup/azure", summary="Save Azure Cost Management credentials on BYOC record")
async def put_azure_billing_setup(
    body: AzureBillingSetupRequest,
    user: User = Depends(get_current_user),
):
    return save_azure_billing_setup(
        user.username,
        subscription_id=body.subscription_id,
        tenant_id=body.tenant_id,
        client_id=body.client_id,
        client_secret=body.client_secret,
    )
