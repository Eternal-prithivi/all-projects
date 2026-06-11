"""Tests for disk_size_gb wiring in tfvars and policy."""

from app.provision.policy_checker import config_to_policy_dict
from app.provision.terraform_runner import write_tfvars
import tempfile
from pathlib import Path


def test_write_tfvars_includes_disk_size_gb_aws():
    with tempfile.TemporaryDirectory() as tmp:
        cfg = {
            "csp": "AWS",
            "enable_ec2": True,
            "disk_size_gb": 50,
            "instance_type": "t2.micro",
            "tags": {"Env": "dev"},
        }
        write_tfvars(tmp, cfg)
        content = Path(tmp, "terraform.tfvars").read_text()
        assert "disk_size_gb  = 50" in content


def test_write_tfvars_includes_disk_gcp():
    with tempfile.TemporaryDirectory() as tmp:
        cfg = {
            "csp": "GCP",
            "enable_gce": True,
            "enable_gcp_network": True,
            "disk_size_gb": 40,
            "gcp_project": "test-proj",
            "tags": {},
        }
        write_tfvars(tmp, cfg)
        content = Path(tmp, "terraform.tfvars").read_text()
        assert "disk_size_gb           = 40" in content


def test_policy_multicloud_vm_size():
    cfg = {
        "csp": "GCP",
        "enable_gce": True,
        "machine_type": "e2-small",
        "environment": "dev",
    }
    policy = config_to_policy_dict(cfg)
    assert policy["vm_enabled"] is True
    assert policy["vm_size"] == "e2-small"
    assert policy["csp"] == "GCP"
