"""Disable slowapi limiters (used by pytest and Playwright CI when ENVIRONMENT=test)."""


def disable_rate_limits(fastapi_app) -> None:
    """Auth routes use module-level Limiters, not only app.state.limiter."""
    limiters = []
    if getattr(fastapi_app.state, "limiter", None) is not None:
        limiters.append(fastapi_app.state.limiter)

    from app.auth import routes_auth, routes_password_reset
    from app.contact import routes_contact as contact_routes_mod
    from app.utils import resource_limiter as resource_limiter_mod

    limiters.extend([
        routes_auth.limiter,
        routes_password_reset.limiter,
        resource_limiter_mod.resource_limiter,
        contact_routes_mod.contact_limiter,
    ])

    for limiter in limiters:
        limiter.enabled = False
        storage = getattr(limiter, "_storage", None)
        if storage is not None and hasattr(storage, "storage"):
            storage.storage.clear()
        elif storage is not None and hasattr(storage, "clear"):
            storage.clear()
