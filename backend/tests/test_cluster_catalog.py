"""Cluster catalog completeness and per-slot specs."""

from app.vm.cluster_catalog import (
    CLUSTER_DEFINITIONS,
    cluster_create_spec,
    cluster_max_vms,
    cluster_types,
    cluster_vms,
    infer_cluster_from_vm_name,
    resolve_vm_alias,
)
from app.vm.models import ClusterType


def test_seven_clusters_four_slots_each():
    assert len(cluster_types()) == 7
    for definition in CLUSTER_DEFINITIONS:
        assert len(definition.slots) == 4
        assert cluster_max_vms(definition.cluster_type) == 4


def test_unique_slot_ids_per_csp():
    for csp in ("GCP", "AWS", "Azure"):
        names = []
        for ct in cluster_types():
            names.extend(cluster_vms(csp, ct))
        assert len(names) == len(set(names))


def test_azure_disk_at_least_30gb():
    for ct in cluster_types():
        for slot_name in cluster_vms("Azure", ct):
            spec = cluster_create_spec("Azure", ct, slot_name)
            assert spec.disk_gb >= 30


def test_legacy_alias_resolves():
    assert resolve_vm_alias("general-vm-1", "GCP") == "general-micro-vm-1"
    assert resolve_vm_alias("ai-ml-aws-vm-2", "AWS").startswith("ai-ml-")


def test_infer_cluster_from_name():
    assert infer_cluster_from_vm_name("general-small-vm-2") == ClusterType.GENERAL
    assert infer_cluster_from_vm_name("database-iops-azure-vm-4") == ClusterType.DATABASE
    assert infer_cluster_from_vm_name("network-network-aws-vm-1") == ClusterType.NETWORK


def test_cluster_create_spec_uses_slot_tier():
    large = cluster_create_spec("GCP", ClusterType.GENERAL, "general-standard-vm-4")
    micro = cluster_create_spec("GCP", ClusterType.GENERAL, "general-micro-vm-1")
    assert large.machine_type != micro.machine_type
    assert large.disk_gb >= micro.disk_gb


def test_storage_slots_tier_by_size_and_type():
    small = cluster_create_spec("GCP", ClusterType.STORAGE, "storage-small-vm-1")
    xlarge = cluster_create_spec("GCP", ClusterType.STORAGE, "storage-xlarge-vm-4")
    assert small.machine_type != xlarge.machine_type
    assert xlarge.disk_gb > small.disk_gb
    assert xlarge.disk_type == "pd-ssd"
    assert small.disk_type == ""

    aws_small = cluster_create_spec("AWS", ClusterType.STORAGE, "storage-small-aws-vm-1")
    aws_xlarge = cluster_create_spec("AWS", ClusterType.STORAGE, "storage-xlarge-aws-vm-4")
    assert aws_small.machine_type != aws_xlarge.machine_type
    assert aws_xlarge.disk_type == "io2"
    assert aws_xlarge.disk_iops == 3000


def test_database_slots_tier_and_iops_on_top_slot():
    slots = [cluster_create_spec("GCP", ClusterType.DATABASE, name) for name in cluster_vms("GCP", ClusterType.DATABASE)]
    machine_types = [s.machine_type for s in slots]
    assert len(set(machine_types)) == 4
    iops = cluster_create_spec("GCP", ClusterType.DATABASE, "database-iops-vm-4")
    assert iops.disk_type == "pd-ssd"
    assert iops.disk_gb >= cluster_create_spec("GCP", ClusterType.DATABASE, "database-small-vm-1").disk_gb

    aws_iops = cluster_create_spec("AWS", ClusterType.DATABASE, "database-iops-aws-vm-4")
    assert aws_iops.disk_type == "io2"
    assert aws_iops.disk_iops == 5000


def test_network_aws_only_top_slot_uses_network_instance():
    small = cluster_create_spec("AWS", ClusterType.NETWORK, "network-small-aws-vm-1")
    network = cluster_create_spec("AWS", ClusterType.NETWORK, "network-network-aws-vm-4")
    assert small.machine_type != network.machine_type
    assert network.machine_type == "m5n.xlarge"
    assert small.machine_type == "t3.small"


def test_memory_gcp_large_and_xlarge_differ():
    large = cluster_create_spec("GCP", ClusterType.MEMORY, "memory-large-vm-2")
    xlarge = cluster_create_spec("GCP", ClusterType.MEMORY, "memory-xlarge-vm-3")
    highmem = cluster_create_spec("GCP", ClusterType.MEMORY, "memory-highmem-vm-4")
    assert large.machine_type != xlarge.machine_type
    assert "highmem" in large.machine_type
    assert "highmem" in xlarge.machine_type
    assert highmem.disk_gb >= xlarge.disk_gb
    assert highmem.disk_gb > large.disk_gb


def test_all_clusters_monotonic_disk_and_compute_tiers():
    """Each slot should be >= prior slot in disk; compute rank should not regress."""
    rank = {
        "e2-micro": 1, "t3.micro": 1, "Standard_B1s": 1,
        "e2-small": 2, "t3.small": 2, "Standard_B2s": 2,
        "e2-medium": 3, "t3.medium": 3, "Standard_D2s_v3": 3,
        "e2-standard-2": 4, "t3.large": 4,
        "e2-standard-4": 5, "m5.large": 5, "Standard_D4s_v3": 5,
        "e2-standard-8": 6, "m5.xlarge": 6, "Standard_D8s_v3": 6,
        "n2-standard-4": 5, "n2-standard-8": 6, "n2-standard-16": 7,
        "m5.2xlarge": 7, "m5d.2xlarge": 7, "m5n.xlarge": 6,
        "n2-highmem-2": 5, "n2-highmem-4": 6, "n2-highmem-8": 7,
        "r5.large": 5, "r5.xlarge": 6, "r5.2xlarge": 7,
        "Standard_E4s_v3": 5, "Standard_E8s_v3": 6, "Standard_E16s_v3": 7,
        "c2-standard-4": 5, "c5.xlarge": 6, "Standard_F4s_v2": 5,
        "n1-standard-4": 5, "g4dn.xlarge": 6, "Standard_NC4as_T4_v3": 6,
    }
    for csp in ("GCP", "AWS", "Azure"):
        for ct in cluster_types():
            specs = [
                cluster_create_spec(csp, ct, name) for name in cluster_vms(csp, ct)
            ]
            for i in range(1, len(specs)):
                prev, cur = specs[i - 1], specs[i]
                assert cur.disk_gb >= prev.disk_gb, (
                    f"{ct.value}/{csp} slot {i}->{i+1} disk regressed"
                )
                pr = rank.get(prev.machine_type, 0)
                cr = rank.get(cur.machine_type, 0)
                assert cr >= pr, (
                    f"{ct.value}/{csp} slot {i}->{i+1} compute regressed "
                    f"{prev.machine_type}->{cur.machine_type}"
                )
