"""Safe defaults and tag merging for provision wizard configs."""

from __future__ import annotations

from typing import Any

from app.provision.provision_catalog import apply_template_defaults

VALID_ENVIRONMENTS = frozenset({"dev", "staging", "prod", "free-tier"})

SIZE_PROFILES: dict[str, dict[str, str]] = {
    "micro": {
        "AWS": "t2.micro",
        "GCP": "e2-micro",
        "Azure": "Standard_B1s",
    },
    "small": {
        "AWS": "t3.small",
        "GCP": "e2-small",
        "Azure": "Standard_B2s",
    },
    "medium": {
        "AWS": "t3.medium",
        "GCP": "e2-medium",
        "Azure": "Standard_B2ms",
    },
}


def apply_safe_defaults(config: dict[str, Any]) -> None:
    """Merge template flags, environment tags, and zenith metadata in-place."""
    apply_template_defaults(config)

    env = str(config.get("environment") or "free-tier").lower()
    if env not in VALID_ENVIRONMENTS:
        env = "free-tier"
    config["environment"] = env

    template = config.get("template") or "custom"
    tags = dict(config.get("tags") or {})
    tags.setdefault("Env", env)
    tags["zenith-managed"] = "true"
    if template and template != "custom":
        tags["zenith-template"] = str(template)
    config["tags"] = tags

    if not config.get("deployment_display_name"):
        config["deployment_display_name"] = f"zenith-{template}-{env}"

    disk = int(config.get("disk_size_gb") or 30)
    config["disk_size_gb"] = max(8, min(disk, 2000))

    csp = (config.get("csp") or "AWS").upper()
    profile = config.get("size_profile") or "micro"
    sizes = SIZE_PROFILES.get(profile, SIZE_PROFILES["micro"])
    if csp == "AWS" and config.get("enable_ec2"):
        config.setdefault("instance_type", sizes["AWS"])
    elif csp == "GCP" and config.get("enable_gce"):
        config.setdefault("machine_type", sizes["GCP"])
    elif csp == "Azure" and config.get("enable_azure_vm"):
        config.setdefault("vm_size", sizes["Azure"])


def skeleton_config_for_template(
    csp: str,
    template: str,
    *,
    size_profile: str = "micro",
    environment: str = "free-tier",
) -> dict[str, Any]:
    """Build a minimal config dict for compare/estimate."""
    cfg: dict[str, Any] = {
        "csp": csp,
        "template": template,
        "environment": environment,
        "size_profile": size_profile,
        "disk_size_gb": 30,
    }
    apply_safe_defaults(cfg)
    return cfg
