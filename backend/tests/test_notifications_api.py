"""Tests for paginated notifications API."""

import pytest

from app.notifications import service as notification_service
from app.database.mongo_client import get_database

COLLECTION = "user_notifications"


@pytest.fixture
def username():
    return "notif_api_test_user"


@pytest.fixture(autouse=True)
def cleanup(username):
    get_database()[COLLECTION].delete_many({"username": username})
    yield
    get_database()[COLLECTION].delete_many({"username": username})


def test_paginated_list_and_unread_filter(username):
    notification_service.create_notification(
        username, title="A", message="one", type="info"
    )
    nid = notification_service.create_notification(
        username, title="B", message="two", type="error"
    )
    notification_service.mark_read(username, nid)

    items, total, unread = notification_service.list_notifications_paginated(
        username, limit=10, skip=0, read_filter="unread"
    )
    assert total == 1
    assert unread == 1
    assert items[0]["title"] == "A"

    recent, unread_recent = notification_service.list_recent_notifications(username, limit=8)
    assert len(recent) == 2
    assert unread_recent == 1
