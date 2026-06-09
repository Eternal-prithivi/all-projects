"""Generate sample datasets and train Zenith's local ML artifacts.

This script is intentionally free-tier/local. It does not need cloud data and
does not contact external services. It creates:
- app/ml/datasets/storage_tier_training.csv
- app/ml/datasets/workload_classification_training.csv
- app/ml/artifacts/storage_ensemble.joblib
- app/ml/artifacts/workload_classifier.joblib
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.ml.inference import (
    DATASET_DIR,
    STORAGE_ENSEMBLE_ARTIFACT,
    WORKLOAD_CLASSIFIER_ARTIFACT,
    clear_model_artifact_cache,
)
from app.ml.sample_datasets import (
    STORAGE_DATASET_FIELDS,
    WORKLOAD_DATASET_FIELDS,
    generate_storage_edge_case_rows,
    generate_storage_training_rows,
    generate_workload_training_rows,
    write_csv,
)
from app.ml.training import train_storage_ensemble, train_workload_classifier


def main() -> None:
    storage_rows = generate_storage_training_rows(repeats=4) + generate_storage_edge_case_rows()
    workload_rows = generate_workload_training_rows(repeats=20)

    storage_count = write_csv(
        DATASET_DIR / "storage_tier_training.csv",
        storage_rows,
        STORAGE_DATASET_FIELDS,
    )
    workload_count = write_csv(
        DATASET_DIR / "workload_classification_training.csv",
        workload_rows,
        WORKLOAD_DATASET_FIELDS,
    )

    storage_artifact = train_storage_ensemble(storage_rows)
    workload_artifact = train_workload_classifier(workload_rows)
    clear_model_artifact_cache()

    summary = {
        "datasets": {
            "storage_tier_training.csv": storage_count,
            "workload_classification_training.csv": workload_count,
        },
        "artifacts": {
            "storage_ensemble.joblib": {
                "path": str(STORAGE_ENSEMBLE_ARTIFACT),
                "training_samples": storage_artifact["training_samples"],
                "xgboost_backend": storage_artifact["xgboost_backend"],
                "test_accuracy": storage_artifact["test_accuracy"],
            },
            "workload_classifier.joblib": {
                "path": str(WORKLOAD_CLASSIFIER_ARTIFACT),
                "training_samples": workload_artifact["training_samples"],
                "test_accuracy": workload_artifact["test_accuracy"],
            },
        },
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
