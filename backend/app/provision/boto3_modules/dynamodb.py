from __future__ import annotations

from typing import Any

from botocore.exceptions import ClientError

from app.provision.boto3_modules.common import aws_err, client
from app.provision.boto3_modules.context import DeployContext


def plan_dynamodb(config: dict, aws_creds: dict, region: str) -> dict[str, Any]:
    table = (config.get("dynamodb_table_name") or "").strip()
    if not table:
        return {"lines": [], "error": "DynamoDB table name is required.", "resources": []}
    ddb = client("dynamodb", aws_creds, region)
    try:
        ddb.describe_table(TableName=table)
        return {"lines": [], "error": f"DynamoDB table '{table}' already exists.", "resources": []}
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "ResourceNotFoundException":
            return {"lines": [], "error": str(exc), "resources": []}
    lines = [
        f"  + aws_dynamodb_table.main ({table})",
        "  + server_side_encryption (enabled)",
    ]
    if config.get("dynamodb_enable_pitr"):
        lines.append("  + point_in_time_recovery (enabled)")
    return {
        "lines": lines,
        "error": None,
        "resources": [f"aws_dynamodb_table.main:{table}"],
    }


def apply_dynamodb(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
    table = (config.get("dynamodb_table_name") or "").strip()
    hash_key = config.get("dynamodb_hash_key", "id")
    hash_type = config.get("dynamodb_hash_key_type", "S")
    rcu = int(config.get("dynamodb_read_capacity", 5))
    wcu = int(config.get("dynamodb_write_capacity", 5))
    enable_pitr = bool(config.get("dynamodb_enable_pitr", False))
    tags = config.get("tags") or {}
    ddb = client("dynamodb", aws_creds, region)
    steps: list[str] = []
    try:
        tag_list = [{"Key": k, "Value": str(v)} for k, v in tags.items()]
        if table and not any(t["Key"] == "Name" for t in tag_list):
            tag_list.append({"Key": "Name", "Value": table})

        ddb.create_table(
            TableName=table,
            KeySchema=[{"AttributeName": hash_key, "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": hash_key, "AttributeType": hash_type}],
            ProvisionedThroughput={"ReadCapacityUnits": rcu, "WriteCapacityUnits": wcu},
            SSESpecification={"Enabled": True},
            Tags=tag_list,
        )
        waiter = ddb.get_waiter("table_exists")
        waiter.wait(TableName=table, WaiterConfig={"Delay": 2, "MaxAttempts": 30})

        if enable_pitr:
            ddb.update_continuous_backups(
                TableName=table,
                PointInTimeRecoverySpecification={"PointInTimeRecoveryEnabled": True},
            )
            steps.append("✓ Point-in-time recovery enabled")

        ctx.dynamodb_table = table
        steps.insert(0, f"✓ DynamoDB table '{table}'")
        return {"success": True, "steps": steps, "error": None}
    except ClientError as exc:
        return {"success": False, "steps": steps, "error": aws_err(exc)}


def destroy_dynamodb(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
    table = (config.get("dynamodb_table_name") or ctx.dynamodb_table or "").strip()
    if not table:
        return {"success": True, "steps": ["DynamoDB: nothing to delete"], "error": None}
    ddb = client("dynamodb", aws_creds, region)
    try:
        ddb.delete_table(TableName=table)
        return {"success": True, "steps": [f"✓ Deleted DynamoDB table '{table}'"], "error": None}
    except ClientError as exc:
        return {"success": False, "steps": [], "error": aws_err(exc)}
