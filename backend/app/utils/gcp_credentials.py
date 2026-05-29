"""Check whether a GCP service account key file is configured and present on disk."""

import os

from app.utils.config import settings


def gcp_credentials_file_present() -> bool:
    gcp_key = getattr(settings, "GCP_SERVICE_ACCOUNT_JSON_PATH", None) or getattr(
        settings, "GCP_SA_KEY_PATH", None
    )
    if not gcp_key:
        return False
    if os.path.isabs(gcp_key):
        return os.path.exists(gcp_key)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_root = os.path.dirname(base_dir)
    return os.path.exists(os.path.join(project_root, "backend", gcp_key))
