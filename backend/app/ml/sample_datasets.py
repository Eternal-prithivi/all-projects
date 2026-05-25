"""Deterministic sample datasets for Zenith ML/NLP training.

These datasets are intentionally synthetic because the project does not include
real user/cloud telemetry. They encode the report's expected behavior and give
the ML paths a visible, repeatable training source.
"""

from __future__ import annotations

import csv
from itertools import product
from pathlib import Path
from typing import Dict, Iterable, List

from app.ml.storage_ensemble import (
    FEATURE_NAMES,
    FILE_TYPE_CODES,
    _rule_tier_from_score,
    _training_label,
    _training_rule_score,
    build_storage_features,
)

STORAGE_SIZES_MB = (1, 5, 10, 25, 50, 100, 250, 512, 1024, 2048, 5120, 10240)
STORAGE_PRIORITIES = ("cost", "performance", "balanced")
STORAGE_INTENTS = ("archival", "infrequent", "frequent")
KEYWORD_BOOSTS = (0, 3, 5, 8)
DATE_FLAGS = (False, True)

FILENAME_PATTERNS = {
    "archive": ("backup", "archive", "export", "bundle"),
    "data": ("events", "dataset", "ledger", "analytics"),
    "media": ("training-video", "product-photo", "raw-footage", "thumbnail"),
    "document": ("proposal", "invoice", "notes", "report"),
}

WORKLOAD_TEMPLATES = {
    "general": [
        "Host a React and FastAPI web app with moderate HTTP traffic",
        "Run an internal dashboard API with cron jobs and simple background tasks",
        "Deploy a Node.js service for user signups, REST endpoints, and notifications",
        "Serve a Django admin portal with lightweight PostgreSQL reads",
        "Run Docker microservices for a student project demo environment",
        "Host a Flask API for CRUD operations and file metadata",
    ],
    "storage": [
        "Run PostgreSQL with nightly backups and 800GB of customer data",
        "Store object files in S3 compatible storage with large archive exports",
        "Operate MongoDB analytics collections with heavy read/write data access",
        "Manage backup ingestion, log retention, and cold archive movement",
        "Serve a document repository with 2TB files and frequent metadata scans",
        "Run MySQL reporting tables with durable disk and snapshot requirements",
    ],
    "memory": [
        "Run Redis cache with high concurrency and low latency session reads",
        "Host an in-memory leaderboard requiring 64GB RAM and fast key lookups",
        "Operate Memcached for API acceleration with strict response latency",
        "Process large joins in memory for a business intelligence dashboard",
        "Keep hot recommendation features in RAM for quick retrieval",
        "Run a memory-heavy Java service with large heap and frequent allocations",
    ],
    "performance": [
        "Run high CPU video encoding jobs with many cores and parallel processing",
        "Serve a latency critical trading simulator requiring high compute throughput",
        "Compile large projects and run parallel test suites every hour",
        "Execute CPU intensive simulations with high network throughput",
        "Process real-time events with strict performance and burst handling",
        "Run a compute-heavy image processing pipeline for production traffic",
    ],
    "ai_ml": [
        "Train a TensorFlow model with GPU acceleration and CUDA support",
        "Run PyTorch deep learning inference for image classification",
        "Execute XGBoost notebook experiments with pandas and scikit-learn",
        "Train neural network models on a CIFAR-10 dataset with 32GB RAM",
        "Run Jupyter machine learning pipelines for feature engineering",
        "Serve an AI inference API with GPU and batch prediction workloads",
    ],
}

WORKLOAD_MODIFIERS = (
    "production priority",
    "low budget student demo",
    "needs autoscaling",
    "with daily monitoring",
    "urgent launch this week",
)


def generate_storage_training_rows(repeats: int = 3) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    file_types = tuple(FILE_TYPE_CODES.keys())

    for repeat, (file_type, file_size_mb, priority, intent, keyword_boost, has_date) in product(
        range(max(repeats, 1)),
        product(file_types, STORAGE_SIZES_MB, STORAGE_PRIORITIES, STORAGE_INTENTS, KEYWORD_BOOSTS, DATE_FLAGS),
    ):
        size_multiplier = 1.0 + (repeat * 0.07)
        adjusted_size = round(float(file_size_mb) * size_multiplier, 2)
        pattern = FILENAME_PATTERNS[file_type][(keyword_boost + repeat) % len(FILENAME_PATTERNS[file_type])]
        date_part = "_2026-05-24" if has_date else ""
        extension = {
            "archive": ".zip",
            "data": ".csv",
            "media": ".mp4",
            "document": ".pdf",
        }[file_type]
        filename = f"{pattern}{date_part}_r{repeat}{extension}"

        rule_score = _training_rule_score(
            file_size_mb=adjusted_size,
            file_type=file_type,
            priority=priority,
            intent=intent,
            keyword_boost=keyword_boost,
            has_date_pattern=has_date,
        )
        rule_tier = _rule_tier_from_score(rule_score)
        label_tier = _training_label(
            file_size_mb=adjusted_size,
            file_type=file_type,
            priority=priority,
            intent=intent,
            rule_score=rule_score,
        )
        features = build_storage_features(
            filename=filename,
            file_size_mb=adjusted_size,
            file_type=file_type,
            user_priority=priority,
            user_intent=intent,
            rule_score=rule_score,
            rule_tier=rule_tier,
        )

        rows.append(
            {
                "filename": filename,
                "file_size_mb": adjusted_size,
                "file_type": file_type,
                "user_priority": priority,
                "user_intent": intent,
                "keyword_boost": keyword_boost,
                "has_date_pattern": has_date,
                "rule_score": rule_score,
                "rule_tier": rule_tier,
                "label_tier": label_tier,
                **features,
            }
        )

    return rows


def generate_workload_training_rows(repeats: int = 4) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for cluster, templates in WORKLOAD_TEMPLATES.items():
        for repeat in range(max(repeats, 1)):
            modifier = WORKLOAD_MODIFIERS[repeat % len(WORKLOAD_MODIFIERS)]
            for template in templates:
                rows.append(
                    {
                        "workload_description": f"{template}; {modifier}.",
                        "label_cluster": cluster,
                    }
                )
    return rows


def write_csv(path: Path, rows: Iterable[Dict[str, object]], fieldnames: List[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})
            count += 1
    return count


STORAGE_DATASET_FIELDS = [
    "filename",
    "file_size_mb",
    "file_type",
    "user_priority",
    "user_intent",
    "keyword_boost",
    "has_date_pattern",
    "rule_score",
    "rule_tier",
    "label_tier",
    *FEATURE_NAMES,
]

WORKLOAD_DATASET_FIELDS = ["workload_description", "label_cluster"]
