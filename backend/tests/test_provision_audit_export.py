"""Tests for provision audit log query window and export."""

from datetime import datetime, timedelta

from app.provision.audit_logger import (
    export_user_audit_csv_rows,
    get_user_audit_log,
    log_provision_action,
)
from app.database.mongo_client import get_database

COLLECTION = "provision_audit_log"


def test_audit_respects_period_and_pagination():
    username = "audit_export_test_user"
    coll = get_database()[COLLECTION]
    coll.delete_many({"actor": username})

    log_provision_action(
        action="plan",
        actor=username,
        deployment_id="dep-1",
        status="success",
    )
    old = datetime.utcnow() - timedelta(days=120)
    coll.insert_one({
        "action": "plan",
        "actor": username,
        "deployment_id": "old",
        "status": "success",
        "timestamp": old,
    })

    try:
        page, total = get_user_audit_log(username, limit=10, skip=0, days=90)
        assert total == 1
        assert len(page) == 1

        rows = export_user_audit_csv_rows(username, days=90)
        assert len(rows) == 1
        assert rows[0]["deployment_id"] == "dep-1"
    finally:
        coll.delete_many({"actor": username})
