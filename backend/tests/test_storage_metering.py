"""Unit tests for storage API metering."""

import pytest

from app.billing.storage_metering import (
    get_storage_metering_summary,
    list_object_api_pages,
    record_storage_meter_event,
    STORAGE_OPERATION_RATES_USD,
)

pytestmark = pytest.mark.integration


def test_list_object_api_pages():
    assert list_object_api_pages(0) == 1
    assert list_object_api_pages(1) == 1
    assert list_object_api_pages(1000) == 1
    assert list_object_api_pages(1001) == 2


def test_record_and_summarize_storage_metering(test_database):
    username = "meter_user"
    record_storage_meter_event(username, "GCP", "list_buckets", count=2)
    record_storage_meter_event(username, "AWS", "upload", count=3)
    record_storage_meter_event(username, "Azure", "list_objects", count=1)

    summary = get_storage_metering_summary(username)
    assert summary["estimated_usd"]["GCP"] == round(
        STORAGE_OPERATION_RATES_USD["GCP"]["list_buckets"] * 2, 6
    )
    assert summary["estimated_usd"]["AWS"] == round(
        STORAGE_OPERATION_RATES_USD["AWS"]["upload"] * 3, 6
    )
    assert summary["by_csp"]["GCP"]["list_buckets"] == 2
    assert summary["by_csp"]["AWS"]["upload"] == 3
    assert summary["by_csp"]["Azure"]["list_objects"] == 1
    assert summary["estimated_usd"]["total"] > 0
