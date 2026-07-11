"""Password strength validation for register, reset, and profile change."""

from __future__ import annotations

import re

from fastapi import HTTPException

_MIN_LENGTH = 8
_COMPLEXITY = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).+$"
)


def validate_password_strength(password: str, *, field_name: str = "Password") -> None:
    if not password or len(password) < _MIN_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must be at least {_MIN_LENGTH} characters.",
        )
    if len(password) > 128:
        raise HTTPException(status_code=400, detail=f"{field_name} is too long.")
    if not _COMPLEXITY.match(password):
        raise HTTPException(
            status_code=400,
            detail=(
                f"{field_name} must include uppercase, lowercase, a number, and a symbol."
            ),
        )
