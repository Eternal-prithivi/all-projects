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

    - **BYOC mode** (any cloud connected): only connected providers.
    - **Platform mode** (no BYOC): all providers Zenith has configured in .env.
    """
    return build_availability_payload(user.username)
