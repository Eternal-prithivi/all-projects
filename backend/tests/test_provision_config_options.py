"""Unit tests for IAM presets, EC2 OS options, and apply ordering."""

from app.provision.boto3_composer import APPLY_ORDER
from app.provision.provision_config_options import (
    azure_custom_data,
    build_iam_role_policy,
    gcp_sa_bucket_roles,
    normalize_azure_startup_script,
    normalize_gce_startup_script,
    normalize_user_data,
    plan_azure_identity_preset_summary,
    plan_gcp_sa_preset_summary,
    plan_iam_preset_summary,
)
from app.provision.sdk_composer import AZURE_APPLY_ORDER, GCP_APPLY_ORDER


def test_iam_comes_before_ec2_in_apply_order():
    assert APPLY_ORDER.index("iam") < APPLY_ORDER.index("ec2")


def test_s3_read_write_policy_includes_put():
    statements, managed = build_iam_role_policy("s3_read_write", {"bucket_name": "my-bucket"})
    assert not managed
    actions = statements[0]["Action"]
    assert "s3:PutObject" in actions


def test_ssm_preset_attaches_managed_policy():
    statements, managed = build_iam_role_policy("ssm_session", {})
    assert statements == []
    assert "AmazonSSMManagedInstanceCore" in managed[0]


def test_user_data_adds_shebang():
    script = normalize_user_data("yum install -y docker", "amazon_linux_2")
    assert script.startswith("#!/bin/bash")
    assert "docker" in script


def test_user_data_passthrough_with_shebang():
    raw = "#!/bin/bash\necho hi"
    assert normalize_user_data(raw, "ubuntu_22_04") == raw


def test_plan_iam_preset_summary():
    assert "S3" in plan_iam_preset_summary("s3_read_only")


def test_gcp_sa_comes_before_gce_in_apply_order():
    assert GCP_APPLY_ORDER.index("gcp_service_account") < GCP_APPLY_ORDER.index("gce")
    assert GCP_APPLY_ORDER.index("gcs") < GCP_APPLY_ORDER.index("gcp_service_account")


def test_azure_storage_comes_before_vm_in_apply_order():
    assert AZURE_APPLY_ORDER.index("azure_storage") < AZURE_APPLY_ORDER.index("azure_vm")


def test_gce_startup_script_adds_shebang():
    script = normalize_gce_startup_script("apt-get update -y", "debian_12")
    assert script.startswith("#!/bin/bash")
    assert "apt-get" in script


def test_azure_custom_data_is_base64():
    encoded = azure_custom_data("echo hello", "ubuntu_22_04")
    assert encoded
    assert "echo" not in encoded


def test_gcp_sa_bucket_roles_read_only():
    assert gcp_sa_bucket_roles("gcs_read_only") == ["roles/storage.objectViewer"]


def test_gcp_and_azure_preset_summaries():
    assert "GCS" in plan_gcp_sa_preset_summary("gcs_read_only")
    assert "Blob" in plan_azure_identity_preset_summary("storage_blob_read")


def test_azure_startup_script_passthrough_with_shebang():
    raw = "#!/bin/bash\necho hi"
    assert normalize_azure_startup_script(raw, "ubuntu_22_04") == raw
