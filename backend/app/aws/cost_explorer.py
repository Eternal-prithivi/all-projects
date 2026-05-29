"""AWS Cost Explorer — per-user BYOC or platform credentials."""

from typing import Any, Dict, List, Optional

from app.storage.cloud_credentials import build_aws_ce_client


def get_cost_and_usage(
    username: str,
    *,
    start_date: str,
    end_date: str,
    granularity: str = "DAILY",
    metrics: Optional[List[str]] = None,
    group_by: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    if metrics is None:
        metrics = ["UnblendedCost"]
    client, _is_byoc = build_aws_ce_client(username)
    return client.get_cost_and_usage(
        TimePeriod={"Start": start_date, "End": end_date},
        Granularity=granularity,
        Metrics=metrics,
        GroupBy=group_by or [],
    )
