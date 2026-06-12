"""Azure resource group region resolution."""

from unittest.mock import MagicMock

from azure.core.exceptions import ResourceNotFoundError

from app.provision.sdk_modules.azure_resource_group import (
    region_scoped_resource_group,
    resolve_azure_resource_group,
)
from app.provision.sdk_modules.context import SdkDeployContext


def _mock_rg(location: str):
    rg = MagicMock()
    rg.location = location
    return rg


def test_region_scoped_resource_group_suffix():
    assert region_scoped_resource_group("zenith-rg", "centralus") == "zenith-rg-centralus"
    assert region_scoped_resource_group("zenith-rg-centralus", "centralus") == "zenith-rg-centralus"


def test_resolve_reuses_rg_when_location_matches():
    client = MagicMock()
    client.resource_groups.get.side_effect = lambda name: (
        _mock_rg("eastus") if name == "zenith-rg" else (_ for _ in ()).throw(ResourceNotFoundError("x"))
    )
    rg, loc, notes = resolve_azure_resource_group(
        client, {"resource_group_name": "zenith-rg", "azure_location": "eastus"}
    )
    assert rg == "zenith-rg"
    assert loc == "eastus"
    assert notes == []


def test_resolve_uses_scoped_rg_when_location_differs():
    client = MagicMock()

    def _get(name: str):
        if name == "zenith-rg":
            return _mock_rg("eastus")
        raise ResourceNotFoundError(name)

    client.resource_groups.get.side_effect = _get
    rg, loc, notes = resolve_azure_resource_group(
        client, {"resource_group_name": "zenith-rg", "azure_location": "centralus"}
    )
    assert rg == "zenith-rg-centralus"
    assert loc == "centralus"
    assert notes


def test_resolve_new_rg_when_none_exists():
    client = MagicMock()
    client.resource_groups.get.side_effect = ResourceNotFoundError("missing")
    rg, loc, notes = resolve_azure_resource_group(
        client, {"resource_group_name": "zenith-rg", "azure_location": "centralus"}
    )
    assert rg == "zenith-rg"
    assert loc == "centralus"
    assert notes == []


def test_azure_effective_location_prefers_context():
    from app.provision.sdk_modules.azure_resource_group import azure_effective_location

    ctx = SdkDeployContext(azure_location="westus2")
    assert azure_effective_location({"azure_location": "eastus"}, ctx) == "westus2"
