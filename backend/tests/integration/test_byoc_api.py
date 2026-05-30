"""BYOC API integration tests — connect/test/disconnect with mocks."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.integration


def _gcp_ok_result(**overrides):
    base = {
        "success": True,
        "message": "GCP OK",
        "csp": "GCP",
        "bucket_name": "my-gcp-bucket",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _gcp_connect_payload():
    return {
        "csp": "GCP",
        "connection_method": "access_keys",
        "service_account_json": '{"type": "service_account", "project_id": "test"}',
        "gcp_bucket_name": "my-gcp-bucket",
    }


def _aws_connect_payload():
    return {
        "csp": "AWS",
        "connection_method": "access_keys",
        "access_key_id": "AKIATESTKEY",
        "secret_access_key": "test-secret-key",
        "storage_bucket_name": "zenith-e2e-storage",
        "secure_bucket_name": "zenith-e2e-secure",
        "replica_bucket_name": "zenith-e2e-replica",
        "secure_dual_write": True,
        "region": "ap-south-1",
        "primary_region": "ap-south-1",
    }


@patch("app.byoc.routes_byoc.test_gcp_credentials")
def test_byoc_test_credentials_success(mock_test, client, auth_headers, pro_subscription):
    mock_test.return_value = _gcp_ok_result()
    headers, user = auth_headers()
    pro_subscription(user["username"])

    response = client.post("/api/byoc/test", headers=headers, json=_gcp_connect_payload())
    assert response.status_code == 200
    assert response.json()["success"] is True


@patch("app.byoc.routes_byoc.test_gcp_credentials")
def test_byoc_connect_and_disconnect(mock_test, client, auth_headers, pro_subscription, db):
    mock_test.return_value = _gcp_ok_result(message="Connected")
    headers, user = auth_headers()
    pro_subscription(user["username"])

    connect = client.post("/api/byoc/connect", headers=headers, json=_gcp_connect_payload())
    assert connect.status_code == 200, connect.text
    assert connect.json()["success"] is True

    status = client.get("/api/byoc/status", headers=headers)
    assert status.status_code == 200
    assert status.json()["eligible"] is True

    disconnect = client.delete("/api/byoc/disconnect/GCP", headers=headers)
    assert disconnect.status_code == 200


@patch("app.byoc.routes_byoc.ensure_aws_buckets_exist", return_value=(True, "Buckets ready"))
@patch(
    "app.byoc.routes_byoc._resolve_aws_session_creds",
    return_value=("AKIATESTKEY", "test-secret-key", None),
)
def test_byoc_aws_connect_and_disconnect(
    _mock_creds, _mock_buckets, client, auth_headers, pro_subscription, db
):
    headers, user = auth_headers()
    pro_subscription(user["username"])

    connect = client.post("/api/byoc/connect", headers=headers, json=_aws_connect_payload())
    assert connect.status_code == 200, connect.text
    body = connect.json()
    assert body["success"] is True
    assert body["csp"] == "AWS"

    status = client.get("/api/byoc/status", headers=headers).json()
    assert status["connections"]["aws"]["connected"] is True

    disconnect = client.delete("/api/byoc/disconnect/AWS", headers=headers)
    assert disconnect.status_code == 200


@patch(
    "app.byoc.routes_byoc.ensure_aws_buckets_exist",
    return_value=(False, "Simulated bucket access failure"),
)
@patch(
    "app.byoc.routes_byoc._resolve_aws_session_creds",
    return_value=("AKIATESTKEY", "test-secret-key", None),
)
def test_byoc_aws_connect_failure_returns_400(
    _mock_creds, _mock_buckets, client, auth_headers, pro_subscription
):
    headers, user = auth_headers()
    pro_subscription(user["username"])

    response = client.post("/api/byoc/connect", headers=headers, json=_aws_connect_payload())
    assert response.status_code == 400
    assert "failure" in response.json()["detail"].lower()


@patch("app.byoc.routes_byoc.test_gcp_credentials")
def test_byoc_status_isolated_per_user(mock_test, client, auth_headers, pro_subscription, db):
    mock_test.return_value = _gcp_ok_result(message="OK", bucket_name="bucket-a")
    headers_a, user_a = auth_headers()
    headers_b, user_b = auth_headers()
    pro_subscription(user_a["username"])
    pro_subscription(user_b["username"])

    client.post("/api/byoc/connect", headers=headers_a, json=_gcp_connect_payload())

    status_b = client.get("/api/byoc/status", headers=headers_b).json()
    gcp_status = (status_b.get("connections") or {}).get("gcp") or {}
    assert gcp_status.get("connected") is not True
