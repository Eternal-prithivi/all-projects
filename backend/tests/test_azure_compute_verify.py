"""Azure BYOC — compute verification unlocks VM without Cost Management."""

from unittest.mock import MagicMock, patch

from app.byoc.routes_byoc import _merge_azure_sp_tier2, _verify_azure_compute_credentials


def test_merge_azure_sp_uses_compute_not_cost():
    creds = {"account_name": "acct", "account_key": "key"}
    with patch(
        "app.byoc.routes_byoc._verify_azure_compute_credentials",
        return_value=(True, "ok"),
    ) as mock_compute:
        with patch("app.byoc.routes_byoc._verify_azure_cost_management") as mock_cost:
            out = _merge_azure_sp_tier2(
                creds,
                "sub-id",
                "tenant-id",
                "client-id",
                "client-secret",
            )
    mock_compute.assert_called_once()
    mock_cost.assert_not_called()
    assert out["subscription_id"] == "sub-id"
    assert out["client_id"] == "client-id"


def test_verify_azure_compute_credentials_success():
    mock_rg_iter = iter([MagicMock(name="rg1")])
    mock_client = MagicMock()
    mock_client.resource_groups.list.return_value = mock_rg_iter

    with patch("azure.identity.ClientSecretCredential", return_value=MagicMock()):
        with patch(
            "azure.mgmt.compute.ComputeManagementClient",
            return_value=mock_client,
        ):
            ok, msg = _verify_azure_compute_credentials(
                "sub", "tenant", "client", "secret"
            )
    assert ok is True
    assert "Compute" in msg
