"""SDK composer parity — all catalog templates supported on GCP/Azure."""

from app.provision.provision_catalog import templates_for_csp
from app.provision.provision_defaults import skeleton_config_for_template
from app.provision.sdk_composer import (
    SDK_AZURE_MODULES,
    SDK_GCP_MODULES,
    enabled_sdk_modules,
    sdk_can_handle,
)


def test_gcp_all_modules_supported():
    assert SDK_GCP_MODULES == frozenset({
        "gcs", "gcp_network", "gce", "gcp_service_account", "gcp_monitoring", "firestore",
    })


def test_azure_all_modules_supported():
    assert SDK_AZURE_MODULES == frozenset({
        "azure_storage", "vnet", "azure_vm", "azure_monitor", "cosmos",
    })


def test_sdk_can_handle_all_gcp_templates():
    for template in ("static-site", "backend-app", "serverless-db"):
        cfg = skeleton_config_for_template("GCP", template)
        ok, unsupported = sdk_can_handle(cfg)
        assert ok, f"{template} unsupported: {unsupported}"
        assert enabled_sdk_modules(cfg)


def test_sdk_can_handle_all_azure_templates():
    for template in ("static-site", "backend-app", "serverless-db"):
        cfg = skeleton_config_for_template("Azure", template)
        ok, unsupported = sdk_can_handle(cfg)
        assert ok, f"{template} unsupported: {unsupported}"
        assert enabled_sdk_modules(cfg)


def test_catalog_template_keys_match():
    for csp in ("AWS", "GCP", "Azure"):
        keys = {t["key"] for t in templates_for_csp(csp)}
        assert keys == {"static-site", "backend-app", "serverless-db"}
