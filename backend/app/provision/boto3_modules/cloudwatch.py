from __future__ import annotations

from typing import Any

from botocore.exceptions import ClientError

from app.provision.boto3_modules.common import aws_err, client
from app.provision.boto3_modules.context import DeployContext

SNS_TOPIC_NAME = "cloudwatch-alerts"
CPU_ALARM_NAME = "ec2-cpu-high"


def plan_cloudwatch(config: dict, aws_creds: dict, region: str) -> dict[str, Any]:
    lines = [f"  + aws_sns_topic.alerts ({SNS_TOPIC_NAME})"]
    if config.get("enable_ec2"):
        lines.append(f"  + aws_cloudwatch_metric_alarm.cpu_high ({CPU_ALARM_NAME})")
    if (config.get("alarm_email") or "").strip():
        lines.append("  + aws_sns_topic_subscription.email")
    return {"lines": lines, "error": None, "resources": ["aws_sns_topic.alerts"]}


def apply_cloudwatch(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
    sns = client("sns", aws_creds, region)
    cw = client("cloudwatch", aws_creds, region)
    email = (config.get("alarm_email") or "").strip()
    try:
        topic = sns.create_topic(Name=SNS_TOPIC_NAME)
        arn = topic["TopicArn"]
        ctx.sns_topic_arn = arn
        steps = [f"✓ SNS topic {arn}"]
        if email:
            sns.subscribe(TopicArn=arn, Protocol="email", Endpoint=email)
            steps.append(f"✓ Email subscription pending for {email}")
        if config.get("enable_ec2") and ctx.instance_id:
            cw.put_metric_alarm(
                AlarmName=CPU_ALARM_NAME,
                ComparisonOperator="GreaterThanThreshold",
                EvaluationPeriods=2,
                MetricName="CPUUtilization",
                Namespace="AWS/EC2",
                Period=300,
                Statistic="Average",
                Threshold=80.0,
                AlarmDescription="EC2 CPU utilization exceeded 80% for 10 minutes.",
                AlarmActions=[arn],
                Dimensions=[{"Name": "InstanceId", "Value": ctx.instance_id}],
            )
            steps.append(f"✓ CPU alarm '{CPU_ALARM_NAME}' on instance {ctx.instance_id}")
        return {"success": True, "steps": steps, "error": None}
    except ClientError as exc:
        return {"success": False, "steps": [], "error": aws_err(exc)}


def destroy_cloudwatch(config: dict, aws_creds: dict, region: str, ctx: DeployContext) -> dict[str, Any]:
    cw = client("cloudwatch", aws_creds, region)
    sns = client("sns", aws_creds, region)
    steps: list[str] = []
    try:
        try:
            cw.delete_alarms(AlarmNames=[CPU_ALARM_NAME])
            steps.append("✓ Deleted CPU alarm")
        except ClientError:
            pass
        if ctx.sns_topic_arn:
            sns.delete_topic(TopicArn=ctx.sns_topic_arn)
            steps.append("✓ Deleted SNS topic")
        return {"success": True, "steps": steps or ["CloudWatch: nothing to delete"], "error": None}
    except ClientError as exc:
        return {"success": False, "steps": steps, "error": aws_err(exc)}
