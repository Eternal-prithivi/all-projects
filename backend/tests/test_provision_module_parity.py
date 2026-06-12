"""Every catalog module must map to a fast-path or Terraform implementation."""

from app.provision.boto3_composer import BOTO3_IMPLEMENTED, MODULE_FLAGS as AWS_FLAGS
from app.provision.provision_catalog import (
    AWS_MODULES,
    AZURE_MODULES,
    GCP_MODULES,
    modules_for_csp,
)
from app.provision.sdk_composer import SDK_AZURE_MODULES, SDK_GCP_MODULES


def _module_keys(modules):
    return {m["key"] for m in modules}


def test_aws_catalog_matches_boto3_implemented():
    catalog_keys = _module_keys(AWS_MODULES)
    # billing is optional in catalog but implemented in boto3
    assert BOTO3_IMPLEMENTED <= catalog_keys | {"billing"}
    for mod in AWS_MODULES:
        assert mod["flag"] in AWS_FLAGS.values() or mod["key"] == "billing"


def test_gcp_catalog_matches_sdk_modules():
    catalog_keys = _module_keys(GCP_MODULES)
    assert SDK_GCP_MODULES == catalog_keys


def test_azure_catalog_matches_sdk_modules():
    catalog_keys = _module_keys(AZURE_MODULES)
    assert SDK_AZURE_MODULES == catalog_keys


def test_modules_for_csp_returns_distinct_flags():
    for csp in ("AWS", "GCP", "Azure"):
        modules = modules_for_csp(csp)
        flags = [m["flag"] for m in modules]
        assert len(flags) == len(set(flags)), f"duplicate flags for {csp}"
