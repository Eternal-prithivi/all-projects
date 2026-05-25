"""Reusable training routines for Zenith ML artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier, VotingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

from app.ml.inference import STORAGE_ENSEMBLE_ARTIFACT, WORKLOAD_CLASSIFIER_ARTIFACT
from app.ml.storage_ensemble import FEATURE_NAMES, LABEL_TO_TIER, TIER_TO_LABEL


def _train_xgboost_or_fallback(x_train: np.ndarray, y_train: np.ndarray):
    try:
        from xgboost import XGBClassifier  # type: ignore

        model = XGBClassifier(
            n_estimators=100,
            max_depth=10,
            learning_rate=0.1,
            objective="multi:softprob",
            eval_metric="mlogloss",
            random_state=42,
            n_jobs=1,
        )
        backend = "xgboost"
    except Exception:
        model = GradientBoostingClassifier(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=3,
            random_state=42,
        )
        backend = "sklearn_gradient_boosting_fallback"

    model.fit(x_train, y_train)
    return model, backend


def train_storage_ensemble(
    rows: List[Dict[str, object]],
    artifact_path: Path = STORAGE_ENSEMBLE_ARTIFACT,
    model_version: str = "storage_ensemble_v1.sample_trained",
) -> Dict[str, Any]:
    x_data = np.array([[float(row[name]) for name in FEATURE_NAMES] for row in rows], dtype=float)
    y_data = np.array([TIER_TO_LABEL[str(row["label_tier"])] for row in rows], dtype=int)

    x_train, x_test, y_train, y_test = train_test_split(
        x_data,
        y_data,
        test_size=0.2,
        random_state=42,
        stratify=y_data,
    )

    rf_model = RandomForestClassifier(
        n_estimators=100,
        max_depth=15,
        min_samples_split=10,
        max_features=3,
        random_state=42,
    )
    rf_model.fit(x_train, y_train)

    xgb_model, xgb_backend = _train_xgboost_or_fallback(x_train, y_train)

    rf_accuracy = accuracy_score(y_test, rf_model.predict(x_test))
    xgb_accuracy = accuracy_score(y_test, xgb_model.predict(x_test))

    artifact = {
        "model_version": model_version,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_samples": len(rows),
        "feature_names": list(FEATURE_NAMES),
        "tier_to_label": TIER_TO_LABEL,
        "label_to_tier": LABEL_TO_TIER,
        "random_forest": rf_model,
        "xgboost": xgb_model,
        "xgboost_backend": xgb_backend,
        "test_accuracy": {
            "random_forest": round(float(rf_accuracy), 4),
            "xgboost": round(float(xgb_accuracy), 4),
        },
    }
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, artifact_path)
    return artifact


def build_workload_text_pipeline() -> Pipeline:
    """Heavier VM workload classifier: TF-IDF plus soft-voting text ensemble."""
    classifier = VotingClassifier(
        estimators=[
            (
                "logreg",
                LogisticRegression(
                    max_iter=1000,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
            ("naive_bayes", MultinomialNB(alpha=0.2)),
            (
                "random_forest",
                RandomForestClassifier(
                    n_estimators=200,
                    max_depth=30,
                    class_weight="balanced",
                    random_state=42,
                    n_jobs=1,
                ),
            ),
        ],
        voting="soft",
        weights=[0.45, 0.20, 0.35],
    )
    return Pipeline(
        steps=[
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, lowercase=True, sublinear_tf=True)),
            ("classifier", classifier),
        ]
    )


def train_workload_classifier(
    rows: List[Dict[str, str]],
    artifact_path: Path = WORKLOAD_CLASSIFIER_ARTIFACT,
    model_version: str = "workload_text_ensemble_v2.sample_trained",
) -> Dict[str, Any]:
    descriptions = [row["workload_description"] for row in rows]
    labels = [row["label_cluster"] for row in rows]

    x_train, x_test, y_train, y_test = train_test_split(
        descriptions,
        labels,
        test_size=0.2,
        random_state=42,
        stratify=labels,
    )

    pipeline = build_workload_text_pipeline()
    pipeline.fit(x_train, y_train)
    predictions = pipeline.predict(x_test)
    accuracy = accuracy_score(y_test, predictions)

    artifact = {
        "model_version": model_version,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_samples": len(rows),
        "pipeline": pipeline,
        "labels": sorted(set(labels)),
        "test_accuracy": round(float(accuracy), 4),
        "classification_report": classification_report(y_test, predictions, output_dict=True),
    }
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, artifact_path)
    return artifact
