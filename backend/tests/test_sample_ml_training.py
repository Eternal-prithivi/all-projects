"""Tests for visible sample datasets used by local ML training."""

from app.ml.sample_datasets import (
    generate_storage_training_rows,
    generate_workload_training_rows,
)


def test_storage_sample_dataset_covers_all_tiers_and_features():
    rows = generate_storage_training_rows(repeats=1)
    labels = {row["label_tier"] for row in rows}

    assert {"hot", "warm", "cold"}.issubset(labels)
    assert len(rows) > 500
    assert all("rule_score" in row and "rule_tier_numeric" in row for row in rows[:10])


def test_workload_sample_dataset_covers_all_report_clusters():
    rows = generate_workload_training_rows(repeats=1)
    labels = {row["label_cluster"] for row in rows}

    assert labels == {"general", "storage", "memory", "performance", "ai_ml"}
    assert len(rows) >= 30
