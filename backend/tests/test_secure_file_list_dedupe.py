"""Secure file list deduplication — primary vault row wins over replica."""

from app.security.routes_security import _dedupe_secure_files_for_list


def test_dedupe_prefers_primary_bucket_and_merges_replication(monkeypatch):
    monkeypatch.setattr(
        "app.security.routes_security.platform_secure_primary_name",
        lambda csp: "zenith-secure-gcp" if csp == "GCP" else "primary",
    )
    rows = [
        {
            "filename": "a.txt",
            "csp": "GCP",
            "cloud_bucket": "zenith-secure-gcp-replica",
            "replication_enabled": False,
        },
        {
            "filename": "a.txt",
            "csp": "GCP",
            "cloud_bucket": "zenith-secure-gcp",
            "replication_enabled": True,
        },
    ]
    out = _dedupe_secure_files_for_list(rows)
    assert len(out) == 1
    assert out[0]["cloud_bucket"] == "zenith-secure-gcp"
    assert out[0]["replication_enabled"] is True


def test_dedupe_keeps_distinct_csps():
    rows = [
        {"filename": "a.txt", "csp": "GCP", "cloud_bucket": "gcp-secure"},
        {"filename": "a.txt", "csp": "AWS", "cloud_bucket": "aws-secure"},
    ]
    out = _dedupe_secure_files_for_list(rows)
    assert len(out) == 2
