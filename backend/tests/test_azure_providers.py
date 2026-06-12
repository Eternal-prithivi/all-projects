"""Azure resource provider registration helpers."""

from unittest.mock import MagicMock, patch

from app.provision.sdk_modules.azure_providers import (
    azure_providers_for_config,
    ensure_azure_resource_providers,
)


def test_azure_providers_for_vm_stack():
    providers = azure_providers_for_config(
        {
            "enable_vnet": True,
            "enable_azure_vm": True,
            "enable_azure_storage": True,
        }
    )
    assert "Microsoft.Network" in providers
    assert "Microsoft.Compute" in providers
    assert "Microsoft.Storage" in providers


@patch("app.provision.sdk_modules.azure_providers.azure_resource_client")
def test_ensure_providers_skips_when_registered(mock_resource_client):
    client = MagicMock()
    mock_resource_client.return_value = (client, None, None)
    client.providers.get.return_value.registration_state = "Registered"

    result = ensure_azure_resource_providers(
        {"enable_vnet": True, "csp": "Azure"},
        {},
    )
    assert result["success"] is True
    client.providers.register.assert_not_called()


@patch("app.provision.sdk_modules.azure_providers._wait_for_registered")
@patch("app.provision.sdk_modules.azure_providers.azure_resource_client")
def test_ensure_providers_registers_missing(mock_resource_client, mock_wait):
    client = MagicMock()
    mock_resource_client.return_value = (client, None, None)
    client.providers.get.return_value.registration_state = "NotRegistered"

    result = ensure_azure_resource_providers(
        {"enable_vnet": True, "csp": "Azure"},
        {},
    )
    assert result["success"] is True
    registered = [call.args[0] for call in client.providers.register.call_args_list]
    assert "Microsoft.Network" in registered
    assert mock_wait.call_count >= 1


@patch("app.provision.sdk_modules.azure_providers._wait_for_registered")
@patch("app.provision.sdk_modules.azure_providers.azure_resource_client")
def test_ensure_providers_skips_register_when_already_registering(mock_resource_client, mock_wait):
    client = MagicMock()
    mock_resource_client.return_value = (client, None, None)
    client.providers.get.return_value.registration_state = "Registering"

    result = ensure_azure_resource_providers(
        {"enable_vnet": True, "csp": "Azure"},
        {},
    )
    assert result["success"] is True
    client.providers.register.assert_not_called()
    assert mock_wait.call_count == 3
