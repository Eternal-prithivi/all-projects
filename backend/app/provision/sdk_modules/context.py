"""Deployment context for GCP/Azure SDK (fast-path) provisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class SdkDeployContext:
    # GCP
    gcs_bucket: str = ""
    gcp_project: str = ""
    gcp_network_name: str = ""
    gcp_subnet_name: str = ""
    gce_name: str = ""
    gce_zone: str = ""
    public_ip: str = ""
    service_account_email: str = ""
    firestore_database_id: str = ""
    monitoring_channel_id: str = ""
    alert_policy_id: str = ""

    # Azure
    azure_resource_group: str = ""
    azure_storage_account: str = ""
    azure_container: str = ""
    vnet_name: str = ""
    subnet_name: str = ""
    nic_name: str = ""
    public_ip_name: str = ""
    vm_name: str = ""
    vm_public_ip: str = ""
    ssh_private_key_pem: str = ""
    action_group_id: str = ""
    cosmos_account_name: str = ""
    cosmos_database_name: str = ""

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, val in (
            ("gcs_bucket", self.gcs_bucket),
            ("gcp_project", self.gcp_project),
            ("gcp_network_name", self.gcp_network_name),
            ("gcp_subnet_name", self.gcp_subnet_name),
            ("gce_name", self.gce_name),
            ("gce_zone", self.gce_zone),
            ("public_ip", self.public_ip),
            ("service_account_email", self.service_account_email),
            ("firestore_database_id", self.firestore_database_id),
            ("monitoring_channel_id", self.monitoring_channel_id),
            ("alert_policy_id", self.alert_policy_id),
            ("azure_resource_group", self.azure_resource_group),
            ("azure_storage_account", self.azure_storage_account),
            ("azure_container", self.azure_container),
            ("vnet_name", self.vnet_name),
            ("subnet_name", self.subnet_name),
            ("nic_name", self.nic_name),
            ("public_ip_name", self.public_ip_name),
            ("vm_name", self.vm_name),
            ("vm_public_ip", self.vm_public_ip),
            ("ssh_private_key_pem", self.ssh_private_key_pem),
            ("action_group_id", self.action_group_id),
            ("cosmos_account_name", self.cosmos_account_name),
            ("cosmos_database_name", self.cosmos_database_name),
        ):
            if val:
                out[key] = val
        return out

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "SdkDeployContext":
        if not data:
            return cls()
        return cls(
            gcs_bucket=str(data.get("gcs_bucket") or ""),
            gcp_project=str(data.get("gcp_project") or ""),
            gcp_network_name=str(data.get("gcp_network_name") or ""),
            gcp_subnet_name=str(data.get("gcp_subnet_name") or ""),
            gce_name=str(data.get("gce_name") or ""),
            gce_zone=str(data.get("gce_zone") or ""),
            public_ip=str(data.get("public_ip") or ""),
            service_account_email=str(data.get("service_account_email") or ""),
            firestore_database_id=str(data.get("firestore_database_id") or ""),
            monitoring_channel_id=str(data.get("monitoring_channel_id") or ""),
            alert_policy_id=str(data.get("alert_policy_id") or ""),
            azure_resource_group=str(data.get("azure_resource_group") or ""),
            azure_storage_account=str(data.get("azure_storage_account") or ""),
            azure_container=str(data.get("azure_container") or ""),
            vnet_name=str(data.get("vnet_name") or ""),
            subnet_name=str(data.get("subnet_name") or ""),
            nic_name=str(data.get("nic_name") or ""),
            public_ip_name=str(data.get("public_ip_name") or ""),
            vm_name=str(data.get("vm_name") or ""),
            vm_public_ip=str(data.get("vm_public_ip") or ""),
            ssh_private_key_pem=str(data.get("ssh_private_key_pem") or ""),
            action_group_id=str(data.get("action_group_id") or ""),
            cosmos_account_name=str(data.get("cosmos_account_name") or ""),
            cosmos_database_name=str(data.get("cosmos_database_name") or ""),
        )
