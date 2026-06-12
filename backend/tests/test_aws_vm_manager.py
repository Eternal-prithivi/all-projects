"""AWS VM manager — AMI resolution and launch config."""

from unittest.mock import MagicMock, patch

import pytest

from app.vm import aws_manager


def test_resolve_vm_ami_uses_config_dict_not_string():
    ec2 = MagicMock()
    with patch("app.vm.aws_manager._resolve_ami", return_value="ami-abc123") as mock_resolve:
        ami_id, root_device = aws_manager._resolve_vm_ami(ec2, "ap-south-1", "")
    mock_resolve.assert_called_once()
    config = mock_resolve.call_args[0][2]
    assert isinstance(config, dict)
    assert config.get("ec2_os") == "ubuntu_22_04"
    assert ami_id == "ami-abc123"
    assert root_device == "/dev/sda1"


def test_resolve_vm_ami_accepts_explicit_ami_id():
    ec2 = MagicMock()
    with patch("app.vm.aws_manager._resolve_ami", return_value="ami-custom") as mock_resolve:
        ami_id, _root = aws_manager._resolve_vm_ami(ec2, "us-east-1", "ami-custom")
    assert mock_resolve.call_args[0][2]["ami_id"] == "ami-custom"
    assert ami_id == "ami-custom"
