"""Per-domain circuit breakers — isolate failures without splitting processes."""

from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterator, Optional

from fastapi import HTTPException

MODULE_NAMES = (
    "auth",
    "core",
    "storage",
    "compute",
    "provision",
    "billing",
    "admin",
)

_FAILURE_THRESHOLD = 3
_COOLDOWN_SECONDS = 60


@dataclass
class _ModuleState:
    failures: int = 0
    open_until: float = 0.0
    last_error: Optional[str] = None


_lock = threading.Lock()
_states: Dict[str, _ModuleState] = {name: _ModuleState() for name in MODULE_NAMES}


def _state(module: str) -> _ModuleState:
    if module not in _states:
        _states[module] = _ModuleState()
    return _states[module]


def is_module_available(module: str) -> bool:
    st = _state(module)
    return time.monotonic() >= st.open_until


def record_module_success(module: str) -> None:
    with _lock:
        st = _state(module)
        st.failures = 0
        st.open_until = 0.0
        st.last_error = None


def record_module_failure(module: str, error: Exception | str) -> None:
    with _lock:
        st = _state(module)
        st.failures += 1
        st.last_error = str(error)
        if st.failures >= _FAILURE_THRESHOLD:
            st.open_until = time.monotonic() + _COOLDOWN_SECONDS


def module_health_snapshot() -> Dict[str, Any]:
    now = time.monotonic()
    out: Dict[str, Any] = {}
    for name in MODULE_NAMES:
        st = _state(name)
        out[name] = {
            "status": "up" if now >= st.open_until else "down",
            "failures": st.failures,
            "last_error": st.last_error,
        }
    return out


def assert_module_available(module: str) -> None:
    if not is_module_available(module):
        raise HTTPException(
            status_code=503,
            detail={
                "code": "MODULE_UNAVAILABLE",
                "module": module,
                "message": f"The {module} service is temporarily unavailable. Try again shortly.",
            },
        )


@contextmanager
def module_guard(module: str) -> Iterator[None]:
    assert_module_available(module)
    try:
        yield
        record_module_success(module)
    except HTTPException:
        raise
    except Exception as exc:
        record_module_failure(module, exc)
        raise


def guarded(module: str, fn: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator for route handlers that belong to a domain module."""

    def wrapper(*args: Any, **kwargs: Any):
        with module_guard(module):
            return fn(*args, **kwargs)

    return wrapper
