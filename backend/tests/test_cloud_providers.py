"""Unit tests for canonical cloud provider normalization."""

import pytest

from app.cloud.providers import (
    normalize_provider,
    normalize_provider_key,
    is_valid_provider,
)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("AWS", "AWS"),
        ("aws", "AWS"),
        ("Amazon", "AWS"),
        ("GCP", "GCP"),
        ("gcp", "GCP"),
        ("google cloud", "GCP"),
        ("Azure", "Azure"),
        ("azure", "Azure"),
        ("microsoft azure", "Azure"),
    ],
)
def test_normalize_provider_accepts_aliases(raw, expected):
    assert normalize_provider(raw) == expected


@pytest.mark.parametrize("raw", ["", None, "oracle", "digitalocean"])
def test_normalize_provider_rejects_invalid(raw):
    with pytest.raises(ValueError):
        normalize_provider(raw)


@pytest.mark.parametrize(
    "raw,key",
    [
        ("AWS", "aws"),
        ("gcp", "gcp"),
        ("Azure", "azure"),
    ],
)
def test_normalize_provider_key(raw, key):
    assert normalize_provider_key(raw) == key


def test_is_valid_provider():
    assert is_valid_provider("aws") is True
    assert is_valid_provider("unknown") is False
