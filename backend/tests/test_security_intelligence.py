from datetime import datetime, timedelta, timezone

from app.security.security_intelligence import (
    build_security_cost_preview,
    build_security_file_insight,
    compute_vault_health,
    compute_vault_savings_summary,
)


def test_build_security_cost_preview_replication():
    preview = build_security_cost_preview(
        file_size_mb=1024,
        encryption_method="server-side",
        selected_csp="AWS",
        enable_replication=True,
    )
    assert preview["base_monthly_usd"] > 0
    assert preview["replication_monthly_usd"] is not None
    assert preview["total_monthly_usd"] > preview["base_monthly_usd"]
    assert len(preview["cross_cloud"]) == 3


def test_build_security_file_insight_awaiting():
    now = datetime.now(timezone.utc)
    insight = build_security_file_insight(
        {
            "awaiting_encryption_choice": True,
            "encryption_status": "awaiting_choice",
            "is_sensitive": True,
            "upload_date": now,
        }
    )
    assert insight["status"] == "action"
    assert insight["next_action"] == "encrypt_now"


def test_build_security_file_insight_stale():
    now = datetime.now(timezone.utc)
    insight = build_security_file_insight(
        {
            "is_encrypted": True,
            "upload_date": now - timedelta(days=100),
            "last_accessed_at": now - timedelta(days=95),
            "vault_status": "active",
        },
        stale_threshold_days=90,
        now=now,
    )
    assert insight["next_action"] == "review_stale"


def test_compute_vault_health_empty():
    health = compute_vault_health([])
    assert health["grade"] == "A"
    assert health["score"] == 100


def test_compute_vault_health_with_issues():
    now = datetime.now(timezone.utc)
    files = [
        {"awaiting_encryption_choice": True, "upload_date": now},
        {
            "is_sensitive": True,
            "is_encrypted": True,
            "upload_date": now,
            "size_bytes": 1024 ** 3,
            "csp": "AWS",
        },
    ]
    health = compute_vault_health(files, username="testuser")
    assert health["factors"]["awaiting_encryption"] == 1
    assert health["score"] < 100


def test_compute_vault_savings_summary():
    summary = compute_vault_savings_summary(
        [{"size_bytes": 1024 ** 3, "csp": "AWS", "upload_date": datetime.now(timezone.utc)}]
    )
    assert summary["files_tracked"] == 1
    assert summary["estimated_monthly_cost_usd"] > 0
