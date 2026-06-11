# =============================================================================
# MODULE: provision/cost_estimator.py
# PURPOSE: Pre-deployment cost estimation — Infracost integration + fallback table
# USED BY: routes_provision.py (/estimate and /plan endpoints)
# DEPENDS ON: Infracost CLI (optional — falls back to built-in lookup table)
# DO NOT:
#   - Assume Infracost is installed — always provide fallback estimates
#   - Return cost estimates without marking free-tier eligibility
# =============================================================================
from __future__ import annotations

import json
import logging
import subprocess
from typing import Any

from app.provision.models import CostEstimate

logger = logging.getLogger(__name__)

# Built-in cost lookup table for common free-tier resources.
# Used as fallback when Infracost is not installed.
FREE_TIER_COSTS: dict[str, dict[str, Any]] = {
    "vpc": {
        "name": "VPC + Subnets + Internet Gateway",
        "monthly_cost": "0.00",
        "note": "VPC itself is free. NAT Gateway is NOT free but not included.",
    },
    "ec2_t2_micro": {
        "name": "EC2 t2.micro (750 hrs/month free tier)",
        "monthly_cost": "0.00",
        "note": "Free for 12 months on new AWS accounts.",
    },
    "ec2_t3_micro": {
        "name": "EC2 t3.micro (750 hrs/month free tier)",
        "monthly_cost": "0.00",
        "note": "Free for 12 months on new AWS accounts.",
    },
    "s3": {
        "name": "S3 Bucket (5GB free tier)",
        "monthly_cost": "0.00",
        "note": "5GB storage + 20K GET + 2K PUT free for 12 months.",
    },
    "iam": {
        "name": "IAM Role + Policy",
        "monthly_cost": "0.00",
        "note": "IAM is always free.",
    },
    "cloudwatch": {
        "name": "CloudWatch Basic Monitoring",
        "monthly_cost": "0.00",
        "note": "Basic monitoring (5-min intervals) is free. Detailed monitoring costs $2.10/instance.",
    },
    "billing": {
        "name": "AWS Budget Alert",
        "monthly_cost": "0.00",
        "note": "First 2 budgets are free. Additional budgets cost $0.02/day.",
    },
    "dynamodb": {
        "name": "DynamoDB (25 RCU + 25 WCU free tier)",
        "monthly_cost": "0.00",
        "note": "25 RCU + 25 WCU + 25GB storage always free.",
    },
}

# Non-free instance types (approximate monthly cost for common types)
PAID_INSTANCE_COSTS: dict[str, str] = {
    "t2.small": "16.79",
    "t2.medium": "33.58",
    "t2.large": "67.16",
    "t3.small": "15.18",
    "t3.medium": "30.37",
    "t3.large": "60.74",
    "m5.large": "70.08",
    "m5.xlarge": "140.16",
    "c5.large": "62.05",
    "r5.large": "91.98",
}

GCP_VM_COSTS: dict[str, str] = {
    "e2-micro": "0.00",
    "e2-small": "12.23",
    "e2-medium": "24.46",
    "e2-standard-2": "48.92",
}

AZURE_VM_COSTS: dict[str, str] = {
    "Standard_B1s": "0.00",
    "Standard_B2s": "30.37",
    "Standard_B2ms": "60.74",
}

GCP_GCS_COST = {"name": "GCS bucket (5GB free/month)", "monthly_cost": "0.00", "note": "Standard storage free tier eligible."}
GCP_FIRESTORE_COST = {"name": "Firestore (free tier)", "monthly_cost": "0.00", "note": "Generous free reads/writes."}
AZURE_BLOB_COST = {"name": "Azure Blob container", "monthly_cost": "0.00", "note": "First 5GB LRS hot tier often free."}
AZURE_COSMOS_COST = {"name": "Cosmos DB SQL API", "monthly_cost": "5.00", "note": "Approximate minimum serverless cost."}

# Approximate EBS/GCE/Azure disk $/GB-month beyond included boot
DISK_GB_MONTHLY_RATE = 0.10


_INFRACOST_AVAILABLE: bool | None = None


def check_infracost_installed() -> bool:
    """Check if the Infracost CLI is available (cached after first check)."""
    global _INFRACOST_AVAILABLE
    if _INFRACOST_AVAILABLE is not None:
        return _INFRACOST_AVAILABLE
    try:
        result = subprocess.run(
            ["infracost", "--version"],
            capture_output=True,
            timeout=3,
        )
        _INFRACOST_AVAILABLE = result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        _INFRACOST_AVAILABLE = False
    return _INFRACOST_AVAILABLE


def estimate_with_infracost(workspace_dir: str) -> CostEstimate:
    """
    Run infracost breakdown on a workspace and return parsed results.
    Requires Infracost CLI + API key configured.
    """
    try:
        result = subprocess.run(
            [
                "infracost", "breakdown",
                "--path", workspace_dir,
                "--terraform-var-file", "terraform.tfvars",
                "--format", "json",
            ],
            capture_output=True, text=True, timeout=120,
            cwd=workspace_dir,
        )

        if result.returncode != 0:
            return CostEstimate(
                available=False,
                error=result.stderr.strip() or "Infracost failed",
            )

        data = json.loads(result.stdout)
        total = data.get("totalMonthlyCost", "0.00")
        projects = data.get("projects", [])

        resources: list[dict[str, Any]] = []
        if projects:
            for res in projects[0].get("breakdown", {}).get("resources", []):
                resources.append({
                    "name": res.get("name", ""),
                    "monthly_cost": res.get("monthlyCost", "0.00"),
                    "hourly_cost": res.get("hourlyCost", "0.00"),
                })

        return CostEstimate(
            available=True,
            total_monthly_cost=total,
            currency="USD",
            resources=resources,
        )

    except FileNotFoundError:
        return CostEstimate(available=False, error="Infracost CLI not installed")
    except subprocess.TimeoutExpired:
        return CostEstimate(available=False, error="Infracost timed out (120s)")
    except Exception as e:
        return CostEstimate(available=False, error=str(e))


def _add_disk_cost(resources: list[dict[str, Any]], total: float, config: dict[str, Any]) -> float:
    disk_gb = int(config.get("disk_size_gb") or 30)
    has_vm = (
        config.get("enable_ec2")
        or config.get("enable_gce")
        or config.get("enable_azure_vm")
    )
    if has_vm and disk_gb > 30:
        extra = disk_gb - 30
        cost = round(extra * DISK_GB_MONTHLY_RATE, 2)
        resources.append({
            "name": f"Additional disk ({extra} GB beyond 30GB)",
            "monthly_cost": f"{cost:.2f}",
            "note": "Approximate block storage charge.",
        })
        return total + cost
    return total


def estimate_from_config(config: dict[str, Any]) -> CostEstimate:
    """
    Estimate cost from config using the built-in lookup table.
    Used as fallback when Infracost is not available.
    """
    from app.cloud.providers import normalize_provider

    csp = normalize_provider(config.get("csp") or "AWS")
    resources: list[dict[str, Any]] = []
    total = 0.0

    if csp == "AWS":
        resources.append({
            "name": FREE_TIER_COSTS["billing"]["name"],
            "monthly_cost": FREE_TIER_COSTS["billing"]["monthly_cost"],
            "note": FREE_TIER_COSTS["billing"]["note"],
        })

    if config.get("enable_vpc", False):
        resources.append({
            "name": FREE_TIER_COSTS["vpc"]["name"],
            "monthly_cost": FREE_TIER_COSTS["vpc"]["monthly_cost"],
            "note": FREE_TIER_COSTS["vpc"]["note"],
        })

    if config.get("enable_ec2", False):
        instance_type = config.get("instance_type", "t2.micro")
        if instance_type in PAID_INSTANCE_COSTS:
            cost = PAID_INSTANCE_COSTS[instance_type]
            resources.append({
                "name": f"EC2 {instance_type}",
                "monthly_cost": cost,
                "note": "⚠️ Not free tier — real charges apply.",
            })
            total += float(cost)
        else:
            key = f"ec2_{instance_type.replace('.', '_')}"
            info = FREE_TIER_COSTS.get(key, FREE_TIER_COSTS.get("ec2_t2_micro"))
            resources.append({
                "name": info["name"],
                "monthly_cost": info["monthly_cost"],
                "note": info["note"],
            })

    if config.get("enable_s3", False):
        resources.append({
            "name": FREE_TIER_COSTS["s3"]["name"],
            "monthly_cost": FREE_TIER_COSTS["s3"]["monthly_cost"],
            "note": FREE_TIER_COSTS["s3"]["note"],
        })

    if config.get("enable_iam", False):
        resources.append({
            "name": FREE_TIER_COSTS["iam"]["name"],
            "monthly_cost": FREE_TIER_COSTS["iam"]["monthly_cost"],
            "note": FREE_TIER_COSTS["iam"]["note"],
        })

    if config.get("enable_cloudwatch", False):
        resources.append({
            "name": FREE_TIER_COSTS["cloudwatch"]["name"],
            "monthly_cost": FREE_TIER_COSTS["cloudwatch"]["monthly_cost"],
            "note": FREE_TIER_COSTS["cloudwatch"]["note"],
        })

    if config.get("enable_dynamodb", False):
        resources.append({
            "name": FREE_TIER_COSTS["dynamodb"]["name"],
            "monthly_cost": FREE_TIER_COSTS["dynamodb"]["monthly_cost"],
            "note": FREE_TIER_COSTS["dynamodb"]["note"],
        })

    if config.get("enable_gcp_network", False):
        resources.append({
            "name": "GCP VPC network",
            "monthly_cost": "0.00",
            "note": "VPC is free; egress charges apply separately.",
        })

    if config.get("enable_gce", False):
        mt = config.get("machine_type", "e2-micro")
        cost = GCP_VM_COSTS.get(mt, "24.46")
        resources.append({
            "name": f"Compute Engine {mt}",
            "monthly_cost": cost,
            "note": "e2-micro free tier eligible in select regions." if cost == "0.00" else "Paid instance size.",
        })
        total += float(cost)

    if config.get("enable_gcs", False):
        resources.append(dict(GCP_GCS_COST))

    if config.get("enable_gcp_service_account", False):
        resources.append({
            "name": "GCP service account",
            "monthly_cost": "0.00",
            "note": "IAM is free.",
        })

    if config.get("enable_gcp_monitoring", False):
        resources.append({
            "name": "Cloud Monitoring alert",
            "monthly_cost": "0.00",
            "note": "Basic alerting free tier.",
        })

    if config.get("enable_firestore", False):
        resources.append(dict(GCP_FIRESTORE_COST))

    if config.get("enable_vnet", False):
        resources.append({
            "name": "Azure VNet",
            "monthly_cost": "0.00",
            "note": "VNet is free.",
        })

    if config.get("enable_azure_vm", False):
        size = config.get("vm_size", "Standard_B1s")
        cost = AZURE_VM_COSTS.get(size, "30.37")
        resources.append({
            "name": f"Azure VM {size}",
            "monthly_cost": cost,
            "note": "B1s free tier eligible for 12 months." if cost == "0.00" else "Paid VM size.",
        })
        total += float(cost)

    if config.get("enable_azure_storage", False):
        resources.append(dict(AZURE_BLOB_COST))

    if config.get("enable_azure_monitor", False):
        resources.append({
            "name": "Azure Monitor action group",
            "monthly_cost": "0.00",
            "note": "Email alerts low cost.",
        })

    if config.get("enable_cosmos", False):
        resources.append(dict(AZURE_COSMOS_COST))
        total += float(AZURE_COSMOS_COST["monthly_cost"])

    total = _add_disk_cost(resources, total, config)

    return CostEstimate(
        available=True,
        total_monthly_cost=f"{total:.2f}",
        currency="USD",
        resources=resources,
    )


def estimate_cost(
    config: dict[str, Any],
    workspace_dir: str | None = None,
    *,
    use_infracost: bool = True,
) -> CostEstimate:
    """
    Estimate cost — built-in table by default (instant).
    Infracost only when workspace_dir is set (terraform plan path).
    """
    if use_infracost and workspace_dir and check_infracost_installed():
        result = estimate_with_infracost(workspace_dir)
        if result.available:
            return result
        logger.info(f"Infracost failed ({result.error}), falling back to built-in estimates")

    return estimate_from_config(config)
