# =============================================================================
# MODULE: provision/policy_store.py
# PURPOSE: Per-user custom governance rules (MongoDB) merged with built-in YAML
# USED BY: policy_checker.py, routes_provision.py
# =============================================================================
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Optional

from bson import ObjectId

from app.database.mongo_client import get_database

COLLECTION = "provision_custom_policies"

# Keys allowed in policy condition expressions (must match config_to_policy_dict)
ALLOWED_POLICY_KEYS = frozenset({
    "s3_bucket_public", "ssh_open_to_world", "rdp_open_to_world", "iam_wildcard",
    "instance_type", "s3_encryption", "tags", "cloudtrail_enabled", "environment",
    "enable_s3", "bucket_name", "budget_limit", "enable_cloudwatch", "enable_ec2",
    "vpc_cidr", "enable_vpc", "True", "False", "None",
})

# Reject obvious injection patterns in user-supplied conditions
_UNSAFE_CONDITION = re.compile(
    r"(__|import|exec|eval|open|compile|globals|locals|getattr|setattr|delattr|"
    r"subprocess|os\.|sys\.|breakpoint)",
    re.IGNORECASE,
)


def _collection():
    return get_database()[COLLECTION]


def validate_policy_condition(condition: str) -> Optional[str]:
    """Return error message if condition is invalid, else None."""
    condition = (condition or "").strip()
    if not condition:
        return "Condition is required"
    if len(condition) > 500:
        return "Condition must be 500 characters or fewer"
    if _UNSAFE_CONDITION.search(condition):
        return "Condition contains disallowed tokens"
    return None


def validate_custom_rule_payload(
    *,
    name: str,
    description: str,
    severity: str,
    condition: str,
) -> Optional[str]:
    name = (name or "").strip()
    if not name or len(name) > 80:
        return "Name is required (max 80 characters)"
    if not re.match(r"^[a-z][a-z0-9_]*$", name):
        return "Name must be snake_case (lowercase letters, numbers, underscores)"
    if severity not in ("block", "warning"):
        return "Severity must be 'block' or 'warning'"
    desc = (description or "").strip()
    if not desc or len(desc) > 2000:
        return "Description is required (max 2000 characters)"
    return validate_policy_condition(condition)


def list_custom_rules(username: str, *, enabled_only: bool = False) -> list[dict[str, Any]]:
    query: dict[str, Any] = {"username": username}
    if enabled_only:
        query["enabled"] = True
    docs = list(_collection().find(query).sort("created_at", 1))
    out = []
    for doc in docs:
        out.append(_serialize_custom(doc))
    return out


def _serialize_custom(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(doc["_id"]),
        "name": doc["name"],
        "description": doc["description"],
        "severity": doc["severity"],
        "condition": doc["condition"],
        "enabled": doc.get("enabled", True),
        "source": "custom",
        "is_customized": False,
        "can_reset": False,
        "username": doc["username"],
        "created_at": doc.get("created_at"),
        "updated_at": doc.get("updated_at"),
    }


def create_custom_rule(
    username: str,
    *,
    name: str,
    description: str,
    severity: str,
    condition: str,
) -> dict[str, Any]:
    err = validate_custom_rule_payload(
        name=name, description=description, severity=severity, condition=condition,
    )
    if err:
        raise ValueError(err)

    coll = _collection()
    if coll.find_one({"username": username, "name": name.strip()}):
        raise ValueError(f"A custom policy named '{name.strip()}' already exists")

    now = datetime.utcnow()
    doc = {
        "username": username,
        "name": name.strip(),
        "description": description.strip(),
        "severity": severity,
        "condition": condition.strip(),
        "enabled": True,
        "created_at": now,
        "updated_at": now,
    }
    result = coll.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _serialize_custom(doc)


def update_custom_rule(
    username: str,
    rule_id: str,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    severity: Optional[str] = None,
    condition: Optional[str] = None,
    enabled: Optional[bool] = None,
) -> dict[str, Any]:
    coll = _collection()
    try:
        oid = ObjectId(rule_id)
    except Exception:
        raise ValueError("Invalid policy id")

    existing = coll.find_one({"_id": oid, "username": username})
    if not existing:
        raise ValueError("Policy not found")

    updates: dict[str, Any] = {"updated_at": datetime.utcnow()}
    if name is not None:
        updates["name"] = name.strip()
    if description is not None:
        updates["description"] = description.strip()
    if severity is not None:
        updates["severity"] = severity
    if condition is not None:
        updates["condition"] = condition.strip()
    if enabled is not None:
        updates["enabled"] = enabled

    merged = {**existing, **updates}
    err = validate_custom_rule_payload(
        name=merged["name"],
        description=merged["description"],
        severity=merged["severity"],
        condition=merged["condition"],
    )
    if err:
        raise ValueError(err)

    if name is not None and name.strip() != existing["name"]:
        dup = coll.find_one({
            "username": username,
            "name": name.strip(),
            "_id": {"$ne": oid},
        })
        if dup:
            raise ValueError(f"A custom policy named '{name.strip()}' already exists")

    coll.update_one({"_id": oid}, {"$set": updates})
    updated = coll.find_one({"_id": oid})
    return _serialize_custom(updated)


def delete_custom_rule(username: str, rule_id: str) -> bool:
    try:
        oid = ObjectId(rule_id)
    except Exception:
        return False
    result = _collection().delete_one({"_id": oid, "username": username})
    return result.deleted_count > 0


def custom_rules_as_yaml_rules(username: str) -> list[dict[str, Any]]:
    """Format enabled custom rules for policy_checker evaluation."""
    rules = []
    for doc in list_custom_rules(username, enabled_only=True):
        rules.append({
            "name": doc["name"],
            "description": doc["description"],
            "severity": doc["severity"],
            "condition": doc["condition"],
        })
    return rules
