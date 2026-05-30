"""Tests for automatic deployment archiving when recent limit is exceeded."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from app.provision.routes_provision import (
    RECENT_DEPLOYMENTS_LIMIT,
    _auto_archive_excess_deployments,
)


def _make_collection(active_docs):
    collection = MagicMock()

    def find(filter_spec, projection=None):
        result = MagicMock()
        if filter_spec.get("archived") is True:
            result.sort.return_value.limit.return_value = []
        else:
            result.sort.return_value = list(active_docs)
        return result

    collection.find.side_effect = find
    return collection


@patch("app.provision.routes_provision.log_provision_action")
@patch("app.provision.routes_provision._get_deployments_collection")
def test_auto_archive_keeps_three_newest(mock_get_coll, mock_log):
    active = [
        {"deployment_name": "newest", "status": "deployed", "created_at": datetime(2026, 1, 3)},
        {"deployment_name": "middle", "status": "deployed", "created_at": datetime(2026, 1, 2)},
        {"deployment_name": "older", "status": "deployed", "created_at": datetime(2026, 1, 1)},
        {"deployment_name": "oldest", "status": "awaiting_apply", "created_at": datetime(2025, 12, 1)},
    ]
    mock_get_coll.return_value = _make_collection(active)

    count = _auto_archive_excess_deployments("alice")

    assert count == 1
    assert RECENT_DEPLOYMENTS_LIMIT == 3
    mock_get_coll.return_value.update_one.assert_called_once()
    call_filter = mock_get_coll.return_value.update_one.call_args[0][0]
    assert call_filter["deployment_name"] == "oldest"


@patch("app.provision.routes_provision.log_provision_action")
@patch("app.provision.routes_provision._get_deployments_collection")
def test_auto_archive_noop_when_within_limit(mock_get_coll, mock_log):
    active = [
        {"deployment_name": "a", "status": "deployed"},
        {"deployment_name": "b", "status": "deployed"},
    ]
    mock_get_coll.return_value = _make_collection(active)

    assert _auto_archive_excess_deployments("alice") == 0
    mock_get_coll.return_value.update_one.assert_not_called()
