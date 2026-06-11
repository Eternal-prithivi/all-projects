"""Unit tests for provision policy_checker (YAML rules, no live Terraform)."""

from app.provision.policy_checker import (
    config_to_policy_dict,
    evaluate_yaml_policies,
    full_policy_check,
    get_yaml_rules,
)
from app.provision.policy_store import create_custom_rule, delete_custom_rule
from app.database.mongo_client import get_database


def test_config_to_policy_dict_safe_defaults():
    policy = config_to_policy_dict({"instance_type": "t2.micro"})
    assert policy["s3_bucket_public"] is False
    assert policy["ssh_open_to_world"] is False
    assert policy["instance_type"] == "t2.micro"


def test_gcp_expensive_vm_warning():
    config = {
        "csp": "GCP",
        "enable_gce": True,
        "enable_gcp_network": True,
        "machine_type": "e2-medium",
        "tags": {"Owner": "tester"},
        "environment": "dev",
    }
    result = evaluate_yaml_policies(config)
    assert any(v.rule_name == "expensive_vm_size" for v in result.warnings)


def test_azure_vm_without_vnet_blocks():
    config = {
        "csp": "Azure",
        "enable_azure_vm": True,
        "enable_vnet": False,
        "tags": {"Owner": "tester"},
    }
    result = evaluate_yaml_policies(config)
    assert any(v.rule_name == "azure_vm_without_vnet" for v in result.blocks)


def test_expensive_instance_type_warning():
    config = {
        "instance_type": "m5.large",
        "enable_ec2": True,
        "enable_vpc": True,
        "tags": {"Owner": "tester"},
    }
    result = evaluate_yaml_policies(config)
    assert any(v.rule_name == "expensive_ec2_instance" for v in result.warnings)
    assert result.can_deploy is True


def test_s3_without_bucket_name_blocks():
    config = {"enable_s3": True, "bucket_name": ""}
    result = evaluate_yaml_policies(config)
    assert any(v.rule_name == "s3_missing_bucket_name" for v in result.blocks)
    assert result.can_deploy is False


def test_free_tier_static_site_passes():
    config = {
        "enable_s3": True,
        "bucket_name": "my-unique-bucket-zenith-test",
        "instance_type": "t2.micro",
        "tags": {"Owner": "tester", "Project": "zenith"},
    }
    result = full_policy_check(config)
    assert result.can_deploy is True
    assert len(result.blocks) == 0


def test_get_yaml_rules_loads_production_file():
    rules = get_yaml_rules()
    assert len(rules) >= 8
    assert any(r.get("name") == "public_s3_bucket" for r in rules)


def test_custom_rule_blocks_deploy_for_user():
    username = "custom_policy_eval_user"
    coll = get_database()["provision_custom_policies"]
    coll.delete_many({"username": username})
    try:
        create_custom_rule(
            username,
            name="force_micro_only",
            description="Only micro instances",
            severity="block",
            condition="instance_type not in ['t2.micro', 't3.micro', 't4g.micro']",
        )
        config = {
            "instance_type": "m5.large",
            "enable_ec2": True,
            "enable_vpc": True,
            "tags": {"Owner": "tester"},
        }
        result = evaluate_yaml_policies(config, username=username)
        assert any(v.rule_name == "force_micro_only" for v in result.blocks)
        assert result.can_deploy is False
    finally:
        coll.delete_many({"username": username})
