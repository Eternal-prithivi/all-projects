"""Unit tests for boto3_modules parity with Terraform (mocked AWS)."""

from unittest.mock import MagicMock, patch

import pytest

from app.provision.boto3_composer import APPLY_ORDER, BOTO3_IMPLEMENTED, boto3_can_handle
from app.provision.boto3_modules.billing import apply_billing, plan_billing
from app.provision.boto3_modules.cloudwatch import CPU_ALARM_NAME, SNS_TOPIC_NAME, apply_cloudwatch
from app.provision.boto3_modules.context import DeployContext
from app.provision.boto3_modules.dynamodb import apply_dynamodb
from app.provision.boto3_modules.iam import apply_iam
from app.provision.boto3_modules.s3 import apply_s3
from app.provision.boto3_modules.vpc import apply_vpc

AWS_CREDS = {
    "AWS_ACCESS_KEY_ID": "AKIATEST",
    "AWS_SECRET_ACCESS_KEY": "secret",
    "AWS_DEFAULT_REGION": "ap-south-1",
}


def _config(**kwargs):
    base = {
        "aws_region": "ap-south-1",
        "enable_vpc": False,
        "enable_ec2": False,
        "enable_s3": False,
        "enable_iam": False,
        "enable_cloudwatch": False,
        "enable_dynamodb": False,
        "enable_billing": False,
        "bucket_name": "zenith-test-bucket",
        "role_name": "app-role",
        "dynamodb_table_name": "zenith-table",
    }
    base.update(kwargs)
    return base


@pytest.mark.parametrize(
    "module,flags",
    [
        ("s3", {"enable_s3": True, "bucket_name": "b1"}),
        ("dynamodb", {"enable_dynamodb": True, "dynamodb_table_name": "t1"}),
        ("vpc", {"enable_vpc": True}),
        ("ec2", {"enable_vpc": True, "enable_ec2": True}),
        ("iam", {"enable_iam": True}),
        ("cloudwatch", {"enable_cloudwatch": True, "enable_ec2": True, "enable_vpc": True}),
        ("billing", {"enable_billing": True, "budget_email": "a@b.com"}),
    ],
)
def test_boto3_can_handle_each_module(module, flags):
    ok, unsupported = boto3_can_handle(_config(**flags))
    assert ok is True, unsupported
    assert module in BOTO3_IMPLEMENTED


def test_apply_order_includes_all_modules():
    for mod in BOTO3_IMPLEMENTED:
        assert mod in APPLY_ORDER


@patch("app.provision.boto3_modules.s3.client")
def test_apply_s3_encryption_and_versioning(mock_client_fn):
    s3 = MagicMock()
    mock_client_fn.return_value = s3
    ctx = DeployContext()
    result = apply_s3(_config(enable_s3=True), AWS_CREDS, "ap-south-1", ctx)
    assert result["success"] is True
    s3.put_public_access_block.assert_called_once()
    s3.put_bucket_encryption.assert_called_once()
    s3.put_bucket_versioning.assert_called_once()
    assert ctx.bucket_name == "zenith-test-bucket"


@patch("app.provision.boto3_modules.vpc.client")
def test_apply_vpc_map_public_ip(mock_client_fn):
    ec2 = MagicMock()
    mock_client_fn.return_value = ec2
    ec2.describe_availability_zones.return_value = {
        "AvailabilityZones": [{"ZoneName": "ap-south-1a"}, {"ZoneName": "ap-south-1b"}]
    }
    ec2.create_vpc.return_value = {"Vpc": {"VpcId": "vpc-1"}}
    ec2.create_subnet.side_effect = [
        {"Subnet": {"SubnetId": "subnet-pub"}},
        {"Subnet": {"SubnetId": "subnet-priv"}},
    ]
    ec2.create_internet_gateway.return_value = {"InternetGateway": {"InternetGatewayId": "igw-1"}}
    ec2.create_route_table.return_value = {"RouteTable": {"RouteTableId": "rt-1"}}

    ctx = DeployContext()
    result = apply_vpc(_config(enable_vpc=True), AWS_CREDS, "ap-south-1", ctx)
    assert result["success"] is True
    ec2.modify_subnet_attribute.assert_called_once_with(
        SubnetId="subnet-pub",
        MapPublicIpOnLaunch={"Value": True},
    )


@patch("app.provision.boto3_modules.iam.client")
def test_apply_iam_creates_instance_profile(mock_client_fn):
    iam = MagicMock()
    mock_client_fn.return_value = iam
    iam.create_role.return_value = {"Role": {"Arn": "arn:aws:iam::123:role/app-role"}}
    ctx = DeployContext()
    result = apply_iam(_config(enable_iam=True), AWS_CREDS, "ap-south-1", ctx)
    assert result["success"] is True
    iam.create_instance_profile.assert_called_once_with(InstanceProfileName="app-role-profile")
    iam.add_role_to_instance_profile.assert_called_once()
    assert ctx.instance_profile_name == "app-role-profile"


@patch("app.provision.boto3_modules.dynamodb.client")
def test_apply_dynamodb_sse_and_pitr(mock_client_fn):
    ddb = MagicMock()
    mock_client_fn.return_value = ddb
    waiter = MagicMock()
    ddb.get_waiter.return_value = waiter

    ctx = DeployContext()
    result = apply_dynamodb(
        _config(enable_dynamodb=True, dynamodb_enable_pitr=True),
        AWS_CREDS,
        "ap-south-1",
        ctx,
    )
    assert result["success"] is True
    call_kw = ddb.create_table.call_args[1]
    assert call_kw["SSESpecification"] == {"Enabled": True}
    ddb.update_continuous_backups.assert_called_once()


@patch("app.provision.boto3_modules.cloudwatch.client")
def test_apply_cloudwatch_terraform_names(mock_client_fn):
    sns = MagicMock()
    cw = MagicMock()

    def _client(svc, creds, region=None):
        return sns if svc == "sns" else cw

    mock_client_fn.side_effect = _client
    sns.create_topic.return_value = {"TopicArn": "arn:aws:sns:1:123:cloudwatch-alerts"}

    ctx = DeployContext(instance_id="i-123")
    result = apply_cloudwatch(
        _config(enable_cloudwatch=True, enable_ec2=True),
        AWS_CREDS,
        "ap-south-1",
        ctx,
    )
    assert result["success"] is True
    sns.create_topic.assert_called_with(Name=SNS_TOPIC_NAME)
    cw.put_metric_alarm.assert_called_once()
    assert cw.put_metric_alarm.call_args[1]["AlarmName"] == CPU_ALARM_NAME


@patch("app.provision.boto3_modules.billing.client")
@patch("app.provision.boto3_modules.billing._account_id", return_value="123456789012")
def test_apply_billing_create_budget(mock_account, mock_client_fn):
    budgets = MagicMock()
    sts = MagicMock()

    def _client(svc, creds, region=None):
        if svc == "budgets":
            return budgets
        return sts

    mock_client_fn.side_effect = _client
    ctx = DeployContext()
    plan = plan_billing(_config(enable_billing=True, budget_email="u@x.com"), AWS_CREDS, "ap-south-1")
    assert plan["error"] is None
    assert "monthly-budget" in plan["lines"][0]

    result = apply_billing(
        _config(enable_billing=True, budget_limit="5", budget_email="u@x.com"),
        AWS_CREDS,
        "ap-south-1",
        ctx,
    )
    assert result["success"] is True
    budgets.create_budget.assert_called_once()
    assert ctx.budget_name == "monthly-budget"
