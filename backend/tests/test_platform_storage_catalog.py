"""Tests for platform storage catalog."""

import json

import pytest

from app.cloud import platform_storage_catalog as catalog


@pytest.fixture(autouse=True)
def clear_catalog_cache():
    catalog.invalidate_platform_catalog_cache()
    yield
    catalog.invalidate_platform_catalog_cache()


def test_resolve_platform_destination_from_inline_catalog(monkeypatch):
    regions = [
        {
            "slug": "asia",
            "label": "Asia",
            "aws": {"bucket": "aws-asia", "region": "ap-south-1"},
            "gcp": {"bucket": "gcp-asia", "location": "ASIA-SOUTH1"},
            "azure": {
                "account_name": "acctasia",
                "account_key": "keyasia",
                "container": "cont-asia",
                "region": "centralindia",
            },
        },
        {
            "slug": "europe",
            "label": "Europe",
            "aws": {"bucket": "aws-eu", "region": "eu-west-1"},
            "gcp": {"bucket": "gcp-eu", "location": "EUROPE-WEST1"},
            "azure": {
                "account_name": "acceu",
                "account_key": "keyeu",
                "container": "cont-eu",
                "region": "westeurope",
            },
        },
    ]
    monkeypatch.setattr(
        catalog.settings,
        "PLATFORM_STORAGE_CATALOG",
        json.dumps(regions),
    )
    catalog.invalidate_platform_catalog_cache()

    dest = catalog.resolve_platform_destination("AWS", "europe")
    assert dest is not None
    assert dest["bucket"] == "aws-eu"
    assert dest["region"] == "eu-west-1"

    buckets = catalog.get_platform_buckets_for_csp("GCP")
    assert len(buckets) == 2
    assert buckets[0]["name"] == "gcp-asia"
    assert catalog.catalog_is_multi_region() is True


def test_legacy_fallback_single_region(monkeypatch):
    monkeypatch.setattr(catalog.settings, "PLATFORM_STORAGE_CATALOG", "")
    monkeypatch.setattr(catalog.settings, "PLATFORM_STORAGE_CATALOG_JSON", "")
    catalog.invalidate_platform_catalog_cache()

    regions = catalog.get_platform_regions()
    assert len(regions) == 1
    assert regions[0]["slug"] == "asia"
    assert catalog.catalog_is_multi_region() is False

    dest = catalog.resolve_platform_destination("AWS")
    assert dest is not None
    assert dest["bucket"]


def test_resolve_platform_destination_by_bucket(monkeypatch):
    regions = [
        {
            "slug": "us",
            "label": "United States",
            "aws": {"bucket": "aws-us", "region": "us-east-1"},
            "gcp": {"bucket": "gcp-us", "location": "US-EAST1"},
            "azure": {
                "account_name": "acctus",
                "account_key": "keyus",
                "container": "cont-us",
                "region": "eastus",
            },
        },
    ]
    monkeypatch.setattr(
        catalog.settings,
        "PLATFORM_STORAGE_CATALOG",
        json.dumps(regions),
    )
    catalog.invalidate_platform_catalog_cache()

    dest = catalog.resolve_platform_destination_by_bucket("Azure", "cont-us")
    assert dest is not None
    assert dest["account_name"] == "acctus"
    assert dest["platform_slug"] == "us"


def test_resolve_platform_storage_target(monkeypatch):
    from app.byoc.credential_resolver import resolve_platform_storage_target

    regions = [
        {
            "slug": "europe",
            "label": "Europe",
            "aws": {"bucket": "aws-eu", "region": "eu-west-1"},
            "gcp": {"bucket": "gcp-eu", "location": "EUROPE-WEST1"},
            "azure": {
                "account_name": "acceu",
                "account_key": "keyeu",
                "container": "cont-eu",
                "region": "westeurope",
            },
        },
    ]
    monkeypatch.setattr(
        catalog.settings,
        "PLATFORM_STORAGE_CATALOG",
        json.dumps(regions),
    )
    catalog.invalidate_platform_catalog_cache()

    dest = resolve_platform_storage_target("demo", "GCP", region_slug="europe")
    assert dest is not None
    assert dest["bucket"] == "gcp-eu"


def test_resolve_azure_shared_container_by_region(monkeypatch):
    regions = [
        {
            "slug": "asia",
            "label": "Asia",
            "azure": {
                "account_name": "acctasia",
                "account_key": "k1",
                "container": "zenith-storage",
                "region": "centralindia",
            },
        },
        {
            "slug": "europe",
            "label": "Europe",
            "azure": {
                "account_name": "acceu",
                "account_key": "k2",
                "container": "zenith-storage",
                "region": "northeurope",
            },
        },
    ]
    monkeypatch.setattr(
        catalog.settings,
        "PLATFORM_STORAGE_CATALOG",
        json.dumps(regions),
    )
    catalog.invalidate_platform_catalog_cache()

    asia = catalog.resolve_platform_destination_by_bucket(
        "Azure", "zenith-storage", cloud_region="centralindia"
    )
    europe = catalog.resolve_platform_destination_by_bucket(
        "Azure", "zenith-storage", cloud_region="northeurope"
    )
    assert asia is not None
    assert asia["account_name"] == "acctasia"
    assert europe is not None
    assert europe["account_name"] == "acceu"

    by_acct = catalog.resolve_platform_destination_by_bucket(
        "Azure", "zenith-storage", account_name="acceu"
    )
    assert by_acct is not None
    assert by_acct["platform_slug"] == "europe"
