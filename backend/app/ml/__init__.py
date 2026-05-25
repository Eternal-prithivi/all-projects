"""ML prediction contracts and acceptance metrics.

Keep this package initializer free of database side effects. Repository helpers
import MongoDB, so routes should import them explicitly when persistence is
needed.
"""

from app.ml.models import (
    ExpertVote,
    MLPredictionCreate,
    MLPredictionRecord,
    WorkloadClassificationCreate,
    WorkloadClassificationRecord,
)

__all__ = [
    "ExpertVote",
    "MLPredictionCreate",
    "MLPredictionRecord",
    "WorkloadClassificationCreate",
    "WorkloadClassificationRecord",
]
