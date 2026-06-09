"""Tests for platform-scoped storage list and sync filters."""

import json

import pytest

from app.cloud import platform_storage_catalog as catalog
from app.storage.file_queries import build_platform_region_list_filter
from app.storage.routes_storage import _stale_sync_filter


@pytest.fixture(autouse=True)
def clear_catalog_cache():
    catalog.invalidate_platform_catalog_cache()
    yield
    catalog.invalidate_platform_catalog_cache()


@pytest.fixture
def shared_azure_catalog(monkeypatch):
    regions = [
        {
            "slug": "asia",
            "label": "Asia",
            "aws": {"bucket": "aws-asia", "region": "ap-south-1"},
            "gcp": {"bucket": "gcp-asia", "location": "ASIA-SOUTH1"},
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
            "aws": {"bucket": "aws-eu", "region": "eu-west-1"},
            "gcp": {"bucket": "gcp-eu", "location": "EUROPE-WEST1"},
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
    return regions


def test_build_platform_region_list_filter_azure_uses_account(shared_azure_catalog):
    query = build_platform_region_list_filter("demo", "asia")
    azure_legs = [
        clause
        for clause in query["$or"]
        if clause.get("csp") == "Azure"
    ]
    assert len(azure_legs) == 1
    assert azure_legs[0]["cloud_bucket"] == "zenith-storage"
    assert azure_legs[0]["cloud_account"] == "acctasia"
    assert "region" not in azure_legs[0]


def test_stale_sync_filter_scopes_azure_by_account(shared_azure_catalog):
    filt = _stale_sync_filter(
        "demo",
        "Azure",
        "zenith-storage",
        platform_slug="asia",
        cloud_account="acctasia",
        region="centralindia",
    )
    legacy = filt["$or"][1]["$and"]
    assert {"cloud_account": "acctasia"} in legacy
