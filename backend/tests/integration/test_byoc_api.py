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
        "secure_bucket_name": "my-gcp-bucket-secure",
        "secure_dual_write": False,
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


@patch("app.byoc.routes_byoc.ensure_gcp_buckets_exist", return_value=(True, "Buckets ready"))
@patch("app.byoc.routes_byoc.test_gcp_credentials")
def test_byoc_connect_and_disconnect(mock_test, _mock_buckets, client, auth_headers, pro_subscription, db):
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


@patch("app.byoc.routes_byoc.list_gcp_buckets_from_json")
@patch("app.byoc.routes_byoc.test_gcp_credentials")
def test_byoc_verify_gcp(mock_test, mock_list, client, auth_headers, pro_subscription):
    mock_test.return_value = _gcp_ok_result(message="Bucket OK")
    mock_list.return_value = {
        "project_id": "test-proj",
        "buckets": [{"name": "my-gcp-bucket", "location": "US"}],
    }
    headers, user = auth_headers()
    pro_subscription(user["username"])
    response = client.post(
        "/api/byoc/verify-credentials",
        headers=headers,
        json={
            "csp": "GCP",
            "connection_method": "access_keys",
            "service_account_json": '{"type": "service_account", "project_id": "test"}',
            "gcp_bucket_name": "my-gcp-bucket",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is True
    assert body["csp"] == "GCP"
    assert len(body["buckets"]) == 1


@patch("app.byoc.routes_byoc.test_azure_credentials")
@patch("app.byoc.routes_byoc.list_azure_containers_from_keys")
def test_byoc_verify_azure(mock_list, mock_test, client, auth_headers, pro_subscription):
    mock_test.return_value = SimpleNamespace(
        success=True,
        message="Azure OK",
        csp="Azure",
        bucket_name="my-container",
    )
    mock_list.return_value = {
        "containers": [{"name": "my-container"}],
    }
    headers, user = auth_headers()
    pro_subscription(user["username"])
    response = client.post(
        "/api/byoc/verify-credentials",
        headers=headers,
        json={
            "csp": "Azure",
            "connection_method": "access_keys",
            "account_name": "acct",
            "account_key": "key123",
            "container_name": "my-container",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["valid"] is True
    assert body["containers"][0]["name"] == "my-container"


@patch("app.byoc.routes_byoc.list_gcp_buckets_from_json")
def test_byoc_discover_gcp_buckets(mock_list, client, auth_headers, pro_subscription):
    mock_list.return_value = {"buckets": [{"name": "b1"}], "project_id": "p1", "count": 1}
    headers, user = auth_headers()
    pro_subscription(user["username"])
    response = client.post(
        "/api/byoc/gcp-buckets/discover",
        headers=headers,
        json={"service_account_json": '{"type": "service_account"}'},
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_byoc_free_plan_rejected(client, auth_headers, db):
    headers, user = auth_headers()
    db["subscriptions"].update_one(
        {"$or": [{"user_id": user["username"]}, {"username": user["username"]}]},
        {"$set": {"user_id": user["username"], "username": user["username"], "plan_id": "free", "status": "active"}},
        upsert=True,
    )
    response = client.post("/api/byoc/test", headers=headers, json=_gcp_connect_payload())
    assert response.status_code == 403
    assert response.json()["detail"]["upgrade_required"] is True


@patch("app.byoc.routes_byoc.test_gcp_credentials")
def test_byoc_basic_plan_rejected(mock_test, client, auth_headers, pro_subscription):
    mock_test.return_value = _gcp_ok_result()
    headers, user = auth_headers()
    pro_subscription(user["username"], plan_id="basic")

    response = client.post("/api/byoc/test", headers=headers, json=_gcp_connect_payload())
    assert response.status_code == 403
    assert response.json()["detail"]["upgrade_required"] is True

    status = client.get("/api/byoc/status", headers=headers).json()
    assert status["eligible"] is False


@patch("app.byoc.routes_byoc.test_gcp_credentials")
def test_byoc_pro_plan_eligible(mock_test, client, auth_headers, pro_subscription):
    mock_test.return_value = _gcp_ok_result()
    headers, user = auth_headers()
    pro_subscription(user["username"], plan_id="pro")

    response = client.post("/api/byoc/test", headers=headers, json=_gcp_connect_payload())
    assert response.status_code == 200

    status = client.get("/api/byoc/status", headers=headers).json()
    assert status["eligible"] is True
    assert "capabilities" in status


@patch("app.byoc.routes_byoc._verify_azure_compute_credentials", return_value=(True, "Compute credentials validated."))
@patch("app.byoc.routes_byoc._verify_azure_cost_management", return_value=(True, "OK"))
@patch("app.byoc.routes_byoc.test_azure_credentials")
@patch("app.byoc.routes_byoc.ensure_azure_containers_exist", return_value=(True, "ready"))
def test_byoc_azure_extend_compute(
    _mock_containers,
    mock_test,
    _mock_cost,
    _mock_compute,
    client,
    auth_headers,
    pro_subscription,
    db,
):
    mock_test.return_value = SimpleNamespace(
        success=True,
        message="Azure OK",
        csp="Azure",
        bucket_name="storage",
    )
    headers, user = auth_headers()
    pro_subscription(user["username"])

    connect = client.post(
        "/api/byoc/connect",
        headers=headers,
        json={
            "csp": "Azure",
            "connection_method": "access_keys",
            "account_name": "acct",
            "account_key": "key123",
            "storage_container_name": "storage",
            "secure_container_name": "secure",
            "secure_dual_write": False,
        },
    )
    assert connect.status_code == 200, connect.text
    body = connect.json()
    assert body["capabilities"]["provision"] is False

    extend = client.patch(
        "/api/byoc/azure/compute",
        headers=headers,
        json={
            "subscription_id": "sub-1",
            "tenant_id": "tenant-1",
            "client_id": "client-1",
            "client_secret": "secret-1",
        },
    )
    assert extend.status_code == 200, extend.text
    assert extend.json()["capabilities"]["provision"] is True


@patch("app.byoc.routes_byoc.ensure_gcp_buckets_exist", return_value=(True, "Buckets ready"))
@patch("app.byoc.routes_byoc.test_gcp_credentials")
def test_byoc_gcp_connect_skip_tier2_storage_only(mock_test, _mock_buckets, client, auth_headers, pro_subscription):
    mock_test.return_value = _gcp_ok_result(message="Connected")
    headers, user = auth_headers()
    pro_subscription(user["username"])

    connect = client.post("/api/byoc/connect", headers=headers, json=_gcp_connect_payload())
    assert connect.status_code == 200, connect.text
    body = connect.json()
    assert body["capabilities"]["storage"] is True
    assert body["capabilities"]["cost"] is False


@patch("app.byoc.routes_byoc.ensure_gcp_buckets_exist", return_value=(True, "Buckets ready"))
@patch("app.byoc.routes_byoc.test_gcp_credentials")
def test_byoc_gcp_connect_rejects_partial_billing_ids(mock_test, _mock_buckets, client, auth_headers, pro_subscription):
    mock_test.return_value = _gcp_ok_result(message="Connected")
    headers, user = auth_headers()
    pro_subscription(user["username"])

    payload = {**_gcp_connect_payload(), "gcp_billing_dataset_id": "billing_export"}
    response = client.post("/api/byoc/connect", headers=headers, json=payload)
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "gcp_billing_export_incomplete"


@patch("app.byoc.routes_byoc.ensure_azure_containers_exist", return_value=(True, "ready"))
@patch("app.byoc.routes_byoc.test_azure_credentials")
def test_byoc_azure_connect_rejects_partial_sp(mock_test, _mock_containers, client, auth_headers, pro_subscription):
    mock_test.return_value = SimpleNamespace(success=True, message="OK", csp="Azure", bucket_name="s")
    headers, user = auth_headers()
    pro_subscription(user["username"])

    response = client.post(
        "/api/byoc/connect",
        headers=headers,
        json={
            "csp": "Azure",
            "connection_method": "access_keys",
            "account_name": "acct",
            "account_key": "key123",
            "storage_container_name": "storage",
            "secure_container_name": "secure",
            "secure_dual_write": False,
            "azure_subscription_id": "sub-only",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "azure_sp_incomplete"


def test_byoc_setup_guides(client, auth_headers):
    headers, _ = auth_headers()
    response = client.get("/api/byoc/setup-guides", headers=headers)
    assert response.status_code == 200
    assert "gcp_billing" in response.json()["guides"]


def test_verify_credentials_aws_only_rejects_unknown_csp(client, auth_headers, pro_subscription):
    headers, user = auth_headers()
    pro_subscription(user["username"])
    response = client.post(
        "/api/byoc/verify-credentials",
        headers=headers,
        json={"csp": "Oracle", "connection_method": "access_keys"},
    )
    assert response.status_code == 400
