"""Deployment context for GCP/Azure SDK (fast-path) provisions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class SdkDeployContext:
    gcs_bucket: str = ""
    gcp_project: str = ""
    azure_resource_group: str = ""
    azure_storage_account: str = ""
    azure_container: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "gcs_bucket": self.gcs_bucket,
            "gcp_project": self.gcp_project,
            "azure_resource_group": self.azure_resource_group,
            "azure_storage_account": self.azure_storage_account,
            "azure_container": self.azure_container,
        }

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "SdkDeployContext":
        if not data:
            return cls()
        return cls(
            gcs_bucket=str(data.get("gcs_bucket") or ""),
            gcp_project=str(data.get("gcp_project") or ""),
            azure_resource_group=str(data.get("azure_resource_group") or ""),
            azure_storage_account=str(data.get("azure_storage_account") or ""),
            azure_container=str(data.get("azure_container") or ""),
        )
