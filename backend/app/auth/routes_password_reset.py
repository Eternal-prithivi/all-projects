"""Forgot password / reset password routes (public, rate-limited)."""

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.auth.password_reset_service import (
    GENERIC_MESSAGE,
    complete_password_reset,
    request_password_reset_email,
    request_password_reset_sms,
)
from app.utils.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(tags=["Authentication"])


class ForgotPasswordRequest(BaseModel):
    identifier: str = Field(..., description="Registered email or username")
    method: str = Field("email", pattern="^(email|sms)$")


class ResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=8)
    method: str = Field("email", pattern="^(email|sms)$")
    token: str | None = Field(None, description="Token from email link")
    otp: str | None = Field(None, description="6-digit SMS code")
    identifier: str | None = Field(None, description="Email/username (required for SMS)")


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(request: Request, body: ForgotPasswordRequest):
    """
    Request password reset via email link or SMS OTP.
    Always returns the same message to avoid account enumeration.
    """
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")

    if body.method == "sms":
        result = request_password_reset_sms(body.identifier)
    else:
        result = request_password_reset_email(body.identifier, frontend_url)

    response = {
        "message": GENERIC_MESSAGE if result.sent or not result.account_matched else "We could not send reset instructions.",
        "method": body.method,
        "sent": result.sent,
    }
    if result.hint:
        response["hint"] = result.hint
    return response


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(request: Request, body: ResetPasswordRequest):
    """Complete password reset with email token or SMS OTP."""
    success, error = complete_password_reset(
        new_password=body.new_password,
        method=body.method,  # type: ignore[arg-type]
        token=body.token,
        otp=body.otp,
        identifier=body.identifier,
    )
    if not success:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=error or "Reset failed")

    return {"message": "Password updated successfully. You can sign in now."}
