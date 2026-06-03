"""Unit tests for shared storage tier normalization."""

import pytest

from app.storage.storage_tiers import normalize_lifecycle_tier


@pytest.mark.parametrize(
    "storage_class,expected",
    [
        ("S3 Standard", "hot"),
        ("STANDARD", "hot"),
        ("Standard Storage", "hot"),
        ("Hot Blob Storage", "hot"),
        ("S3 Standard-IA", "warm"),
        ("Nearline Storage", "warm"),
        ("NEARLINE", "warm"),
        ("Cool Blob Storage", "warm"),
        ("S3 Glacier Flexible", "cold"),
        ("GLACIER", "cold"),
        ("Archive Storage", "cold"),
        ("ARCHIVE", "cold"),
    ],
)
def test_normalize_lifecycle_tier_tri_cloud(storage_class, expected):
    assert normalize_lifecycle_tier(storage_class) == expected
