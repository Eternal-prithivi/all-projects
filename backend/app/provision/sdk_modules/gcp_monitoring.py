"""GCP Cloud Monitoring alert SDK module."""

from __future__ import annotations

from typing import Any

from google.cloud import monitoring_v3

from app.provision.sdk_clients import gcp_monitoring_client
from app.provision.sdk_modules.context import SdkDeployContext


def plan_gcp_monitoring(config: dict, cloud_env: dict[str, str]) -> dict[str, Any]:
    lines = ["  + google_monitoring_notification_channel.email"]
    if config.get("enable_gce"):
        lines.append("  + google_monitoring_alert_policy.instance_cpu")
    return {"lines": lines, "error": None, "resources": lines}


def apply_gcp_monitoring(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> dict[str, Any]:
    channel_client, alert_client, project = gcp_monitoring_client(cloud_env)
    email = (config.get("alarm_email") or "").strip()
    steps: list[str] = []
    try:
        channel_name = ""
        if email:
            channel = monitoring_v3.NotificationChannel(
                type_="email",
                display_name="Zenith Email",
                labels={"email_address": email},
            )
            created = channel_client.create_notification_channel(
                name=f"projects/{project}",
                notification_channel=channel,
            )
            channel_name = created.name
            ctx.monitoring_channel_id = channel_name
            steps.append(f"✓ Monitoring email channel for {email}")

        if config.get("enable_gce") and ctx.gce_name:
            filter_expr = (
                'resource.type = "gce_instance" AND '
                f'resource.labels.instance_id = "{ctx.gce_name}" AND '
                'metric.type = "compute.googleapis.com/instance/cpu/utilization"'
            )
            policy = monitoring_v3.AlertPolicy(
                display_name="Zenith GCE CPU alert",
                combiner=monitoring_v3.AlertPolicy.ConditionCombinerType.OR,
                conditions=[
                    monitoring_v3.AlertPolicy.Condition(
                        display_name="CPU utilization",
                        condition_threshold=monitoring_v3.AlertPolicy.Condition.MetricThreshold(
                            filter=filter_expr,
                            comparison=monitoring_v3.ComparisonType.COMPARISON_GT,
                            threshold_value=0.85,
                            duration={"seconds": 300},
                            aggregations=[
                                monitoring_v3.Aggregation(
                                    alignment_period={"seconds": 60},
                                    per_series_aligner=monitoring_v3.Aggregation.Aligner.ALIGN_MEAN,
                                )
                            ],
                        ),
                    )
                ],
                notification_channels=[channel_name] if channel_name else [],
            )
            created_policy = alert_client.create_alert_policy(
                name=f"projects/{project}",
                alert_policy=policy,
            )
            ctx.alert_policy_id = created_policy.name
            steps.append("✓ CPU alert policy for GCE instance")

        if not steps:
            steps.append("✓ Monitoring configured (no email or GCE — skipped)")
        return {"success": True, "steps": steps, "error": None}
    except Exception as exc:
        return {"success": False, "steps": steps, "error": str(exc)}


def destroy_gcp_monitoring(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> dict[str, Any]:
    channel_client, alert_client, project = gcp_monitoring_client(cloud_env)
    steps: list[str] = []
    try:
        if ctx.alert_policy_id:
            try:
                alert_client.delete_alert_policy(name=ctx.alert_policy_id)
                steps.append("✓ Deleted alert policy")
            except Exception:
                pass
        if ctx.monitoring_channel_id:
            try:
                channel_client.delete_notification_channel(name=ctx.monitoring_channel_id)
                steps.append("✓ Deleted notification channel")
            except Exception:
                pass
        return {"success": True, "steps": steps or ["Monitoring: nothing to delete"], "error": None}
    except Exception as exc:
        return {"success": False, "steps": steps, "error": str(exc)}


def check_gcp_monitoring_drift(
    config: dict, cloud_env: dict[str, str], ctx: SdkDeployContext
) -> tuple[int, list[str]]:
    if not ctx.alert_policy_id and not ctx.monitoring_channel_id:
        return 0, []
    _, alert_client, _ = gcp_monitoring_client(cloud_env)
    try:
        if ctx.alert_policy_id:
            alert_client.get_alert_policy(name=ctx.alert_policy_id)
        return 0, []
    except Exception:
        return 1, ["~ GCP monitoring policy missing or changed"]
