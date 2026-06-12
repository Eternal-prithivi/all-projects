"""Per-request platform region slug for VM compute (asia / us / europe / africa)."""

from __future__ import annotations

import contextvars
from typing import Optional

_platform_region_slug: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "vm_platform_region_slug",
    default=None,
)


def set_platform_region_slug(slug: Optional[str]) -> contextvars.Token:
    return _platform_region_slug.set((slug or "").strip().lower() or None)


def reset_platform_region_slug(token: contextvars.Token) -> None:
    _platform_region_slug.reset(token)


def get_platform_region_slug() -> Optional[str]:
    return _platform_region_slug.get()
