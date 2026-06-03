"""Canonical cloud provider identifiers — single source for AWS/GCP/Azure spelling."""

from __future__ import annotations

from typing import Literal, Union

CloudProvider = Literal["AWS", "GCP", "Azure"]
CloudProviderKey = Literal["aws", "gcp", "azure"]

_DISPLAY: dict[str, CloudProvider] = {
    "aws": "AWS",
    "amazon": "AWS",
    "amazon web services": "AWS",
    "gcp": "GCP",
    "google": "GCP",
    "google cloud": "GCP",
    "google cloud platform": "GCP",
    "azure": "Azure",
    "microsoft azure": "Azure",
    "ms azure": "Azure",
}

_KEYS: dict[str, CloudProviderKey] = {
    "aws": "aws",
    "amazon": "aws",
    "gcp": "gcp",
    "google": "gcp",
    "azure": "azure",
}


def normalize_provider(value: Union[str, None]) -> CloudProvider:
    """
    Map user/API input to canonical display form: AWS | GCP | Azure.

    Raises ValueError when the provider is missing or unrecognized.
    """
    if value is None or not str(value).strip():
        raise ValueError("Cloud provider is required")

    key = str(value).strip().lower()
    canonical = _DISPLAY.get(key)
    if canonical:
        return canonical

    upper = str(value).strip().upper()
    if upper in ("AWS", "GCP"):
        return upper  # type: ignore[return-value]
    if upper == "AZURE":
        return "Azure"

    title = str(value).strip().title()
    if title in ("Aws", "Gcp"):
        return "AWS" if title == "Aws" else "GCP"
    if title == "Azure":
        return "Azure"

    raise ValueError(f"Unsupported cloud provider: {value!r}")


def normalize_provider_key(value: Union[str, None]) -> CloudProviderKey:
    """Map input to lowercase API key: aws | gcp | azure."""
    display = normalize_provider(value)
    if display == "AWS":
        return "aws"
    if display == "GCP":
        return "gcp"
    return "azure"


def is_valid_provider(value: Union[str, None]) -> bool:
    try:
        normalize_provider(value)
        return True
    except ValueError:
        return False
