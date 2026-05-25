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


def check_infracost_installed() -> bool:
    """Check if the Infracost CLI is available."""
    try:
        result = subprocess.run(
            ["infracost", "--version"],
            capture_output=True, timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


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


def estimate_from_config(config: dict[str, Any]) -> CostEstimate:
    """
    Estimate cost from config using the built-in lookup table.
    Used as fallback when Infracost is not available.
    """
    resources: list[dict[str, Any]] = []
    total = 0.0

    # Always-included: billing module
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

    return CostEstimate(
        available=True,
        total_monthly_cost=f"{total:.2f}",
        currency="USD",
        resources=resources,
    )


def estimate_cost(config: dict[str, Any], workspace_dir: str | None = None) -> CostEstimate:
    """
    Estimate cost — tries Infracost first, falls back to built-in table.
    """
    if workspace_dir and check_infracost_installed():
        result = estimate_with_infracost(workspace_dir)
        if result.available:
            return result
        logger.info(f"Infracost failed ({result.error}), falling back to built-in estimates")

    return estimate_from_config(config)
