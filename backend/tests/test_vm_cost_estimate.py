"""VM slot cost estimate tests."""

from app.vm.cluster_catalog import cluster_vms
from app.vm.models import ClusterType
from app.vm.vm_cost_estimate import (
    estimate_cluster_cost_range,
    estimate_vm_slot_cost,
)


def test_slot_estimate_has_monthly_and_hourly():
    spec = estimate_vm_slot_cost("GCP", vm_name="general-small-vm-2")
    assert spec["total_monthly_usd"] > 0
    assert spec["hourly_usd"] > 0
    assert spec["compute_monthly_usd"] > 0
    assert len(spec["usage_examples"]) >= 2
    assert spec["is_approximate"] is True


def test_larger_slot_costs_more_than_smaller():
    small = estimate_vm_slot_cost("AWS", vm_name="storage-small-aws-vm-1")
    xlarge = estimate_vm_slot_cost("AWS", vm_name="storage-xlarge-aws-vm-4")
    assert xlarge["total_monthly_usd"] > small["total_monthly_usd"]


def test_cluster_range_spans_all_slots():
    data = estimate_cluster_cost_range("GCP", ClusterType.DATABASE)
    assert data["min_monthly_usd"] < data["max_monthly_usd"]
    assert len(data["slots"]) == len(cluster_vms("GCP", ClusterType.DATABASE))


def test_iops_slot_includes_disk_component():
    iops = estimate_vm_slot_cost("GCP", vm_name="database-iops-vm-4")
    assert iops["disk_monthly_usd"] > 0
    assert iops["disk_type"] == "pd-ssd"
