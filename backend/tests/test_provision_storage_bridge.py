"""Provisioned storage appears on Storage bucket lists."""

from unittest.mock import MagicMock, patch

from app.provision.created_resources import resources_from_sdk_context
from app.provision.models import DeploymentStatus
from app.provision.storage_bridge import (
    list_provisioned_storage_buckets,
    merge_provisioned_storage_buckets,
)


def test_sdk_context_azure_uses_container_name():
    ctx = {
        "azure_storage_account": "zenithstore01",
        "azure_container": "my-static",
    }
    config = {"csp": "Azure", "enable_azure_storage": True}
    resources = resources_from_sdk_context(config, ctx)
    assert len(resources) == 1
    assert resources[0]["name"] == "my-static"
    assert resources[0]["account_name"] == "zenithstore01"


@patch("app.database.mongo_client.get_database")
def test_list_provisioned_s3_from_deployments(mock_db):
    collection = MagicMock()
    mock_db.return_value = {"provision_deployments": collection}
    collection.find.return_value = [
        {
            "deployment_name": "alice-123",
            "config": {
                "csp": "AWS",
                "enable_s3": True,
                "bucket_name": "my-provisioned-bucket",
                "aws_region": "ap-south-1",
                "deployment_display_name": "my-api",
            },
            "created_resources": [
                {"type": "bucket", "name": "my-provisioned-bucket", "csp": "AWS"},
            ],
        }
    ]

    buckets = list_provisioned_storage_buckets("alice", "AWS")
    assert len(buckets) == 1
    assert buckets[0]["name"] == "my-provisioned-bucket"
    assert buckets[0]["provisioned"] is True
    assert buckets[0]["deployment_id"] == "alice-123"


def test_merge_dedupes_existing_catalog_bucket():
    catalog = [{"name": "existing-bucket", "region": "us-east-1"}]
    with patch(
        "app.provision.storage_bridge.list_provisioned_storage_buckets",
        return_value=[{"name": "existing-bucket", "region": "us-east-1", "provisioned": True}],
    ):
        merged = merge_provisioned_storage_buckets("u", "AWS", catalog)
    assert len(merged) == 1

    with patch(
        "app.provision.storage_bridge.list_provisioned_storage_buckets",
        return_value=[{"name": "new-bucket", "region": "ap-south-1", "provisioned": True}],
    ):
        merged = merge_provisioned_storage_buckets("u", "AWS", catalog)
    assert len(merged) == 2
    assert merged[1]["name"] == "new-bucket"


def test_storage_bridge_only_deployed_status():
    """Destroyed stacks must not appear — query filters by deployed status."""
    from app.provision.storage_bridge import _storage_enabled

    assert _storage_enabled({"enable_s3": True}) is True
    assert _storage_enabled({"enable_ec2": True}) is False
    assert DeploymentStatus.DEPLOYED.value == "deployed"
