"""Unit tests for Terraform helper utilities (no live terraform CLI)."""

import tempfile
from pathlib import Path

from app.provision.terraform_runner import write_tfvars


def test_write_tfvars_enables_flags_and_tags():
    with tempfile.TemporaryDirectory() as tmp:
        config = {
            "aws_region": "us-east-1",
            "enable_s3": True,
            "enable_ec2": False,
            "bucket_name": "zenith-test-bucket",
            "instance_type": "t2.micro",
            "tags": {"Env": "test", "Owner": "ci"},
        }
        path = write_tfvars(tmp, config)
        content = Path(path).read_text(encoding="utf-8")
        assert 'aws_region = "us-east-1"' in content
        assert "enable_s3         = true" in content
        assert "enable_ec2        = false" in content
        assert 'bucket_name   = "zenith-test-bucket"' in content
        assert 'Env = "test"' in content


def test_write_tfvars_dynamodb_capacity_fields():
    with tempfile.TemporaryDirectory() as tmp:
        config = {
            "enable_dynamodb": True,
            "dynamodb_read_capacity": 5,
            "dynamodb_write_capacity": 5,
            "dynamodb_enable_pitr": False,
        }
        path = write_tfvars(tmp, config)
        content = Path(path).read_text(encoding="utf-8")
        assert "dynamodb_read_capacity = 5" in content
        assert "dynamodb_enable_pitr = false" in content
