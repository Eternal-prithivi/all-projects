"""Per-request AWS EC2 context for BYOC and platform credentials."""

from __future__ import annotations

import contextvars
from contextlib import contextmanager
from typing import Iterator, Optional

from app.byoc.credential_resolver import resolve_aws_credentials
from app.utils.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

_aws_username: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "aws_username", default=None
)


def set_aws_username(username: Optional[str]) -> contextvars.Token:
    return _aws_username.set(username)


def reset_aws_username(token: contextvars.Token) -> None:
    _aws_username.reset(token)


def aws_region() -> str:
    from app.vm.platform_region_context import get_platform_region_slug
    from app.vm.platform_regions import resolve_vm_compute

    slug = get_platform_region_slug()
    if slug:
        return resolve_vm_compute("AWS", slug)["aws_region"]

    username = _aws_username.get()
    if username:
        aws = resolve_aws_credentials(username)
        return aws.get("region") or settings.PRIMARY_S3_REGION
    return settings.PRIMARY_S3_REGION


def aws_boto_credentials() -> dict[str, str]:
    """Shape expected by provision boto3_modules.common.client."""
    username = _aws_username.get()
    if username:
        aws = resolve_aws_credentials(username)
    else:
        aws = {
            "access_key_id": settings.AWS_ACCESS_KEY_ID,
            "secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
            "region": settings.PRIMARY_S3_REGION,
            "is_byoc": False,
        }
    creds = {
        "AWS_ACCESS_KEY_ID": aws.get("access_key_id", ""),
        "AWS_SECRET_ACCESS_KEY": aws.get("secret_access_key", ""),
        "AWS_DEFAULT_REGION": aws.get("region") or settings.PRIMARY_S3_REGION,
    }
    if aws.get("session_token"):
        creds["AWS_SESSION_TOKEN"] = aws["session_token"]
    return creds


@contextmanager
def aws_user_context(username: str) -> Iterator[None]:
    token = set_aws_username(username)
    try:
        yield
    finally:
        reset_aws_username(token)
