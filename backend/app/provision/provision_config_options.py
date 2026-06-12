"""Shared provision wizard options — AWS / GCP / Azure VM and identity presets."""

from __future__ import annotations

import base64
from typing import Any

IAM_ROLE_PRESETS: dict[str, dict[str, Any]] = {
    "s3_read_only": {
        "label": "S3 read only",
        "description": "List and download objects from your stack S3 bucket (default).",
    },
    "s3_read_write": {
        "label": "S3 read & write",
        "description": "Upload, download, and delete objects in your stack S3 bucket.",
    },
    "ssm_session": {
        "label": "SSM Session Manager",
        "description": "Connect to the instance via AWS Session Manager (no SSH keys required).",
    },
    "s3_read_ssm": {
        "label": "S3 read + SSM",
        "description": "Read S3 objects and use Session Manager for shell access.",
    },
    "dynamodb_app": {
        "label": "DynamoDB app access",
        "description": "Read/write items in your stack DynamoDB table (enable DynamoDB module).",
    },
    "minimal": {
        "label": "Trust only (no AWS API access)",
        "description": "EC2 role with no permissions — attach policies later in AWS console.",
    },
}

EC2_OS_IMAGES: dict[str, dict[str, Any]] = {
    "amazon_linux_2": {
        "label": "Amazon Linux 2",
        "description": "Stable, widely used — good default for most apps.",
        "owners": ["amazon"],
        "name_filter": "amzn2-ami-hvm-*-x86_64-gp2",
        "root_device": "/dev/xvda",
        "user_data_shell": "bash",
    },
    "amazon_linux_2023": {
        "label": "Amazon Linux 2023",
        "description": "Newer Amazon Linux with long-term support.",
        "owners": ["amazon"],
        "name_filter": "al2023-ami-2023*-x86_64",
        "root_device": "/dev/xvda",
        "user_data_shell": "bash",
    },
    "ubuntu_22_04": {
        "label": "Ubuntu 22.04 LTS",
        "description": "Popular Ubuntu LTS for Debian-style tooling (apt).",
        "owners": ["099720109477"],
        "name_filter": "ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*",
        "root_device": "/dev/sda1",
        "user_data_shell": "bash",
    },
    "ubuntu_24_04": {
        "label": "Ubuntu 24.04 LTS",
        "description": "Latest Ubuntu LTS.",
        "owners": ["099720109477"],
        "name_filter": "ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*",
        "root_device": "/dev/sda1",
        "user_data_shell": "bash",
    },
}

SSM_MANAGED_POLICY_ARN = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"

GCP_SA_PRESETS: dict[str, dict[str, Any]] = {
    "gcs_read_only": {
        "label": "GCS read only",
        "description": "List and download objects from your stack GCS bucket (default).",
    },
    "gcs_read_write": {
        "label": "GCS read & write",
        "description": "Upload, download, and delete objects in your stack bucket.",
    },
    "firestore_app": {
        "label": "Firestore app access",
        "description": "Read/write Firestore data (enable Firestore module).",
    },
    "logging_writer": {
        "label": "Cloud Logging writer",
        "description": "Write application logs to Cloud Logging.",
    },
    "gcs_read_logging": {
        "label": "GCS read + Logging",
        "description": "Read GCS objects and write logs.",
    },
    "minimal": {
        "label": "Service account only (no roles)",
        "description": "Create SA for attachment — grant roles later in GCP console.",
    },
}

GCE_OS_IMAGES: dict[str, dict[str, Any]] = {
    "debian_12": {
        "label": "Debian 12",
        "description": "Default stable image for GCE.",
        "source_image": "projects/debian-cloud/global/images/family/debian-12",
        "startup_shell": "bash",
    },
    "ubuntu_22_04": {
        "label": "Ubuntu 22.04 LTS",
        "description": "Ubuntu LTS (apt).",
        "source_image": "projects/ubuntu-os-cloud/global/images/family/ubuntu-2204-lts",
        "startup_shell": "bash",
    },
    "ubuntu_24_04": {
        "label": "Ubuntu 24.04 LTS",
        "description": "Latest Ubuntu LTS.",
        "source_image": "projects/ubuntu-os-cloud/global/images/family/ubuntu-2404-lts-amd64",
        "startup_shell": "bash",
    },
    "cos_stable": {
        "label": "Container-Optimized OS",
        "description": "Google COS — ideal for Docker/Kubernetes workloads.",
        "source_image": "projects/cos-cloud/global/images/family/cos-stable",
        "startup_shell": "bash",
    },
}

AZURE_IDENTITY_PRESETS: dict[str, dict[str, Any]] = {
    "storage_blob_read": {
        "label": "Blob Storage read",
        "description": "Read blobs in your stack storage account (default).",
        "role_name": "Storage Blob Data Reader",
        "role_id": "2a2b9908-6ea1-4ae2-8e65-a410df84e7d1",
    },
    "storage_blob_contributor": {
        "label": "Blob Storage read & write",
        "description": "Read, write, and delete blobs in your storage account.",
        "role_name": "Storage Blob Data Contributor",
        "role_id": "ba92f5a4-2d11-453d-a403-e96b0029c9fe",
    },
    "cosmos_data_contributor": {
        "label": "Cosmos DB access",
        "description": "Manage Cosmos DB account resources (enable Cosmos module).",
        "role_name": "DocumentDB Account Contributor",
        "role_id": "5bd9cd88-fe45-4216-938b-f97437e15450",
    },
    "minimal": {
        "label": "Managed identity only (no roles)",
        "description": "System-assigned identity with no RBAC — assign roles later.",
        "role_name": "",
        "role_id": "",
    },
}

AZURE_OS_IMAGES: dict[str, dict[str, Any]] = {
    "ubuntu_22_04": {
        "label": "Ubuntu 22.04 LTS",
        "description": "Canonical Ubuntu Jammy (default).",
        "image_reference": {
            "publisher": "Canonical",
            "offer": "0001-com-ubuntu-server-jammy",
            "sku": "22_04-lts",
            "version": "latest",
        },
        "startup_shell": "bash",
    },
    "ubuntu_24_04": {
        "label": "Ubuntu 24.04 LTS",
        "description": "Canonical Ubuntu Noble.",
        "image_reference": {
            "publisher": "Canonical",
            "offer": "ubuntu-24_04-lts",
            "sku": "server",
            "version": "latest",
        },
        "startup_shell": "bash",
    },
    "debian_12": {
        "label": "Debian 12",
        "description": "Debian bookworm.",
        "image_reference": {
            "publisher": "Debian",
            "offer": "debian-12",
            "sku": "12",
            "version": "latest",
        },
        "startup_shell": "bash",
    },
    "azure_linux": {
        "label": "Azure Linux 3",
        "description": "Microsoft Azure Linux image.",
        "image_reference": {
            "publisher": "Microsoft",
            "offer": "azure-linux-3",
            "sku": "azure-linux-3",
            "version": "latest",
        },
        "startup_shell": "bash",
    },
}

GCP_PROJECT_ROLES = {
    "logging_writer": "roles/logging.logWriter",
    "firestore_app": "roles/datastore.user",
}


def list_iam_role_presets() -> list[dict[str, str]]:
    return [
        {"id": key, "label": meta["label"], "description": meta["description"]}
        for key, meta in IAM_ROLE_PRESETS.items()
    ]


def list_ec2_os_images() -> list[dict[str, str]]:
    return [
        {"id": key, "label": meta["label"], "description": meta["description"]}
        for key, meta in EC2_OS_IMAGES.items()
    ]


def list_gcp_sa_presets() -> list[dict[str, str]]:
    return [
        {"id": key, "label": meta["label"], "description": meta["description"]}
        for key, meta in GCP_SA_PRESETS.items()
    ]


def list_gce_os_images() -> list[dict[str, str]]:
    return [
        {"id": key, "label": meta["label"], "description": meta["description"]}
        for key, meta in GCE_OS_IMAGES.items()
    ]


def list_azure_identity_presets() -> list[dict[str, str]]:
    return [
        {"id": key, "label": meta["label"], "description": meta["description"]}
        for key, meta in AZURE_IDENTITY_PRESETS.items()
    ]


def list_azure_os_images() -> list[dict[str, str]]:
    return [
        {"id": key, "label": meta["label"], "description": meta["description"]}
        for key, meta in AZURE_OS_IMAGES.items()
    ]


def normalize_iam_role_preset(value: str | None) -> str:
    key = (value or "s3_read_only").strip()
    return key if key in IAM_ROLE_PRESETS else "s3_read_only"


def normalize_ec2_os(value: str | None) -> str:
    key = (value or "amazon_linux_2").strip()
    return key if key in EC2_OS_IMAGES else "amazon_linux_2"


def normalize_gcp_sa_preset(value: str | None) -> str:
    key = (value or "gcs_read_only").strip()
    return key if key in GCP_SA_PRESETS else "gcs_read_only"


def normalize_gce_os(value: str | None) -> str:
    key = (value or "debian_12").strip()
    return key if key in GCE_OS_IMAGES else "debian_12"


def normalize_azure_identity_preset(value: str | None) -> str:
    key = (value or "storage_blob_read").strip()
    return key if key in AZURE_IDENTITY_PRESETS else "storage_blob_read"


def normalize_azure_os(value: str | None) -> str:
    key = (value or "ubuntu_22_04").strip()
    return key if key in AZURE_OS_IMAGES else "ubuntu_22_04"


def gce_source_image(os_key: str | None) -> str:
    return GCE_OS_IMAGES[normalize_gce_os(os_key)]["source_image"]


def azure_image_reference(os_key: str | None) -> dict[str, str]:
    return dict(AZURE_OS_IMAGES[normalize_azure_os(os_key)]["image_reference"])


def plan_gcp_sa_preset_summary(preset: str) -> str:
    meta = GCP_SA_PRESETS.get(normalize_gcp_sa_preset(preset), GCP_SA_PRESETS["gcs_read_only"])
    return meta["label"]


def plan_azure_identity_preset_summary(preset: str) -> str:
    meta = AZURE_IDENTITY_PRESETS.get(
        normalize_azure_identity_preset(preset),
        AZURE_IDENTITY_PRESETS["storage_blob_read"],
    )
    return meta["label"]


def _s3_bucket_arns(bucket: str) -> tuple[str, str]:
    if bucket:
        return f"arn:aws:s3:::{bucket}", f"arn:aws:s3:::{bucket}/*"
    return "arn:aws:s3:::*", "arn:aws:s3:::*/*"


def build_iam_role_policy(
    preset: str,
    config: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Return (inline_policy_statements, managed_policy_arns) for the selected preset.
    """
    preset = normalize_iam_role_preset(preset)
    bucket = (config.get("bucket_name") or "").strip()
    bucket_arn, object_arn = _s3_bucket_arns(bucket)
    table = (config.get("dynamodb_table_name") or "").strip()

    managed: list[str] = []
    statements: list[dict[str, Any]] = []

    if preset == "minimal":
        return statements, managed

    if preset in ("s3_read_only", "s3_read_ssm"):
        statements.append(
            {
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:ListBucket", "s3:GetBucketLocation"],
                "Resource": [bucket_arn, object_arn],
            }
        )

    if preset == "s3_read_write":
        statements.append(
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject",
                    "s3:ListBucket",
                    "s3:GetBucketLocation",
                ],
                "Resource": [bucket_arn, object_arn],
            }
        )

    if preset in ("ssm_session", "s3_read_ssm"):
        managed.append(SSM_MANAGED_POLICY_ARN)

    if preset == "dynamodb_app":
        if table:
            table_arn = f"arn:aws:dynamodb:*:*:table/{table}"
            statements.append(
                {
                    "Effect": "Allow",
                    "Action": [
                        "dynamodb:GetItem",
                        "dynamodb:PutItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:DeleteItem",
                        "dynamodb:Query",
                        "dynamodb:Scan",
                        "dynamodb:BatchGetItem",
                        "dynamodb:BatchWriteItem",
                        "dynamodb:DescribeTable",
                    ],
                    "Resource": table_arn,
                }
            )
        else:
            statements.append(
                {
                    "Effect": "Allow",
                    "Action": [
                        "dynamodb:GetItem",
                        "dynamodb:PutItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:DeleteItem",
                        "dynamodb:Query",
                        "dynamodb:Scan",
                    ],
                    "Resource": "arn:aws:dynamodb:*:*:table/*",
                }
            )

    return statements, managed


def _startup_shell_for_os(os_key: str | None, catalog: dict[str, dict[str, Any]], default_key: str) -> str:
    meta = catalog.get(os_key or default_key) or catalog[default_key]
    return meta.get("user_data_shell") or meta.get("startup_shell") or "bash"


def normalize_startup_script(
    script: str | None,
    os_key: str | None,
    *,
    catalog: dict[str, dict[str, Any]],
    default_key: str,
) -> str | None:
    """Return cloud-init/shell startup script or None if empty."""
    raw = (script or "").strip()
    if not raw:
        return None
    if raw.startswith("#!"):
        return raw
    shell = _startup_shell_for_os(
        os_key if os_key in catalog else default_key,
        catalog,
        default_key,
    )
    return f"#!/bin/{shell}\n{raw}\n"


def normalize_user_data(script: str | None, os_key: str | None) -> str | None:
    return normalize_startup_script(
        script,
        normalize_ec2_os(os_key),
        catalog=EC2_OS_IMAGES,
        default_key="amazon_linux_2",
    )


def normalize_gce_startup_script(script: str | None, os_key: str | None) -> str | None:
    return normalize_startup_script(
        script,
        normalize_gce_os(os_key),
        catalog=GCE_OS_IMAGES,
        default_key="debian_12",
    )


def normalize_azure_startup_script(script: str | None, os_key: str | None) -> str | None:
    return normalize_startup_script(
        script,
        normalize_azure_os(os_key),
        catalog=AZURE_OS_IMAGES,
        default_key="ubuntu_22_04",
    )


def azure_custom_data(script: str | None, os_key: str | None) -> str | None:
    """Base64-encoded custom data for Azure Linux VMs."""
    normalized = normalize_azure_startup_script(script, os_key)
    if not normalized:
        return None
    return base64.b64encode(normalized.encode("utf-8")).decode("ascii")


def gcp_sa_preset_needs_bucket(preset: str) -> bool:
    return normalize_gcp_sa_preset(preset) in ("gcs_read_only", "gcs_read_write", "gcs_read_logging")


def gcp_sa_bucket_roles(preset: str) -> list[str]:
    preset = normalize_gcp_sa_preset(preset)
    if preset in ("gcs_read_only", "gcs_read_logging"):
        return ["roles/storage.objectViewer"]
    if preset == "gcs_read_write":
        return ["roles/storage.objectAdmin"]
    return []


def gcp_sa_project_roles(preset: str) -> list[str]:
    preset = normalize_gcp_sa_preset(preset)
    roles: list[str] = []
    if preset in ("logging_writer", "gcs_read_logging"):
        roles.append(GCP_PROJECT_ROLES["logging_writer"])
    if preset == "firestore_app":
        roles.append(GCP_PROJECT_ROLES["firestore_app"])
    return roles


def ec2_os_root_device(os_key: str | None) -> str:
    return EC2_OS_IMAGES.get(normalize_ec2_os(os_key), EC2_OS_IMAGES["amazon_linux_2"])["root_device"]


def plan_iam_preset_summary(preset: str) -> str:
    meta = IAM_ROLE_PRESETS.get(normalize_iam_role_preset(preset), IAM_ROLE_PRESETS["s3_read_only"])
    return meta["label"]
