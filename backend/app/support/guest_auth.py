"""Short-lived JWT for guest ticket access after OTP verification."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.support.constants import GUEST_TOKEN_HOURS
from app.utils.config import settings

guest_bearer = HTTPBearer(auto_error=False)

GUEST_TOKEN_TYPE = "guest_ticket"


def create_guest_ticket_token(*, reference_code: str, email: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=GUEST_TOKEN_HOURS)
    payload = {
        "sub": reference_code.upper().strip(),
        "typ": GUEST_TOKEN_TYPE,
        "email": email.strip().lower(),
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_guest_ticket_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired guest access token",
        ) from exc
    if payload.get("typ") != GUEST_TOKEN_TYPE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid guest access token",
        )
    return payload


def get_guest_ticket_access(
    reference_code: str,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(guest_bearer),
) -> dict:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Guest verification required",
        )
    payload = decode_guest_ticket_token(credentials.credentials)
    ref = reference_code.upper().strip()
    if payload.get("sub") != ref:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token does not match this ticket",
        )
    return payload
