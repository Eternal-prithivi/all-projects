"""Disable slowapi limiters (used by pytest and Playwright CI when ENVIRONMENT=test)."""


def disable_rate_limits(fastapi_app) -> None:
    """Auth routes use module-level Limiters, not only app.state.limiter."""
    limiters = []
    if getattr(fastapi_app.state, "limiter", None) is not None:
        limiters.append(fastapi_app.state.limiter)

    from app.auth import routes_auth, routes_password_reset

    limiters.extend([routes_auth.limiter, routes_password_reset.limiter])

    for limiter in limiters:
        limiter.enabled = False
        storage = getattr(limiter, "_storage", None)
        if storage is not None and hasattr(storage, "storage"):
            storage.storage.clear()
        elif storage is not None and hasattr(storage, "clear"):
            storage.clear()
