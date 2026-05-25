"""Model artifact loading helpers for local/free-tier inference.

The project can run without persisted artifacts by falling back to deterministic
report-aligned rules. When sample-trained artifacts exist, these helpers load
them once and let inference use the trained models.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

from app.utils.logger import setup_logger

logger = setup_logger(__name__)

ML_DIR = Path(__file__).resolve().parent
ARTIFACT_DIR = ML_DIR / "artifacts"
DATASET_DIR = ML_DIR / "datasets"

STORAGE_ENSEMBLE_ARTIFACT = ARTIFACT_DIR / "storage_ensemble.joblib"
WORKLOAD_CLASSIFIER_ARTIFACT = ARTIFACT_DIR / "workload_classifier.joblib"


def _load_joblib(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None

    try:
        import joblib

        artifact = joblib.load(path)
        if isinstance(artifact, dict):
            return artifact
        logger.warning(f"Model artifact at {path} was not a dictionary")
    except Exception as exc:
        logger.warning(f"Failed to load model artifact at {path}: {exc}")

    return None


@lru_cache(maxsize=1)
def load_storage_ensemble_artifact() -> Optional[Dict[str, Any]]:
    return _load_joblib(STORAGE_ENSEMBLE_ARTIFACT)


@lru_cache(maxsize=1)
def load_workload_classifier_artifact() -> Optional[Dict[str, Any]]:
    return _load_joblib(WORKLOAD_CLASSIFIER_ARTIFACT)


def clear_model_artifact_cache() -> None:
    load_storage_ensemble_artifact.cache_clear()
    load_workload_classifier_artifact.cache_clear()
