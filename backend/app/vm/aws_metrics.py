"""CloudWatch-backed VM metrics for AWS EC2 (with simulated fallback)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from app.utils.config import settings
from app.utils.logger import setup_logger
from app.vm.aws_manager import get_vm_details
from app.vm.aws_runtime import aws_boto_credentials, aws_region
from app.vm.models import ClusterType, VMMetricsDB, VMStatus
from app.provision.boto3_modules.common import client

logger = setup_logger(__name__)


class AwsVMMetricsCollector:
    """Collect EC2 metrics via CloudWatch or simulated demo data."""

    def __init__(self) -> None:
        self._cw = None
        try:
            self._cw = client("cloudwatch", aws_boto_credentials(), aws_region())
        except Exception as exc:
            logger.warning("CloudWatch client unavailable: %s", exc)

    def get_vm_status(self, vm_name: str) -> Optional[VMStatus]:
        try:
            details = get_vm_details(vm_name)
            raw = details.get("status", "UNKNOWN")
            if raw == "RUNNING":
                return VMStatus.RUNNING
            if raw == "TERMINATED":
                return VMStatus.TERMINATED
            return VMStatus(raw)
        except Exception:
            return None

    def _metric_avg(
        self, instance_id: str, namespace: str, metric_name: str, minutes: int = 5
    ) -> float:
        if not self._cw or not instance_id:
            return self._simulated(metric_name)

        end = datetime.now(timezone.utc)
        start = end - timedelta(minutes=minutes)
        try:
            resp = self._cw.get_metric_statistics(
                Namespace=namespace,
                MetricName=metric_name,
                Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                StartTime=start,
                EndTime=end,
                Period=60,
                Statistics=["Average"],
            )
            points = resp.get("Datapoints", [])
            if not points:
                return self._simulated(metric_name)
            values = [p["Average"] for p in points]
            return round(sum(values) / len(values), 2)
        except Exception as exc:
            logger.debug("CloudWatch %s failed: %s", metric_name, exc)
            return self._simulated(metric_name)

    @staticmethod
    def _simulated(metric_name: str) -> float:
        import random

        if metric_name == "CPUUtilization":
            return round(random.uniform(15.0, 65.0), 2)
        if metric_name == "MemoryUtilization":
            return round(random.uniform(30.0, 70.0), 2)
        return round(random.uniform(5.0, 40.0), 2)

    async def collect_all_metrics(
        self,
        vm_name: str,
        cluster_type: ClusterType,
        active_users: int,
        last_started: Optional[datetime],
    ) -> VMMetricsDB:
        instance_id = None
        try:
            instance_id = get_vm_details(vm_name).get("instance_id")
        except Exception:
            pass

        cpu = self._metric_avg(
            instance_id or "", "AWS/EC2", "CPUUtilization"
        )
        memory = self._simulated("MemoryUtilization")
        import random

        disk_io = {
            "read_mb": round(random.uniform(5.0, 50.0), 2),
            "write_mb": round(random.uniform(2.0, 30.0), 2),
        }
        network = {
            "in_mb": round(random.uniform(1.0, 20.0), 2),
            "out_mb": round(random.uniform(0.5, 15.0), 2),
        }
        uptime_hours = 0.0
        if last_started and self.get_vm_status(vm_name) == VMStatus.RUNNING:
            uptime_hours = round(
                (datetime.utcnow() - last_started).total_seconds() / 3600, 2
            )
        hourly = 0.0116 if "medium" in vm_name else 0.0058
        return VMMetricsDB(
            vm_name=vm_name,
            cluster_type=cluster_type,
            cpu_usage=cpu,
            memory_usage=memory,
            disk_io_read_mb=disk_io["read_mb"],
            disk_io_write_mb=disk_io["write_mb"],
            network_in_mb=network["in_mb"],
            network_out_mb=network["out_mb"],
            active_users=active_users,
            uptime_hours=uptime_hours,
            estimated_cost_usd=round(uptime_hours * hourly, 4),
            last_started=last_started,
            last_stopped=None if uptime_hours > 0 else datetime.utcnow(),
            recorded_at=datetime.utcnow(),
        )
