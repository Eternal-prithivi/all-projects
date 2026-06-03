"""Per-request Azure Compute context for BYOC and platform credentials."""

from __future__ import annotations

import contextvars
from contextlib import contextmanager
from typing import Iterator, Optional

from app.byoc.credential_resolver import resolve_azure_credentials
from app.utils.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

_azure_username: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "azure_username", default=None
)


def set_azure_username(username: Optional[str]) -> contextvars.Token:
    return _azure_username.set(username)


def reset_azure_username(token: contextvars.Token) -> None:
    _azure_username.reset(token)


@contextmanager
def azure_user_context(username: str) -> Iterator[None]:
    token = set_azure_username(username)
    try:
        yield
    finally:
        reset_azure_username(token)


def _azure_creds() -> dict[str, str]:
    username = _azure_username.get()
    if username:
        return resolve_azure_credentials(username)
    return resolve_azure_credentials("")


def azure_subscription_id() -> str:
    return (_azure_creds().get("subscription_id") or settings.AZURE_SUBSCRIPTION_ID or "").strip()


def azure_resource_group() -> str:
    creds = _azure_creds()
    return (
        (creds.get("resource_group") or "").strip()
        or getattr(settings, "AZURE_RESOURCE_GROUP", "zenith-rg")
    )


def azure_location() -> str:
    creds = _azure_creds()
    return (
        (creds.get("location") or "").strip()
        or getattr(settings, "AZURE_LOCATION", "eastus")
    )


def azure_service_principal() -> dict[str, str]:
    creds = _azure_creds()
    return {
        "subscription_id": azure_subscription_id(),
        "tenant_id": (creds.get("tenant_id") or settings.AZURE_TENANT_ID or "").strip(),
        "client_id": (creds.get("client_id") or settings.AZURE_CLIENT_ID or "").strip(),
        "client_secret": (
            creds.get("client_secret") or settings.AZURE_CLIENT_SECRET or ""
        ).strip(),
    }
