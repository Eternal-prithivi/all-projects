# =============================================================================
# MODULE: auth_utils.py  (104 lines)
# PURPOSE: Core auth dependencies used by EVERY route in the backend
#   - get_password_hash() / verify_password()  — bcrypt wrappers
#   - get_current_user()  — decodes JWT → returns UserInDB (use for normal routes)
#   - require_2fa()       — same as above + enforces 2FA verified flag
#   - mark_2fa_unverified() — called on every login to reset 2FA session state
# USED BY: Almost every route file in the project via Depends(get_current_user)
#          Security endpoints use Depends(require_2fa) instead
# DO NOT:
#   - Add bcrypt work factor changes without testing performance impact
#   - Change the JWT payload format (sub: username) — all routes decode this
#   - Remove the 2fa_verified flag check from require_2fa() — breaks vault security
# =============================================================================
import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from app.database.mongo_client import get_users_collection
from app.users.user_model import UserInDB
from app.utils.config import settings
from fastapi import WebSocket, status, Query, Request
# --- existing password functions ---

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# --- JWT authentication ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token", auto_error=False)


def _resolve_bearer_token(
    request: Request,
    bearer_token: Optional[str] = Depends(oauth2_scheme),
) -> str:
    from app.auth.cookie_auth import get_access_token_from_request

    cookie_token = get_access_token_from_request(request)
    if cookie_token:
        return cookie_token
    if bearer_token:
        return bearer_token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    request: Request,
    token: str = Depends(_resolve_bearer_token),
) -> UserInDB:
    """
    Decodes the JWT token and fetches the current user from the database.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    users_col = get_users_collection()
    user_data = users_col.find_one({"username": username})

    if user_data is None:
        raise credentials_exception
    if user_data.get("deleted") or user_data.get("status") == "deleted":
        raise credentials_exception
    acct_status = (user_data.get("status") or "active").lower()
    if acct_status in ("suspended", "banned"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ACCOUNT_SUSPENDED",
                "message": f"Account is {acct_status}.",
            },
        )
    return UserInDB(**user_data)


def get_current_user_optional(
    request: Request,
    bearer_token: Optional[str] = Depends(oauth2_scheme),
) -> Optional[UserInDB]:
    """Return user when authenticated; None when no/invalid credentials (no 401)."""
    from app.auth.cookie_auth import get_access_token_from_request

    token = get_access_token_from_request(request) or bearer_token
    if not token:
        return None
    try:
        return get_current_user(request=request, token=token)
    except HTTPException:
        return None


# --- 2FA specific functions ---
def mark_2fa_unverified(username: str):
    """
    Resets the 2FA verified flag for the user.
    This should be called after a user logs in.
    """
    users_col = get_users_collection()
    users_col.update_one({"username": username}, {"$set": {"two_fa_verified": False}})

def require_2fa(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """
    A dependency that enforces 2FA verification for an endpoint.
    """
    if current_user.two_fa_enabled and not current_user.two_fa_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="2FA verification is required to access this resource."
        )
    return current_user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def get_current_user_ws(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
) -> UserInDB:
    """
    WebSocket auth: query token (legacy) or zenith_access cookie.
    """
    from app.auth.cookie_auth import ACCESS_COOKIE_NAME

    raw_token = token or websocket.cookies.get(ACCESS_COOKIE_NAME)
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not raw_token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise credentials_exception
    try:
        payload = jwt.decode(raw_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        # Close the connection with a specific code for authentication failure
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise credentials_exception

    users_col = get_users_collection()
    user_data = users_col.find_one({"username": username})

    if user_data is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise credentials_exception
        
    return UserInDB(**user_data)