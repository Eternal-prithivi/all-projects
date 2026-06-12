"""Plain-English deployment review summaries."""

from __future__ import annotations

from typing import Any, List

from app.cloud.providers import normalize_provider
from app.provision.cost_estimator import estimate_from_config
from app.provision.provision_catalog import enabled_module_keys


def build_review_summary(config: dict[str, Any]) -> dict[str, Any]:
    """Human-readable bullets + counts for the review step."""
    csp = normalize_provider(config.get("csp") or "AWS")
    env = config.get("environment") or "free-tier"
    template = config.get("template") or "custom"
    display = config.get("deployment_display_name") or template

    modules = enabled_module_keys(config)
    estimate = estimate_from_config(config)

    bullets: List[str] = []
    warnings: List[str] = []

    bullets.append(f'Deployment "{display}" in {csp} ({env} environment).')

    if config.get("enable_ec2") or config.get("enable_gce") or config.get("enable_azure_vm"):
        inst = (
            config.get("instance_type")
            or config.get("machine_type")
            or config.get("vm_size")
            or "small VM"
        )
        disk = config.get("disk_size_gb", 30)
        if config.get("enable_ec2"):
            os_label = config.get("ec2_os", "amazon_linux_2").replace("_", " ")
        elif config.get("enable_gce"):
            os_label = config.get("gce_os", "debian_12").replace("_", " ")
        else:
            os_label = config.get("azure_os", "ubuntu_22_04").replace("_", " ")
        bullets.append(f"1 virtual server ({inst}, {os_label}) with about {disk} GB disk.")
        startup = (
            (config.get("ec2_user_data") or "")
            or (config.get("gce_startup_script") or "")
            or (config.get("azure_startup_script") or "")
        ).strip()
        if startup:
            bullets.append("Bootstrap script runs on first boot.")

    if config.get("enable_vpc") or config.get("enable_gcp_network") or config.get("enable_vnet"):
        bullets.append("Private network (VPC/VNet) for isolation.")

    if config.get("enable_s3") or config.get("enable_gcs") or config.get("enable_azure_storage"):
        bullets.append("Object storage bucket for static files or assets.")

    if config.get("enable_dynamodb") or config.get("enable_firestore") or config.get("enable_cosmos"):
        bullets.append("Managed database for application data.")

    if config.get("enable_cloudwatch") or config.get("enable_gcp_monitoring") or config.get("enable_azure_monitor"):
        bullets.append("Monitoring alerts for operational visibility.")

    if config.get("enable_iam"):
        from app.provision.provision_config_options import plan_iam_preset_summary

        preset = plan_iam_preset_summary(config.get("iam_role_preset", "s3_read_only"))
        bullets.append(f"EC2 IAM role attached at launch ({preset}).")
    elif config.get("enable_gcp_service_account"):
        from app.provision.provision_config_options import plan_gcp_sa_preset_summary

        preset = plan_gcp_sa_preset_summary(config.get("gcp_sa_preset", "gcs_read_only"))
        bullets.append(f"GCE service account with {preset} permissions.")
    elif config.get("enable_azure_vm"):
        from app.provision.provision_config_options import plan_azure_identity_preset_summary

        preset = plan_azure_identity_preset_summary(
            config.get("azure_identity_preset", "storage_blob_read")
        )
        bullets.append(f"Azure VM managed identity ({preset}).")

    region = (
        config.get("aws_region")
        or config.get("gcp_region")
        or config.get("azure_location")
        or "default region"
    )
    bullets.append(f"Region: {region}.")

    bullets.append(f"Estimated cost: about ${estimate.total_monthly_cost}/month.")

    if float(estimate.total_monthly_cost or "0") > 0:
        warnings.append("This stack may incur charges beyond free tier limits.")

    if env == "prod" and not (
        config.get("enable_cloudwatch")
        or config.get("enable_gcp_monitoring")
        or config.get("enable_azure_monitor")
    ):
        warnings.append("Production stacks should include monitoring.")

    return {
        "plain_english_bullets": bullets,
        "warnings": warnings,
        "resource_module_count": len(modules),
        "estimated_monthly": estimate.total_monthly_cost,
        "currency": estimate.currency,
        "template": template,
        "csp": csp,
        "environment": env,
    }
