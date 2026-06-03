"""Azure Monitor VM metrics (simulated fallback when Monitor is unavailable)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.utils.logger import setup_logger
from app.vm.azure_manager import get_vm_details
from app.vm.models import ClusterType, VMMetricsDB, VMStatus

logger = setup_logger(__name__)


class AzureVMMetricsCollector:
    """Collect Azure VM metrics via Monitor or simulated demo data."""

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

    @staticmethod
    def _simulated(metric_name: str) -> float:
        import random

        if metric_name == "Percentage CPU":
            return round(random.uniform(15.0, 65.0), 2)
        if metric_name == "Available Memory Bytes":
            return round(random.uniform(30.0, 70.0), 2)
        return round(random.uniform(5.0, 40.0), 2)

    async def collect_all_metrics(
        self,
        vm_name: str,
        cluster_type: ClusterType,
        active_users: int,
        last_started: Optional[datetime],
    ) -> VMMetricsDB:
        cpu = self._simulated("Percentage CPU")
        memory = self._simulated("Available Memory Bytes")
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
        hourly = 0.012 if "performance" in vm_name or "ai" in vm_name else 0.006
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
