from __future__ import annotations

from typing import Any

from botocore.exceptions import ClientError

from app.provision.boto3_modules.common import aws_err, client
from app.provision.boto3_modules.context import DeployContext

BUDGET_NAME = "monthly-budget"


def _account_id(aws_creds: dict) -> str:
    sts = client("sts", aws_creds)
    return sts.get_caller_identity()["Account"]


def plan_billing(config: dict, aws_creds: dict, region: str) -> dict[str, Any]:
    limit = str(config.get("budget_limit", "1"))
    email = (config.get("budget_email") or "").strip()
    lines = [
        f"  + aws_budgets_budget.monthly ({BUDGET_NAME}, ${limit}/month)",
    ]
    if email:
        lines.append(f"  + budget notification → {email} (100% actual, 80% forecast)")
    return {
        "lines": lines,
        "error": None,
        "resources": [f"aws_budgets_budget.monthly:{BUDGET_NAME}"],
    }


def apply_billing(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
    # AWS Budgets API is only available in us-east-1
    budgets = client("budgets", aws_creds, "us-east-1")
    limit = str(config.get("budget_limit", "1"))
    email = (config.get("budget_email") or "").strip()
    try:
        account_id = _account_id(aws_creds)
        budget_def = {
            "BudgetName": BUDGET_NAME,
            "BudgetLimit": {"Amount": limit, "Unit": "USD"},
            "TimeUnit": "MONTHLY",
            "BudgetType": "COST",
        }
        notifications = []
        if email:
            notifications = [
                {
                    "Notification": {
                        "NotificationType": "ACTUAL",
                        "ComparisonOperator": "GREATER_THAN",
                        "Threshold": 100,
                        "ThresholdType": "PERCENTAGE",
                    },
                    "Subscribers": [{"SubscriptionType": "EMAIL", "Address": email}],
                },
                {
                    "Notification": {
                        "NotificationType": "FORECASTED",
                        "ComparisonOperator": "GREATER_THAN",
                        "Threshold": 80,
                        "ThresholdType": "PERCENTAGE",
                    },
                    "Subscribers": [{"SubscriptionType": "EMAIL", "Address": email}],
                },
            ]
        kwargs: dict[str, Any] = {
            "AccountId": account_id,
            "Budget": budget_def,
        }
        if notifications:
            kwargs["NotificationsWithSubscribers"] = notifications
        budgets.create_budget(**kwargs)
        ctx.budget_name = BUDGET_NAME
        msg = f"✓ AWS Budget '{BUDGET_NAME}' (${limit}/month)"
        if email:
            msg += f" with alerts to {email}"
        return {"success": True, "steps": [msg], "error": None}
    except ClientError as exc:
        return {"success": False, "steps": [], "error": aws_err(exc)}


def destroy_billing(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
    name = ctx.budget_name or BUDGET_NAME
    budgets = client("budgets", aws_creds, "us-east-1")
    try:
        account_id = _account_id(aws_creds)
        budgets.delete_budget(AccountId=account_id, BudgetName=name)
        return {"success": True, "steps": [f"✓ Deleted budget '{name}'"], "error": None}
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")
        if code in ("NotFoundException", "ResourceNotFoundException"):
            return {"success": True, "steps": ["Billing: nothing to delete"], "error": None}
        return {"success": False, "steps": [], "error": aws_err(exc)}
