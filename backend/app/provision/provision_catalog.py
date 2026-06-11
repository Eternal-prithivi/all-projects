"""Per-cloud provisioning templates and module metadata."""

from __future__ import annotations

from typing import Any

AWS_TEMPLATES: list[dict[str, Any]] = [
    {
        "key": "static-site",
        "name": "Static Website (Amazon S3)",
        "description": "Host a static HTML/CSS/JS website on S3. Private, encrypted, free tier eligible.",
        "services": {"enable_s3": True},
        "estimated_cost": "$0.00/month",
        "icon": "globe",
    },
    {
        "key": "backend-app",
        "name": "Backend Application (VPC + EC2 + IAM)",
        "description": "EC2 instance with VPC networking, IAM role, and CloudWatch monitoring.",
        "services": {
            "enable_vpc": True,
            "enable_ec2": True,
            "enable_iam": True,
            "enable_cloudwatch": True,
        },
        "estimated_cost": "$0.00/month",
        "icon": "server",
    },
    {
        "key": "serverless-db",
        "name": "Serverless Database (Amazon DynamoDB)",
        "description": "DynamoDB table with provisioned capacity within AWS always-free limits.",
        "services": {"enable_dynamodb": True},
        "estimated_cost": "$0.00/month",
        "icon": "database",
    },
]

GCP_TEMPLATES: list[dict[str, Any]] = [
    {
        "key": "static-site",
        "name": "Static Website (Google Cloud Storage)",
        "description": "Private GCS bucket for static site assets with uniform access. BYOC GCP project.",
        "services": {"enable_gcs": True},
        "estimated_cost": "$0.00/month",
        "icon": "globe",
    },
    {
        "key": "backend-app",
        "name": "Backend Application (VPC + Compute Engine)",
        "description": "e2-micro VM on a custom VPC, service account, and Cloud Monitoring CPU alert.",
        "services": {
            "enable_gcp_network": True,
            "enable_gce": True,
            "enable_gcp_service_account": True,
            "enable_gcp_monitoring": True,
        },
        "estimated_cost": "$0.00/month",
        "icon": "server",
    },
    {
        "key": "serverless-db",
        "name": "Serverless Database (Cloud Firestore)",
        "description": "Firestore Native database in your GCP region for document workloads.",
        "services": {"enable_firestore": True},
        "estimated_cost": "$0.00/month",
        "icon": "database",
    },
]

AZURE_TEMPLATES: list[dict[str, Any]] = [
    {
        "key": "static-site",
        "name": "Static Website (Azure Blob Storage)",
        "description": "Storage account and private container for static site assets.",
        "services": {"enable_azure_storage": True},
        "estimated_cost": "$0.00/month",
        "icon": "globe",
    },
    {
        "key": "backend-app",
        "name": "Backend Application (VNet + Linux VM)",
        "description": "Standard_B1s Linux VM on a VNet with optional email alerts via Monitor.",
        "services": {
            "enable_vnet": True,
            "enable_azure_vm": True,
            "enable_azure_monitor": True,
        },
        "estimated_cost": "$0.00/month",
        "icon": "server",
    },
    {
        "key": "serverless-db",
        "name": "Serverless Database (Azure Cosmos DB)",
        "description": "Cosmos DB SQL API account and database for globally distributed NoSQL.",
        "services": {"enable_cosmos": True},
        "estimated_cost": "$5.00/month",
        "icon": "database",
    },
]

AWS_MODULES = [
    {"key": "vpc", "name": "VPC", "flag": "enable_vpc", "desc": "Virtual Private Cloud with public/private subnets"},
    {"key": "ec2", "name": "EC2", "flag": "enable_ec2", "requires": ["vpc"], "desc": "Elastic Compute Cloud instance (t2.micro free tier)"},
    {"key": "s3", "name": "S3", "flag": "enable_s3", "desc": "Simple Storage Service bucket (5 GB free tier)"},
    {"key": "iam", "name": "IAM", "flag": "enable_iam", "desc": "Identity & Access Management role"},
    {"key": "cloudwatch", "name": "CloudWatch", "flag": "enable_cloudwatch", "requires": ["ec2"], "desc": "Monitoring & email alerting"},
    {"key": "dynamodb", "name": "DynamoDB", "flag": "enable_dynamodb", "desc": "NoSQL database table (25 RCU/WCU free tier)"},
    {"key": "billing", "name": "AWS Budgets", "flag": "enable_billing", "desc": "Monthly cost budget with email alerts (requires budgets:* IAM)"},
]

GCP_MODULES = [
    {"key": "gcs", "name": "Cloud Storage", "flag": "enable_gcs", "desc": "GCS bucket for static assets or object storage"},
    {"key": "gcp_network", "name": "VPC Network", "flag": "enable_gcp_network", "desc": "Custom VPC and regional subnet"},
    {"key": "gce", "name": "Compute Engine", "flag": "enable_gce", "requires": ["gcp_network"], "desc": "e2-micro VM (free tier eligible in select regions)"},
    {"key": "gcp_service_account", "name": "Service Account", "flag": "enable_gcp_service_account", "desc": "Dedicated service account with optional GCS viewer"},
    {"key": "gcp_monitoring", "name": "Cloud Monitoring", "flag": "enable_gcp_monitoring", "requires": ["gce"], "desc": "CPU utilization alert policy"},
    {"key": "firestore", "name": "Firestore", "flag": "enable_firestore", "desc": "Firestore Native serverless database"},
]

AZURE_MODULES = [
    {"key": "azure_storage", "name": "Blob Storage", "flag": "enable_azure_storage", "desc": "Storage account and private blob container"},
    {"key": "vnet", "name": "Virtual Network", "flag": "enable_vnet", "desc": "VNet with subnet for compute workloads"},
    {"key": "azure_vm", "name": "Linux Virtual Machine", "flag": "enable_azure_vm", "requires": ["vnet"], "desc": "Standard_B1s Ubuntu VM (free tier eligible)"},
    {"key": "azure_monitor", "name": "Azure Monitor", "flag": "enable_azure_monitor", "desc": "Email action group for operational alerts"},
    {"key": "cosmos", "name": "Cosmos DB", "flag": "enable_cosmos", "desc": "Cosmos DB SQL API account and database"},
]


def templates_for_csp(csp: str) -> list[dict[str, Any]]:
    from app.cloud.providers import normalize_provider

    provider = normalize_provider(csp)
    if provider == "GCP":
        return GCP_TEMPLATES
    if provider == "Azure":
        return AZURE_TEMPLATES
    return AWS_TEMPLATES


def modules_for_csp(csp: str) -> list[dict[str, Any]]:
    from app.cloud.providers import normalize_provider

    provider = normalize_provider(csp)
    if provider == "GCP":
        return GCP_MODULES
    if provider == "Azure":
        return AZURE_MODULES
    return AWS_MODULES


_TEMPLATE_ALIASES = {
    "static-gcs": "static-site",
    "static-blob": "static-site",
}


def apply_template_defaults(config: dict) -> None:
    """Apply template preset flags for the config's csp."""
    template = config.get("template")
    if not template or template == "custom":
        return
    template = _TEMPLATE_ALIASES.get(template, template)
    config["template"] = template
    csp = config.get("csp") or "AWS"
    for tmpl in templates_for_csp(csp):
        if tmpl["key"] == template:
            for flag, value in tmpl["services"].items():
                config[flag] = value
            break


def enabled_module_keys(config: dict) -> list[str]:
    csp = config.get("csp") or "AWS"
    modules = modules_for_csp(csp)
    return [m["key"] for m in modules if config.get(m["flag"], False)]
