"""Tests for Storage vs Security bucket classification."""

from app.byoc.aws_bucket_discovery import (
    classify_bucket_role,
    filter_buckets_for_surface,
    infer_security_bucket_by_name,
)


LAYOUT = {
    "storage_bucket_name": "zenith-user-abc-storage",
    "secure_bucket_name": "zenith-user-abc-secure",
    "replica_bucket_name": "zenith-user-abc-replica",
    "primary_region": "ap-south-1",
    "replica_region": "us-east-1",
}


def _bucket(name: str, role: str = "other", region: str = "ap-south-1"):
    return {
        "name": name,
        "region": region,
        "role": role,
        "is_default": False,
        "is_replica": role == "replica",
    }


def test_infer_security_bucket_by_name():
    assert infer_security_bucket_by_name("zenith-alice-xyz-secure") is True
    assert infer_security_bucket_by_name("zenith-alice-xyz-replica") is True
    assert infer_security_bucket_by_name("zenith-user-abc-storage") is False
    assert infer_security_bucket_by_name("my-terraform-state") is False


def test_classify_bucket_roles():
    assert classify_bucket_role("zenith-user-abc-storage", LAYOUT) == "storage"
    assert classify_bucket_role("zenith-user-abc-secure", LAYOUT) == "secure"
    assert classify_bucket_role("zenith-user-abc-replica", LAYOUT) == "replica"
    assert classify_bucket_role("zenith-other-secure", LAYOUT) == "secure"


def test_storage_surface_excludes_vault_buckets():
    buckets = [
        _bucket("zenith-user-abc-storage", "storage"),
        _bucket("zenith-user-abc-secure", "secure"),
        _bucket("zenith-user-abc-replica", "replica"),
        _bucket("terraform-state-412628362844", "other"),
        _bucket("zenith-neighbor-secure", "other"),
    ]
    storage_list = filter_buckets_for_surface(buckets, "storage", layout=LAYOUT)
    names = {b["name"] for b in storage_list}
    assert "zenith-user-abc-storage" in names
    assert "terraform-state-412628362844" in names
    assert "zenith-user-abc-secure" not in names
    assert "zenith-user-abc-replica" not in names
    assert "zenith-neighbor-secure" not in names


def test_security_surface_includes_vault_only():
    buckets = [
        _bucket("zenith-user-abc-storage", "storage"),
        _bucket("zenith-user-abc-secure", "secure"),
        _bucket("zenith-user-abc-replica", "replica"),
        _bucket("terraform-state-412628362844", "other"),
    ]
    security_list = filter_buckets_for_surface(buckets, "security", layout=LAYOUT)
    names = {b["name"] for b in security_list}
    assert "zenith-user-abc-secure" in names
    assert "zenith-user-abc-replica" in names
    assert "zenith-user-abc-storage" not in names
    assert "terraform-state-412628362844" not in names


def test_shared_storage_secure_bucket_security_only():
    shared_layout = {
        **LAYOUT,
        "storage_bucket_name": "zenith-shared-bucket",
        "secure_bucket_name": "zenith-shared-bucket",
        "replica_bucket_name": "",
    }
    buckets = [_bucket("zenith-shared-bucket", "secure")]
    storage_list = filter_buckets_for_surface(buckets, "storage", layout=shared_layout)
    assert len(storage_list) == 0
    security_list = filter_buckets_for_surface(buckets, "security", layout=shared_layout)
    assert len(security_list) == 1
