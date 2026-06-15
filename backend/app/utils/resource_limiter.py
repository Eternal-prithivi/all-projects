"""Shared rate limiters for resource-intensive API routes."""

from slowapi import Limiter
from slowapi.util import get_remote_address

resource_limiter = Limiter(key_func=get_remote_address)
