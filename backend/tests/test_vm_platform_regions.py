"""Platform region → compute location mapping for VM cluster."""

from app.vm.gcp_zones import gcp_zone_from_location
from app.vm.platform_regions import resolve_vm_compute


def test_gcp_zone_from_location_explicit_zone():
    assert gcp_zone_from_location("ASIA-SOUTH1") == "asia-south1-a"
    assert gcp_zone_from_location("us-central1-a") == "us-central1-a"
    assert gcp_zone_from_location(
        "EUROPE-WEST1",
        explicit_zone="europe-west1-c",
    ) == "europe-west1-c"


def test_gcp_zone_from_location_picks_available_zone():
    europe_zones = frozenset(
        {"europe-west1-b", "europe-west1-c", "europe-west1-d"},
    )
    assert (
        gcp_zone_from_location("EUROPE-WEST1", available_zones=europe_zones)
        == "europe-west1-b"
    )


def test_resolve_vm_compute_uses_catalog_slug(monkeypatch):
    monkeypatch.setattr(
        "app.vm.platform_regions.get_region_by_slug",
        lambda slug: {
            "slug": "europe",
            "label": "Europe",
            "aws": {"region": "eu-west-1"},
            "gcp": {"location": "EUROPE-WEST1"},
            "azure": {"region": "westeurope"},
        }
        if slug == "europe"
        else None,
    )
    monkeypatch.setattr(
        "app.vm.platform_regions.default_platform_slug",
        lambda: "asia",
    )
    monkeypatch.setattr(
        "app.vm.gcp_zones._project_zones",
        lambda: frozenset({"europe-west1-b", "europe-west1-c"}),
    )

    aws = resolve_vm_compute("AWS", "europe")
    assert aws["compute_target"] == "eu-west-1"
    assert aws["label"] == "Europe"

    gcp = resolve_vm_compute("GCP", "europe")
    assert gcp["compute_target"] == "europe-west1-b"

    az = resolve_vm_compute("Azure", "europe")
    assert az["compute_target"] == "westeurope"
