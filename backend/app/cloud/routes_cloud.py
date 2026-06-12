"""Cloud availability API — which providers a user may use per feature."""

from fastapi import APIRouter, Depends

from app.auth.auth_utils import get_current_user
from app.cloud.availability import build_availability_payload
from app.users.user_model import User

router = APIRouter(tags=["Cloud"])


@router.get("/availability", summary="Per-user available cloud providers by feature")
async def get_cloud_availability(user: User = Depends(get_current_user)):
    """
    Drives CSP selectors across Storage, Security, VM, Provision, and Cost.

    Hybrid union of BYOC-connected and platform-configured CSPs. When BYOC is
    connected but credentials are incomplete (e.g. Azure storage-only), the CSP
    appears under ``locked_providers`` for features that are not yet ready.
    """
    return build_availability_payload(user.username)
