"""Per-cloud provisioning templates and module metadata."""

from __future__ import annotations

from typing import Any

AWS_TEMPLATES: list[dict[str, Any]] = [
    {
        "key": "static-site",
        "name": "Static Website (S3 Only)",
        "description": "Host a static HTML/CSS/JS website on S3. Free tier eligible.",
        "services": {"enable_s3": True},
        "estimated_cost": "$0.00/month",
        "icon": "globe",
    },
    {
        "key": "backend-app",
        "name": "Backend Application (VPC + EC2 + IAM)",
        "description": "EC2 instance with VPC networking and IAM role. Free tier eligible.",
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
        "name": "Serverless Database (DynamoDB)",
        "description": "DynamoDB table with provisioned capacity within free limits.",
        "services": {"enable_dynamodb": True},
        "estimated_cost": "$0.00/month",
        "icon": "database",
    },
]

GCP_TEMPLATES: list[dict[str, Any]] = [
    {
        "key": "static-gcs",
        "name": "Static Website (GCS)",
        "description": "Private GCS bucket for static site assets. Uses your BYOC GCP project.",
        "services": {"enable_gcs": True},
        "estimated_cost": "$0.00/month",
        "icon": "globe",
    },
]

AZURE_TEMPLATES: list[dict[str, Any]] = [
    {
        "key": "static-blob",
        "name": "Static Website (Blob Storage)",
        "description": "Storage account and private container for static assets.",
        "services": {"enable_azure_storage": True},
        "estimated_cost": "$0.00/month",
        "icon": "globe",
    },
]

AWS_MODULES = [
    {"key": "vpc", "name": "VPC", "flag": "enable_vpc"},
    {"key": "ec2", "name": "EC2", "flag": "enable_ec2", "requires": ["vpc"]},
    {"key": "s3", "name": "S3", "flag": "enable_s3"},
    {"key": "iam", "name": "IAM", "flag": "enable_iam"},
    {"key": "cloudwatch", "name": "CloudWatch", "flag": "enable_cloudwatch", "requires": ["ec2"]},
    {"key": "dynamodb", "name": "DynamoDB", "flag": "enable_dynamodb"},
]

GCP_MODULES = [
    {"key": "gcs", "name": "Cloud Storage", "flag": "enable_gcs"},
]

AZURE_MODULES = [
    {"key": "azure_storage", "name": "Blob Storage", "flag": "enable_azure_storage"},
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


def apply_template_defaults(config: dict) -> None:
    """Apply template preset flags for the config's csp."""
    template = config.get("template")
    if not template or template == "custom":
        return
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
