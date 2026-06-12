"""Register Azure resource providers before SDK provisioning."""

from __future__ import annotations

import time
from typing import Any

from app.provision.sdk_clients import azure_resource_client

_AZURE_MODULE_FLAGS: dict[str, str] = {
    "vnet": "enable_vnet",
    "azure_vm": "enable_azure_vm",
    "azure_monitor": "enable_azure_monitor",
    "azure_storage": "enable_azure_storage",
    "cosmos": "enable_cosmos",
}

# Namespaces required per enabled module (unioned before apply).
AZURE_MODULE_PROVIDERS: dict[str, tuple[str, ...]] = {
    "vnet": ("Microsoft.Network",),
    "azure_storage": ("Microsoft.Storage",),
    "azure_vm": ("Microsoft.Network", "Microsoft.Compute"),
    "azure_monitor": ("Microsoft.Insights",),
    "cosmos": ("Microsoft.DocumentDB",),
}

# Role assignments and resource groups rely on these being available.
AZURE_BASE_PROVIDERS = ("Microsoft.Resources", "Microsoft.Authorization")


def azure_providers_for_config(config: dict) -> list[str]:
    """Return sorted provider namespaces needed for the enabled Azure modules."""
    needed: set[str] = set(AZURE_BASE_PROVIDERS)
    for module, flag in _AZURE_MODULE_FLAGS.items():
        if config.get(flag):
            needed.update(AZURE_MODULE_PROVIDERS.get(module, ()))
    return sorted(needed)


def _registration_state(client: Any, namespace: str) -> str:
    return (client.providers.get(namespace).registration_state or "").strip()


def _is_registered(state: str) -> bool:
    return state.lower() == "registered"


def _wait_for_registered(
    client: Any,
    namespace: str,
    steps: list[str],
    *,
    timeout_sec: int = 600,
) -> None:
    """Poll until Azure marks the namespace Registered (often 1–10 min on new subs)."""
    deadline = time.time() + timeout_sec
    last_report = 0.0
    last_state = ""
    while time.time() < deadline:
        state = _registration_state(client, namespace)
        if _is_registered(state):
            return
        if state.lower() == "failed":
            raise RuntimeError(f"Azure provider '{namespace}' registration failed.")
        if state != last_state:
            steps.append(f"… {namespace} status: {state or 'unknown'}")
            last_state = state
        elif time.time() - last_report >= 30:
            steps.append(f"… still waiting on {namespace} ({state or 'Registering'})")
            last_report = time.time()
        time.sleep(5)
    final_state = _registration_state(client, namespace)
    raise RuntimeError(
        f"Timed out waiting for Azure provider '{namespace}' to register "
        f"(last status: {final_state or 'unknown'}). "
        "Register it manually: Azure Portal → Subscription → Resource providers → "
        f"{namespace} → Register, then retry Apply."
    )


def ensure_azure_resource_providers(
    config: dict,
    cloud_env: dict[str, str],
    *,
    timeout_sec: int = 600,
) -> dict[str, Any]:
    """Register required resource provider namespaces for this deployment."""
    namespaces = azure_providers_for_config(config)
    if not namespaces:
        return {"success": True, "steps": [], "error": None}

    steps: list[str] = []
    try:
        client, _, _ = azure_resource_client(cloud_env)
        for namespace in namespaces:
            state = _registration_state(client, namespace)
            if _is_registered(state):
                continue
            if state.lower() == "registering":
                steps.append(f"Azure provider {namespace} is already registering…")
            else:
                steps.append(f"Registering Azure provider {namespace}…")
                client.providers.register(namespace)
            _wait_for_registered(client, namespace, steps, timeout_sec=timeout_sec)
            steps.append(f"✓ Provider {namespace} registered")
        return {"success": True, "steps": steps, "error": None}
    except Exception as exc:
        msg = str(exc)
        if "Authorization" in msg or "403" in msg or "does not have authorization" in msg.lower():
            providers = ", ".join(namespaces)
            msg = (
                "Azure credentials cannot register resource providers for this subscription. "
                f"Ask a subscription admin to register: {providers}. "
                "Portal: Subscription → Settings → Resource providers. "
                "Or grant Contributor on the subscription to the provisioning service principal."
            )
        elif "MissingSubscriptionRegistration" in msg:
            namespace = msg.split("'")[1] if "'" in msg else "Microsoft.Network"
            msg = (
                f"Subscription is not registered for {namespace}. "
                "Zenith attempted auto-registration; retry apply in 1–2 minutes, "
                "or register the provider manually in the Azure portal."
            )
        return {"success": False, "steps": steps, "error": msg}
