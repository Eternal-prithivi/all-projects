# =============================================================================
# MODULE: provision/policy_overrides.py
# PURPOSE: Per-user overrides for built-in YAML governance rules
# =============================================================================
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from app.database.mongo_client import get_database
from app.provision.policy_store import validate_custom_rule_payload, validate_policy_condition

COLLECTION = "provision_policy_overrides"


def _collection():
    return get_database()[COLLECTION]


def list_overrides(username: str) -> dict[str, dict[str, Any]]:
    """Map builtin_name -> override document."""
    docs = _collection().find({"username": username})
    return {doc["builtin_name"]: _serialize_override(doc) for doc in docs}


def _serialize_override(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "builtin_name": doc["builtin_name"],
        "name": doc["builtin_name"],
        "description": doc.get("description", ""),
        "severity": doc.get("severity", "warning"),
        "condition": doc.get("condition", ""),
        "enabled": doc.get("enabled", True),
        "source": "override",
        "id": None,
        "is_customized": True,
        "can_reset": True,
        "updated_at": doc.get("updated_at"),
    }


def get_builtin_names() -> set[str]:
    from app.provision.policy_checker import get_yaml_rules
    return {r["name"] for r in get_yaml_rules()}


def upsert_override(
    username: str,
    builtin_name: str,
    *,
    description: Optional[str] = None,
    severity: Optional[str] = None,
    condition: Optional[str] = None,
    enabled: Optional[bool] = None,
) -> dict[str, Any]:
    builtin_name = (builtin_name or "").strip()
    if builtin_name not in get_builtin_names():
        raise ValueError(f"Unknown platform policy: {builtin_name}")

    from app.provision.policy_checker import get_yaml_rules
    builtin = next(r for r in get_yaml_rules() if r["name"] == builtin_name)

    coll = _collection()
    existing = coll.find_one({"username": username, "builtin_name": builtin_name})
    base = existing or {}

    merged_desc = description.strip() if description is not None else base.get(
        "description", (builtin.get("description") or "").strip()
    )
    merged_sev = severity if severity is not None else base.get("severity", builtin["severity"])
    merged_cond = condition.strip() if condition is not None else base.get(
        "condition", builtin.get("condition", "")
    )
    merged_enabled = enabled if enabled is not None else base.get("enabled", True)

    if merged_enabled:
        err = validate_custom_rule_payload(
            name=builtin_name,
            description=merged_desc,
            severity=merged_sev,
            condition=merged_cond,
        )
        if err:
            raise ValueError(err)
    else:
        if severity is not None and severity not in ("block", "warning"):
            raise ValueError("Severity must be 'block' or 'warning'")

    now = datetime.utcnow()
    doc = {
        "username": username,
        "builtin_name": builtin_name,
        "description": merged_desc,
        "severity": merged_sev,
        "condition": merged_cond,
        "enabled": merged_enabled,
        "updated_at": now,
    }
    if existing:
        coll.update_one(
            {"username": username, "builtin_name": builtin_name},
            {"$set": doc},
        )
    else:
        doc["created_at"] = now
        coll.insert_one(doc)

    saved = coll.find_one({"username": username, "builtin_name": builtin_name})
    return _serialize_override(saved)


def delete_override(username: str, builtin_name: str) -> bool:
    result = _collection().delete_one({
        "username": username,
        "builtin_name": builtin_name.strip(),
    })
    return result.deleted_count > 0


def apply_overrides_to_builtins(
    builtin_rules: list[dict[str, Any]],
    username: str,
) -> list[dict[str, Any]]:
    """Merge overrides into builtin rules for evaluation and UI."""
    overrides = list_overrides(username)
    result: list[dict[str, Any]] = []

    for rule in builtin_rules:
        name = rule["name"]
        ov = overrides.get(name)
        merged = dict(rule)
        if ov:
            if not ov.get("enabled", True):
                merged["source"] = "override"
                merged["is_customized"] = True
                merged["can_reset"] = True
                merged["enabled"] = False
            else:
                merged["description"] = ov.get("description") or merged.get("description", "")
                merged["severity"] = ov.get("severity", merged.get("severity"))
                merged["condition"] = ov.get("condition") or merged.get("condition", "")
                merged["source"] = "override"
                merged["is_customized"] = True
                merged["can_reset"] = True
                merged["enabled"] = True
        else:
            merged["source"] = "builtin"
            merged["is_customized"] = False
            merged["can_reset"] = False
            merged["enabled"] = True
        merged["id"] = None
        result.append(merged)
    return result


def overrides_as_eval_rules(username: str, builtin_rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rules list for policy evaluation (excludes disabled builtins)."""
    return [r for r in apply_overrides_to_builtins(builtin_rules, username) if r.get("enabled", True)]
